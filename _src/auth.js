// ══ Auth — Supabase, cloud sync, auth sheet ══
// SOURCE: index.html L2492-2710

function _sbInit(){
  try{
    _sb=supabase.createClient(_SB_URL,_SB_KEY);
    _sb.auth.onAuthStateChange(async(event,session)=>{
      _sbUser=session?.user??null;
      _sbUpdateUI();
      if(event==='SIGNED_IN'){
        await _cloudLoad();
        _renderAfterSync();
      }
      if(event==='SIGNED_OUT') _sbUpdateUI();
    });
    _sb.auth.getSession().then(({data:{session}})=>{
      _sbUser=session?.user??null;
      _sbReady=true;
      _sbUpdateUI();
    });
  }catch(e){console.warn('Supabase init error:',e);}
}

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

// Festival date map

// ═══════════════════════════════════════════════════════════════
// 3 · CONFIGURACIÓN
//     FESTIVAL_DATES, VENUES, PRIO_LIMIT, constantes Mi Plan
// ═══════════════════════════════════════════════════════════════
// Fin del festival — última función del Domingo + margen

// Check if a screening has passed (with 10 min grace)

// ═══════════════════════════════════════════════════════════════
// 4 · UTILIDADES
//     Funciones puras: fechas, tiempo, conflictos, normalización
// ═══════════════════════════════════════════════════════════════
