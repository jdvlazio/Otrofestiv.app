// ── src/controller/persistence.js ─────────────────────────────────────────────
// p8 Step 7b — Persistencia local + cloud sync + Supabase auth. UN módulo porque
// save↔cloud es un ciclo real (_cloudLoad llama saves; saves llaman _cloudSave).
// Leaf de controller (sin back-edges a dispatchers). _sbInit/_renderAfterSync se
// quedan en main.js (llaman dispatchers) → 7e. _sb (cliente) vía STATE BRIDGE
// (lo crea _sbInit en main.js). normTitle (util general) vía globalThis bridge.
// Roster (watchlist/watched/…) vía bridge.

import { FESTIVAL_CONFIG } from '../config.js';
import { report } from '../telemetry.js';
import { deriveHydrate } from '../state/festival-context.js';
import { closeAuthSheet } from '../view/sheets.js';
import { showToast } from '../view/feedback.js';
import { state } from '../state/state.js';
import { storage } from '../storage/storage.js';
import { t } from '../i18n/i18n.js';

// Debounce timer de _cloudSave — module-local (solo _cloudSave lo usa).
let _cloudSaveTimer=null;
// Canal Realtime del sync del plan EN VIVO (F0.5) — module-local.
// _planLive: el canal está SUBSCRIBED → alimenta el estado base del sync-dot.
let _planChannel=null, _planChannelKey=null, _planRerenderCb=null, _planLive=false;

export function saveWL(){ storage.setWatchlist(watchlist); _cloudSave(); }

export function saveWatched(){ storage.setWatched(watched); _cloudSave(); }

export function saveRating(title,rating){
  state.update('filmRatings', o => rating>0 ? {...o, [title]: rating} : state._omit(o, title));
  storage.setFilmRatings(filmRatings); _cloudSave();
}

export function saveAV(){ storage.setAvailability(availability); _cloudSave(); }

export function saveSavedAgenda(){ storage.setSavedAgenda(savedAgenda); _cloudSave(); _scheduleNotifications(); }

export function savePrio(){ storage.setPrioritized(prioritized); _cloudSave(); }

export function saveLastSlot(){ storage.setLastRemovedSlots(lastRemovedSlots); }

export function saveDelays(){ storage.setFilmDelays(filmDelays); storage.setFilmDelaysHistory(filmDelaysHistory); }

export function saveState(...keys){
  const all=!keys.length;
  if(all||keys.includes('wl'))      saveWL();
  if(all||keys.includes('watched')) saveWatched();
  if(all||keys.includes('prio'))    savePrio();
  if(all||keys.includes('agenda'))  saveSavedAgenda();
  if(all||keys.includes('av'))      saveAV();
  if(all||keys.includes('lastslot'))saveLastSlot();
}

export function loadState(){
  try{
    // Los 9 estados por-festival se hidratan DERIVADOS de FESTIVAL_STATE
    // (festival-context.js): cada hydrate captura su lógica fina (normTitle en los
    // Sets, merge de ratings, merge por-día de availability, normalización de
    // venues). batchUpdate atómico. Fuente única con el clear de batch1.
    state.batchUpdate(deriveHydrate());
    // Heal: garantiza que todo lo que está en prioritized esté en watchlist
    state.update('watchlist', s => { let n=s; prioritized.forEach(t=>{ if(!n.has(t)) n=state._addToSet(n,t); }); return n; });
    saveWL();
    const _v = storage.getViewmodes(); if(_v.miPlan) miPlanViewMode=_v.miPlan; if(_v.intereses) interesesViewMode=_v.intereses;
  }catch(e){report(e,'loadState');}
}

export function _cloudSave(){
  if(!_sb||!_sbUser||_sbUser.is_anonymous) return; // anon = solo identidad de reportes, no sync de plan
  // Hay mutación local pendiente de subir → dirty. El boot-load no debe pisarla.
  storage.setCloudDirty(true);
  _sbShowSyncDot('dirty'); // ámbar mientras hay cambio local sin subir
  clearTimeout(_cloudSaveTimer);
  _cloudSaveTimer=setTimeout(_doCloudSave,2000);
}

