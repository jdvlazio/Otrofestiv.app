// ── src/controller/auth.js ────────────────────────────────────────────────────────
// p8 Step 7e — Auth-UI Supabase: init + re-render post-sync + display name. _sbReady module-local; _sb vía bridge.

import { _renderProgramaContent } from '../view/programa.js';
import { _cloudLoad, _cloudSave, _sbUpdateUI, subscribePlanCloud, _hasLocalPlan } from './persistence.js';
import { showDayView } from './pipeline.js';
import { t } from '../i18n/i18n.js';

// _sb/_sbUser viven en main.js (backing del STATE BRIDGE); aquí solo el flag interno.
let _sbReady=false;
const _SB_URL='https://eytxrvbnwzxuedbmnnqr.supabase.co';
const _SB_KEY='sb_publishable_-edEGNPRmpsRy7ThJMWtdw_bs6IVZSC';

export function _sbInit(){
  if(typeof supabase==='undefined'){window.addEventListener('load',_sbInit,{once:true});return;}
  try{
    _sb=supabase.createClient(_SB_URL,_SB_KEY);
    _sb.auth.onAuthStateChange(async(event,session)=>{
      _sbUser=session?.user??null;
      // CRÍTICO para el sync en vivo: pasar el JWT al socket de Realtime. supabase-js
      // SOLO auto-setea en SIGNED_IN/TOKEN_REFRESHED, NO en INITIAL_SESSION — y al
      // reabrir la app con sesión persistida (WKWebView) el evento es INITIAL_SESSION.
      // Sin el token, el socket queda anónimo → la RLS auth.uid()=user_id de
      // user_festival_state no matchea → CERO eventos del plan (los retrasos, con
      // USING(true), tapaban el bug). Ref: supabase-js #1304 + docs Realtime Authorization.
      if(session?.access_token) try{ _sb.realtime.setAuth(session.access_token); }catch(e){}
      _sbUpdateUI();
      // Sign-in fresco: la nube gana (guard=false). Si está vacía Y hay plan local,
      // subirlo (primera vez). Anti-clobber: NO subir un plan vacío → un dispositivo
      // vacío no debe plantar una fila vacía que pise datos buenos de otro (F0.5).
      if(event==='SIGNED_IN' && !session?.user?.is_anonymous){
        const _applied=await _cloudLoad();
        if(!_applied && _hasLocalPlan()) _cloudSave();
        subscribePlanCloud();      // sync EN VIVO desde ya
        _renderAfterSync();
      }
      // INITIAL_SESSION (arranque con sesión restaurada): cubre la CARRERA del
      // boot-load — loader.js puede correr antes de que getSession resuelva _sbUser,
      // saltándose la bajada. Acá, con la sesión ya lista, bajamos con guard y
      // suscribimos en vivo. No-op si el festival aún no cargó (loader lo hará).
      if(event==='INITIAL_SESSION' && session?.user && !session.user.is_anonymous){
        await _cloudLoad({guard:true});
        subscribePlanCloud();
        _renderAfterSync();
      }
      if(event==='SIGNED_OUT') _sbUpdateUI();
    });
    _sb.auth.getSession().then(({data:{session}})=>{
      _sbUser=session?.user??null;
      if(session?.access_token) try{ _sb.realtime.setAuth(session.access_token); }catch(e){} // token al socket de Realtime (cold start)
      _sbReady=true;
      _sbUpdateUI();
      // Sin auth anónima (Camino A). La identidad es SOLO la sesión de email (opt-in).
      // Antes, signInAnonymously() abría una sesión de dispositivo que pisaba el slot
      // ÚNICO de sesión del cliente Supabase → clobbeaba la sesión de email → _cloudSave
      // quedaba gateado por is_anonymous y el plan NUNCA sincronizaba (user_festival_state
      // 0 filas pese a usuarios con email). Y en cada arranque sin sesión inundaba
      // /auth/v1/signup → 429 (rate-limit por IP) → 401 en todo REST. El plan/programa
      // funcionan sin sesión (local); el retraso colaborativo requiere firmar con email.
    });
  }catch(e){console.warn('Supabase init error:',e);}
}

export function _renderAfterSync(){
  // Re-renderiza la vista activa después de cargar datos de la nube
  if(typeof showDayView==='function') showDayView();
  if(typeof _renderProgramaContent==='function') _renderProgramaContent();
}

export function _getDisplayName(){
  if(_sbUser){
    const meta=_sbUser.user_metadata||{};
    if(meta.display_name) return meta.display_name;
  }
  const local=localStorage.getItem('otrofestiv_display_name');
  if(local) return local;
  if(_sbUser&&_sbUser.email) return _sbUser.email.split('@')[0];
  return null;
}

export async function _saveDisplayName(name){
  const n=name.trim().slice(0,30);
  if(!n) return;
  localStorage.setItem('otrofestiv_display_name',n);
  if(_sb&&_sbUser){
    try{ await _sb.auth.updateUser({data:{display_name:n}}); }catch(e){console.warn('[auth] updateUser failed',e);}
  }
}

export function _promptDisplayName(onSave){
  const prev=document.getElementById('display-name-sheet');if(prev)prev.remove();
  const el=document.createElement('div');
  el.id='display-name-sheet';
  el.style.cssText='position:fixed;inset:0;background:var(--overlay-70);z-index:9999;display:flex;align-items:flex-end;justify-content:center';
  el.innerHTML=`<div class="auth-sheet-body">
    <div class="sheet-handle-bar"></div>
    <div class="sheet-title">${t('export_como_aparecer')}</div>
    <div class="sheet-subtitle">${t('export_aparecera')}</div>
    <input class="sheet-input" id="dname-input" type="text" maxlength="30" placeholder="${t('auth_nombre')}" autocomplete="name">
    <button class="sheet-cta" id="dname-save">${t('export_guardar_compartir')}</button>
  </div>`;
  document.body.appendChild(el);
  const input=document.getElementById('dname-input');
  input.focus();
  document.getElementById('dname-save').onclick=async()=>{
    const v=input.value.trim();
    if(!v){input.style.borderColor='var(--red)';return;}
    await _saveDisplayName(v);
    el.remove();
    if(onSave) onSave();
  };
  el.addEventListener('click',e=>{if(e.target===el)el.remove();});
}
