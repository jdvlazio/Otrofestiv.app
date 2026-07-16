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

import { FESTIVAL_BUFFER } from "../config.js";
import { toMin, parseDur } from "./time.js";
import { effectiveDuration, screeningPassed, shuffle, scoreFilm, _titleSeed, _mulberry32 } from "./film.js";
import { travelMins } from "./festival.js";
export function screensConflict(a,b){
  // Eventos informativos (info:true) — drop-in / sin hora fija: nunca generan
  // conflicto (no se planifican). Ver docs/SCHEMA.md.
  if((a&&a.info)||(b&&b.info)) return false;
  if(a.day!==b.day) return false;
  // effectiveDuration: suma 30 min si has_qa:true (Q&A extiende la función)
  const aS=toMin(a.time), aE=aS+effectiveDuration(a);
  const bS=toMin(b.time), bE=bS+effectiveDuration(b);
  // Gap requerido: tiempo de viaje entre sedes + buffer mínimo
  const travel=(a.venue&&b.venue)?travelMins(a.venue,b.venue):0;
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
export function screensConflictReason(a,b){
  if(!screensConflict(a,b)) return null;
  const aS=toMin(a.time), aE=aS+effectiveDuration(a);
  const bS=toMin(b.time), bE=bS+effectiveDuration(b);
  if(aE>bS && bE>aS) return {kind:'solape'}; // ninguno termina antes de que arranque el otro
  const bFirst = bE<=aS;
  const gap = bFirst ? (aS-bE) : (bS-aE);
  const travel = (a.venue&&b.venue) ? travelMins(a.venue,b.venue) : 0;
  return travel>0 ? {kind:'viaje', travel, gap, bFirst} : {kind:'ajustado', gap, bFirst};
}

export function isScreeningBlocked(s){
  const av=availability[s.day];if(!av) return false;
  // effectiveDuration (no parseDur): incluye los +30 de Q&A, consistente con
  // screensConflict. Sin esto, el Q&A de una función podía correr dentro de un
  // bloque de no-disponibilidad sin ser detectado. (has_qa:false → idéntico a parseDur.)
  const sStart=toMin(s.time),sEnd=sStart+effectiveDuration(s);
  // Chequeo de solapamiento completo: excluye funciones que ocurran durante el bloque
  return av.blocks.some(b=>sStart<toMin(b.to)&&sEnd>toMin(b.from));
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
    const endA=toMin(a.time)+parseDur(a.duration);
    const endB=toMin(b.time)+parseDur(b.duration);
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
    const screens=FILMS.filter(f=>f.title===t&&!isScreeningBlocked(f)&&!screeningPassed(f));
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