// _doCloudSave — sube el plan del festival ACTIVO AL MOMENTO de invocarse. El
// festival_id y los arrays (watchlist/…) se capturan síncronamente al construir el
// objeto (antes del primer await) → si se llama con los globals correctos, sube esos.
async function _doCloudSave(){
  if(!_sb||!_sbUser||_sbUser.is_anonymous) return;
  // Capturar festival + su storageKey ANTES del await. El upsert async puede
  // resolver tras un cambio de festival (garantizado por _flushCloudSave, que
  // dispara esto al tope de loadFestival). Los flags cloud_at/cloud_dirty se
  // escriben al festival QUE SE GUARDÓ (_sk), no al activo actual — si no, se
  // marcaba el festival equivocado y el otro quedaba dirty para siempre.
  const _fest=_activeFestId, _sk=FESTIVAL_CONFIG[_fest]?.storageKey;
  try{
    const _ts=new Date().toISOString();
    await _sb.from('user_festival_state').upsert({
      user_id:_sbUser.id,
      festival_id:_fest,
      watchlist:[...watchlist],
      watched:[...watched],
      ratings:filmRatings,
      saved_agenda:savedAgenda,
      prioritized:[...prioritized],
      availability,
      updated_at:_ts
    },{onConflict:'user_id,festival_id'});
    storage.setCloudSyncedAt(_ts, _sk);
    storage.setCloudDirty(false, _sk);
    if(_fest===_activeFestId) _sbShowSyncDot('ok'); // el dot refleja el festival visible
  }catch(e){
    report(e,'cloudSave');
    if(_fest===_activeFestId) _sbShowSyncDot('err'); // queda dirty → reintenta en la próxima mutación/boot
  }
}

// _flushCloudSave — dispara YA el save pendiente (si hay timer armado) con los
// globals ACTUALES. Se llama al TOPE de loadFestival, antes de swapear el estado:
// así una edición del festival que estás dejando se sube a SU fila y no se pierde
// (el debounce de 2s dispararía luego con los globals del festival nuevo → subía
// una fila redundante y la edición vieja quedaba sin subir). Bug cazado en la
// auditoría de festivales simultáneos.
export function _flushCloudSave(){
  if(!_cloudSaveTimer) return;
  clearTimeout(_cloudSaveTimer); _cloudSaveTimer=null;
  _doCloudSave(); // captura festival_id + arrays actuales (aún los del festival saliente)
}

// _cloudGuardSkip — decisión PURA del boot-load multi-dispositivo. true = NO
// aplicar la nube. Aislada para testear la matriz de conflictos sin Supabase.
//   guard=false (SIGN-IN) → nunca skip: la nube gana (restaurar cuenta).
//   guard=true (BOOT):
//     · dirty (ediciones locales sin subir) → skip (que _cloudSave las empuje).
//     · local ya al día/adelante (cloudUpdatedAt <= localSyncedAt) → skip.
//     · si no hay localSyncedAt (primera vez) o la nube es más nueva → aplicar.
export function _cloudGuardSkip({guard, dirty, cloudUpdatedAt, localSyncedAt}){
  if(!guard) return false;
  if(dirty) return true;
  if(localSyncedAt && cloudUpdatedAt && cloudUpdatedAt<=localSyncedAt) return true;
  return false;
}

// _cloudLoad — baja el plan de la nube. Devuelve true SI aplicó datos de la nube,
//   false si no había fila (nube vacía), hubo error, o el guard saltó. El caller
//   de sign-in usa el false de "nube vacía" para SUBIR el plan local (primera vez).
//   opts.guard=true (BOOT): multi-dispositivo. Ver _cloudGuardSkip.
//   Sin guard (SIGN-IN): la nube gana siempre — el usuario firma para restaurar.
export async function _cloudLoad(opts){
  if(!_sb||!_sbUser) return false;
  const _guard = !!(opts&&opts.guard);
  // Festival al momento de disparar la consulta. Se re-verifica tras el await: si el
  // usuario cambió de festival mientras la nube respondía (red lenta de cine), NO
  // aplicar — si no, el plan del festival A se escribiría bajo las claves del B.
  // Bug cazado en la auditoría de festivales simultáneos (mismo guard que delays-cloud).
  const _fest=_activeFestId;
  try{
    const{data,error}=await _sb
      .from('user_festival_state')
      .select('*')
      .eq('user_id',_sbUser.id)
      .eq('festival_id',_fest)
      .single();
    if(_fest!==_activeFestId) return false; // el usuario cambió de festival durante el await
    if(error||!data) return false; // Sin datos en nube — conservar local (y, en sign-in, subir)
    if(_cloudGuardSkip({guard:_guard, dirty:storage.getCloudDirty(), cloudUpdatedAt:data.updated_at, localSyncedAt:storage.getCloudSyncedAt()})) return false;
    // Boot/sign-in: aplicar solo campos NO vacíos (defensivo — una fila incompleta
    // no debe borrar datos locales). El Realtime usa wholesale (ver _applyCloudRow).
    return _applyCloudRow(data, {wholesale:false});
  }catch(e){report(e,'cloudLoad');return false;}
}

