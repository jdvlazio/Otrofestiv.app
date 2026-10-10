// ── src/controller/story.js — la historia 9:16 de «Tu festival» (#1055, F2) ───
// 1080×1920, dirección A aprobada por Juan (mosaico con estrellas). Retícula de
// la maqueta con guías de #1064, márgenes 92 como los slides de marca:
//   y 286  acreditación (nombre · ciudad), 700 26px, tracking, gris
//   y 358  titular 112px: verbo hueso + cifra y unidad en ámbar
//   y 618  recorrido en una línea: números 700 hueso, unidades 500 gris
//   y 698  mosaico a sangre, afiches 2:3, ≤470 de alto (geometriaMosaico)
//   +62    etiqueta («Mis mejores» / «No me las pierdo») + tarjetas
//   +72    wordmark + otrofestiv.app — todo desde el final REAL del mosaico
//   y 1440–1920 LIBRE: ahí el usuario pone el sticker del festival.
// Sin nombre de usuario. Fuente de marca cargada ANTES de dibujar (está
// autoalojada; sin esperar, el canvas pinta con la del sistema).

import { FESTIVAL_CONFIG } from '../config.js';
import { festivalRecap, planRecap } from '../domain/festival.js';
import { recapTitular, recorridoPartes } from '../view/recap.js';
import { parseProgramTitle, _sectionColor, makeProgramPoster } from '../view/components.js';
import { starsText, posterModel, itemPosterParts, dayLabel } from '../view/helpers.js';
import { state } from '../state/state.js';
import { showToast, showActionModal } from '../view/feedback.js';
import { _esRevisionActiva } from '../view/sheets.js';
import { t } from '../i18n/i18n.js';
import { storage } from '../storage/storage.js';
import { cargarAfiche, sharePlan, _shareNativeImage, _shareNativeImages, _dlDirect } from './share.js';

const W=1080, H=1920, M=92;
const BG='#0B0A08', HUESO='#F0EDE8', AMBAR='#F59E0B', GRIS='#8A8A8A', GRIS2='#6A6A6A';
const F="'Plus Jakarta Sans', system-ui, sans-serif";

// abrirCompartirFestival — la hoja «Historia / Grilla». La Grilla es el export
// en carrusel 4:5 para el feed (shareGrilla); la Historia, la pieza para stories.
export function abrirCompartirFestival(){
  if(_esRevisionActiva()){ showToast(t('review_no_compartir')); return; }
  showActionModal(t('recap_compartir'),'',t('share_historia'),()=>shareStory(),undefined,
    {altLabel:t('share_grilla'), altCb:()=>shareGrilla()});
}

// abrirCompartirPlan — la hoja «Historia / Calendario» de Mi Plan (#1064). El
// Calendario es la imagen de siempre (sharePlan), sin cambios.
export function abrirCompartirPlan(){
  if(_esRevisionActiva()){ showToast(t('review_no_compartir')); return; }
  if(!planRecap().n){ sharePlan(); return; } // sin obras (solo charlas): no hay historia que contar
  showActionModal(t('plan_compartir_plan'),'',t('share_historia'),()=>shareStoryPlan(),undefined,
    {altLabel:t('share_calendario'), altCb:()=>sharePlan()});
}

async function _fuentes(){
  if(!document.fonts||!document.fonts.load) return;
  try{ await Promise.all(['500','700','800'].map(w=>document.fonts.load(`${w} 40px 'Plus Jakarta Sans'`))); }catch(e){}
}

// Mosaico (regla de Juan, 10 oct — comentario en #1064): afiche SIEMPRE 2:3, a
// sangre (las columnas llenan el ancho). Columnas ≥7: primero la menor cantidad
// que deje FILAS COMPLETAS con el mosaico ≤ altoMax (14 → 7+7, 18 → 9+9,
// 22 → 11+11) sin achicar el afiche más de la mitad; si ninguna, la menor que
// entre en el alto, y la última fila queda a la izquierda. altoMax lo fija quien llama (≤470) para que el bloque de abajo
// nunca pise el cuarto libre (y ≥ 1440).
export function geometriaMosaico(n, altoMax=470){
  if(!n) return {filas:0, cols:0, cw:0, ch:0, porFila:[]};
  const alto=c=>Math.ceil(n/c)*1.5*W/c;
  // La menor cantidad que entra en el alto (filas parejas o no)…
  let min=7; while(alto(min)>altoMax) min++;
  // …y una con filas completas gana solo si no achica los afiches más de la
  // mitad: con un primo (23) la única fila «completa» es UNA de 23 afiches
  // diminutos, que la regla al pie de la letra elegía (medido, 10 oct).
  let cols=min;
  for(let c=min; c<=min*1.5; c++) if(n%c===0){ cols=c; break; }
  const filas=Math.ceil(n/cols), cw=W/cols;
  const porFila=Array.from({length:filas},(_,i)=>Math.min(cols,n-i*cols));
  return {filas, cols, cw, ch:cw*1.5, porFila};
}

