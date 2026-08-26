// ── src/domain/schedule.js — Fase 8 Step 5 (CABLEADO) ───────────────────────
//
// ESTADO: importado por src/main.js (Step 5). Conflicto + scheduling engine.
//
// DEPS:
//   - domain/time: toMin, parseDur (imports ↓)
//   - domain/film: effectiveDuration, screeningPassed, shuffle, scoreFilm (↓)
//   - domain/festival: travelMins (screensConflict) — import directo (↓)
//   - config: FESTIVAL_BUFFER (screensConflict) — import directo.
//   - festival-state vía STATE BRIDGE: availability (isScreeningBlocked),
//     FILMS + watched + prioritized (computeScenarios).
//
// WORKER: las sched pure fns tienen COPIAS en el template del calc worker; el
//   worker las consume vía eval(name).toString(). [worker-overlap] valida.

import { FESTIVAL_BUFFER, FESTIVAL_CONFIG } from "../config.js";
import { toMin, parseDur } from "./time.js";
import { effectiveDuration, blockDuration, durationForTravel, screeningPassed, shuffle, scoreFilm, _titleSeed, _mulberry32 } from "./film.js";
import { travelMins, _resolveVenue } from "./festival.js";
export function screensConflict(a,b){
  // Eventos informativos (info:true) — drop-in / sin hora fija: nunca generan
  // conflicto (no se planifican). Ver docs/SCHEMA.md.
  if((a&&a.info)||(b&&b.info)) return false;
  // Misma FUNCIÓN (mismo día, hora y sala, programadas una tras otra): nunca se
  // pisan — con una entrada ves las dos. Lo marca el loader vía `_slotKey`.
  if(a&&b&&a._slotKey&&a._slotKey===b._slotKey) return false;
  if(a.day!==b.day) return false;
  // ── Cuándo cuenta el Q&A (decisión de Juan, 30 jul 2026) ─────────────────────
  // El Q&A es OPCIONAL y sus +30 min son una ESTIMACIÓN. Solo compromete el
  // tiempo cuando salir de la función tiene costo: hay TRASLADO de por medio
  // (variables incontrolables — mejor no comprometerse). En la MISMA sede,
  // quedarse o salir es una decisión de asiento: el fin duro es el de las
  // películas (blockDuration) y el Q&A queda como ADVERTENCIA en Mi Plan
  // ("Q&A · si te quedás tenés ~N min"), que ya existía pero nunca podía
  // aparecer porque esta regla excluía la opción antes.
  // Caso que lo destapó: FINCA jue 13, función 18:00 (106+5) + Ziki 20:30 en el
  // MISMO Cine York — 39 min entre películas, el festival lo programó para que
  // se pudiera, y la app la excluía por 9<15 contando el Q&A estimado.
  const travel=(a.venue&&b.venue)?travelMins(a.venue,b.venue):0;
  // durationForTravel = la doctrina del Q&A (dueño único en domain/film.js)
  const aS=toMin(a.time), aE=aS+durationForTravel(a,travel);
  const bS=toMin(b.time), bE=bS+durationForTravel(b,travel);
  const minGap=Math.max(FESTIVAL_BUFFER, travel+FESTIVAL_BUFFER);
  if(aE<=bS) return (bS-aE)<minGap; // a antes que b
  if(bE<=aS) return (aS-bE)<minGap; // b antes que a
  return true; // solapamiento directo
}