// _applyCloudRow — aplica una fila de user_festival_state al estado local y persiste
//   SIN eco a la nube (no llama saveX → _cloudSave). Deja el dispositivo en sync con
//   data.updated_at.
//   wholesale=false (boot/sign-in): solo pisa campos NO vacíos — una fila incompleta
//     no borra datos locales.
//   wholesale=true (Realtime): la fila es el estado AUTORITATIVO del otro dispositivo
//     → refleja también los borrados (campos que quedaron vacíos).
export function _applyCloudRow(data, opts){
  if(!data) return false;
  const whole=!!(opts&&opts.wholesale);
  const _u={};
  if(whole||data.watchlist?.length) _u.watchlist=new Set(data.watchlist||[]);
  if(whole||data.watched?.length) _u.watched=new Set(data.watched||[]);
  if(whole||(data.ratings&&Object.keys(data.ratings).length)) _u.filmRatings=whole?(data.ratings||{}):{...state.get('filmRatings'),...data.ratings};
  if(whole||data.saved_agenda) _u.savedAgenda=data.saved_agenda||null;
  if(whole||data.prioritized?.length) _u.prioritized=new Set(data.prioritized||[]);
  if(whole||(data.availability&&Object.keys(data.availability).length)){
    if(whole){ _u.availability=data.availability||{}; }
    else { const _newAv={...state.get('availability')}; DAY_KEYS.forEach(d=>{ if(data.availability[d]) _newAv[d]=data.availability[d]; }); _u.availability=_newAv; }
  }
  if(Object.keys(_u).length) state.batchUpdate(_u);
  // Persistir en local (identidad de arrays/Sets vía globals bridgeados).
  storage.setWatchlist(watchlist);storage.setWatched(watched);
  storage.setPrioritized(prioritized);storage.setSavedAgenda(savedAgenda);
  storage.setAvailability(availability);storage.setFilmRatings(filmRatings);
  storage.setCloudSyncedAt(data.updated_at||new Date().toISOString());
  storage.setCloudDirty(false);
  // Reprogramar notificaciones locales del plan aplicado. Idempotente.
  _scheduleNotifications();
  return true;
}

// ── Sync del plan EN VIVO (F0.5) — Realtime de user_festival_state ─────────────
// Base para festival en tiempo real + Apple Watch. Espeja el patrón de delays-cloud.

export function setPlanRerender(cb){ _planRerenderCb=cb; }
function _planRerender(){ if(typeof _planRerenderCb==='function'){ try{ _planRerenderCb(); }catch(e){ /* noop */ } } }

// _shouldApplyRealtimeRow — decisión PURA para un evento Realtime entrante. true =
//   aplicar la fila. Evita el eco de la propia escritura y filas viejas, y NO pisa
//   ediciones locales sin subir (dirty → la nuestra gana y se sube en su debounce).
//   Aislada para testear sin Supabase (como _cloudGuardSkip).
export function _shouldApplyRealtimeRow({rowUpdatedAt, localSyncedAt, dirty}){
  if(!rowUpdatedAt) return false;
  if(dirty) return false;                                        // edición local pendiente → no pisar
  if(localSyncedAt && rowUpdatedAt<=localSyncedAt) return false; // eco propio / fila vieja
  return true;
}

