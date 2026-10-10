// ── src/controller/share.js ───────────────────────────────────────────────────────
// p8 Step 7e — Compartir plan (canvas/imagen) + export ICS.

import { FESTIVAL_CONFIG } from '../config.js';
import {vcfg, icsUid, icsNuevas, icsFantasmas, icsCampos, icsHuella, icsSeq, _icsEntrega, _icsUtc} from '../view/helpers.js';
import { parseProgramTitle } from '../view/components.js';
import { showToast, showActionModal } from '../view/feedback.js';
import { _esRevisionActiva } from '../view/sheets.js';
import { t } from '../i18n/i18n.js';
import { state } from '../state/state.js';
import { storage } from '../storage/storage.js';
import { _getDisplayName, _promptDisplayName } from './auth.js';  // share→auth (sharePlan pide nombre)

// cargarAfiche — DUEÑO ÚNICO de cómo un afiche entra a un canvas (la grilla del
// Diario y la historia 9:16 de «Tu festival»). Los afiches del export se piden de otra forma que en la pantalla, y ESA es la
// razón por la que no cargaban (reportado por Juan, FICCI desde iPhone, 4 sep
// 2026). El canvas EXIGE permiso cruzado —dibujar una imagen sin él lo
// contamina y `toBlob` tira excepción, medido—, pero la grilla ya cargó ese
// mismo afiche SIN pedirlo, y la copia guardada no sirve para una petición que
// sí lo pide: el navegador la rechaza. Medido con un póster real de FICCI
// (TMDB w185): con permiso cruzado falla, sin él carga, y con permiso cruzado
// más una dirección distinta carga. El servidor autoriza —manda
// `access-control-allow-origin: *`—; lo que falla es reusar la copia vieja.
//
// Tres casos, cada uno con lo que necesita:
//  · `data:` — no hay servidor ni copia que arreglar, y pedirle permiso cruzado
//    la rompe en WebKit (el motor de la app de iPhone). Se pide tal cual.
//  · mismo origen — no hay permiso que pedir: el canvas no se contamina.
//  · otro origen — permiso cruzado Y una dirección distinta, para no recibir la
//    copia que la pantalla dejó sin permiso.
export const cargarAfiche=src=>new Promise(res=>{
  if(!src){res(null);return;}
  const im=new Image();
  let _u=src;
  if(/^https?:/i.test(src)){
    let _ajeno=true;
    try{ _ajeno=new URL(src,location.href).origin!==location.origin; }catch(e){}
    // El mismo origen no necesita ninguna de las dos cosas: no hay permiso que
    // pedir ni copia envenenada. Distinguirlo evita descargar dos veces cada
    // afiche propio — ninguna mutación mueve esta rama (el archivo sale igual),
    // así que queda dicho: la protege el sentido, no el test.
    if(_ajeno){
      im.crossOrigin='anonymous';
      _u=src+(src.includes('?')?'&':'?')+'ofx=1';
    }
  }
  im.onload=()=>res(im); im.onerror=()=>res(null); im.src=_u;
});

// ── shareDiary — la acción «Compartir mi Diario». Desde #1066 la dibuja
// shareGrilla (story.js): carrusel 4:5 con el lenguaje de la historia. Se
// importa al vuelo porque story.js ya importa de este módulo.
export async function shareDiary(){
  const S=await import('./story.js');
  return S.shareGrilla();
}