// Retícula vertical (maqueta con guías de #1064, bajada 50 px el 10 oct: la
// franja superior —~250 px, foto y nombre de quien publica— tapaba la
// acreditación): el mosaico arranca en Y_MOS;
// debajo, etiqueta (+62), tarjetas (+33, 93 de alto, filas cada 120) y el
// wordmark (+72 desde el final de lo que haya arriba). Todo termina antes de
// Y_LIBRE: el cuarto inferior es del sticker del festival.
const Y_MOS=698, Y_LIBRE=1428, G_MARCA=72; // 72: con 1 fila de tarjetas el mosaico conserva sus 470
function _altoBloque(filasTarjetas){
  return filasTarjetas ? 62+33+filasTarjetas*93+(filasTarjetas-1)*27+G_MARCA : G_MARCA;
}
function _altoMosaico(filasTarjetas){
  return Math.min(470, Y_LIBRE-Y_MOS-_altoBloque(filasTarjetas));
}

export async function shareStory(){
  if(_esRevisionActiva()){ showToast(t('review_no_compartir')); return; }
  const rec=festivalRecap();
  if(!rec.actividades){ showToast(t('diary_vacio'),'warn'); return; }
  storage.setDiarioNotaVista();
  const {c,x,cfg}=await _lienzo(recapTitular(rec,true), recorridoPartes(rec));
  // mosaico: todo lo visto con estrellas posibles, mejor calificado primero
  const yMos=await _mosaico(x, rec.obras.slice().sort((a,b)=>b.rating-a.rating), _altoMosaico(rec.top.length?1:0));
  let yFin=yMos;

  // «Mis mejores» (primera persona: la historia la publica el asistente)
  if(rec.top.length){
    const ye=yMos+62;
    _tracked(x,t('story_mis_mejores').toUpperCase(),M,ye,`700 22px ${F}`,GRIS,0.32*22);
    const topAfs=rec.top.map(_modeloAfiche);
    const tops=await _cargarConRespaldo(topAfs);
    const col=(W-M*2)/3;
    rec.top.forEach((o,i)=>{
      const bx=M+i*col, by=ye+33; yFin=by+93;
      x.font=`800 40px ${F}`; x.fillStyle=AMBAR; x.fillText(String(i+1),bx,by+60);
      const px=bx+44; _rr(x,px,by,62,93,8); x.save(); x.clip(); _afiche(x,topAfs[i],tops[i],px,by,62,93); x.restore();
      const tx=px+80, tw=col-(tx-bx)-12;
      const {displayTitle:dt}=parseProgramTitle(o.title);
      x.font=`700 24px ${F}`; x.fillStyle=HUESO;
      const lns=_lineas(x,dt,tw).slice(0,2);
      lns.forEach((l,k)=>x.fillText(l,tx,by+28+k*28));
      x.font=`600 22px ${F}`; x.fillStyle=AMBAR; x.fillText(starsText(o.rating),tx,by+28+lns.length*28+6);
    });
  }

  await _cierre(c,x,cfg,yFin,'historia',`${t('recap_tu_festival')} · ${cfg.name||'Otrofestiv'}`);
}

