// ── src/controller/share.js ───────────────────────────────────────────────────────
// p8 Step 7e — Compartir plan (canvas/imagen) + export ICS.

import { FESTIVAL_CONFIG } from '../config.js';
import { ICONS } from '../view/components.js';
import { DAYS, vcfg } from '../view/helpers.js';
import { showActionModal, showToast } from '../view/feedback.js';
import { _festDate } from '../domain/time.js';
import { screeningPassed } from '../domain/film.js';
import { screensConflict } from '../domain/schedule.js';
import { t } from '../i18n/i18n.js';
import { _getDisplayName, _promptDisplayName } from './auth.js';  // share→auth (sharePlan pide nombre)

export async function sharePlan(){
  if(!savedAgenda||!savedAgenda.schedule||!savedAgenda.schedule.length){
    showToast(t('plan_sin_plan'),'warn');return;
  }
  // Pedir nombre si no existe — solo la primera vez
  if(!_getDisplayName()){
    _promptDisplayName(()=>sharePlan());
    return;
  }
  let canvas,dataUrl;
  try{
    canvas=_buildAgendaCanvas();
    dataUrl=canvas.toDataURL('image/png');
    if(!dataUrl||dataUrl==='data:,') throw new Error('canvas vacío');
  }catch(e){showToast(t('toast_err_imagen'),'err');return;}

  // Web Share API con archivo (iOS Safari 15+, Chrome Android 86+)
  if(navigator.share&&navigator.canShare){
    canvas.toBlob(async blob=>{
      if(!blob){_dlDirect(dataUrl);return;}
      const cfg=FESTIVAL_CONFIG[_activeFestId]||{};
      const fname=`otrofestiv-${(cfg.shortName||'plan').toLowerCase().replace(/\s+/g,'-')}.png`;
      const file=new File([blob],fname,{type:'image/png'});
      if(navigator.canShare({files:[file]})){
        try{
          await navigator.share({files:[file],title:`${t('share_mi_plan')} · ${cfg.name||'Otrofestiv'}`});
          showToast(t('toast_compartido'),'info');
        }catch(e){if(e.name!=='AbortError') _dlDirect(dataUrl);}
      }else{_dlDirect(dataUrl);}
    },'image/png');
  }else{
    // Fallback desktop: descarga directa
    _dlDirect(dataUrl);
  }
}

export function shareAsImage(){
  if(!savedAgenda||!savedAgenda.schedule||!savedAgenda.schedule.length){
    showToast(t('plan_sin_plan'),'warn'); return;
  }

  // ── Guardia de integridad del plan ────────────────────────────
  // Antes de generar la imagen verificamos tres condiciones:
  // 1. Que todas las películas del plan siguen en la watchlist
  // 2. Que no hay conflictos internos entre funciones del plan
  // 3. Que al menos una función no ha pasado ya
  const issues=[];

  // 1. Películas del plan ya no en watchlist
  const notInWL=savedAgenda.schedule.filter(s=>!watchlist.has(s._title));
  if(notInWL.length){
    const names=notInWL.map(s=>s._title.length>20?s._title.slice(0,18)+'…':s._title).join(', ');
    issues.push(t('share_no_intereses',{names}));
  }

  // 2. Conflictos internos entre funciones del plan
  const sched=savedAgenda.schedule;
  const conflicting=[];
  for(let i=0;i<sched.length;i++){
    for(let j=i+1;j<sched.length;j++){
      if(sched[i].day===sched[j].day && screensConflict(sched[i],sched[j])){
        conflicting.push(sched[i]._title);
      }
    }
  }
  if(conflicting.length){
    const names=[...new Set(conflicting)].map(t=>t.length>20?t.slice(0,18)+'…':t).join(', ');
    issues.push(t('share_solapadas',{names}));
  }

  // 3. Plan completamente pasado
  const stillActive=savedAgenda.schedule.some(s=>!screeningPassed(s));
  if(!stillActive) issues.push(t('share_todas_pasaron'));

  // Si hay problemas: mostrar advertencia con opción de continuar igual
  if(issues.length){
    const msg=`<b>${t('plan_desactualizado')}</b><br><br>`
      +issues.map(i=>`• ${i}`).join('<br>')
      +`<br><br>${t('share_compartir_igual_q')}`;
    showActionModal(
      `${ICONS.share} ${t('share_compartir_imagen')}`,
      msg,
      t('share_compartir_igual'),
      ()=>{_generateAndShare();},
      t('share_revisar_plan')
    );
    return;
  }

  _generateAndShare();
}