// screensConflictReason(a,b) — el MOTIVO del conflicto, para poder explicarlo.
// screensConflict() responde sí/no (la consumen el planeador y su worker); ésta dice
// POR QUÉ, reusando esa misma regla como fuente (no la duplica) → nunca divergen.
// NO va en _SCHED_PURE_FNS: es para explicar en la UI, el worker no la necesita.
//
// Devuelve null si no hay conflicto, o:
//   {kind:'solape'}                     — las horas se pisan. Es un DATO (tenemos las
//                                         horas) → la UI puede AFIRMARLO.
//   {kind:'viaje', travel, gap, bFirst} — NO se pisan, pero el hueco < viaje+buffer
//                                         entre sedes distintas. `travel` es una
//                                         ESTIMACIÓN (heurística km/h) → la UI SUGIERE,
//                                         no afirma, y muestra los minutos.
//   {kind:'ajustado', gap, bFirst}      — misma sede, hueco < buffer (sin viaje).
// bFirst: true si `b` termina antes de que empiece `a` (para decir "desde X" vs "hasta X").
//
// Motivo: "Choca con X" era el mismo mensaje para dos problemas distintos y no decía
// ninguno — el usuario buscaba un solape inexistente (caso real TT: Contra Todo
// 13:00–14:55 en Cinemateca → Raíces del juego 16:00 en Fontanar: 65 min de hueco,
// 17,6 km de por medio).
// _cityOf — ciudad declarada de la sede de una función ('' si no declara).
// Local al dominio: no puede importar de view/. Lee la misma fuente que vcfg.
function _cityOf(s){
  const vs=(FESTIVAL_CONFIG[_activeFestId]||{}).venues||{};
  return (s&&s.venue)?(_resolveVenue(s.venue,vs).city||''):'';
}

export function screensConflictReason(a,b){
  if(!screensConflict(a,b)) return null;
  // Mismos fines que screensConflict (Q&A solo cuenta si hay traslado).
  // CIUDADES DISTINTAS (FICDEH 2026: 11 ciudades) — kind propio, antes que el de
  // viaje. Motivo: travelMins aplica velocidad URBANA (10 km/h con overhead de
  // transporte público) a distancias intermunicipales, así que Bogotá→Ibagué
  // (130 km, ~4 h en bus) le sale 13 h. Ese número no es confiable y NO se
  // muestra: la app dice la ciudad, que es un dato, y deja que el usuario juzgue.
  // Mismo criterio que el Q&A: donde no sabemos, no afirmamos.
  // metroArea: el festival declara que sus ciudades son UNA sola área de
  // traslado. Cinemancia 2026 corre en seis municipios —Medellín, Bello,
  // Itagüí, Envigado, Caldas, Copacabana— que son el Valle de Aburrá: ir de
  // uno a otro son minutos, no un viaje intermunicipal. Ahí la velocidad
  // urbana de travelMins SÍ es confiable, y decir «es en otra ciudad» informa
  // MENOS que decir cuántos minutos faltan. Sin la bandera nada cambia:
  // FICDEH sigue negándose a estimar Bogotá→Ibagué.
  const _metro=(FESTIVAL_CONFIG[_activeFestId]||{}).metroArea===true;
  const _ca=_cityOf(a), _cb=_cityOf(b);
  if(!_metro&&_ca&&_cb&&_ca!==_cb) return {kind:'ciudad', city:_cb, cityFrom:_ca};
  const _tv=(a.venue&&b.venue)?travelMins(a.venue,b.venue):0;
  const aS=toMin(a.time), aE=aS+durationForTravel(a,_tv);
  const bS=toMin(b.time), bE=bS+durationForTravel(b,_tv);
  if(aE>bS && bE>aS) return {kind:'solape'}; // ninguno termina antes de que arranque el otro
  const bFirst = bE<=aS;
  const gap = bFirst ? (aS-bE) : (bS-aE);
  const travel = (a.venue&&b.venue) ? travelMins(a.venue,b.venue) : 0;
  if(!travel) return {kind:'ajustado', gap, bFirst};
  // ¿El choque existe SOLO por el Q&A? Con traslado el Q&A cuenta (doctrina 30
  // jul), pero es OPCIONAL y sus 30 min son ESTIMADOS: si saliendo al final de
  // la película la función entra, eso no es una imposibilidad sino una decisión
  // que el usuario puede tomar. Medido en FINCA: 4 de 27 choques con Q&A son de
  // este tipo — «Tierra que habla» → «El amor duerme en la calle» deja 38 min de
  // hueco sin la charla y hacen falta 25.
  // La cuenta se repite acá con blockDuration en vez de durationForTravel; no se
  // delega en screensConflict porque ésa es, por definición, la que cuenta el Q&A.
  const _minGap=Math.max(FESTIVAL_BUFFER, travel+FESTIVAL_BUFFER);
  const _aE=toMin(a.time)+blockDuration(a), _bE=toMin(b.time)+blockDuration(b);
  const _chocaSinQa=(_aE<=toMin(b.time))?(toMin(b.time)-_aE)<_minGap
    :(_bE<=toMin(a.time))?(toMin(a.time)-_bE)<_minGap:true;
  const qaOnly=(a.has_qa||b.has_qa)&&!_chocaSinQa;
  return {kind:'viaje', travel, gap, bFirst, qaOnly};
}