// shareStoryPlan — la historia «Mi plan» (#1064): misma retícula que la de «Tu
// festival». Titular «Voy a ver N obras.», línea «días · sedes · N que no me
// pierdo», mosaico con TODO lo planeado (prioridades primero, con su marca) y
// «No me las pierdo»: cada prioridad con su afiche chico, día y hora.
export async function shareStoryPlan(){
  if(_esRevisionActiva()){ showToast(t('review_no_compartir')); return; }
  const pr=planRecap();
  if(!pr.n){ showToast(t('plan_sin_plan'),'warn'); return; }
  const u=(n,uno,varios)=>({n, unidad:t(n===1?uno:varios)});
  const partes=[u(pr.dias,'recap_u_dia','recap_u_dias'),
    pr.ciudades>1?u(pr.ciudades,'recap_u_ciudad','recap_u_ciudades'):u(pr.sedes,'recap_u_sede','recap_u_sedes')];
  if(pr.prios.length) partes.push({n:pr.prios.length, unidad:t(pr.prios.length===1?'story_no_me_pierdo_1':'story_no_me_pierdo_n')});
  const {c,x,cfg}=await _lienzo({verbo:t('story_voy_a_ver'), n:pr.n, unidad:t(pr.n===1?'recap_u_obra':'recap_u_obras')}, partes);
  const filasT=Math.ceil(pr.prios.length/3);
  const yMos=await _mosaico(x, pr.obras, _altoMosaico(filasT));
  let yFin=yMos;

  if(pr.prios.length){
    const ye=yMos+62;
    _tracked(x,t('story_no_me_las_pierdo').toUpperCase(),M,ye,`700 22px ${F}`,GRIS,0.32*22);
    const afs=pr.prios.map(p=>_modeloAfiche({film:p.film}));
    const ims=await _cargarConRespaldo(afs);
    // Hasta 3 por fila (el máximo de prioridades es 5 → dos filas a lo sumo).
    const col=(W-M*2)/3;
    pr.prios.forEach((p,i)=>{
      const bx=M+(i%3)*col, by=ye+33+Math.floor(i/3)*120; yFin=Math.max(yFin,by+93);
      _rr(x,bx,by,62,93,8); x.save(); x.clip(); _afiche(x,afs[i],ims[i],bx,by,62,93); x.restore();
      const tx=bx+80, tw=col-80-12;
      const {displayTitle:dt}=parseProgramTitle(p.title);
      x.font=`700 26px ${F}`; x.fillStyle=HUESO;
      const lns=_lineas(x,dt,tw).slice(0,2);
      lns.forEach((l,k)=>x.fillText(l,tx,by+32+k*30));
      x.font=`500 24px ${F}`; x.fillStyle=GRIS; x.fillText(`${dayLabel(p.day)} · ${p.time}`,tx,by+32+lns.length*30+4);
    });
  }
  await _cierre(c,x,cfg,yFin,'plan',`${t('share_mi_plan')} · ${cfg.name||'Otrofestiv'}`);
}

// _lienzo — fondo, glow, acreditación, titular y línea de recorrido: la parte
// común de las dos historias. T={verbo,n,unidad}; partes=[{n,unidad}].
async function _lienzo(T, partes){
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
  _tracked(x,_cred,M,286,`700 26px ${F}`,GRIS,0.32*26);
  // titular
  x.font=`800 112px ${F}`; x.fillStyle=HUESO; x.fillText(T.verbo,M,358+96);
  x.fillStyle=AMBAR; x.fillText(`${T.n} ${T.unidad}.`,M,358+96+116);
  // recorrido en una línea (se achica si no entra)
  if(partes.length){
    let sz=34, total;
    const medir=()=>{ total=0; partes.forEach((p,i)=>{ x.font=`700 ${sz}px ${F}`; total+=x.measureText(String(p.n)).width;
      x.font=`500 ${sz}px ${F}`; total+=x.measureText(' '+p.unidad+(i<partes.length-1?' · ':'')).width; }); };
    medir(); while(total>W-M*2&&sz>22){ sz-=2; medir(); }
    let cx=M; const y=618+34;
    partes.forEach((p,i)=>{
      x.font=`700 ${sz}px ${F}`; x.fillStyle=HUESO; x.fillText(String(p.n),cx,y); cx+=x.measureText(String(p.n)).width;
      x.font=`500 ${sz}px ${F}`; x.fillStyle=GRIS; const u=' '+p.unidad+(i<partes.length-1?' · ':''); x.fillText(u,cx,y); cx+=x.measureText(u).width;
    });
  }
  return {c,x,cfg};
}

// _mosaico — la franja de afiches desde y=712 (geometriaMosaico: 2:3, filas
// parejas, hasta 3). Un ítem con `prio` lleva la marca de prioridad. → y final.
async function _mosaico(x, obras, altoMax){
  const geo=geometriaMosaico(obras.length, altoMax);
  const afs=obras.map(_modeloAfiche);
  const imgs=await _cargarConRespaldo(afs);
  const y0=Y_MOS;
  let k=0;
  geo.porFila.forEach((nf,fila)=>{
    const x0=0; // a sangre; la última fila incompleta queda a la izquierda
    for(let c=0;c<nf;c++,k++){
      const cx=x0+c*geo.cw, cy=y0+fila*geo.ch;
      _afiche(x,afs[k],imgs[k],cx,cy,geo.cw,geo.ch);
      if(obras[k].prio) _marca(x,cx+geo.cw-geo.cw*0.24,cy+geo.cw*0.06,geo.cw*0.16);
    }
  });
  return y0+geo.filas*geo.ch;
}

