// ── src/controller/overlays.js ────────────────────────────────────────────────
// p8 Step 7d-2 — Overlays del controller (leaf): seccion + search + lugar
// dropdowns + fuzzyMatch/normalize (utils de búsqueda). No llama a mutators/
// filters (7d-3); importa view + pipeline + sheets-controller. normTitle vía
// globalThis bridge. Roster/viewstate vía bridge.

import { FILM_CATEGORY_LABEL, FILM_CATEGORY_ORDER, SECTION_ORDER_LIST } from '../config.js';
import { ICONS, _secLabelFull, parseProgramTitle } from '../view/components.js';
import { emptyState, getFilmPoster, vcfg, venueMatches, isCitySel, festivalCities, SEDE_SEP } from '../view/helpers.js';
import { storage } from '../storage/storage.js';
import { _renderProgramaContent, lugarClose, lugarOutside, render } from '../view/programa.js';
import { t } from '../i18n/i18n.js';
import { _updateProgramaActiveFilter } from './pipeline.js';
import { countryToFlags } from './sheets-controller.js';

// _dropRight — posición horizontal de un panel de filtro, ACOTADA al viewport.
// Bug (FICDEH, 6 ago 2026): el panel se anclaba al borde derecho de su botón sin
// tope, así que con el botón a media pantalla (Sección termina en x=274 de 375)
// y el panel en su ancho máximo de 300px, el borde izquierdo caía en -26px: se
// leía "odo el programa" sin la T y los emojis salían partidos. Le pasa a
// cualquier festival cuyo panel llegue al máximo — con secciones de nombre largo
// es sistemático. El clamp deja al menos MARGEN px de aire a la izquierda.
// El ancho llega MEDIDO, no supuesto (auditoría A-6, 3 sep 2026). Antes esta
// función espejaba el tope de `.filter-drop` (300px) y se posicionaba por el peor
// caso, así que un panel angosto se anclaba como si midiera 300 y uno ancho
// desperdiciaba lo que le sobraba: medido en Sección con TODO, el panel quedaba
// de 8 a 308 en un viewport de 390 —82px sin usar— y 4 de 15 secciones salían
// cortadas, una perdiendo el 45% del nombre. Con el ancho real, el panel angosto
// sigue pegado a su botón y el ancho usa la pantalla.
function _dropRight(btnRight, ancho){
  const MARGEN=8;
  const _a=ancho||Math.min(300, window.innerWidth*0.9);
  const right=window.innerWidth-btnRight;
  return Math.max(MARGEN, Math.min(right, window.innerWidth-_a-MARGEN))+'px';
}

// _velaElCorte — DUEÑO ÚNICO del desvanecido al pie de un dropdown de filtro.
// El panel se corta donde llega su max-height, y eso caía a MEDIA LETRA: medido
// en Sección (max-height 464,2 · scrollHeight 660), la fila 11 quedaba con 23 de
// sus 44px y se leía como error de render, no como «hay más abajo».
//
// La máscara NO puede ser fija: al llegar al final de la lista se come la última
// opción —medido: «Función de clausura» a 1px de la base, dentro del degradado—,
// que es peor que el corte. Se enciende solo mientras queda algo por debajo.
// Lo usan los DOS dropdowns (sección y lugar): un solo listener, un solo dueño.
function _velaElCorte(drop){
  if(!drop) return;
  const _sync=()=>drop.classList.toggle('hay-mas',
    drop.scrollTop + drop.clientHeight < drop.scrollHeight - 2);
  drop.addEventListener('scroll', _sync, {passive:true});
  _sync();
}