export function isScreeningBlocked(s){
  const av=availability[s.day];if(!av) return false;
  // blockDuration (SIN Q&A): el bloque de "no disponible" mide contra el fin de
  // las PELÍCULAS. El Q&A es opcional y no hay traslado de por medio — si tu
  // bloque arranca cuando termina el film, salís del Q&A y ya. Excluir la
  // función por su Q&A estimado era el mismo sobre-compromiso del caso Ziki
  // (doctrina 30 jul 2026: el Q&A solo compromete cuando salir cuesta).
  const sStart=toMin(s.time),sEnd=sStart+blockDuration(s);
  // Chequeo de solapamiento completo: excluye funciones que ocurran durante el bloque
  return av.blocks.some(b=>sStart<toMin(b.to)&&sEnd>toMin(b.from));
}

// ── plannableScreens — DUEÑO ÚNICO de «qué funciones de este título son
// planificables AHORA MISMO, para vos» ───────────────────────────────────────
// Junta los cuatro filtros que el planeador aplica antes de decidir: cancelada,
// ya pasada, en una franja que vetaste, y la regla del taller multi-día.
//
// TALLER MULTI-DÍA: entero o nada — también frente a TU disponibilidad. La rama
// todo-o-nada del backtracking mete el grupo completo, pero el grupo ya venía
// FILTRADO: si vetaste la tarde de una de las sesiones, llegaba con 2 de 3 y el
// plan proponía medio taller. Quien se inscribe va a todas; un plan con 2 de 3
// no es medio taller, es un plan que miente — es lo que verifyPlan llama
// 'bloque-incompleto'. Se compara contra el CATÁLOGO, no contra el filtro, para
// que valga igual si la sesión falta por veto, por cancelación o porque pasó.
//
// Cazado por tests/recorrido-festival.spec.js en Leviza (9 ago 2026) al vetar un
// día entero. Vive acá y no inline porque la regla la necesitan tres: el
// planeador, el oráculo exacto y el recorrido por festival — y una regla con
// tres copias es una regla que se desincroniza.
// ── screeningPlannable — el predicado POR FUNCIÓN de «puede entrar a tu plan» ──
// La mitad por-función de plannableScreens, extraída como dueño único (16 ago
// 2026): el panel de alternativas reimplementaba 2 de los 4 chequeos y ofrecía
// funciones de otras ciudades (436 de 836 con filtro Bogotá) y canceladas por
// el sismo (118); el bloque de recuperación de Sugerencias se saltaba
// `_cancelled`. Cancelada · pasada · franja vetada · ciudad. La regla del
// taller entero-o-nada es GRUPAL y queda en plannableScreens, que es su casa.
// WORKER: viaja serializada (_SCHED_PURE_FNS) — PLAN_CITY_VENUES con guard de
// typeof, mismo patrón que en plannableScreens.
export function screeningPlannable(s){
  if(!s||s._cancelled) return false;
  if(screeningPassed(s)) return false;
  if(isScreeningBlocked(s)) return false;
  const _pv=(typeof PLAN_CITY_VENUES!=='undefined')?PLAN_CITY_VENUES:null;
  if(_pv&&s.venue&&!_pv.has(s.venue)) return false;
  return true;
}