export function _generateAndShare(){
  let canvas,dataUrl;
  try{
    canvas=_buildAgendaCanvas();
    dataUrl=canvas.toDataURL('image/png');
    if(!dataUrl||dataUrl==='data:,') throw new Error('canvas vacío');
  }catch(e){
    showToast(t('toast_err_imagen'),'err'); return;
  }
  _showImageModal(dataUrl,canvas);
}

export function _buildAgendaCanvas(){
  const cfg=FESTIVAL_CONFIG[_activeFestId]||{};
  const festDays=cfg.days||DAY_KEYS.map(k=>({k,lbl:k.slice(0,3).toUpperCase(),d:parseInt(k.slice(-2))||''}));
  const DAYS=festDays.map(d=>d.k);
  const DS=festDays.map(d=>d.lbl);
  const DN=festDays.map(d=>String(d.d));
  const byDay={};
  DAYS.forEach(d=>{byDay[d]=[];});
  (savedAgenda.schedule||[]).forEach(s=>{if(byDay[s.day])byDay[s.day].push(s);});
  DAYS.forEach(d=>{byDay[d].sort((a,b)=>a.time.localeCompare(b.time));});
  const active=DAYS; // Todos los días del festival — registro completo independiente del plan
  const nC=active.length||1;
  // DPR adaptativo: iOS limita canvas a ~4096px por dimensión — calcular tras conocer nC
  const _W_RAW=48+nC*200-10; // PAD*2 + nC*CW + (nC-1)*CGAP
  const DPR=Math.max(1,Math.min(window.devicePixelRatio||2,3,Math.floor(4096/_W_RAW)));
  const cleanDur=s=>String(s.duration||'').replace(/\s*min\s*min/i,'min').trim();
  const PAD=24,HDR=72,COL_HDR=46,CW=190,CGAP=10,CARD_PAD=12,CARD_R=8,CARD_GAP=8;
  const FONT_T=12,LINE_T=16,MAX_TL=3,CARD_MIN=90;
  const cv0=document.createElement('canvas');
  const c0=cv0.getContext('2d');
  c0.font=`600 ${FONT_T}px system-ui,-apple-system,sans-serif`;
  const cHts={};
  active.forEach(day=>{
    cHts[day]=byDay[day].map(s=>{
      const tl=_measureLines(c0,s._title||'',CW-CARD_PAD*2-6,MAX_TL);
      return Math.max(CARD_PAD+18+4+tl*LINE_T+4+14+CARD_PAD,CARD_MIN);
    });
  });
  const maxColH=active.reduce((mx,day)=>{
    const h=cHts[day].reduce((s,h)=>s+h+CARD_GAP,0)-CARD_GAP;
    return Math.max(mx,h);
  },0);
  const W=PAD*2+nC*CW+(nC-1)*CGAP;
  const H=HDR+PAD+COL_HDR+CARD_GAP+Math.max(0,maxColH)+PAD*2;
  const cv=document.createElement('canvas');
  cv.width=W*DPR;cv.height=H*DPR;
  const c=cv.getContext('2d');
  c.scale(DPR,DPR);
  c.fillStyle='#0A0A0A';c.fillRect(0,0,W,H);
  // Banner: --surf-2 (#1A1A1A) — gris sobrio de la paleta
  c.fillStyle='#1A1A1A';c.fillRect(0,0,W,HDR);
  // Wordmark: "Otro" blanco + "festiv" ámbar — igual que en la app
  c.font='800 22px system-ui,-apple-system,sans-serif';
  c.textBaseline='alphabetic';
  c.fillStyle='#FFFFFF';
  const otroW=c.measureText('Otro').width;
  c.fillText('Otro',PAD,HDR/2+4);
  c.fillStyle='#D4900A';
  c.fillText('festiv',PAD+otroW,HDR/2+4);
  // Subtítulo: --gray (#888888)
  c.fillStyle='#888888';
  c.font='500 11px system-ui,-apple-system,sans-serif';
  const _dn=_getDisplayName();
  const _sub=(_dn?_dn+' · ':'')+t('share_mi_plan')+' · '+(cfg.name||'Festival')+' · '+active.length+' '+(active.length!==1?t('misc_dias'):t('misc_dia'));
  c.fillText(_sub,PAD,HDR/2+20);
  active.forEach((day,ci)=>{
    const x=PAD+ci*(CW+CGAP);
    const di=DAYS.indexOf(day);
    const films=byDay[day];
    const hy=HDR+PAD;
    c.fillStyle='rgba(212,144,10,0.12)';_rr(c,x,hy,CW,COL_HDR,8);c.fill();
    c.fillStyle='rgba(212,144,10,0.5)';c.fillRect(x,hy+COL_HDR-1,CW,1);
    c.fillStyle='#D4900A';
    c.font='700 9px system-ui,-apple-system,sans-serif';
    c.textBaseline='top';c.fillText(DS[di],x+12,hy+9);
    c.fillStyle='#FFFFFF';
    c.font='700 20px system-ui,-apple-system,sans-serif';
    c.fillText(DN[di],x+12,hy+20);
    let cardY=hy+COL_HDR+CARD_GAP;
    films.forEach((s,fi)=>{
      const ch=cHts[day][fi];
      const prio=prioritized&&prioritized.has&&prioritized.has(s._title);
      const dur=cleanDur(s);
      c.fillStyle=prio?'rgba(212,144,10,0.18)':'rgba(255,255,255,0.06)';
      _rr(c,x,cardY,CW,ch,CARD_R);c.fill();
      c.fillStyle=prio?'#D4900A':'rgba(212,144,10,0.35)';
      _rr(c,x,cardY,4,ch,CARD_R);c.fill();
      const tx=x+CARD_PAD+6;let ty=cardY+CARD_PAD;
      c.fillStyle='#D4900A';
      c.font='700 14px system-ui,-apple-system,sans-serif';
      c.textBaseline='top';c.fillText(s.time,tx,ty);
      if(dur){const hw=c.measureText(s.time).width;c.fillStyle='#666';c.font='400 10px system-ui,-apple-system,sans-serif';c.fillText(' · '+dur,tx+hw,ty+2);}
      ty+=22;
      c.fillStyle='#FFF';c.font=`600 ${FONT_T}px system-ui,-apple-system,sans-serif`;
      ty=_drawWrapped(c,s._title||'',tx,ty,CW-CARD_PAD*2-6,LINE_T,MAX_TL);
      if(s.venue){const _vc=vcfg(s.venue);const _vraw=_vc.short||s.venue;const v=_vraw.length>30?_vraw.slice(0,28)+'…':_vraw;c.fillStyle='#5A5A5A';c.font='400 10px system-ui,-apple-system,sans-serif';c.textBaseline='top';c.fillText(v,tx,cardY+ch-CARD_PAD-11);}
      cardY+=ch+CARD_GAP;
    });
  });
  c.fillStyle='rgba(212,144,10,0.2)';c.fillRect(0,H-1,W,1);
  return cv;
}

