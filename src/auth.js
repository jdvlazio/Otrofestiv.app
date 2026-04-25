// ══ Auth — Supabase, cloud sync, auth sheet ══
// SOURCE: index.html L2492-2710

async function _sbSignIn(email){
  if(!_sb) return {error:'no client'};
  const{error}=await _sb.auth.signInWithOtp({
    email,
    options:{shouldCreateUser:true}
  });
  return{error};
}

// Sign out
async function _sbSignOut(){
  if(!_sb) return;
  await _sb.auth.signOut();
  _sbUser=null;
  _sbUpdateUI();
}

// Cargar estado del usuario desde la nube
async function _cloudLoad(){
  if(!_sb||!_sbUser) return;
  try{
    const{data,error}=await _sb
      .from('user_festival_state')
      .select('*')
      .eq('user_id',_sbUser.id)
      .eq('festival_id',_activeFestId)
      .single();
    if(error||!data) return; // Sin datos en nube — conservar local
    // Aplicar datos de la nube (tienen prioridad sobre localStorage)
    if(data.watchlist?.length) watchlist=new Set(data.watchlist);
    if(data.watched?.length) watched=new Set(data.watched);
    if(data.ratings&&Object.keys(data.ratings).length) Object.assign(filmRatings,data.ratings);
    if(data.saved_agenda) savedAgenda=data.saved_agenda;
    if(data.prioritized?.length) prioritized=new Set(data.prioritized);
    if(data.availability&&Object.keys(data.availability).length){
      DAY_KEYS.forEach(d=>{if(data.availability[d]) availability[d]=data.availability[d];});
    }
    // Sincronizar también en local
    saveWL();saveWatched();savePrio();saveSavedAgenda();saveAV();
  }catch(e){console.warn('Cloud load error:',e);}
}

// Guardar estado en la nube (debounced 2s)
let _cloudSaveTimer=null;
function _cloudSave(){
  if(!_sb||!_sbUser) return;
  clearTimeout(_cloudSaveTimer);
  _cloudSaveTimer=setTimeout(async()=>{
    try{
      await _sb.from('user_festival_state').upsert({
        user_id:_sbUser.id,
        festival_id:_activeFestId,
        watchlist:[...watchlist],
        watched:[...watched],
        ratings:filmRatings,
        saved_agenda:savedAgenda,
        prioritized:[...prioritized],
        availability,
        updated_at:new Date().toISOString()
      },{onConflict:'user_id,festival_id'});
      _sbShowSyncDot('ok');
    }catch(e){
      console.warn('Cloud save error:',e);
      _sbShowSyncDot('err');
    }
  },2000);
}

// UI helpers
function _sbUpdateUI(){
  const btn=document.getElementById('auth-btn');
  const av=document.getElementById('auth-avatar');
  if(!btn) return;
  if(_sbUser){
    const initial=(_sbUser.email||'?')[0].toUpperCase();
    if(av) av.textContent=initial;
    btn.title=_sbUser.email;
    btn.classList.add('signed-in');
  } else {
    if(av) av.textContent='';
    btn.title='Sincronizar entre dispositivos';
    btn.classList.remove('signed-in');
  }
}
function _sbShowSyncDot(state){
  const dot=document.getElementById('sync-dot');
  if(!dot) return;
  dot.className='sync-dot sync-'+state;
  if(state==='ok') setTimeout(()=>{dot.className='sync-dot';},3000);
}
function _renderAfterSync(){
  // Re-renderiza la vista activa después de cargar datos de la nube
  if(typeof showDayView==='function') showDayView();
  if(typeof _renderProgramaContent==='function') _renderProgramaContent();
}

// Abrir sheet de login
function openAuthSheet(){
  if(_sbUser){_showSignedInSheet();return;}
  const s=document.getElementById('auth-sheet');
  if(s){s.style.display='flex';setTimeout(()=>s.classList.add('open'),10);}
}
function closeAuthSheet(){
  const s=document.getElementById('auth-sheet');
  if(s){s.classList.remove('open');setTimeout(()=>s.style.display='none',300);}
}
async function submitAuthEmail(){
  const inp=document.getElementById('auth-email-inp');
  const btn=document.getElementById('auth-send-btn');
  const msg=document.getElementById('auth-msg');
  const email=(inp?.value||'').trim();
  if(!email||!email.includes('@')){msg.textContent='Ingresa un email válido.';return;}
  btn.disabled=true;btn.textContent='Enviando…';
  const{error}=await _sbSignIn(email);
  if(error){
    msg.textContent='Error al enviar. Intenta de nuevo.';
    btn.disabled=false;btn.textContent='Enviar código';
  } else {
    msg.textContent='';
    // Guardar email para verificación OTP
    document.getElementById('auth-otp-email').textContent=email;
    document.getElementById('auth-sheet-step1').style.display='none';
    document.getElementById('auth-sheet-step2').style.display='block';
    setTimeout(()=>document.getElementById('auth-otp-inp')?.focus(),300);
  }
}