// _marca — el marcador de prioridad (la forma de ICONS.bookmarkFill) en ámbar,
// sobre un fondo oscuro para que se lea encima de cualquier afiche.
function _marca(x,px,py,w){
  const h=w*1.3;
  x.save();
  x.fillStyle='rgba(11,10,8,.55)'; _rr(x,px-w*0.25,py-w*0.2,w*1.5,h+w*0.4,w*0.3); x.fill();
  x.fillStyle=AMBAR; x.beginPath(); x.moveTo(px,py); x.lineTo(px+w,py); x.lineTo(px+w,py+h);
  x.lineTo(px+w/2,py+h-w*0.4); x.lineTo(px,py+h); x.closePath(); x.fill();
  x.restore();
}

// _cierre — wordmark + dominio y la salida (Web Share → menú nativo → descarga).
async function _cierre(c,x,cfg,yFin,tipo,titulo){
  // cierre: wordmark bicolor + dominio, desde el final real de lo de arriba —
  // nunca dentro de la zona libre (geometría garantizada por _altoMosaico).
  const yw=yFin+G_MARCA;
  x.font=`800 44px ${F}`; x.fillStyle=HUESO; const w1=x.measureText('Otro').width;
  x.fillText('Otro',M,yw); x.fillStyle=AMBAR; x.fillText('festiv',M+w1,yw);
  x.font=`500 28px ${F}`; x.fillStyle=GRIS2; x.textAlign='right'; x.fillText('otrofestiv.app',W-M,yw); x.textAlign='left';

  const fname=`otrofestiv-${tipo}-${(cfg.shortName||'fest').toLowerCase().replace(/\s+/g,'-')}.png`;
  try{
    const blob=await new Promise(r=>c.toBlob(r,'image/png'));
    const file=blob?new File([blob],fname,{type:'image/png'}):null;
    if(file&&navigator.share&&navigator.canShare&&navigator.canShare({files:[file]})){
      await navigator.share({files:[file],title:titulo});
      _etiqueta(cfg);
      return;
    }
  }catch(e){ if(e&&e.name==='AbortError') return; }
  const durl=c.toDataURL('image/png');
  if(await _shareNativeImage(fname,durl,titulo)){ _etiqueta(cfg); return; }
  _dlDirect(durl);
}