export function _measureLines(c,text,maxW,maxLines){
  const words=text.split(' ');let line='',lines=1;
  for(let i=0;i<words.length;i++){
    const t=line?line+' '+words[i]:words[i];
    if(c.measureText(t).width>maxW&&line){if(lines>=maxLines)return maxLines;lines++;line=words[i];}
    else{line=t;}
  }
  return lines;
}

export function _drawWrapped(c,text,x,y,maxW,lh,maxLines){
  c.textBaseline='top';
  const words=text.split(' ');let line='',ln=0;
  for(let i=0;i<words.length;i++){
    const t=line?line+' '+words[i]:words[i];
    if(c.measureText(t).width>maxW&&line){
      if(ln>=maxLines-1){c.fillText(line+'…',x,y+ln*lh);return y+ln*lh+lh;}
      c.fillText(line,x,y+ln*lh);line=words[i];ln++;
    }else{line=t;}
  }
  if(line)c.fillText(line,x,y+ln*lh);
  return y+ln*lh+lh;
}

export function _rr(c,x,y,w,h,r){
  r=Math.min(r,w/2,h/2);
  c.beginPath();c.moveTo(x+r,y);c.lineTo(x+w-r,y);c.quadraticCurveTo(x+w,y,x+w,y+r);
  c.lineTo(x+w,y+h-r);c.quadraticCurveTo(x+w,y+h,x+w-r,y+h);
  c.lineTo(x+r,y+h);c.quadraticCurveTo(x,y+h,x,y+h-r);
  c.lineTo(x,y+r);c.quadraticCurveTo(x,y,x+r,y);c.closePath();
}

