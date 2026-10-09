// ── src/controller/story.js — la historia 9:16 de «Tu festival» (#1055, F2) ───
// 1080×1920, dirección A aprobada por Juan (mosaico con estrellas). Retícula del
// diseño (09_Marketing/plans/tu-festival-diseno.md §D), márgenes 92 como los
// slides de marca:
//   y 300  acreditación (nombre · ciudad), 700 26px, tracking, gris
//   y 372  titular 112px: «Viste» hueso + cifra y unidad en ámbar
//   y 632  recorrido en una línea: números 700 hueso, unidades 500 gris
//   y 712  mosaico a sangre de TODO lo visto, ordenado por calificación
//   y 1060 «Tus mejores» + 3 tarjetas (número ámbar · afiche · título · estrellas)
//   y 1340 wordmark + otrofestiv.app
//   y 1440–1920 LIBRE: ahí el usuario pone el sticker del festival.
// Sin nombre de usuario. Fuente de marca cargada ANTES de dibujar (está
// autoalojada; sin esperar, el canvas pinta con la del sistema).

import { FESTIVAL_CONFIG } from '../config.js';
import { festivalRecap } from '../domain/festival.js';
import { recapTitular, recorridoPartes, recapPoster } from '../view/recap.js';
import { parseProgramTitle } from '../view/components.js';
import { starsText } from '../view/helpers.js';
import { showToast, showActionModal } from '../view/feedback.js';
import { _esRevisionActiva } from '../view/sheets.js';
import { t } from '../i18n/i18n.js';
import { storage } from '../storage/storage.js';
import { cargarAfiche, shareDiary, _shareNativeImage, _dlDirect } from './share.js';

const W=1080, H=1920, M=92;
const BG='#0B0A08', HUESO='#F0EDE8', AMBAR='#F59E0B', GRIS='#8A8A8A', GRIS2='#6A6A6A';
const F="'Plus Jakarta Sans', system-ui, sans-serif";

// abrirCompartirFestival — la hoja «Historia / Grilla». La Grilla es el export
// de siempre (shareDiary); la Historia es la pieza nueva para stories.
export function abrirCompartirFestival(){
  if(_esRevisionActiva()){ showToast(t('review_no_compartir')); return; }
  showActionModal(t('recap_compartir'),'',t('share_historia'),()=>shareStory(),undefined,
    {altLabel:t('share_grilla'), altCb:()=>shareDiary()});
}

async function _fuentes(){
  if(!document.fonts||!document.fonts.load) return;
  try{ await Promise.all(['500','700','800'].map(w=>document.fonts.load(`${w} 40px 'Plus Jakarta Sans'`))); }catch(e){}
}

// Mosaico: TODAS las vistas a sangre, afiches en 2:3 (nunca recortados a otra
// proporción). Se elige la grilla con la celda MÁS GRANDE que entre en la franja
// (hasta 3 filas, alto máximo 388 px: lo que deja «Tus mejores» y el wordmark en
// su lugar). Con 22 vistas da 11×2 de 98 px, como el mockup aprobado; con menos,
// la celda crece; la última fila puede quedar incompleta, alineada a la izquierda.
export function geometriaMosaico(n){
  if(!n) return {cols:0, filas:0, cw:0, ch:0};
  const ALTO_MAX=388; let mejor=null;
  for(let f=1; f<=3; f++){
    const cols=Math.max(Math.ceil(n/f), Math.ceil(W/(ALTO_MAX/f/1.5)));
    const filas=Math.ceil(n/cols);
    const cw=W/cols;
    if(!mejor||cw>mejor.cw) mejor={cols, filas, cw, ch:cw*1.5};
  }
  return mejor;
}