// Tras compartir, si el festival tiene Instagram en su config, sugerir la
// etiqueta: así el festival se entera y puede repostear (el cuarto inferior de
// la historia queda libre justo para ese sticker). Sin el campo, el aviso de siempre.
function _etiqueta(cfg){
  const h=String(cfg.instagram||'').replace(/^@/,'').trim();
  if(h) setTimeout(()=>showToast(t('share_etiqueta',{handle:h}),'info',5000),600);
  else showToast(t('toast_compartido'),'info');
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

// _modeloAfiche — el afiche que la app ya muestra para esa obra, sin inventar
// otro (dueños: posterModel para obras, itemPosterParts
// para cortos de un programa — docs/POSTERS.md):
//   · original 2:3 → a sangre en la celda
//   · fotograma 16:9 (editorial) → ENTERO, nunca recortado (regla «16:9
//     intacto»): en la posición del marco editorial de la app, sobre fondo cálido
//     con el filete del color de la sección
//   · sin imagen → el póster generativo de la app (el mismo de la ficha)
function _modeloAfiche(o){
  const f=o.film||{};
  if(f._prog){
    // Dueño único del afiche de un corto (itemPosterParts): decide si es
    // fotograma editorial y cuál es su imagen; acá solo se dibuja.
    const pp=itemPosterParts(f, f._prog.section||'', '', {header:true});
    return {kind: pp.ed?'editorial':'image', src:pp.src, accent:_sectionColor(f._prog.section||''),
      respaldo:()=>makeProgramPoster(state,f.title,f.duration||'',f._prog.section||'')};
  }
  const respaldo=()=>makeProgramPoster(state,f.title||o.title,f.duration||'',f.section||'');
  const m=posterModel(f);
  if(m.kind==='editorial') return {kind:'editorial', src:m.src, accent:m.accent, respaldo};
  if(m.kind==='empty') return {kind:'image', src:respaldo(), accent:''};
  return {kind:'image', src:m.src, accent:'', respaldo};
}
function _afiche(x,a,im,cx,cy,cw,ch){
  if(a&&a.kind==='editorial'&&im&&im.width){
    x.save(); x.beginPath(); x.rect(cx,cy,cw,ch); x.clip();
    x.fillStyle='#1B1917'; x.fillRect(cx,cy,cw,ch);
    // Forma B de la app: un campo 16:9 de todo el ancho, a 3,5/12 del alto.
    const sh=cw*9/16, sy=cy+ch*3.5/12;
    x.fillStyle=a.accent||AMBAR; x.fillRect(cx,sy-Math.max(2,cw*0.02),cw,Math.max(2,cw*0.02));
    const s=Math.min(cw/im.width, sh/im.height), dw=im.width*s, dh=im.height*s;
    x.drawImage(im,cx+(cw-dw)/2,sy+(sh-dh)/2,dw,dh);
    x.restore();
    return;
  }
  _cover(x,im,cx,cy,cw,ch,'');
}

// Un afiche que no se puede dibujar (servidor sin permiso cruzado — TIFF, medido —
// o caído) no deja una celda vacía: cae al póster generativo de la app para esa
// obra, el mismo que muestra cuando no hay imagen. Nunca un hueco.
async function _cargarConRespaldo(afs){
  const imgs=await Promise.all(afs.map(a=>cargarAfiche(a.src)));
  return Promise.all(imgs.map(async (im,i)=>{
    if(im&&im.width) return im;
    const a=afs[i]; if(!a||!a.respaldo) return null;
    a.kind='image';
    return cargarAfiche(a.respaldo());
  }));
}

// ── shareGrilla — el Diario como carrusel 4:5 para el feed (#1066) ─────────────
// Mismo lenguaje que la historia: acreditación espaciada, titular en primera
// persona, resplandor ámbar, wordmark. Tarjetas con estrellas (la razón de ser
// de la Grilla), de la mejor nota a la peor. Hasta 12 por lámina y REPARTIDAS
// PAREJO (Juan, 10 oct: en un carrusel cada lámina se ve sola — 18 → 9+9).
// Afiches: los mismos dueños que la historia (_modeloAfiche) con respaldo
// generativo para lo que no se puede dibujar (_cargarConRespaldo).
const G_W=1080, G_H=1350, G_P=80, G_GAP=14, G_RAD=16, G_Y0=222, G_MAX=12;

// geometriaGrilla(k) — cómo se acomodan k tarjetas en una lámina 4:5.
//   ≤6 → 3 columnas grandes; 9 → 3×3; el resto → 4 columnas. Centrada.
export function geometriaGrilla(k){
  const ancho=(G_W-G_P*2-G_GAP*3)/4;                 // tarjeta de 4 columnas
  const cols=k<=6?3:(k===9?3:4);
  const cw=k<=6?(G_W-G_P*2-G_GAP*2)/3:ancho;
  const x0=(G_W-(cols*cw+(cols-1)*G_GAP))/2;
  return {cols, cw, ch:cw*1.5, x0, filas:Math.ceil(k/cols)};
}
// repartoLaminas(n) → cuántas tarjetas va en cada lámina, parejo.
export function repartoLaminas(n){
  const L=Math.ceil(n/G_MAX), base=Math.floor(n/L), extra=n%L;
  return Array.from({length:L},(_,i)=>base+(i<extra?1:0));
}

export async function shareGrilla(){
  if(_esRevisionActiva()){ showToast(t('review_no_compartir')); return; }
  const rec=festivalRecap();
  if(!rec.obras.length){ showToast(t('diary_vacio'),'warn'); return; }
  storage.setDiarioNotaVista();   // compartir = ya aceptó la lista; la nota se retira
  // De la MEJOR calificada a la peor (decisión de Juan); sort estable → los
  // empates conservan el orden cronológico, y las sin nota caen al final.
  const obras=rec.obras.slice().sort((a,b)=>b.rating-a.rating);
  await _fuentes();
  const cfg=FESTIVAL_CONFIG[_activeFestId]||{};
  const afs=obras.map(_modeloAfiche), imgs=await _cargarConRespaldo(afs);
  const T=recapTitular(rec,true);
  const reparto=repartoLaminas(obras.length);
  const lams=[]; let k0=0;
  reparto.forEach((k,L)=>{
    const c=document.createElement('canvas'); c.width=G_W; c.height=G_H;
    const x=c.getContext('2d');
    x.fillStyle=BG; x.fillRect(0,0,G_W,G_H);
    const g=x.createRadialGradient(G_W*0.86,0,0,G_W*0.86,0,520);
    g.addColorStop(0,'rgba(245,158,11,.22)'); g.addColorStop(1,'rgba(245,158,11,0)');
    x.fillStyle=g; x.fillRect(0,0,G_W,600);
    x.textBaseline='alphabetic'; x.textAlign='left';
    const _cred=[cfg.name||'', cfg.city||''].filter(Boolean).join(' · ').toUpperCase();
    _tracked(x,_cred,G_P,92,`700 24px ${F}`,GRIS,0.32*24);
    if(reparto.length>1){ x.font=`600 24px ${F}`; x.fillStyle=GRIS; x.textAlign='right'; x.fillText(`${L+1}/${reparto.length}`,G_W-G_P,92); x.textAlign='left'; }
    x.font=`800 76px ${F}`; x.fillStyle=HUESO; x.fillText(T.verbo+' ',G_P,186);
    const wv=x.measureText(T.verbo+' ').width;
    x.fillStyle=AMBAR; x.fillText(`${T.n} ${T.unidad}.`,G_P+wv,186);
    const geo=geometriaGrilla(k);
    for(let j=0;j<k;j++){
      const i=k0+j, o=obras[i];
      const cx=geo.x0+(j%geo.cols)*(geo.cw+G_GAP), cy=G_Y0+Math.floor(j/geo.cols)*(geo.ch+G_GAP);
      x.save(); _rr(x,cx,cy,geo.cw,geo.ch,G_RAD); x.clip();
      _afiche(x,afs[i],imgs[i],cx,cy,geo.cw,geo.ch);
      const sg=x.createLinearGradient(0,cy+geo.ch-110,0,cy+geo.ch); sg.addColorStop(0,'rgba(0,0,0,0)'); sg.addColorStop(1,'rgba(0,0,0,.8)');
      x.fillStyle=sg; x.fillRect(cx,cy+geo.ch-110,geo.cw,110);
      x.textAlign='center'; x.fillStyle=o.rating?AMBAR:GRIS; x.font=`600 ${geo.cw>260?32:26}px ${F}`;
      x.fillText(o.rating?starsText(o.rating):'·',cx+geo.cw/2,cy+geo.ch-22); x.textAlign='left';
      x.restore();
    }
    k0+=k;
    const yw=G_H-46;
    x.font=`800 38px ${F}`; x.fillStyle=HUESO; const w1=x.measureText('Otro').width;
    x.fillText('Otro',G_P,yw); x.fillStyle=AMBAR; x.fillText('festiv',G_P+w1,yw);
    x.font=`500 26px ${F}`; x.fillStyle=GRIS2; x.textAlign='right'; x.fillText('otrofestiv.app',G_W-G_P,yw); x.textAlign='left';
    lams.push(c);
  });

  const base=`otrofestiv-diario-${(cfg.shortName||'fest').toLowerCase().replace(/\s+/g,'-')}`;
  const nom=i=>lams.length>1?`${base}-${i+1}.png`:`${base}.png`;
  const titulo=`${t('diary_eyebrow')} · ${cfg.name||'Otrofestiv'}`;
  // Web Share con TODAS las láminas: el sistema las entrega juntas y en orden,
  // que es lo que Instagram arma como carrusel.
  try{
    const blobs=await Promise.all(lams.map(c=>new Promise(r=>c.toBlob(r,'image/png'))));
    const files=blobs.every(Boolean)?blobs.map((b,i)=>new File([b],nom(i),{type:'image/png'})):null;
    if(files&&navigator.share&&navigator.canShare&&navigator.canShare({files})){
      await navigator.share({files,title:titulo});
      _etiqueta(cfg);
      return;
    }
  }catch(e){ if(e&&e.name==='AbortError') return; }
  const urls=lams.map(c=>c.toDataURL('image/png'));
  if(await _shareNativeImages(urls.map((u,i)=>({fname:nom(i),dataUrl:u})),titulo)) return;
  urls.forEach(u=>_dlDirect(u));
}