// _filasQueVeras — DUEÑO ÚNICO del número de una fila de filtro. El contrato lo
// fijó Juan (7 ago, citado en sheets.js): «en el filtro el número dice vas a ver
// N si filtrás por esto — es la consecuencia de la acción». Entonces la unidad
// no la elige el menú, la elige la VISTA: con un día activo pinta una fila por
// FUNCIÓN; en «todas» pinta una tarjeta por OBRA. Medido en FICDEH: día 15 → 88
// filas (88 funciones, 55 obras); todas → 118 tarjetas (118 obras, 447
// funciones). Sin esto la fila de ciudad prometía 136 —la suma de sus sedes, que
// cuenta dos veces la obra proyectada en dos salas— y pintaba 79.
function _filasQueVeras(films){
  return activeDay==='all' ? new Set(films.map(f=>f.title)).size : films.length;
}

export function seccionOpen(){
  const btn = document.getElementById('seccion-btn');
  const r = btn.getBoundingClientRect();
  const drop = document.createElement('div');
  drop.id = 'seccion-drop';
  drop.className = 'filter-drop'; // anatomía única; el build solo aporta posición
  drop.style.top = (r.bottom+4)+'px';
  drop.style.right = _dropRight(r.right);

  const baseFilms = activeDay==='all' ? FILMS : FILMS.filter(f=>f.day===activeDay);
  const films = activeVenue!=='all' ? baseFilms.filter(f=>venueMatches(f.venue,activeVenue)) : baseFilms;

  const secFilms={}, secCatMap={}, secMap={};
  films.forEach(f=>{
    const s=f.section||'';
    if(!s) return;
    (secFilms[s]||(secFilms[s]=[])).push(f);
    if(f.filmCategory) secCatMap[s]=f.filmCategory;
  });
  Object.keys(secFilms).forEach(s=>{ secMap[s]=_filasQueVeras(secFilms[s]); });

  // data-s SIEMPRE = section ES (clave de filtro/orden); solo el <span> visible se localiza.
  const _opt=(s,cnt,isActive)=>'<div class="lugar-opt'+(isActive?' on':'')+'" data-s="'+s.replace(/"/g,'&quot;')+'">'
    +'<span>'+_secLabelFull(s)+'</span><span class="lugar-cnt">'+cnt+'</span>'+(isActive?'<span class="txt-amber-ml">✓</span>':'')+'</div>';

  // La opción "todo el programa" NO lleva conteo: el total general sin contexto
  // confunde (no hay referencia). Las opciones individuales sí lo mantienen.
  let html='<div class="lugar-opt'+(activeSec==='all'?' on':'')+'" data-s="all">'
    +'<span>'+t('filter_todo_programa')+'</span>'
    +'</div>';

  const hasCategories=Object.keys(secCatMap).length>0;
  const orderedSecs=Object.keys(secMap).sort((a,b)=>{
    const ia=SECTION_ORDER_LIST.indexOf(a),ib=SECTION_ORDER_LIST.indexOf(b);
    return (ia<0?999:ia)-(ib<0?999:ib);
  });

  if(hasCategories){
    const groups={};
    orderedSecs.forEach(s=>{ const cat=secCatMap[s]||''; if(cat){if(!groups[cat])groups[cat]=[];groups[cat].push(s);} });
    const uncategorized=orderedSecs.filter(s=>!secCatMap[s]);
    FILM_CATEGORY_ORDER.forEach(cat=>{
      if(!groups[cat]) return;
      html+='<div class="sec-drop-hdr">'+(FILM_CATEGORY_LABEL[cat]||cat)+'</div>';
      groups[cat].forEach(s=>{ html+=_opt(s,secMap[s],activeSec===s); });
    });
    uncategorized.forEach(s=>{ html+=_opt(s,secMap[s],activeSec===s); });
  } else {
    orderedSecs.forEach(s=>{ html+=_opt(s,secMap[s],activeSec===s); });
  }

  drop.innerHTML=html;
  drop.addEventListener('click',e=>{
    const opt=e.target.closest('.lugar-opt');
    if(!opt) return;
    const s=opt.dataset.s;
    activeSec=(s==='all'||s===activeSec)?'all':s;
    _programaChipMatchFn=null; programaChip='all';
    seccionClose(); _updateProgramaActiveFilter();
    if(activeMNav==='mnav-cartelera') _renderProgramaContent(true); else render(); // selección sección → scroll al tope
  });
  document.body.appendChild(drop);
  // Recién acá el panel tiene ancho: se posiciona con el REAL, no con el tope.
  drop.style.right = _dropRight(r.right, drop.offsetWidth);
  _velaElCorte(drop);
  btn.classList.add('on');
  setTimeout(()=>{ document.addEventListener('click',seccionOutside); },0);
}

export function seccionClose(){
  const drop = document.getElementById('seccion-drop');
  if(drop) drop.remove();
  document.removeEventListener('click', seccionOutside);
  const btn = document.getElementById('seccion-btn');
  if(btn) btn.classList.toggle('on', activeSec!=='all');
  const lbl = document.getElementById('seccion-lbl');
  if(lbl) lbl.textContent = _seccionLabel(activeSec);
}

export function seccionOutside(e){
  const drop = document.getElementById('seccion-drop');
  const btn = document.getElementById('seccion-btn');
  if(drop && !drop.contains(e.target) && e.target!==btn && !btn?.contains(e.target)){
    seccionClose();
  }
}

export function seccionToggle(){
  if(document.getElementById('lugar-drop')) lugarClose();
  if(document.getElementById('seccion-drop')) seccionClose();
  else seccionOpen();
}

export function _seccionLabel(sec){
  // Botón mode bar: solo el emoji que ya viene en el nombre de sección
  // Las secciones tienen formato "🏆 Nombre" en todos los festivales
  if(!sec||sec==='all') return t('label_seccion');
  return sec.match(/^\S+/)?.[0] || sec.slice(0,4);
}

export function searchOpen(){
  const overlay = document.getElementById('search-overlay');
  const inp = document.getElementById('search-input');
  if(!overlay) return;
  window.scrollTo({top:0, behavior:'instant'});
  // Posicionar ANTES de mostrar para evitar flash sin top
  const tb = document.querySelector('.topbar');
  const top = tb ? Math.ceil(tb.getBoundingClientRect().bottom) : 88;
  overlay.style.top = top + 'px';
  overlay.style.bottom = '0';
  overlay.style.display = 'flex';
  requestAnimationFrame(()=>{
    overlay.style.opacity = '1';
    searchPositionOverlay();
    if(inp){
      inp.focus();
      // Si hay texto previo, disparar búsqueda inmediatamente
      if(inp.value.trim()) searchQuery();
    }
  });
}

export function searchClose(){
  const overlay = document.getElementById('search-overlay');
  const inp = document.getElementById('search-input');
  const results = document.getElementById('search-results');
  if(overlay){
    overlay.style.opacity = '0';
    setTimeout(()=>{ overlay.style.display = 'none'; }, 150);
  }
  if(inp){ inp.value = ''; inp.blur(); }
  if(results) results.innerHTML = '';
}

export function searchPositionOverlay(){
  const overlay = document.getElementById('search-overlay');
  const results = document.getElementById('search-results');
  if(!overlay || overlay.style.display==='none') return;
  // Overlay: desde topbar hasta el borde inferior de la pantalla (bottom:0)
  // El teclado es UI del sistema — siempre por encima, no interfiere con el overlay
  const tb = document.querySelector('.topbar');
  const top = tb ? Math.ceil(tb.getBoundingClientRect().bottom) : 88;
  overlay.style.top = top + 'px';
  overlay.style.bottom = '0';
  overlay.style.height = 'auto';
  // Padding-bottom en resultados = altura del teclado para que nada quede oculto
  if(results){
    const vv = window.visualViewport;
    const kbH = vv ? Math.max(0, window.innerHeight - vv.height - (vv.offsetTop||0)) : 0;
    results.style.paddingBottom = (kbH + 16) + 'px';
  }
}

export function _searchAll(q){
  // Motor único: fuzzyMatch scoring en títulos + cortos individuales.
  // Reemplaza los tres motores paralelos anteriores.
  if(!q) return[];
  const ql=q.toLowerCase();
  const seen=new Set();
  const results=[];

  // 1. Programas y películas (deduplicados por título)
  const titleMap={};
  FILMS.forEach(f=>{if(!titleMap[f.title]) titleMap[f.title]=f;});
  Object.values(titleMap).forEach(f=>{
    const r1=fuzzyMatch(q,f.title);
    // Títulos alternos: el usuario busca lo que TIENE DELANTE, y la única pista
    // frente a él es el afiche. Cuando nuestro póster viene con el arte de
    // distribución en español y el festival titula en otro idioma, esas dos
    // cosas no coinciden: «Hoja seca» en el afiche sobre una ficha que se llama
    // «Dry Leaf» (Cinemancia 2026, título correcto por doctrina — así lo publica
    // el festival). Medido: buscar «hoja» daba «Sin resultados».
    // Un solo dueño para todos los alternos, así agregar otro idioma no vuelve
    // a tocar la fórmula del puntaje.
    const rAlt=[f.title_en,f.title_es].filter(Boolean)
      .reduce((mej,alt)=>{const r=fuzzyMatch(q,alt);return r.score>mej.score?r:mej;},{match:false,score:0});
    const secScore=(f.section||'').toLowerCase().includes(ql)?0.3:0;
    const cntScore=(f.country||'').toLowerCase().includes(ql)?0.2:0;
    const score=Math.max(r1.score,rAlt.score)+secScore+cntScore;
    if((r1.match||rAlt.match||secScore||cntScore)&&!seen.has(f.title)){
      seen.add(f.title);
      results.push({...f,_score:score});
    }
  });

  // 2. Cortos individuales dentro de film_list
  FILMS.filter(f=>f.is_cortos&&f.film_list?.length).forEach(prog=>{
    prog.film_list.forEach(item=>{
      const r=fuzzyMatch(q,item.title);
      if(r.match&&!seen.has(item.title)){
        seen.add(item.title);
        results.push({_isCortoItem:true,_prog:prog,_score:r.score,
          title:item.title,country:item.country,duration:item.duration,
          flags:item.flags||countryToFlags(item.country||''),section:prog.section,is_cortos:false});
      }
    });
  });

  return results.sort((a,b)=>b._score-a._score).slice(0,10);
}

export function searchQuery(){
  const inp = document.getElementById('search-input');
  const results = document.getElementById('search-results');
  if(!inp || !results) return;
  const q = inp.value.trim();

  if(!q){ results.innerHTML = ''; return; }

  const matches = _searchAll(q);

  if(!matches.length){
    results.innerHTML = `<div class="search-empty">${emptyState(ICONS.search,t('search_sin_res_para')+' \u201c'+q+'\u201d')}</div>`;
    return;
  }

  const hasCortos=matches.some(f=>f._isCortoItem);
  const hasFilms=matches.some(f=>!f._isCortoItem);
  const hdr=hasFilms&&hasCortos?t('search_resultados')||'Resultados':hasCortos?t('label_cortos')||'Cortometrajes':t('planear_peliculas');
  results.innerHTML = `<div class="search-section-hdr">${hdr}</div>`
    + matches.map(f=>{
      const{displayTitle,progSuffix}=parseProgramTitle(f.title);
      const poster=getFilmPoster(f)||'';
      const _dur=f.duration!=null?String(f.duration):'';
      const meta=f._isCortoItem
        ?t('label_cortometraje')+(f._prog?' · '+parseProgramTitle(f._prog.title).displayTitle:'')
        :(_dur?_dur.replace(/\s*min\s*$/i,'')+' min':'')+(f.section?' · '+f.section.replace(/^[^ ]+ /,''):'');
      const _q=s=>String(s).replace(/"/g,'&quot;');
      const _siAttrs=f._isCortoItem
        ?`data-action="searchOpenCorto" data-title="${_q(f.title)}" data-country="${_q(f.country||'')}" data-dur="${_q(_dur)}" data-section="${_q(f.section||'')}" data-flags="${_q(f.flags||'🌍')}"`
        :`data-action="searchOpenFilm" data-title="${_q(f.title)}"`;
      return '<div class="search-item" '+_siAttrs+'>'
        +(poster?'<img class="search-item-poster" src="'+poster+'" onerror="this.remove()" alt="" loading="lazy">'
                :'<div class="search-item-poster"></div>')
        +'<div class="search-item-info">'
        +'<div class="search-item-title">'+displayTitle
        +(progSuffix?'<span class="txt-amber-sm"> '+progSuffix+'</span>':'')
        +'</div>'
        +'<div class="search-item-meta">'+meta+'</div>'
        +'</div>'
        +'<div class="search-item-arrow">›</div>'
        +'</div>';
    }).join('');
}

export function lugarOpen(){
  const btn = document.getElementById('lugar-btn');
  const r = btn.getBoundingClientRect();

  // Build dropdown
  const drop = document.createElement('div');
  drop.id = 'lugar-drop';
  drop.className = 'filter-drop'; // anatomía única; el build solo aporta posición
  drop.style.top = (r.bottom+4)+'px';
  drop.style.right = _dropRight(r.right);

  // Collect unique venues from FILMS
  // Embedded screenings[] format (Tribeca): expand all screenings, dedupe by title.
  // Flat format (FICCI/AFF): one row per screening, use f.venue directly.
  const venueMap = {};
  const _vSeen = new Set();
  (activeDay==='all'?FILMS:FILMS.filter(f=>f.day===activeDay))
    .forEach(f=>{
      if(f.screenings&&f.screenings.length){
        if(_vSeen.has(f.title)) return;
        _vSeen.add(f.title);
        const rel=activeDay==='all'?f.screenings:f.screenings.filter(s=>s.date===activeDay||s.day===activeDay);
        rel.forEach(s=>_acum(s.venue,f));
      } else {
        _acum(f.venue,f);
      }
    });
  // La clave agrupa por (CIUDAD, short), no por short a secas: el short no es único
  // entre ciudades —FICDEH tiene dos «Cinema Local» (Bogotá y Cali) y dos «Alianza
  // Francesa» (Barranquilla y Cartagena)— y fundirlas mezclaba las funciones de las
  // dos, descuadraba el conteo de la ciudad y hacía DESAPARECER la sede de la
  // segunda. Dentro de una misma ciudad el short sí agrupa a propósito: son las
  // salas de un edificio (Cinemateca Sala 2/3/Capital, las 5 de Plaza Bocagrande).
  function _acum(venue,film){
    const cfg=vcfg(venue);const short=cfg.short||venue;
    if(!short) return;
    const city=cfg.city||'';
    const k=city+SEDE_SEP+short;
    if(!venueMap[k]) venueMap[k]={key:k,label:short,city,films:[]};
    venueMap[k].films.push(film);
  }

  const venues = Object.values(venueMap)
    .map(v=>({...v, count:_filasQueVeras(v.films)}))
    .sort((a,b)=>b.count-a.count);
  // La ciudad cuenta sobre SU conjunto, no sumando el de sus sedes: sumarlas
  // duplica la obra que se proyecta en dos salas de la misma ciudad.
  const _cuentaCiudad=name=>_filasQueVeras(
    venues.filter(v=>v.city===name).reduce((a,v)=>a.concat(v.films),[]));

  // ── Nivel de CIUDAD (solo festivales multiciudad — FICDEH 11, Cinemancia 10) ──
  // Multiciudad = ≥2 ciudades DISTINTAS y NO VACÍAS entre las sedes visibles. El
  // borde que valida la regla es FINCA: 1 sede declara city y 5 no — una regla
  // ingenua ("¿hay city? agrupá") le inventaría dos grupos absurdos. Mono-ciudad
  // → este bloque no corre y el filtro queda EXACTO como siempre.
  // Anatomía aprobada (Juan, 5 ago 2026): nivel 1 = ciudades con conteo (caben
  // las 11 de FICDEH sin scroll); nivel 2 = "‹ Ciudades" + la ciudad misma
  // (filtra entera, centinela 'city:<Ciudad>' — ver venueMatches) + sus sedes.
  // Un solo target por fila; navegación interna no cierra el dropdown.
  // festivalCities es el dueño único (helpers.js) — el sheet de bienvenida
  // multiciudad lee la MISMA lista, así que nunca pueden divergir. Se filtra a
  // las ciudades visibles en este dropdown (que respeta el día activo).
  const _visibles=new Set(venues.map(v=>v.city).filter(Boolean));
  const cities = festivalCities(activeDay==='all'?FILMS:FILMS.filter(f=>f.day===activeDay))
    .filter(c=>_visibles.has(c.name));
  const multiCity = cities.length>=2;
  // Si ya hay selección (ciudad o sede), el dropdown abre DENTRO de su ciudad.
  let drillCity = (activeVenue&&activeVenue.startsWith('city:'))?activeVenue.slice(5):null;
  if(multiCity&&!drillCity&&activeVenue!=='all'){
    const cur=venues.find(v=>('sede:'+v.key)===activeVenue||v.label===activeVenue);
    if(cur&&cur.city) drillCity=cur.city;
  }

  function _row(dataV,label,count,opts={}){
    const isActive=(dataV==='all'&&activeVenue==='all')||(activeVenue===dataV);
    return '<div class="lugar-opt'+(isActive?' on':'')+(opts.cls?' '+opts.cls:'')+'" data-v="'+dataV.replace(/"/g,'&quot;')+'">'
      +(opts.icon||'')
      +'<span>'+label+'</span>'
      // "todos los lugares" sin conteo (total general sin referencia confunde);
      // ciudades y sedes sí muestran su número.
      // Marca de ciudad caída (2 sep 2026): el dato sale de festivalCities —el
      // MISMO dueño que alimenta la hoja de apertura—, así que las dos
      // superficies no pueden decir cosas distintas de la misma ciudad. Antes
      // acá se leía «Quibdó 14» sobre catorce obras con todas sus funciones
      // caídas por el sismo.
      +(opts.canc?'<span class="lugar-canc">'+t('notice_cancelada')+'</span>':'')
      +(count!=null?'<span class="lugar-cnt">'+count+'</span>':'')
      +(opts.chev?ICONS.chevronR:'')
      +'</div>';
  }

  function _paint(){
    if(!multiCity){
      // Camino de UNA ciudad: el short pelado, sin centinela. Es el que no puede
      // cambiar (FICMA es la regresión a vigilar) y por eso se deja intacto.
      drop.innerHTML=_row('all', t('filter_todos_lugares'), null)
        +venues.map(v=>_row(v.label, v.label, v.count, {icon:ICONS.pin})).join('');
      return;
    }
    if(!drillCity){
      drop.innerHTML=_row('all', t('filter_todos_lugares'), null)
        +cities.map(c=>_row('drill:'+c.name, c.name, _cuentaCiudad(c.name), {chev:true, canc:c.cancelled})).join('');
    } else {
      const cv=venues.filter(v=>v.city===drillCity);
      const ccount=_cuentaCiudad(drillCity);
      // La fila que filtra la CIUDAD entera es la única sin icono —el pin es de
      // las SEDES ([filtro-lugar-multiciudad]: la ciudad no lo lleva)— así que su
      // texto arrancaba 21px a la izquierda de todas las demás (63 contra 84).
      // En una lista, el ítem que cuelga fuera de la columna se lee como TÍTULO
      // de los de abajo, y esta es la única forma de pedir «todo Medellín». Un
      // hueco del ancho del pin la mete en la columna sin darle un pin que no le
      // toca. No es color —las tres filas miden el mismo rgb(136,136,136)—: es
      // la sangría.
      const _hueco='<span class="lugar-gutter" aria-hidden="true"></span>';
      drop.innerHTML='<div class="lugar-opt lugar-back" data-v="back">'+ICONS.chevronL+'<span>'+t('filter_ciudades')+'</span></div>'
        +_row('city:'+drillCity, drillCity, ccount, {icon:_hueco, canc:!!(cities.find(c=>c.name===drillCity)||{}).cancelled})
        +cv.map(v=>_row('sede:'+v.key, v.label, v.count, {icon:ICONS.pin})).join('');
    }
  }
  _paint();

  drop.addEventListener('click', e=>{
    const opt = e.target.closest('.lugar-opt');
    if(!opt) return;
    const v = opt.dataset.v;
    // Navegación INTERNA (no filtra, no cierra). stopPropagation es obligatorio:
    // _paint() reemplaza el innerHTML, así que para cuando el evento llega a
    // `document` la fila clickeada ya no está en el DOM → lugarOutside evalúa
    // drop.contains(e.target)===false y cerraría el dropdown recién repintado.
    if(v==='back'){ e.stopPropagation(); drillCity=null; _paint(); return; }
    if(v.startsWith('drill:')){ e.stopPropagation(); drillCity=v.slice(6); _paint(); return; }
    activeVenue = (v==='all'||v===activeVenue)?'all':v;
    // La CIUDAD se recuerda entre sesiones (es contexto: el usuario sigue estando
    // ahí la próxima vez que abra). Una SEDE no: es un filtro momentáneo. Elegir
    // "todos los lugares" o cambiar de ciudad reescribe/borra lo guardado, así que
    // siempre se puede cambiar desde el mismo dropdown.
    storage.setCityFilter(isCitySel(activeVenue)?activeVenue:'');
    lugarClose();
    _updateProgramaActiveFilter();
    if(activeMNav==='mnav-cartelera') _renderProgramaContent(true); else render(); // selección lugar → scroll al tope
  });

  document.body.appendChild(drop);
  drop.style.right = _dropRight(r.right, drop.offsetWidth);   // ancho real (ver _dropRight)
  _velaElCorte(drop);
  btn.classList.add('on');

  // Close on outside click
  setTimeout(()=>{
    document.addEventListener('click', lugarOutside);
  }, 0);
  // Close on scroll — dropdown is fixed, button moves with sticky bar
  window.addEventListener('scroll', lugarClose, {passive:true, once:true});
}

export function lugarToggle(){
  if(document.getElementById('seccion-drop')) seccionClose();
  if(document.getElementById('lugar-drop')) lugarClose();
  else lugarOpen();
}

export function fuzzyMatch(query,title){
  const q=normalize(query),t=normalize(title);
  if(t.includes(q)) return{match:true,score:100+q.length};
  if(!q.length) return{match:false,score:0};
  // La subsecuencia vale SOLO si es compacta: las letras tienen que caber en una
  // ventana de como mucho el doble de lo escrito. Sin este techo, «techo» casaba
  // con «The Children's Hour» (5 letras repartidas en 17) y con cuatro títulos
  // más, uno de 57 caracteres — 6 resultados de los que 1 tenía que ver. Medido
  // sobre el catálogo: una errata real (una letra caída) se pasa de la consulta
  // por 1 en 29 de 35 casos; el ruido empieza en 9. El umbral vive en ese hueco
  // y escala solo con lo escrito, sin constante mágica.
  // Se busca la ocurrencia MÁS COMPACTA, no la primera: arrancar por la primera
  // letra disponible puede desparramar un match que más adelante era estrecho.
  let best=-1;
  for(let s0=0;s0<t.length;s0++){
    if(t[s0]!==q[0]) continue;
    let qi=0,last=-1;
    for(let i=s0;i<t.length&&qi<q.length;i++) if(t[i]===q[qi]){ last=i; qi++; }
    if(qi<q.length) break;                       // desde acá ya no alcanza
    const sp=last-s0+1;
    if(best<0||sp<best) best=sp;
  }
  if(best>0&&best<=q.length*2) return{match:true,score:q.length};
  return{match:false,score:0};
}

export function normalize(str){
  return str.normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase();
}