export function plannableScreens(title){
  // PLAN_CITY_VENUES — el planificador NO cruza ciudades (QA de ojos frescos,
  // 15 ago 2026): con filtro Bogotá, «Calcular mi Plan» armaba el domingo en
  // Medellín y el lunes en Ibagué sin avisar, y las filas del plan no muestran
  // ciudad, así que era indetectable en pantalla. El set lo calcula calc.js
  // desde el filtro activo (venueMatches, el dueño del predicado de lugar) y
  // viaja al worker como payload. null = sin restricción.
  // `typeof` y no la referencia: este global no existe en el sandbox de los unit
  // tests ni en contextos que no calculan (la lección de FESTIVAL_POSTPONED).
  // La mitad por-función vive en screeningPlannable (dueño único); acá queda
  // lo que es de TÍTULO: el match y la regla grupal del taller.
  const screens=FILMS.filter(f=>f.title===title&&screeningPlannable(f));
  if(screens.length&&screens[0].is_recurring){
    const total=FILMS.filter(f=>f.title===title&&f.is_recurring&&f.day&&f.time&&!f._cancelled).length;
    if(total&&screens.length!==total) return [];
  }
  return screens;
}

export function sortScreensByStrategy(screens, allGroups){
  // Precalcular todas las funciones de todas las otras películas
  const allOtherScreenings=allGroups.flatMap(g=>g.screens);
  return [...screens].sort((a,b)=>{
    // Contar cuántas funciones ajenas conflictan con cada opción
    const conflA=allOtherScreenings.filter(s=>s!==a&&screensConflict(a,s)).length;
    const conflB=allOtherScreenings.filter(s=>s!==b&&screensConflict(b,s)).length;
    if(conflA!==conflB) return conflA-conflB; // menos conflictos primero
    // Si empatan, earliest finish time (termina antes = deja más espacio)
    // blockDuration: con anclaje, la función termina cuando termina el BLOQUE.
    const endA=toMin(a.time)+blockDuration(a);
    const endB=toMin(b.time)+blockDuration(b);
    return endA-endB;
  });
}

