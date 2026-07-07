// ── src/controller/persistence.js ─────────────────────────────────────────────
// p8 Step 7b — Persistencia local + cloud sync + Supabase auth. UN módulo porque
// save↔cloud es un ciclo real (_cloudLoad llama saves; saves llaman _cloudSave).
// Leaf de controller (sin back-edges a dispatchers). _sbInit/_renderAfterSync se
// quedan en main.js (llaman dispatchers) → 7e. _sb (cliente) vía STATE BRIDGE
// (lo crea _sbInit en main.js). normTitle (util general) vía globalThis bridge.
// Roster (watchlist/watched/…) vía bridge.

import { FESTIVAL_CONFIG } from '../config.js';
import { closeAuthSheet } from '../view/sheets.js';
import { showToast } from '../view/feedback.js';
import { state } from '../state/state.js';
import { storage } from '../storage/storage.js';
import { t } from '../i18n/i18n.js';

// Debounce timer de _cloudSave — module-local (solo _cloudSave lo usa).
let _cloudSaveTimer=null;
// Canal Realtime del sync del plan EN VIVO (F0.5) — module-local.
let _planChannel=null, _planChannelKey=null, _planRerenderCb=null;

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
    // Computar todos los valores hidratados (puro, sin escribir)
    const _wl = new Set([...storage.getWatchlist()].map(normTitle));
    const _wd = new Set([...storage.getWatched()].map(normTitle));
    const _pr = new Set([...storage.getPrioritized()].map(normTitle));
    const _ratings = {...state.get('filmRatings'), ...storage.getFilmRatings()};
    const _av = storage.getAvailability();
    const _newAv = {...state.get('availability')};
    DAY_KEYS.forEach(d=>{ if(_av[d]) _newAv[d]=_av[d]; });
    let _sa = storage.getSavedAgenda();
    if(_sa && _sa.schedule){
      // Normalizar venues viejos (ej: 'CC Bocagrande' → 'Plaza Bocagrande')
      _sa = {..._sa, schedule: _sa.schedule.map(s => s.venue ? {...s, venue: s.venue.replace(/CC Bocagrande/g,'Plaza Bocagrande')} : s)};
    }
    state.batchUpdate({
      watchlist: _wl,
      watched: _wd,
      prioritized: _pr,
      filmRatings: _ratings,
      availability: _newAv,
      savedAgenda: _sa,
      lastRemovedSlots: storage.getLastRemovedSlots(),
      filmDelays: storage.getFilmDelays(),
      filmDelaysHistory: storage.getFilmDelaysHistory(),
    });
    // Heal: garantiza que todo lo que está en prioritized esté en watchlist
    state.update('watchlist', s => { let n=s; prioritized.forEach(t=>{ if(!n.has(t)) n=state._addToSet(n,t); }); return n; });
    saveWL();
    const _v = storage.getViewmodes(); if(_v.miPlan) miPlanViewMode=_v.miPlan; if(_v.intereses) interesesViewMode=_v.intereses;
  }catch(e){console.warn('[loadState] failed',e);}
}