export async function sharePlan(_yaPregunte){
  // RESTRICCIÓN 2 — de un festival en revisión no sale nada. Su programación
  // es provisional y compartirla la hace circular como si fuera definitiva:
  // una captura del plan o un .ics en el calendario de alguien sobreviven a
  // la revisión y ya no se pueden desmentir. Se avisa, no se falla en silencio.
  if(_esRevisionActiva()){ showToast(t('review_no_compartir')); return; }

  if(!savedAgenda||!savedAgenda.schedule||!savedAgenda.schedule.length){
    showToast(t('plan_sin_plan'),'warn');return;
  }
  // Pedir nombre si no existe. El flag corta la RECURSIÓN: el nombre es
  // opcional, así que al volver de la hoja sin haberlo puesto esta misma
  // condición era verdadera otra vez y la hoja se reabría en bucle — medido:
  // con el campo vacío no se cerraba nunca. La compuerta pregunta una vez por
  // gesto de compartir, no hasta que haya nombre.
  if(!_getDisplayName()&&!_yaPregunte){
    _promptDisplayName(()=>sharePlan(true));
    return;
  }
  let canvas,dataUrl;
  try{
    canvas=_buildAgendaCanvas();
    dataUrl=canvas.toDataURL('image/png');
    if(!dataUrl||dataUrl==='data:,') throw new Error('canvas vacío');
  }catch(e){showToast(t('toast_err_imagen'),'err');return;}

  const cfg=FESTIVAL_CONFIG[_activeFestId]||{};
  const fname=`otrofestiv-${(cfg.shortName||'plan').toLowerCase().replace(/\s+/g,'-')}.png`;
  // El File DEBE venir de un Blob real de canvas.toBlob — NO de un Uint8Array/atob:
  // en iOS un File hecho de bytes crudos NO se reconoce como imagen guardable →
  // el sheet solo ofrece "Guardar en Archivos", nunca "Guardar imagen". Con un Blob
  // de toBlob, iOS sí lo trata como imagen y aparece "Guardar imagen". Patrón
  // idéntico al de la-primada, verificado mostrando "Save Image" en el mismo iOS.
  // (toBlob async NO rompe la activación de usuario — la-primada lo confirma.)
  // Web Share API con archivo (iOS Safari 15+, Chrome Android 86+)
  try{
    const blob=await new Promise(r=>canvas.toBlob(r,'image/png'));
    const file=blob?new File([blob],fname,{type:'image/png'}):null;
    if(file&&navigator.share&&navigator.canShare&&navigator.canShare({files:[file]})){
      await navigator.share({files:[file],title:`${t('share_mi_plan')} · ${cfg.name||'Otrofestiv'}`});
      showToast(t('toast_compartido'),'info');
      return;
    }
  }catch(e){
    if(e&&e.name==='AbortError') return;  // el usuario cerró el sheet — no es error
    // cualquier otro error cae al fallback de descarga
  }
  // App nativa de Android: por el menú del sistema (ver _shareNativeImage)
  if(await _shareNativeImage(fname,dataUrl,`${t('share_mi_plan')} · ${cfg.name||'Otrofestiv'}`)) return;
  // Fallback: descarga directa (desktop, sin file-share, o conversión/share fallida)
  _dlDirect(dataUrl);
}