export function _showImageModal(dataUrl,canvas){
  const prev=document.getElementById('img-share-modal');if(prev)prev.remove();
  const isIOS=/iPad|iPhone|iPod/.test(navigator.userAgent);
  const ov=document.createElement('div');
  ov.id='img-share-modal';
  ov.style.cssText='position:fixed;inset:0;background:var(--overlay-92);z-index:9999;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px;box-sizing:border-box;gap:var(--sp-btn)';
  const hint=document.createElement('p');
  hint.style.cssText='color:var(--gray);font-size:var(--t-caption);font-family:system-ui;text-align:center;margin:0;line-height:1.6';
  hint.textContent=isIOS?t('misc_mantener'):t('misc_descargar_guardar');
  ov.appendChild(hint);
  const img=document.createElement('img');
  img.src=dataUrl;
  img.style.cssText='max-width:100%;max-height:62vh;border-radius:var(--r);display:block;box-shadow:0 8px 32px var(--overlay-70)';
  ov.appendChild(img);
  const row=document.createElement('div');
  row.style.cssText='display:flex;gap:10px;width:100%;max-width:320px';
  if(!isIOS){
    const btnDl=document.createElement('button');
    btnDl.textContent='⬇ '+t('misc_descargar');
    btnDl.style.cssText='flex:1;padding:var(--sp-btn);background:var(--amber);color:var(--black);border:none;border-radius:var(--r-md);font-size:var(--t-base);font-family:system-ui;font-weight:var(--w-bold);cursor:pointer';
    btnDl.onclick=function(){
      if(navigator.share&&navigator.canShare){
        canvas.toBlob(blob=>{
          if(!blob){_dlDirect(dataUrl);return;}
          const file=new File([blob],'otrofestiv-miplan.png',{type:'image/png'});
          if(navigator.canShare({files:[file]})){navigator.share({files:[file]}).then(()=>{ov.remove();showToast(t('toast_compartido'),'info');}).catch(()=>_dlDirect(dataUrl));}
          else{_dlDirect(dataUrl);}
        },'image/png');
      }else{_dlDirect(dataUrl);}
    };
    row.appendChild(btnDl);
  }
  const btnX=document.createElement('button');
  btnX.textContent=t('misc_cerrar');
  btnX.style.cssText=(isIOS?'flex:1;':'')+'padding:var(--sp-btn) var(--sp-5);background:rgba(255,255,255,0.08);color:var(--gray2);border:none;border-radius:var(--r-md);font-size:var(--t-base);font-family:system-ui;cursor:pointer';
  btnX.onclick=()=>ov.remove();
  row.appendChild(btnX);
  ov.appendChild(row);
  ov.addEventListener('click',e=>{if(e.target===ov)ov.remove();});
  document.body.appendChild(ov);
}

export function _dlDirect(dataUrl){
  const a=document.createElement('a');
  a.href=dataUrl;a.download='otrofestiv-miplan.png';
  a.style.cssText='position:fixed;top:-999px;left:-999px;opacity:0';
  document.body.appendChild(a);a.click();
  setTimeout(()=>{document.body.removeChild(a);showToast(t('toast_imagen_guardada'),'info');},200);
}