export function computeScenarios(titles){
  // Fix bug #2: RNG sembrado por la watchlist → output determinístico (misma
  // watchlist = mismo seed = misma secuencia de shuffles = mismos escenarios).
  // _titleSeed ordena internamente → independiente del orden de los títulos.
  const _rand=_mulberry32(_titleSeed(titles));
  // Excluir eventos informativos (info:true): no entran al plan generado.
  const pending=titles.filter(t=>!watched.has(t)&&!FILMS.some(f=>f.title===t&&f.info));
  const allPendingTitles=pending; // for section uniqueness check
  const baseGroups=pending.map(t=>{
    // `_cancelled` lo sella el loader desde NOTICES. Sin este filtro el
    // optimizador armaba el día alrededor de una función que no va a ocurrir.
    const screens=plannableScreens(t);
    const isPrio=prioritized.has(t);
    const sc=scoreFilm(t,screens,isPrio,allPendingTitles);
    const isRec=screens.length>0&&!!screens[0].is_recurring;
    return{title:t,screens,priority:isPrio,score:sc,is_recurring:isRec};
  }).filter(g=>g.screens.length>0);
  if(!baseGroups.length) return[];

  // Aplicar Mejora 2: ordenar las funciones de cada película por estrategia
  baseGroups.forEach(g=>{
    if(g.screens.length>1) g.screens=sortScreensByStrategy(g.screens,baseGroups);
  });

  // MRV + Score: restaurado (DP con grupos requiere formulación diferente)
  const mrvGroups=[...baseGroups].sort((a,b)=>{
    if(b.score!==a.score) return b.score-a.score;
    return a.screens.length-b.screens.length;
  });

  // ─────────────────────────────────────────────────────────────────────────
  // ⚠️  FIX CRÍTICO — NO REMOVER (Apr 2026)
  // MAX_NODES_PER_CALL debe aplicarse a AMBAS funciones: findMax/bb y collectAt
  // Sin este límite en findMax, el motor JS de mobile corta la recursión antes
  // que desktop → trueMax diferente entre dispositivos → opciones inconsistentes
  // (ej: desktop muestra 8 películas por opción, mobile solo 2)
  // Valor 80000: suficiente para watchlists de hasta ~25 películas en mobile.
  // DEBE declararse ANTES de findMax — const tiene zona muerta temporal (TDZ).
  // ─────────────────────────────────────────────────────────────────────────
  const MAX_NODES_PER_CALL=80000;

  function findMax(groups, mustIncludeAll){
    let best=0;
    let nodes=0;
    const _bbMax=groups.map(g=>g.is_recurring?g.screens.length:1);
    const _bbRem=[];let _s=0;for(let i=_bbMax.length-1;i>=0;i--){_s+=_bbMax[i];_bbRem[i]=_s;}
    function bb(idx,chosen){
      if(++nodes>MAX_NODES_PER_CALL) return;
      const remaining=idx<groups.length?_bbRem[idx]:0;
      if(chosen.length+remaining<=best) return;
      if(idx===groups.length){
        if(!mustIncludeAll){
          if(chosen.length>best) best=chosen.length;
        } else {
          const chosenTitles=new Set(chosen.map(s=>s._title));
          const allPrioritiesIn=groups.every(g=>!g.priority||chosenTitles.has(g.title));
          if(allPrioritiesIn&&chosen.length>best) best=chosen.length;
        }
        return;
      }
      const g=groups[idx];
      if(g.is_recurring){
        const allFit=g.screens.every(s=>!chosen.some(c=>screensConflict(c,s)));
        if(allFit){
          g.screens.forEach(s=>chosen.push({...s,_title:g.title}));
          bb(idx+1,chosen);
          g.screens.forEach(()=>chosen.pop());
        }
        if(!g.priority) bb(idx+1,chosen);
      } else {
        for(const s of g.screens){
          if(!chosen.some(c=>screensConflict(c,s))){
            chosen.push({...s,_title:g.title});bb(idx+1,chosen);chosen.pop();
          }
        }
        if(!g.priority) bb(idx+1,chosen);
        else bb(idx+1,chosen);
      }
    }
    bb(0,[]);
    return best;
  }

  const trueMax=findMax(mrvGroups,false);
  const hasPriorities=baseGroups.some(g=>g.priority);
  const maxWithPriorities=hasPriorities?findMax(mrvGroups,true):trueMax;
  const priorityCost=trueMax-maxWithPriorities;

  const seenKeys=new Set();const allScenarios=[];
  let incompatiblePriorities=false;

  function collectAt(groups,targetCount,enforcePriority){
    let nodes=0;
    const _btMax=groups.map(g=>g.is_recurring?g.screens.length:1);
    const _btRem=[];let _rs=0;for(let i=_btMax.length-1;i>=0;i--){_rs+=_btMax[i];_btRem[i]=_rs;}
    function backtrack(idx,chosen){
      if(allScenarios.length>=8) return;
      if(++nodes>MAX_NODES_PER_CALL) return; // mismo límite en todos los dispositivos
      if(chosen.length+(idx<groups.length?_btRem[idx]:0)<targetCount) return;
      if(idx===groups.length){
        if(chosen.length===targetCount){
          if(enforcePriority){
            const ct=new Set(chosen.map(s=>s._title));
            if(!groups.every(g=>!g.priority||ct.has(g.title))) return;
          }
          const key=chosen.map(s=>s._title+'@'+s.day+s.time).sort().join('|');
          if(!seenKeys.has(key)){seenKeys.add(key);allScenarios.push(chosen.map(c=>({...c})));}
        }
        return;
      }
      const g=groups[idx];
      if(g.is_recurring){
        const allFit=g.screens.every(s=>!chosen.some(c=>screensConflict(c,s)));
        if(allFit){
          g.screens.forEach(s=>chosen.push({...s,_title:g.title}));
          backtrack(idx+1,chosen);
          g.screens.forEach(()=>chosen.pop());
          if(allScenarios.length>=8) return;
        }
        if(!enforcePriority||!g.priority) backtrack(idx+1,chosen);
      } else {
        for(const s of g.screens){
          if(!chosen.some(c=>screensConflict(c,s))){
            chosen.push({...s,_title:g.title});backtrack(idx+1,chosen);chosen.pop();
            if(allScenarios.length>=8) return;
          }
        }
        if(!enforcePriority||!g.priority) backtrack(idx+1,chosen);
      }
    }
    backtrack(0,[]);
  }

  const prioritySorted=[...baseGroups].sort((a,b)=>{
    if(a.priority&&!b.priority) return -1;
    if(!a.priority&&b.priority) return 1;
    return a.screens.length-b.screens.length;
  });

  // Phase 1: scenarios WITH priorities — max 4 slots to leave room for diversity
  if(hasPriorities&&maxWithPriorities>0){
    collectAt(prioritySorted,maxWithPriorities,true);
    for(let i=0;i<20&&allScenarios.length<4;i++) collectAt(shuffle(baseGroups,_rand),maxWithPriorities,true);
  }

  // Phase 2: if still no scenarios (priorities all conflict with each other), fall back
  if(!allScenarios.length&&hasPriorities){
    incompatiblePriorities=true;
    collectAt(prioritySorted,trueMax,false);
    for(let i=0;i<20&&allScenarios.length<4;i++) collectAt(shuffle(baseGroups,_rand),trueMax,false);
  }

  // Phase 3 removida (modelo de "plan único" — sin enumeración de variaciones).
  // Caso sin prioridades: Phase 1 y 2 no corrieron → garantizamos ≥1 plan con
  // una sola pasada por collectAt(trueMax,false). El sort final deja el mejor
  // (menor dayBalance) en índice 0; la UI muestra solo ese.
  if(!hasPriorities) collectAt(prioritySorted,trueMax,false);

  allScenarios.forEach(sc=>sc.sort((a,b)=>a.day_order!==b.day_order?a.day_order-b.day_order:toMin(a.time)-toMin(b.time)));

  // ── Mejora 3: Balanceo por día ──
  // Calcular desviación estándar de películas por día — menor = más balanceado
  function dayBalance(sc){
    const counts={};
    sc.forEach(s=>{counts[s.day]=(counts[s.day]||0)+1;});
    const vals=Object.values(counts);
    if(vals.length<=1) return 0;
    const mean=vals.reduce((a,b)=>a+b,0)/vals.length;
    const variance=vals.reduce((a,v)=>a+Math.pow(v-mean,2),0)/vals.length;
    return Math.sqrt(variance); // 0 = perfectamente balanceado
  }
  // Ordenar: (1) planes que respetan TODAS las prioridades schedulables primero,
  // (2) entre iguales, menor dayBalance. Fix bug #1: antes ordenaba solo por
  // dayBalance, y un plan de Fase 3 de mayor cardinalidad SIN la prioridad podía
  // ganar el índice 0 ("óptimo"). Prioridades sin funciones (no en baseGroups) no
  // se exigen; si las prioridades son mutuamente incompatibles, ningún plan las
  // respeta todas → degrada a dayBalance (comportamiento previo).
  const _prioTitles=baseGroups.filter(g=>g.priority).map(g=>g.title);
  const _respectsPrios=sc=>{const inSc=new Set(sc.map(s=>s._title));return _prioTitles.every(t=>inSc.has(t));};
  allScenarios.sort((a,b)=>{
    const ra=_respectsPrios(a),rb=_respectsPrios(b);
    if(ra!==rb) return ra?-1:1;
    return dayBalance(a)-dayBalance(b);
  });
  const conflictingPriorityPairs=[];
  if(incompatiblePriorities){
    const prioGroups=baseGroups.filter(g=>g.priority);
    for(let i=0;i<prioGroups.length;i++){
      for(let j=i+1;j<prioGroups.length;j++){
        const allConflict=prioGroups[i].screens.every(s1=>prioGroups[j].screens.every(s2=>screensConflict(s1,s2)));
        if(allConflict) conflictingPriorityPairs.push([prioGroups[i].title,prioGroups[j].title]);
      }
    }
  }

  return allScenarios.map(sc=>{
    const included=new Set(sc.map(s=>s._title));
    return{
      schedule:sc,
      excluded:pending.filter(t=>!included.has(t)),
      incompatiblePriorities,
      conflictingPriorityPairs,
      trueMax,
      maxWithPriorities,
      priorityCost,
      dayBalance:Math.round(dayBalance(sc)*10)/10
    };
  });
}