export async function shareStory(){
  if(_esRevisionActiva()){ showToast(t('review_no_compartir')); return; }
  const rec=festivalRecap();
  if(!rec.actividades){ showToast(t('diary_vacio'),'warn'); return; }
  storage.setDiarioNotaVista();
  await _fuentes();
  const cfg=FESTIVAL_CONFIG[_activeFestId]||{};
  const c=document.createElement('canvas'); c.width=W; c.height=H;
  const x=c.getContext('2d');
  x.fillStyle=BG; x.fillRect(0,0,W,H);
  // glow ámbar arriba a la derecha (el del mockup)
  const g=x.createRadialGradient(W*0.86,0,0,W*0.86,0,620);
  g.addColorStop(0,'rgba(245,158,11,.22)'); g.addColorStop(1,'rgba(245,158,11,0)');
  x.fillStyle=g; x.fillRect(0,0,W,700);
  x.textBaseline='alphabetic'; x.textAlign='left';

  // acreditación: nombre · ciudad, con tracking
  const _cred=[cfg.name||'', cfg.city||''].filter(Boolean).join(' · ').toUpperCase();
  _tracked(x,_cred,M,300,`700 26px ${F}`,GRIS,0.32*26);

  // titular
  const T=recapTitular(rec);
  x.font=`800 112px ${F}`; x.fillStyle=HUESO; x.fillText(T.verbo,M,372+96);
  x.fillStyle=AMBAR; x.fillText(`${T.n} ${T.unidad}.`,M,372+96+116);

  // recorrido en una línea (se achica si no entra)
  const partes=recorridoPartes(rec);
  if(partes.length){
    let sz=34, total;
    const medir=()=>{ total=0; partes.forEach((p,i)=>{ x.font=`700 ${sz}px ${F}`; total+=x.measureText(String(p.n)).width;
      x.font=`500 ${sz}px ${F}`; total+=x.measureText(' '+p.unidad+(i<partes.length-1?' · ':'')).width; }); };
    medir(); while(total>W-M*2&&sz>22){ sz-=2; medir(); }
    let cx=M; const y=632+34;
    partes.forEach((p,i)=>{
      x.font=`700 ${sz}px ${F}`; x.fillStyle=HUESO; x.fillText(String(p.n),cx,y); cx+=x.measureText(String(p.n)).width;
      x.font=`500 ${sz}px ${F}`; x.fillStyle=GRIS; const u=' '+p.unidad+(i<partes.length-1?' · ':''); x.fillText(u,cx,y); cx+=x.measureText(u).width;
    });
  }

  // mosaico: todo lo visto con estrellas posibles, mejor calificado primero
  const obras=rec.obras.slice().sort((a,b)=>b.rating-a.rating);
  const geo=geometriaMosaico(obras.length);
  const imgs=await Promise.all(obras.map(o=>cargarAfiche(recapPoster(o))));
  const y0=712;
  obras.forEach((o,i)=>{
    const col=i%geo.cols, fila=Math.floor(i/geo.cols);
    _cover(x,imgs[i],col*geo.cw,y0+fila*geo.ch,geo.cw,geo.ch,o.title);
  });
  const yMos=y0+geo.filas*geo.ch;

  // «Tus mejores»
  if(rec.top.length){
    const ye=Math.max(1060,yMos+56);
    _tracked(x,t('recap_tus_mejores').toUpperCase(),M,ye,`700 22px ${F}`,GRIS,0.32*22);
    const tops=await Promise.all(rec.top.map(o=>cargarAfiche(recapPoster(o))));
    const col=(W-M*2)/3;
    rec.top.forEach((o,i)=>{
      const bx=M+i*col, by=ye+50;
      x.font=`800 40px ${F}`; x.fillStyle=AMBAR; x.fillText(String(i+1),bx,by+60);
      const px=bx+44; _rr(x,px,by,62,93,8); x.save(); x.clip(); _cover(x,tops[i],px,by,62,93,o.title); x.restore();
      const tx=px+80, tw=col-(tx-bx)-12;
      const {displayTitle:dt}=parseProgramTitle(o.title);
      x.font=`700 24px ${F}`; x.fillStyle=HUESO;
      const lns=_lineas(x,dt,tw).slice(0,2);
      lns.forEach((l,k)=>x.fillText(l,tx,by+28+k*28));
      x.font=`600 22px ${F}`; x.fillStyle=AMBAR; x.fillText(starsText(o.rating),tx,by+28+lns.length*28+6);
    });
  }

  // cierre: wordmark bicolor + dominio (sobre la zona libre, nunca dentro)
  const yw=1340+44;
  x.font=`800 44px ${F}`; x.fillStyle=HUESO; const w1=x.measureText('Otro').width;
  x.fillText('Otro',M,yw); x.fillStyle=AMBAR; x.fillText('festiv',M+w1,yw);
  x.font=`500 28px ${F}`; x.fillStyle=GRIS2; x.textAlign='right'; x.fillText('otrofestiv.app',W-M,yw); x.textAlign='left';

  const fname=`otrofestiv-historia-${(cfg.shortName||'fest').toLowerCase().replace(/\s+/g,'-')}.png`;
  const titulo=`${t('recap_tu_festival')} · ${cfg.name||'Otrofestiv'}`;
  try{
    const blob=await new Promise(r=>c.toBlob(r,'image/png'));
    const file=blob?new File([blob],fname,{type:'image/png'}):null;
    if(file&&navigator.share&&navigator.canShare&&navigator.canShare({files:[file]})){
      await navigator.share({files:[file],title:titulo});
      showToast(t('toast_compartido'),'info');
      return;
    }
  }catch(e){ if(e&&e.name==='AbortError') return; }
  const durl=c.toDataURL('image/png');
  if(await _shareNativeImage(fname,durl,titulo)) return;
  _dlDirect(durl);
}