export function _cloudSave(){
  if(!_sb||!_sbUser||_sbUser.is_anonymous) return; // anon = solo identidad de reportes, no sync de plan
  // Hay mutación local pendiente de subir → dirty. El boot-load no debe pisarla.
  storage.setCloudDirty(true);
  clearTimeout(_cloudSaveTimer);
  _cloudSaveTimer=setTimeout(async()=>{
    try{
      const _ts=new Date().toISOString();
      await _sb.from('user_festival_state').upsert({
        user_id:_sbUser.id,
        festival_id:_activeFestId,
        watchlist:[...watchlist],
        watched:[...watched],
        ratings:filmRatings,
        saved_agenda:savedAgenda,
        prioritized:[...prioritized],
        availability,
        updated_at:_ts
      },{onConflict:'user_id,festival_id'});
      // Éxito: este dispositivo está al día con _ts; ya no hay pendientes.
      storage.setCloudSyncedAt(_ts);
      storage.setCloudDirty(false);
      _sbShowSyncDot('ok');
    }catch(e){
      console.warn('Cloud save error:',e);
      _sbShowSyncDot('err'); // queda dirty → reintenta en la próxima mutación/boot
    }
  },2000);
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
  try{
    const{data,error}=await _sb
      .from('user_festival_state')
      .select('*')
      .eq('user_id',_sbUser.id)
      .eq('festival_id',_activeFestId)
      .single();
    if(error||!data) return false; // Sin datos en nube — conservar local (y, en sign-in, subir)
    if(_cloudGuardSkip({guard:_guard, dirty:storage.getCloudDirty(), cloudUpdatedAt:data.updated_at, localSyncedAt:storage.getCloudSyncedAt()})) return false;
    // Boot/sign-in: aplicar solo campos NO vacíos (defensivo — una fila incompleta
    // no debe borrar datos locales). El Realtime usa wholesale (ver _applyCloudRow).
    return _applyCloudRow(data, {wholesale:false});
  }catch(e){console.warn('Cloud load error:',e);return false;}
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
  _planChannel=_sb.channel('ufs-'+key)
    .on('postgres_changes',
      { event:'*', schema:'public', table:'user_festival_state', filter:'user_id=eq.'+uid },
      (payload)=>{
        const row=payload.new;
        if(!row||row.festival_id!==fest) return; // otro festival del mismo usuario
        if(!_shouldApplyRealtimeRow({rowUpdatedAt:row.updated_at, localSyncedAt:storage.getCloudSyncedAt(), dirty:storage.getCloudDirty()})) return;
        if(_applyCloudRow(row,{wholesale:true})) _planRerender();
      })
    .subscribe();
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

export function _sbShowSyncDot(state){
  const dot=document.getElementById('sync-dot');
  if(!dot) return;
  dot.className='sync-dot sync-'+state;
  if(state==='ok') setTimeout(()=>{dot.className='sync-dot';},3000);
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

export async function _scheduleNotifications(){
  if(!window.Capacitor?.isNativePlatform()) return;
  try{
    const {LocalNotifications}=window.Capacitor.Plugins;
    // Solicitar permiso si no se tiene
    const perm=await LocalNotifications.requestPermissions();
    if(perm.display!=='granted') return;
    // Cancelar notificaciones anteriores del plan
    await _cancelNotifications();
    if(!savedAgenda?.schedule?.length) return;
    // Convertir tiempo 12h→24h (mismo helper que exportICS)
    const pad=n=>String(n).padStart(2,'0');
    const to24h=t=>{if(!t)return'12:00';const m=t.match(/(\d+):(\d+)\s*(AM|PM)/i);if(!m)return t;let h=parseInt(m[1]),mn=m[2],ap=m[3].toUpperCase();if(ap==='PM'&&h!==12)h+=12;if(ap==='AM'&&h===12)h=0;return pad(h)+':'+mn;};
    const notifications=[];
    savedAgenda.schedule.forEach((s,i)=>{
      const dateStr=FESTIVAL_DATES[s.day];if(!dateStr) return;
      const [h,min]=to24h(s.time).split(':').map(Number);
      const tz=FESTIVAL_CONFIG[_activeFestId]?.timezoneOffset??-5;
      const start=new Date(`${dateStr}T${pad(h)}:${pad(min)}:00`);
      if(isNaN(start.getTime())) return;
      // 30 min antes
      const notify=new Date(start.getTime()-30*60000);
      if(notify<=new Date()) return; // ya pasó
      notifications.push({
        id:1000+i,
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
    const toCancel=pending.notifications.filter(n=>n.id>=1000&&n.id<2000);
    if(toCancel.length) await LocalNotifications.cancel({notifications:toCancel});
  }catch(e){}
}