// ── syncScheduleWithCatalog — el plan guarda la ELECCIÓN, el catálogo manda el resto ──
// Una entrada de savedAgenda es una copia congelada de la función al momento de
// elegirla. Si el catálogo cambia después (corrección de duración, anclaje de
// función nuevo, Q&A agregado), la copia miente — y de ella leen Mi Plan, los
// conflictos, el ICS, las notificaciones y Compartir. Bug real: plan de FINCA
// guardado antes del anclaje mostraba "18:05" de fin y "~115 min" de Q&A donde
// el catálogo vivo dice "19:51" y "~9 min" (31 jul 2026).
// Contrato:
//   - La identidad de la elección es título+día+hora EXACTOS. Con match, la
//     entrada se reemplaza por la función viva; solo sobreviven los campos
//     propios de la entrada (_title, _squeezed).
//   - Sin match, la entrada queda INTACTA: es el caso reprogramada/cancelada
//     que el camino de avisos marca con badge y salida. Nada se corrige ni se
//     borra en silencio.
//   - Idempotente: correrla dos veces = una vez (deriva todo del catálogo).
// ── sameEntry — DUEÑO ÚNICO de «esta entrada del Plan es aquella» ────────────
// La identidad de una función es título + día + hora + SEDE. La sede no es un
// adorno: FICDEH programa la misma obra el mismo día y a la misma hora en
// ciudades distintas — 13 casos medidos (ej. «La independencia», 13 AGO 14:00,
// en Bogotá Y en Ibagué). Sin ella, agendar la de Bogotá marcaba la fila de
// Ibagué como «en tu plan» (medido en main, 25 ago 2026): la app le decía a
// alguien de Ibagué que ya tenía una función que nunca agendó, y la que sí
// quería aparecía tomada.
//
// TOLERANCIA DELIBERADA: si UNO de los dos lados no declara sede, no se exige
// que coincida. Los planes guardados antes de que la sede viajara en la entrada
// no la tienen, y endurecer acá los desconectaría del catálogo — que es
// exactamente la pérdida de datos que se quiere evitar. Si los dos la declaran,
// tiene que coincidir.
//
// FALLA CERRADO por diseño: sin día u hora NO matchea nada. La versión previa
// de este predicado (revertida) matcheaba TODO cuando faltaban esos campos, así
// que un llamador que se olvidaba de pasarlos no daba error: borraba en masa.
// Acá el olvido es un no-op — se nota, pero no destruye.
export function sameEntry(a, b){
  if(!a || !b) return false;
  const ta = a._title || a.title, tb = b._title || b.title;
  if(!ta || ta !== tb) return false;
  if(!a.day || !b.day || a.day !== b.day) return false;
  if(!a.time || !b.time || a.time !== b.time) return false;
  return (!a.venue || !b.venue || a.venue === b.venue);
}