// subscribePlanCloud — (re)suscribe a los cambios del plan del propio usuario. La RLS
//   own_select (auth.uid()=user_id) ya scope las filas al usuario; el handler filtra
//   además por festival activo. Idempotente por (user, festival). Requiere email.
//   Lo llaman loader.js (al cargar festival) y auth.js (INITIAL_SESSION/SIGNED_IN).
export async function subscribePlanCloud(){
  if(!_sb||!_sbUser||_sbUser.is_anonymous||!_activeFestId) return;
  const key=_sbUser.id+'|'+_activeFestId;
  if(_planChannelKey===key && _planChannel) return; // ya suscrito a este (user,festival)
  if(_planChannel){ try{ _sb.removeChannel(_planChannel); }catch(e){ /* noop */ } _planChannel=null; }
  _planChannelKey=key;
  const fest=_activeFestId, uid=_sbUser.id;
  // CRÍTICO: el socket de Realtime necesita el JWT ANTES de suscribir, o la RLS
  // auth.uid()=user_id lo trata como anónimo y entrega CERO eventos (docs: "set the
  // token before connecting to a Channel"). setAuth aquí garantiza el orden aunque el
  // handler de auth aún no haya corrido (carrera de arranque en WKWebView).
  try{ const{data:{session}}=await _sb.auth.getSession(); if(session?.access_token) await _sb.realtime.setAuth(session.access_token); }catch(e){ /* noop */ }
  // CARRERA (mismo patrón que delays-cloud, cazado por T39): si (user,festival)
  // cambió durante el await, abortar — si no, quedaba un canal zombie suscrito y
  // el próximo _sb.channel() del mismo topic fallaba con ".on() after subscribe()".
  if(_planChannelKey!==key) return;
  try{
    const _zombie=_sb.getChannels && _sb.getChannels().find(c=>c.topic==='realtime:ufs-'+key);
    if(_zombie) _sb.removeChannel(_zombie);
  }catch(e){ /* noop */ }
  _planChannel=_sb.channel('ufs-'+key)
    .on('postgres_changes',
      { event:'*', schema:'public', table:'user_festival_state', filter:'user_id=eq.'+uid },
      (payload)=>{
        const row=payload.new;
        if(!row||row.festival_id!==fest) return; // otro festival del mismo usuario
        // El canal es de `fest`; si ese festival ya NO es el activo (el usuario cambió
        // y este canal viejo aún no se tumbó), NO aplicar — _applyCloudRow persiste con
        // las claves del festival ACTIVO → escribiría datos de `fest` bajo otro festival.
        if(fest!==_activeFestId) return;
        if(!_shouldApplyRealtimeRow({rowUpdatedAt:row.updated_at, localSyncedAt:storage.getCloudSyncedAt(), dirty:storage.getCloudDirty()})) return;
        if(_applyCloudRow(row,{wholesale:true})) _planRerender();
      })
    .subscribe((status)=>{
      // Estado del canal → sync-dot: verde fijo solo mientras está SUBSCRIBED.
      // realtime-js reintenta solo tras TIMED_OUT/CLOSED; el punto refleja cada transición.
      _planLive=(status==='SUBSCRIBED');
      _sbShowSyncDot('live');
    });
}

// unsubscribePlanCloud — teardown del canal (sign-out). Apaga el punto.
export function unsubscribePlanCloud(){
  if(_planChannel){ try{ _sb.removeChannel(_planChannel); }catch(e){ /* noop */ } }
  _planChannel=null; _planChannelKey=null; _planLive=false;
  _sbShowSyncDot('live'); // recomputa el base → oculto (sin canal)
}

// _hasLocalPlan — ¿hay algo en el plan local? Anti-clobber: en el primer sign-in NO
//   subimos un plan vacío (evita plantar una fila vacía que pise datos buenos de otro
//   dispositivo — el bug del "dispositivo vacío gana").
export function _hasLocalPlan(){
  return watchlist.size>0 || watched.size>0 || prioritized.size>0 || !!(savedAgenda&&savedAgenda.schedule&&savedAgenda.schedule.length);
}

export async function _sbSignIn(email){
  if(!_sb) return {error:'no client'};
  const{error}=await _sb.auth.signInWithOtp({
    email,
    options:{shouldCreateUser:true}
  });
  return{error};
}