function _buildAgendaCanvas(){
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
  c.fillStyle='#0B0A08';c.fillRect(0,0,W,H);
  // Banner: --surf-2 (#1B1917) — gris cálido de la paleta
  c.fillStyle='#1B1917';c.fillRect(0,0,W,HDR);
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
  // Los días del PLAN, no los del festival (2 sep 2026). El subtítulo reusaba
  // `active.length`, y `active` son TODOS los días del festival a propósito —la
  // grilla es un registro completo, con sus columnas vacías—: medido en FICDEH
  // con 3 obras en 4 días, la imagen decía «8 días». Leído bajo «Mi Plan» eso
  // es el tamaño de tu Plan, y era el del festival.
  // Misma derivación que la línea de resultado de Planear (días con algo
  // adentro), no el lapso entre la primera y la última: con una obra el lunes y
  // otra el viernes, tu Plan es de 2 días, no de 5.
  const _diasPlan=new Set((savedAgenda.schedule||[]).map(s=>s.day)).size||1;
  const _sub=(_dn?_dn+' · ':'')+t('share_mi_plan')+' · '+(cfg.name||'Festival')+' · '+_diasPlan+' '+(_diasPlan!==1?t('misc_dias'):t('misc_dia'));
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

function _measureLines(c,text,maxW,maxLines){
  const words=text.split(' ');let line='',lines=1;
  for(let i=0;i<words.length;i++){
    const t=line?line+' '+words[i]:words[i];
    if(c.measureText(t).width>maxW&&line){if(lines>=maxLines)return maxLines;lines++;line=words[i];}
    else{line=t;}
  }
  return lines;
}

function _drawWrapped(c,text,x,y,maxW,lh,maxLines){
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

function _rr(c,x,y,w,h,r){
  r=Math.min(r,w/2,h/2);
  c.beginPath();c.moveTo(x+r,y);c.lineTo(x+w-r,y);c.quadraticCurveTo(x+w,y,x+w,y+r);
  c.lineTo(x+w,y+h-r);c.quadraticCurveTo(x+w,y+h,x+w-r,y+h);
  c.lineTo(x+r,y+h);c.quadraticCurveTo(x,y+h,x,y+h-r);
  c.lineTo(x,y+r);c.quadraticCurveTo(x,y,x+r,y);c.closePath();
}

// ── Imagen en la app nativa de ANDROID (Capacitor) ───────────────────────────
// La vista web embebida no tiene gestor de descargas, así que el <a download> de
// _dlDirect no escribe nada — y el aviso «Imagen guardada» salía igual, porque era
// un temporizador (22 sep 2026, usuario de Android: «dice image saved pero no
// aparece»). Mismo camino que el calendario: Filesystem + Share del sistema, y el
// aviso solo si el sistema devolvió. Dueño único para el plan Y el diario (la
// revisión cazó que el diario tenía el mismo camino muerto). El iPhone no pasa
// por acá: su app es WKWebView, sin window.Capacitor, y su Web Share sí funciona.
// Devuelve true si se hizo cargo (nativo), false si hay que seguir por la web.
export async function _shareNativeImage(fname,dataUrl,title){
  if(!window.Capacitor?.isNativePlatform()) return false;
  try{
    const {Filesystem,Share}=window.Capacitor.Plugins;
    // base64 crudo, sin el prefijo data: — con el prefijo el PNG sale corrupto
    const result=await Filesystem.writeFile({path:fname,data:dataUrl.split(',')[1],directory:'CACHE'});
    await Share.share({title,files:[result.uri]});
    showToast(t('toast_compartido'),'info');
  }catch(e){
    // @capacitor/share rechaza con exactamente "Share canceled" cuando el usuario
    // cierra el menú: no es error. Anclado al inicio para no tragar otros mensajes.
    if(/^share cancel/i.test(String(e?.message||''))) return true;
    console.error('share image error:',e);
    showToast(t('toast_compartir_err'),'err'); // la imagen SÍ se generó: lo que falló fue compartirla
  }
  return true;
}

// _shareNativeImages — como _shareNativeImage, con VARIAS imágenes en un solo
// menú del sistema (el carrusel del Diario). [{fname,dataUrl}] → true si era nativo.
export async function _shareNativeImages(list,title){
  if(!window.Capacitor?.isNativePlatform()) return false;
  try{
    const {Filesystem,Share}=window.Capacitor.Plugins;
    const uris=[];
    for(const it of list){
      const r=await Filesystem.writeFile({path:it.fname,data:it.dataUrl.split(',')[1],directory:'CACHE'});
      uris.push(r.uri);
    }
    await Share.share({title,files:uris});
    showToast(t('toast_compartido'),'info');
  }catch(e){
    if(/^share cancel/i.test(String(e?.message||''))) return true;
    console.error('share images error:',e);
    showToast(t('toast_compartir_err'),'err');
  }
  return true;
}

export function _dlDirect(dataUrl){
  const a=document.createElement('a');
  a.href=dataUrl;a.download='otrofestiv-miplan.png';
  a.style.cssText='position:fixed;top:-999px;left:-999px;opacity:0';
  document.body.appendChild(a);a.click();
  setTimeout(()=>{document.body.removeChild(a);showToast(t('toast_imagen_guardada'),'info');},200);
}

// exportICS(soloNuevas) — `soloNuevas` exporta ÚNICAMENTE lo que todavía no
// salió de acá. Nace de un reporte real (usuaria de TIFF, 10 sep 2026): tenía su
// plan en el calendario, agregó una obra, volvió a exportar y se le duplicó todo.
// Medido antes de tocar nada: nuestros UID YA eran estables —3 de 3 idénticos
// entre dos exportaciones seguidas—, así que el archivo no era el culpable: su
// calendario sencillamente no reconcilia por UID al importar un archivo. Contra
// eso no alcanza con ser correctos; hay que no volver a mandarle lo que ya tiene.
// LA ELECCIÓN ES DEL USUARIO, NO NUESTRA (Juan, 10 sep 2026). La primera versión
// de esto decidía sola: con memoria de entregas y plan crecido, mandaba la resta
// y punto. Juan encontró el agujero: si ella tocó «Exportar» explorando y NO
// guardó el archivo, anotamos las N como entregadas y desde entonces solo podía
// pedir las nuevas — el plan completo le quedaba inalcanzable. Y no es un caso
// raro: la memoria se escribe al ENTREGAR porque ninguno de los tres caminos nos
// devuelve un acuse del calendario, así que la primera exploración ya la
// envenena. Peor: mi propio comentario decía que el error de anotar de más «se
// arregla pidiendo todo el plan», y no había manera de pedirlo.
//
// Ahora, cuando volver a mandar todo DUPLICARÍA algo, se pregunta. Las dos
// salidas quedan a la vista y con conducta de verdad —el modal exige etiqueta y
// callback para su tercera acción, precisamente por el bug de la intención
// inalcanzable— y el que no está en ese caso no paga ninguna pregunta.
// LA ELECCIÓN ES DEL USUARIO, NO NUESTRA (Juan, 10 sep 2026). La primera versión
// de esto decidía sola: con memoria de entregas y plan crecido, mandaba la resta
// y punto. Juan encontró el agujero: si ella tocó «Exportar» explorando y NO
// guardó el archivo, anotamos las N como entregadas y desde entonces solo podía
// pedir las nuevas — el plan completo le quedaba inalcanzable. Y no es un caso
// raro: la memoria se escribe al ENTREGAR porque ninguno de los tres caminos nos
// devuelve un acuse del calendario, así que la primera exploración ya la
// envenena. Peor: mi propio comentario decía que el error de anotar de más «se
// arregla pidiendo todo el plan», y no había manera de pedirlo.
//
// Ahora, cuando volver a mandar todo DUPLICARÍA algo, se pregunta. Las dos
// salidas quedan a la vista y con conducta de verdad —el modal exige etiqueta y
// callback para su tercera acción, precisamente por el bug de la intención
// inalcanzable— y el que no está en ese caso no paga ninguna pregunta.
export async function exportICS(modo){
  // RESTRICCIÓN 2 — de un festival en revisión no sale nada. Su programación
  // es provisional y compartirla la hace circular como si fuera definitiva:
  // una captura del plan o un .ics en el calendario de alguien sobreviven a
  // la revisión y ya no se pueden desmentir. Se avisa, no se falla en silencio.
  if(_esRevisionActiva()){ showToast(t('review_no_compartir')); return; }

  if(!savedAgenda||!savedAgenda.schedule.length){showToast(t('plan_sin_plan'),'warn');return;}
  // fmt y to24h se mudaron a view/helpers junto al UID: los tres son la misma
  // pregunta —cómo se nombra este pase en un calendario— y tenerlos acá los
  // dejaba a un refactor de distancia de discrepar con el UID.
  const fmt=_icsUtc;
  // Lo que se va a exportar. Sin `soloNuevas` va el plan entero, que es también
  // la salida de emergencia: al que perdió su calendario le sirve pedirlo todo.
  const _entregados=state.get('icsEntregados')||[];
  const _previos=new Map(_entregados.map(_icsEntrega).filter(e=>e.uid).map(e=>[e.uid,e]));
  const _nuevas=icsNuevas(savedAgenda.schedule,_entregados);
  // Lo ya entregado que SIGUE en el plan: es lo único que se duplicaría al
  // mandar todo. Si es cero no hay disyuntiva —nada que duplicar— y preguntar
  // sería un peaje sin motivo, así que el primer export de la vida no ve nada.
  const _yaEnPlan=savedAgenda.schedule.length-_nuevas.length;
  // LO QUE QUEDÓ COLGADO se dice ACÁ y no en la pantalla (Juan, 11 sep 2026):
  // un bloque permanente en Mi Plan era ruido, y el momento en que esto importa
  // es el único en que ella está pensando en su calendario. Una línea, con
  // nombres para poder encontrarlos —máximo dos, o no se lee— y sin botón
  // propio: se dice una vez y no se insiste.
  const _fant=icsFantasmas(savedAgenda.schedule,_entregados);
  const _lista=_fant.slice(0,2).map(e=>{
    const{displayTitle}=parseProgramTitle(e.title||'');
    // Recorte de la casa (el mismo de confirmReplace): un título largo convierte
    // una línea en un párrafo, y acá el párrafo era la queja.
    const _d=displayTitle||e.title||'';
    return `${_d.length>22?_d.slice(0,20)+'…':_d}${e.time?` (${e.time})`:''}`;
  }).join(', ')+(_fant.length>2?` ${t('ics_fantasma_mas',{n:_fant.length-2})}`:'');
  // Dos formas del mismo hecho, ninguna con variante singular/plural: cuando el
  // aviso va SOLO, el título dice el hecho y el cuerpo son los nombres; cuando
  // comparte modal con la elección, el hecho se pega delante de los nombres.
  const _avisoFant=_fant.length?t('ics_fantasma_inline',{lista:_lista}):'';
  if(!modo&&(( _nuevas.length&&_yaEnPlan)||_fant.length)){
    const _hayEleccion=!!(_nuevas.length&&_yaEnPlan);
    const _cuerpo=_hayEleccion
      ? [t('ics_elegir_cuerpo',{m:_yaEnPlan,n:savedAgenda.schedule.length}),_avisoFant].filter(Boolean).join('<br>')
      : _lista;
    showActionModal(
      _hayEleccion?t('ics_elegir_titulo'):t('ics_fantasma_titulo'),
      _cuerpo,
      _hayEleccion
        ?(_nuevas.length===1?t('ics_solo_la_nueva'):t('ics_solo_nuevas',{n:_nuevas.length}))
        :t('plan_exportar_cal'),
      ()=>exportICS(_hayEleccion?'nuevas':'todo'),
      null,
      _hayEleccion?{ altLabel:t('ics_todo_el_plan'), altCb:()=>exportICS('todo') }:undefined
    );
    return;
  }
  const _lote=modo==='nuevas'?_nuevas:savedAgenda.schedule;
  if(!_lote.length){ showToast(t('ics_nada_nuevo'),'info'); return; }
  // DTSTAMP lo exige el RFC 5545 §3.6.1 en TODO VEVENT y no lo teníamos (medido:
  // false). Es la marca de cuándo se publicó este objeto, y es parte de lo que un
  // cliente mira para decidir «el mismo evento, actualizado» en vez de «otro
  // evento». No se inventa un SEQUENCE: su valor por defecto ya es 0 y ponerlo a
  // mano no dice nada nuevo — un SEQUENCE de verdad pide versionar cada evento.
  const _ahora=fmt(new Date());
  const _icsCfg=FESTIVAL_CONFIG[_activeFestId]||{};
  const _icsId=(_icsCfg.shortName||'festival').toLowerCase().replace(/\s+/g,'');
  const lines=['BEGIN:VCALENDAR','VERSION:2.0',`PRODID:-//Otrofestiv//${_icsId}//ES`,'CALSCALE:GREGORIAN','METHOD:PUBLISH'];
  // RFC 5545 §3.3.11: en un valor TEXT la barra invertida, la coma, el punto y
  // coma y el salto de línea se ESCAPAN; borrarlos es perder el dato. Acá se
  // reemplazaban por un espacio y «Ni un minuto de silencio, toda una vida de
  // búsqueda» llegaba al calendario del teléfono partido en dos, con doble
  // espacio donde iba la coma. Medido: 39 obras en 12 festivales lo sufren
  // (auditoría 4 sep 2026). El orden importa — la barra primero, o se escaparían
  // las barras que agrega el propio escape. El ESCAPE es de este consumidor; el
  // CONTENIDO lo decide icsCampos, que es el dueño.
  const clean=str=>(str||'')
    .replace(/\\/g,'\\\\')
    .replace(/\r?\n/g,'\\n')
    .replace(/([,;])/g,'\\$1');
  // Versión de cada evento. Se calcula ACÁ, contra lo que se está por mandar, y
  // el mismo número se guarda al anotar: si se recalculara en los dos lados
  // podrían discrepar y el apunte diría una versión que nunca salió.
  const _versiones=new Map();
  _lote.forEach(s=>{
    const c=icsCampos(s);
    if(!c) return;                                  // sin fecha válida no hay evento
    const _h=icsHuella(c);
    const _seq=icsSeq(_previos.get(c.uid),_h);
    _versiones.set(c.uid,{seq:_seq,h:_h});
    lines.push('BEGIN:VEVENT',
      `DTSTART:${fmt(c.start)}`,`DTEND:${fmt(c.end)}`,
      `SUMMARY:${clean(c.summary)}`,
      `LOCATION:${clean(c.location)}`,
      `DESCRIPTION:${clean(c.description)}`,
      `UID:${c.uid}`,
      `DTSTAMP:${_ahora}`,
      `SEQUENCE:${_seq}`,
      'END:VEVENT');
  });
  lines.push('END:VCALENDAR');
  // PLEGADO — RFC 5545 §3.1: ninguna línea pasa de 75 OCTETOS; la continuación
  // empieza con un espacio. Medido en un .ics de FICDEH: 10 de 53 líneas se
  // pasaban, hasta 138 (el UID del Encuentro) y 98 (un SUMMARY largo). Ningún
  // calendario nos lo rechazó —Google y Apple son tolerantes—, así que es deuda
  // de formato, no un fallo visto; se paga porque el estándar es el contrato con
  // un programa que no controlamos.
  // Se cuenta en OCTETOS y se corta por punto de código: partir un carácter de
  // varios bytes por la mitad rompería el UTF-8, y los títulos traen acentos.
  const _plegar=l=>{
    const _oct=c=>new TextEncoder().encode(c).length;
    if(_oct(l)<=75) return l;
    const out=[]; let cur='', max=75;
    for(const ch of l){
      if(_oct(cur)+_oct(ch)>max){ out.push(cur); cur=' '; max=76; }  // 1 octeto se va en el espacio
      cur+=ch;
    }
    if(cur.trim()!=='') out.push(cur);
    return out.join('\r\n');
  };
  const icsText=lines.map(_plegar).join('\r\n');
  const fileName=`otrofestiv-${_icsId}.ics`;
  // Memoria de lo que salió de acá. Se anota al ENTREGAR, no al confirmar que el
  // calendario lo aceptó: no tenemos ese acuse en ninguno de los tres caminos, y
  // el error de anotar de más (no volver a ofrecerle algo) se arregla pidiendo
  // todo el plan, mientras que el de anotar de menos vuelve a duplicarle.
  const _anotar=()=>{
    // Se guarda el UID y además título/día/hora: sin eso, lo que quede colgado en
    // su calendario se puede contar pero no NOMBRAR, y un aviso que no dice cuál
    // no se puede accionar.
    const _prev=(state.get('icsEntregados')||[]).map(_icsEntrega).filter(e=>e.uid);
    const _map=new Map(_prev.map(e=>[e.uid,e]));
    _lote.forEach(s=>{
      const u=icsUid(s); if(!u) return;
      const v=_versiones.get(u)||{seq:0,h:null};
      _map.set(u,{uid:u,title:s._title||'',day:s.day||'',time:s.time||'',seq:v.seq,h:v.h});
    });
    // Los colgados se OLVIDAN al exportar: ya se avisaron en el modal y nadie
    // nos va a confirmar que los borró. Insistir sería el ruido que Juan sacó de
    // la pantalla. Costo asumido: si no los borró y esa misma función vuelve al
    // Plan, se la mandamos como nueva y le queda duplicada — un caso de borde
    // contra un aviso permanente, y el aviso permanente era peor.
    const _fantUid=new Set(icsFantasmas(savedAgenda.schedule,[..._map.values()]).map(e=>e.uid));
    const _arr=[..._map.values()].filter(e=>!_fantUid.has(e.uid));
    state.set('icsEntregados',_arr); storage.setIcsEntregados(_arr);
  };
  // iOS nativo (SwiftUI WKWebView + EventKit): alta directa al Calendario,
  // sin hoja de compartir. El puente Swift expone messageHandler 'calendar'.
  // Mandamos instantes absolutos en epoch ms (ya correctos: offset del festival).
  const _wk=window.webkit?.messageHandlers?.calendar;
  if(_wk){
    const _clean=str=>(str||'').replace(/[\r\n]/g,' ').trim();
    const events=[];
    _lote.forEach(s=>{
      // MISMO dueño que el .ics: antes esto recalculaba inicio y fin por su
      // cuenta y un comentario prometía que coincidían. Una promesa a mano no
      // es un dueño — el día que el .ics cambiara su cálculo, el puente se
      // quedaba atrás en silencio.
      const c=icsCampos(s);
      if(!c) return;

      events.push({
        title:_clean(c.summary),
        start:c.start.getTime(),
        end:c.end.getTime(),
        location:_clean(c.location),            // MISMO texto que el ICS: a qué sala
                                                //  entrar no puede depender del teléfono
        notes:`${_clean(_icsCfg.name||'Festival')}${c.seccion?(' · '+_clean(c.seccion)):''}`,
        // El puente mandaba título/hora/sede y NADA que identificara el evento,
        // así que EventKit no podía deduplicar aunque quisiera: cada exportación
        // creaba eventos nuevos, siempre. Va el mismo UID del .ics para que el
        // lado Swift pueda buscar y actualizar en vez de agregar. Hasta que ese
        // lado lo use, el campo viaja y no estorba.
        uid:c.uid
      });
    });
    if(!events.length){ showToast(t('plan_sin_plan'),'warn'); return; }
    // Swift llama esto vía evaluateJavaScript con el resultado.
    window.__otfCalResult=res=>{
      if(res&&res.status==='added') showToast(t('ics_success').replace('{n}',res.count),'info');
      else showToast(t('ics_permission_denied'),'warn',5000); // denied | error → mismo aviso accionable
    };
    _anotar();
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
      _anotar();
    }catch(e){
      // Cerrar el menú no es error y no se festeja: antes caía acá y ADEMÁS
      // seguía hasta «Calendario listo» (medido en Android, 24 sep 2026).
      if(/^share cancel/i.test(String(e?.message||''))) return;
      console.error('ICS share error:',e);
      showToast(t('toast_cal_err'),'warn');
      return;
    }
  } else {
    const blob=new Blob([icsText],{type:'text/calendar;charset=utf-8'});
    const url=URL.createObjectURL(blob);
    const a=document.createElement('a');a.href=url;a.download=fileName;
    a.style.cssText='position:fixed;top:-999px;left:-999px;opacity:0';
    document.body.appendChild(a);a.click();
    setTimeout(()=>{document.body.removeChild(a);URL.revokeObjectURL(url);},200);
    _anotar();
  }
  showToast(t('misc_calendario_listo'),'info');
}