export function syncScheduleWithCatalog(schedule, films){
  if(!schedule||!schedule.length) return schedule;
  return schedule.map(e=>{
    // La identidad de una función incluye su SEDE. FICDEH programa el mismo
    // título el mismo día a la misma hora en ciudades distintas (13 tripletas
    // así, medido el 16 ago 2026), y matchear solo por título+día+hora hacía
    // que .find() devolviera la PRIMERA del catálogo: el plan guardado con
    // «Notas sobre un destierro · Cinemateca de Bogotá» amanecía en la
    // Cinemateca del Caribe (Barranquilla) tras recargar — lo cazó la re-corrida
    // del QA de ojos frescos. Si la entrada trae sede y esa sede ya no existe
    // en el catálogo, la entrada queda INTACTA: es el camino reprogramada/
    // cancelada que los avisos marcan con badge y salida — nunca un swap mudo.
    const live=(films||[]).find(f=>sameEntry(f, e));
    if(!live) return e;
    const out={...live,_title:e._title};
    if(e._squeezed) out._squeezed=e._squeezed;
    return out;
  });
}

// ── verifyPlan — CERTIFICADOR independiente del plan ──────────────────────────
// Patrón "certifying algorithms": en vez de confiar en cómo se construyó el
// plan, se verifica el RESULTADO contra las reglas del dominio. Barato de
// auditar (lee, no construye) y sirve a dos amos: el oráculo del planeador en
// CI (falla duro) y el chokepoint de escritura (PR 2: report-only en prod).
// Fuente de factibilidad: el MISMO screensConflict de producción — si el
// verificador re-implementara la regla sería una segunda opinión, no un
// certificado.
// `_squeezed` se respeta: es una violación DELIBERADA que el usuario aceptó
// (plan apretado a sabiendas) — certificarla como error sería un falso rojo.
// Devuelve {ok, violations:[{kind, title, with?}]} — kinds:
//   'conflicto'  — dos entradas no-squeezed en conflicto real
//   'cancelada'  — entrada cuya función está _cancelled
//   'duplicado'  — la MISMA ENTRADA dos veces (título+día+hora+sede)
//   'pasada'     — (opt-in checkPassed) función ya pasada al momento de armar
export function verifyPlan(schedule, opts){
  const v=[];
  const list=schedule||[];
  list.forEach(s=>{
    const t=s._title||s.title||'';
    if(s._cancelled) v.push({kind:'cancelada', title:t});
    if(opts&&opts.checkPassed&&screeningPassed(s)) v.push({kind:'pasada', title:t});
  });
  for(let i=0;i<list.length;i++){
    for(let j=i+1;j<list.length;j++){
      const a=list[i], b=list[j];
      // DUPLICADO — por IDENTIDAD DE ENTRADA, vía sameEntry (el dueño único),
      // no por título. Antes bastaba con repetir el título para ser duplicado,
      // y is_recurring era el permiso que salvaba a los talleres. Esa regla ya
      // no distingue: un plan legítimo con la misma obra en DOS funciones —lo
      // que el usuario puede pedir a propósito— salía marcado igual que un plan
      // con la MISMA función dos veces, que sí es corrupción. Un guardián que
      // grita siempre no avisa nunca. Con identidad de entrada, el permiso de
      // is_recurring sobra: las sesiones de un taller ya tienen día distinto.
      // El `continue` evita el eco: dos entradas idénticas también «chocan»
      // consigo mismas y reportarlo dos veces enmascara el hallazgo real.
      if(sameEntry(a,b)){ v.push({kind:'duplicado', title:a._title||a.title||'', day:a.day, time:a.time}); continue; }
      if(a._squeezed||b._squeezed) continue;
      if(screensConflict(a,b)) v.push({kind:'conflicto', title:a._title||a.title, with:b._title||b.title});
    }
  }
  // BLOQUE INCOMPLETO — un taller multi-día se toma ENTERO: quien se inscribe va
  // a todas las sesiones. Un plan con 1 de 2 no es medio taller, es un plan que
  // miente. El chequeo de duplicado de arriba no puede cazarlo: para él las
  // repeticiones del título son legítimas, y ese es justo el permiso que da
  // is_recurring. Necesita el catálogo (opts.catalog) porque el schedule solo sabe
  // lo que YA está; sin catálogo no se verifica (las llamadas viejas no cambian).
  const cat=opts&&opts.catalog;
  if(cat){
    const enPlan={};
    list.forEach(s=>{ const t=s._title||s.title||''; if(s.is_recurring) enPlan[t]=(enPlan[t]||0)+1; });
    Object.keys(enPlan).forEach(t=>{
      const total=cat.filter(f=>f&&f.is_recurring&&(f.title===t)&&f.day&&f.time).length;
      if(total&&enPlan[t]!==total)
        v.push({kind:'bloque-incompleto', title:t, tiene:enPlan[t], necesita:total});
    });
  }
  // CIUDAD CRUZADA — la red del chokepoint para la restricción de plan por
  // ciudad (#594). Va acá y no solo en plannableScreens porque el squeeze de
  // excluidas inserta DESPUÉS de computeScenarios y queda exento del chequeo
  // de conflicto (`_squeezed`): por esa puerta entraron Medellín y Barranquilla
  // con filtro Bogotá. Un guardián que solo mira el camino feliz no es red.
  const _pv=(typeof PLAN_CITY_VENUES!=='undefined')?PLAN_CITY_VENUES:null;
  if(_pv) list.forEach(s=>{
    if(s.venue&&!_pv.has(s.venue)) v.push({kind:'ciudad-fuera', title:s._title||s.title||'', venue:s.venue});
  });
  return {ok:v.length===0, violations:v};
}