export async function _sbSignOut(){
  if(!_sb) return;
  await _sb.auth.signOut();
  _sbUser=null;
  _sbUpdateUI();
}

export function _sbUpdateUI(){
  const btn=document.getElementById('auth-btn');
  const av=document.getElementById('auth-avatar');
  if(!btn) return;
  if(_sbUser && !_sbUser.is_anonymous){
    const initial=(_sbUser.email||'?')[0].toUpperCase();
    if(av) av.textContent=initial;
    btn.title=_sbUser.email;
    btn.classList.add('signed-in');
  } else {
    if(av) av.textContent='';
    btn.title=t('aria_sincronizar');
    btn.classList.remove('signed-in');
  }
}

// _sbShowSyncDot — punto de estado en el botón de cuenta (F0.5).
//   'live' (verde) = canal Realtime conectado · 'dirty' (ámbar) = cambio local
//   pendiente de subir · 'err' (rojo) = la última subida falló · 'ok' = subida
//   exitosa → vuelve al estado BASE (verde si el canal sigue vivo, oculto si no).
//   _planLive lo mantiene el status callback de subscribePlanCloud.
export function _sbShowSyncDot(state){
  const dot=document.getElementById('sync-dot');
  if(!dot) return;
  if(state==='ok'||state==='live'){ dot.className=_planLive?'sync-dot sync-live':'sync-dot'; return; }
  dot.className='sync-dot sync-'+state;
}

export async function submitAuthEmail(){
  const inp=document.getElementById('auth-email-inp');
  const btn=document.getElementById('auth-send-btn');
  const msg=document.getElementById('auth-msg');
  const email=(inp?.value||'').trim();
  if(!email||!email.includes('@')){msg.textContent=t('auth_email_hint');return;}
  btn.disabled=true;btn.textContent=t('auth_enviando');
  const{error}=await _sbSignIn(email);
  if(error){
    msg.textContent=t('toast_envio_err');
    btn.disabled=false;btn.textContent=t('auth_enviar_cod');
  } else {
    msg.textContent='';
    // Guardar email para verificación OTP
    document.getElementById('auth-otp-email').textContent=email;
    document.getElementById('auth-sheet-step1').style.display='none';
    document.getElementById('auth-sheet-step2').style.display='block';
    setTimeout(()=>document.getElementById('auth-otp-inp')?.focus(),300);
  }
}

export async function submitOTP(){
  const email=document.getElementById('auth-otp-email').textContent;
  const token=(document.getElementById('auth-otp-inp')?.value||'').trim();
  const btn=document.getElementById('auth-otp-btn');
  const msg=document.getElementById('auth-otp-msg');
  if(!token||token.length<6){msg.textContent=t('auth_cod_hint');return;}
  btn.disabled=true;btn.textContent=t('auth_verificando');
  try{
    const{data,error}=await _sb.auth.verifyOtp({email,token,type:'email'});
    if(error){
      msg.textContent=t('toast_cod_mal');
      btn.disabled=false;btn.textContent=t('av_confirmar');
    } else {
      closeAuthSheet();
      // Reset steps
      document.getElementById('auth-sheet-step1').style.display='block';
      document.getElementById('auth-sheet-step2').style.display='none';
      document.getElementById('auth-otp-inp').value='';
    }
  }catch(e){
    msg.textContent=t('toast_algo_mal');
    btn.disabled=false;btn.textContent=t('av_confirmar');
  }
}

export async function deleteAccount(){
  if(!_sb||!_sbUser) return;
  const btn=document.getElementById('auth-delete-btn');
  if(!btn) return;
  // Confirmación inline
  if(!btn.dataset.confirmed){
    btn.dataset.confirmed='1';
    btn.textContent=t('auth_eliminar_confirm');
    btn.style.fontWeight='var(--w-bold)';
    setTimeout(()=>{
      if(btn.dataset.confirmed){
        delete btn.dataset.confirmed;
        btn.textContent=t('auth_eliminar');
        btn.style.fontWeight='';
      }
    },4000);
    return;
  }
  // Segunda pulsación — ejecutar
  btn.disabled=true;
  btn.textContent=t('auth_eliminando');
  try{
    const{error}=await _sb.rpc('delete_user');
    if(error) throw error;
    await _sbSignOut();
    closeAuthSheet();
    showToast(t('toast_cuenta_eliminada'),'info');
  }catch(e){
    btn.disabled=false;
    btn.textContent=t('auth_eliminar');
    delete btn.dataset.confirmed;
    btn.style.fontWeight='';
    showToast(t('toast_error_generico',{msg:e.message}),'err');
  }
}