async function submitOTP(){
  const email=document.getElementById('auth-otp-email').textContent;
  const token=(document.getElementById('auth-otp-inp')?.value||'').trim();
  const btn=document.getElementById('auth-otp-btn');
  const msg=document.getElementById('auth-otp-msg');
  if(!token||token.length<6){msg.textContent='Ingresa el código de 6 dígitos.';return;}
  btn.disabled=true;btn.textContent='Verificando…';
  try{
    const{data,error}=await _sb.auth.verifyOtp({email,token,type:'email'});
    if(error){
      msg.textContent='Código incorrecto o expirado. Intenta de nuevo.';
      btn.disabled=false;btn.textContent='Confirmar';
    } else {
      closeAuthSheet();
      // Reset steps
      document.getElementById('auth-sheet-step1').style.display='block';
      document.getElementById('auth-sheet-step2').style.display='none';
      document.getElementById('auth-otp-inp').value='';
    }
  }catch(e){
    msg.textContent='Error. Intenta de nuevo.';
    btn.disabled=false;btn.textContent='Confirmar';
  }
}
function _showSignedInSheet(){
  const s=document.getElementById('auth-sheet');
  document.getElementById('auth-sheet-step1').style.display='none';
  document.getElementById('auth-sheet-step2').style.display='none';
  document.getElementById('auth-sheet-step3').style.display='block';
  document.getElementById('auth-signed-email').textContent=_sbUser?.email||'';
  if(s){s.style.display='flex';setTimeout(()=>s.classList.add('open'),10);}
}
async function signOutAndClose(){
  await _sbSignOut();
  closeAuthSheet();
  // Reset steps
  document.getElementById('auth-sheet-step1').style.display='block';
  document.getElementById('auth-sheet-step3').style.display='none';
}
const LB_SVG=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="13" height="13" style="display:block;flex-shrink:0"><rect width="64" height="64" rx="9" fill="#2C3440"/><circle cx="21" cy="32" r="12" fill="#00B020" opacity=".9"/><circle cx="32" cy="32" r="12" fill="#3CBEDB" opacity=".85"/><circle cx="43" cy="32" r="12" fill="#FF8000" opacity=".9"/></svg>`;

/* ── Lucide Icons — sistema de íconos Otrofestiv ── */
const ICONS={
  star:     `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>`,
  starFill: `<svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>`,
  heart:    `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>`,
  heartFill:`<svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>`,
  x:        `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
  check:    `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="display:block;flex-shrink:0"><polyline points="20 6 9 17 4 12"/></svg>`,
  undo:     `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:block;flex-shrink:0"><path d="M2.5 9C3.5 5.5 6.8 3 12 3a9 9 0 1 1-9 9"/><polyline points="2 3 2 9 8 9"/></svg>`,
  switch:   `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>`,
  plus:     `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>`,
  clock:    `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`,
  play:     `<svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="5 3 19 12 5 21 5 3"/></svg>`,
  calendar: `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>`,
  alert:    `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
  chevronR: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>`,
  chevronD: `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>`,
  share:    `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><polyline points="16 6 12 2 8 6"/><line x1="12" y1="2" x2="12" y2="15"/></svg>`,
  image:    `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>`,
  search:   `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`,
  pin:      `<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>`,
};

// Festival date map

// ═══════════════════════════════════════════════════════════════
// 3 · CONFIGURACIÓN
//     FESTIVAL_DATES, VENUES, PRIO_LIMIT, constantes Mi Plan
// ═══════════════════════════════════════════════════════════════
let FESTIVAL_DATES={
  'Martes':'2026-04-14','Miércoles':'2026-04-15','Jueves':'2026-04-16',
  'Viernes':'2026-04-17','Sábado':'2026-04-18','Domingo':'2026-04-19'
};
// Fin del festival — última función del Domingo + margen
let FESTIVAL_END=new Date('2026-04-20T02:00:00');
function festivalEnded(){ return simNow()>FESTIVAL_END; }

// Check if a screening has passed (with 10 min grace)

// ═══════════════════════════════════════════════════════════════
// 4 · UTILIDADES
//     Funciones puras: fechas, tiempo, conflictos, normalización
// ═══════════════════════════════════════════════════════════════
function screeningPassed(s){
  if(festivalEnded()) return false; // festival terminado — todo vuelve a plena opacidad
  const dateStr=FESTIVAL_DATES[s.day];
  if(!dateStr) return false;
  const screeningTime=new Date(`${dateStr}T${s.time}:00`);
  screeningTime.setMinutes(screeningTime.getMinutes()+10); // 10 min grace
  return simNow()>screeningTime;
}