// ── helpers de dibujo ──
function _tracked(x,txt,px,py,font,color,track){
  x.font=font; x.fillStyle=color; let cx=px;
  for(const ch of txt){ x.fillText(ch,cx,py); cx+=x.measureText(ch).width+track; }
}
function _rr(x,px,py,w,h,r){ x.beginPath(); x.moveTo(px+r,py); x.arcTo(px+w,py,px+w,py+h,r); x.arcTo(px+w,py+h,px,py+h,r); x.arcTo(px,py+h,px,py,r); x.arcTo(px,py,px+w,py,r); x.closePath(); }
function _lineas(x,txt,max){
  const out=[]; let ln='';
  String(txt).split(/\s+/).forEach(w=>{ const tt=ln?ln+' '+w:w; if(x.measureText(tt).width>max&&ln){ out.push(ln); ln=w; } else ln=tt; });
  if(ln) out.push(ln);
  if(out.length>2){ out[1]=out[1].replace(/.?$/,'…'); }
  return out;
}
// Afiche "cover" en su celda; sin imagen → celda cálida con el título (como la grilla).
function _cover(x,im,cx,cy,cw,ch,title){
  x.save(); x.beginPath(); x.rect(cx,cy,cw,ch); x.clip();
  if(im&&im.width){
    const s=Math.max(cw/im.width,ch/im.height), dw=im.width*s, dh=im.height*s;
    x.drawImage(im,cx+(cw-dw)/2,cy+(ch-dh)/2,dw,dh);
  } else {
    x.fillStyle='#1B1917'; x.fillRect(cx,cy,cw,ch);
    if(cw>50){
      const {displayTitle:dt}=parseProgramTitle(title||'');
      const sz=Math.max(11,Math.round(cw/7));
      x.font=`700 ${sz}px ${F}`; x.fillStyle=HUESO; x.textAlign='center';
      _lineas(x,dt,cw-10).slice(0,3).forEach((l,k)=>x.fillText(l,cx+cw/2,cy+ch/2+k*(sz+3)-sz));
      x.textAlign='left';
    }
  }
  x.restore();
}