export async function signOutAndClose(){
  await _sbSignOut();
  closeAuthSheet();
  // Reset steps
  document.getElementById('auth-sheet-step1').style.display='block';
  document.getElementById('auth-sheet-step3').style.display='none';
}

// _notifBase — rango de IDs de notificación PROPIO de cada festival (bloque de 100).
// Antes todos compartían 1000–1999 → guardar el plan de un festival CANCELABA los
// recordatorios del otro (auditoría de festivales simultáneos). El índice en
// FESTIVAL_CONFIG (orden de declaración, estable) da un base determinista y sin
// colisión hasta ~90 festivales. Fuera del wrapper nativo esto es inerte.
const _NOTIF_SLOT=100;
function _notifBase(festId){
  const idx=Object.keys(FESTIVAL_CONFIG).indexOf(festId);
  return 1000+(idx<0?0:idx)*_NOTIF_SLOT; // festId desconocido → base 1000 (defensivo)
}

export async function _scheduleNotifications(){
  if(!window.Capacitor?.isNativePlatform()) return;
  try{
    const {LocalNotifications}=window.Capacitor.Plugins;
    // Solicitar permiso si no se tiene
    const perm=await LocalNotifications.requestPermissions();
    if(perm.display!=='granted') return;
    // Cancelar solo los recordatorios de ESTE festival (no los del otro simultáneo)
    await _cancelNotifications();
    if(!savedAgenda?.schedule?.length) return;
    const _base=_notifBase(_activeFestId);
    // Convertir tiempo 12h→24h (mismo helper que exportICS)
    const pad=n=>String(n).padStart(2,'0');
    const to24h=t=>{if(!t)return'12:00';const m=t.match(/(\d+):(\d+)\s*(AM|PM)/i);if(!m)return t;let h=parseInt(m[1]),mn=m[2],ap=m[3].toUpperCase();if(ap==='PM'&&h!==12)h+=12;if(ap==='AM'&&h===12)h=0;return pad(h)+':'+mn;};
    const notifications=[];
    savedAgenda.schedule.forEach((s,i)=>{
      if(i>=_NOTIF_SLOT) return; // no desbordar al rango del siguiente festival (nunca alcanzable: <60 slots/semana)
      const dateStr=FESTIVAL_DATES[s.day];if(!dateStr) return;
      const [h,min]=to24h(s.time).split(':').map(Number);
      const tz=FESTIVAL_CONFIG[_activeFestId]?.timezoneOffset??-5;
      const start=new Date(`${dateStr}T${pad(h)}:${pad(min)}:00`);
      if(isNaN(start.getTime())) return;
      // 30 min antes
      const notify=new Date(start.getTime()-30*60000);
      if(notify<=new Date()) return; // ya pasó
      notifications.push({
        id:_base+i,
        title:'Otrofestiv',
        body:`${s._title} · ${s.venue||''} · ${s.time}`,
        schedule:{at:notify,allowWhileIdle:true},
        sound:null,extra:null
      });
    });
    if(notifications.length){
      await LocalNotifications.schedule({notifications});
    }
  }catch(e){console.warn('Notifications error:',e);}
}

export async function _cancelNotifications(){
  if(!window.Capacitor?.isNativePlatform()) return;
  try{
    const {LocalNotifications}=window.Capacitor.Plugins;
    const pending=await LocalNotifications.getPending();
    // Solo el rango de ESTE festival — no tocar los recordatorios de otro simultáneo.
    const _base=_notifBase(_activeFestId);
    const toCancel=pending.notifications.filter(n=>n.id>=_base&&n.id<_base+_NOTIF_SLOT);
    if(toCancel.length) await LocalNotifications.cancel({notifications:toCancel});
  }catch(e){}
}