export async function exportICS(){
  if(!savedAgenda||!savedAgenda.schedule.length){showToast(t('plan_sin_plan'),'warn');return;}
  const pad=n=>String(n).padStart(2,'0');
  // UTC con sufijo Z — instante absoluto. El Date se construye con el offset del
  // festival (_festDate usa TZ_OFFSET); aquí lo serializamos en UTC para que cada
  // calendario lo convierta a la tz local del usuario sin ambigüedad.
  const fmt=dt=>`${dt.getUTCFullYear()}${pad(dt.getUTCMonth()+1)}${pad(dt.getUTCDate())}T${pad(dt.getUTCHours())}${pad(dt.getUTCMinutes())}${pad(dt.getUTCSeconds())}Z`;
  // Convierte tiempo 12h (8:00 PM) → 24h (20:00) para _festDate
  const to24h=t=>{if(!t)return'12:00';const m=t.match(/(\d+):(\d+)\s*(AM|PM)/i);if(!m)return t;let h=parseInt(m[1]),mn=m[2],ap=m[3].toUpperCase();if(ap==='PM'&&h!==12)h+=12;if(ap==='AM'&&h===12)h=0;return pad(h)+':'+mn;};
  const _icsCfg=FESTIVAL_CONFIG[_activeFestId]||{};
  const _icsId=(_icsCfg.shortName||'festival').toLowerCase().replace(/\s+/g,'');
  const lines=['BEGIN:VCALENDAR','VERSION:2.0',`PRODID:-//Otrofestiv//${_icsId}//ES`,'CALSCALE:GREGORIAN','METHOD:PUBLISH'];
  savedAgenda.schedule.forEach(s=>{
    const dateStr=FESTIVAL_DATES[s.day];if(!dateStr) return;
    const start=_festDate(dateStr,to24h(s.time));
    if(isNaN(start.getTime())) return; // skip si fecha inválida
    const dur=s.duration?parseInt(String(s.duration)):90;
    const end=new Date(start.getTime()+(isNaN(dur)?90:dur)*60000);
    const clean=str=>(str||'').replace(/[\r\n,;\\]/g,' ').trim();
    lines.push('BEGIN:VEVENT',
      `DTSTART:${fmt(start)}`,`DTEND:${fmt(end)}`,
      `SUMMARY:${clean(s._title)}`,
      `LOCATION:${clean(s.venue)}`,
      `DESCRIPTION:${clean(_icsCfg.name||'Festival')} - ${clean(s.section)} - ${clean(s.duration)}`,
      `UID:otrofestiv-${_icsId}-${s._title?.replace(/\s/g,'')}-${fmt(start)}@otrofestiv.app`,
      'END:VEVENT');
  });
  lines.push('END:VCALENDAR');
  const icsText=lines.join('\r\n');
  const fileName=`otrofestiv-${_icsId}.ics`;
  // iOS nativo (SwiftUI WKWebView + EventKit): alta directa al Calendario,
  // sin hoja de compartir. El puente Swift expone messageHandler 'calendar'.
  // Mandamos instantes absolutos en epoch ms (ya correctos: offset del festival).
  const _wk=window.webkit?.messageHandlers?.calendar;
  if(_wk){
    const _clean=str=>(str||'').replace(/[\r\n]/g,' ').trim();
    const events=[];
    savedAgenda.schedule.forEach(s=>{
      const dateStr=FESTIVAL_DATES[s.day]; if(!dateStr) return;
      const start=_festDate(dateStr,to24h(s.time));
      if(isNaN(start.getTime())) return;
      const dur=s.duration?parseInt(String(s.duration)):90;
      const end=new Date(start.getTime()+(isNaN(dur)?90:dur)*60000);
      events.push({
        title:_clean(s._title),
        start:start.getTime(),
        end:end.getTime(),
        location:_clean(vcfg(s.venue).short||s.venue),
        notes:`${_clean(_icsCfg.name||'Festival')}${s.section?(' · '+_clean(s.section)):''}`
      });
    });
    if(!events.length){ showToast(t('plan_sin_plan'),'warn'); return; }
    // Swift llama esto vía evaluateJavaScript con el resultado.
    window.__otfCalResult=res=>{
      if(res&&res.status==='added') showToast(t('ics_success').replace('{n}',res.count),'info');
      else showToast(t('ics_permission_denied'),'warn',5000); // denied | error → mismo aviso accionable
    };
    _wk.postMessage({events});
    return;
  }
  // Capacitor nativo: Filesystem + Share para invocar Calendar.app
  if(window.Capacitor?.isNativePlatform()){
    const b64=btoa(unescape(encodeURIComponent(icsText)));
    try{
      const {Filesystem,Share}=window.Capacitor.Plugins;
      const result=await Filesystem.writeFile({
        path:fileName,
        data:b64,
        directory:'CACHE'
      });
      await Share.share({
        title:'Otrofestiv — '+t('share_mi_plan'),
        files:[result.uri]
      });
    }catch(e){
      console.error('ICS share error:',e);
      showToast(t('toast_cal_err'),'warn');
    }
  } else {
    const blob=new Blob([icsText],{type:'text/calendar;charset=utf-8'});
    const url=URL.createObjectURL(blob);
    const a=document.createElement('a');a.href=url;a.download=fileName;
    a.style.cssText='position:fixed;top:-999px;left:-999px;opacity:0';
    document.body.appendChild(a);a.click();
    setTimeout(()=>{document.body.removeChild(a);URL.revokeObjectURL(url);},200);
  }
  showToast(t('misc_calendario_listo'),'info');
}
