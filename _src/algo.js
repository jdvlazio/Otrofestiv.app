// ══════════════════════════════════════════════════════════════════
// ALGORITMO DE PLANIFICACIÓN — exhaustive max + MRV + backtracking
// Dependencias: FILMS, watchlist, prioritized, availability,
//               screensConflict(), screeningPassed(), isScreeningBlocked(),
//               parseDur(), toMin(), FESTIVAL_BUFFER
// ══════════════════════════════════════════════════════════════════

// ── ALGORITHM — exhaustive max + MRV + random restarts ──
function shuffle(arr){
  const a=[...arr];
  for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}
  return a;
}

// ── Mejora 1: Scoring por película ──
// Pondera cuánto vale incluir una película según rareza, sección y duración
function scoreFilm(title, screens, isPriority, allTitles){
  let score=0;
  // Prioridad explícita: peso máximo
  if(isPriority) score+=100;
  // Unicidad: menos funciones = más difícil de ver = mayor peso
  const n=screens.length;
  if(n===1) score+=40;
  else if(n===2) score+=20;
  else score+=5;
  // Sección única: si es la única película de su sección en la watchlist
  const mySection=screens[0]?.section||'';
  const siblingsInSection=allTitles.filter(t=>{
    if(t===title) return false;
    return FILMS.some(f=>f.title===t&&f.section===mySection);
  });
  if(siblingsInSection.length===0) score+=15;
  // Duración larga: película de >150 min es un compromiso grande, priorizar
  const dur=parseInt(screens[0]?.duration)||0;
  if(dur>150) score+=10;
  // Urgencia: si todas las funciones restantes son hoy, el título se acaba
  const todayStr=simTodayStr();
  if(screens.length>0&&screens.every(s=>FESTIVAL_DATES[s.day]===todayStr)) score+=25;
  return score;
}

// ── Mejora 2: Interval Scheduling — ordenar funciones por conflictos mínimos + fin temprano ──
// Para cada película con múltiples funciones, prioriza la que:
// 1. Conflicta con menos otras funciones de la watchlist (menos bloqueos)
// 2. Termina más temprano (earliest-finish-time: principio clásico de interval scheduling)
function sortScreensByStrategy(screens, allGroups){
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


// ── Mejora 3: Greedy floor — earliest-finish-time ──
// Garantiza un piso para trueMax: el B&B siempre parte de al menos este resultado.
// Si el nodo-limit corta el árbol, el greedy salva la estimación.
// Solo aplica a mustIncludeAll=false — para prioridades el B&B arranca desde 0.
function greedyFloor(groups){
  const all=groups.flatMap(g=>g.screens.map(s=>({...s,_gTitle:g.title})));
  all.sort((a,b)=>(toMin(a.time)+parseDur(a.duration))-(toMin(b.time)+parseDur(b.duration)));
  const chosen=[];
  const used=new Set();
  for(const s of all){
    if(used.has(s._gTitle)) continue;
    if(!chosen.some(c=>screensConflict(c,s))){chosen.push(s);used.add(s._gTitle);}
  }
  return chosen.length;
}



/* ── ALGO: backtracking MRV + escenarios óptimos ────────────────────── */
function computeScenarios(titles){
  const pending=titles.filter(t=>!watched.has(t));
  const allPendingTitles=pending; // for section uniqueness check
  const baseGroups=pending.map(t=>{
    const screens=FILMS.filter(f=>f.title===t&&!isScreeningBlocked(f)&&!screeningPassed(f));
    const isPrio=prioritized.has(t);
    const sc=scoreFilm(t,screens,isPrio,allPendingTitles);
    return{title:t,screens,priority:isPrio,score:sc};
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
    let best=mustIncludeAll?0:greedyFloor(groups); // piso garantizado si no hay prioridades
    let nodes=0;
    function bb(idx,chosen){
      if(++nodes>MAX_NODES_PER_CALL) return;
      const remaining=groups.length-idx;
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
      for(const s of g.screens){
        if(!chosen.some(c=>screensConflict(c,s))){
          chosen.push({...s,_title:g.title});bb(idx+1,chosen);chosen.pop();
        }
      }
      if(!mustIncludeAll||!g.priority) bb(idx+1,chosen);
      // Si mustIncludeAll=true y el grupo es prioritario, NO se puede saltar
    }
    bb(0,[]);
    return best;
  }

  const trueMax=findMax(mrvGroups,false);
  const hasPriorities=baseGroups.some(g=>g.priority);
  const maxWithPriorities=hasPriorities?findMax(mrvGroups,true):trueMax;
  const priorityCost=trueMax-maxWithPriorities;

  const seenKeys=new Set();const seenTitleSets=new Set();const allScenarios=[];
  let incompatiblePriorities=false;

  function collectAt(groups,targetCount,enforcePriority){
    let nodes=0;
    function backtrack(idx,chosen){
      if(allScenarios.length>=8) return;
      if(++nodes>MAX_NODES_PER_CALL) return; // mismo límite en todos los dispositivos
      if(chosen.length+(groups.length-idx)<targetCount) return;
      if(idx===groups.length){
        if(chosen.length===targetCount){
          if(enforcePriority){
            const ct=new Set(chosen.map(s=>s._title));
            if(!groups.every(g=>!g.priority||ct.has(g.title))) return;
          }
          const key=chosen.map(s=>s._title+'@'+s.day+s.time).sort().join('|');
          const titleKey=chosen.map(s=>s._title).sort().join('|');
          if(!seenKeys.has(key)&&!seenTitleSets.has(titleKey)){
            seenKeys.add(key);seenTitleSets.add(titleKey);
            allScenarios.push(chosen.map(c=>({...c})));
          }
        }
        return;
      }
      const g=groups[idx];
      for(const s of g.screens){
        if(!chosen.some(c=>screensConflict(c,s))){
          chosen.push({...s,_title:g.title});backtrack(idx+1,chosen);chosen.pop();
          if(allScenarios.length>=8) return;
        }
      }
      if(!enforcePriority||!g.priority) backtrack(idx+1,chosen);
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
    for(let i=0;i<20&&allScenarios.length<4;i++) collectAt(shuffle(baseGroups),maxWithPriorities,true);
  }

  // Phase 2: if still no scenarios (priorities all conflict with each other), fall back
  if(!allScenarios.length&&hasPriorities){
    incompatiblePriorities=true;
    collectAt(prioritySorted,trueMax,false);
    for(let i=0;i<20&&allScenarios.length<4;i++) collectAt(shuffle(baseGroups),trueMax,false);
  }

  // Phase 3: fill remaining slots with diverse no-priority scenarios
  for(let i=0;i<30&&allScenarios.length<8;i++) collectAt(shuffle(baseGroups),trueMax,false);

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
  // Ordenar: primero los más balanceados (menor desviación estándar)
  allScenarios.sort((a,b)=>dayBalance(a)-dayBalance(b));

  return allScenarios.map(sc=>{
    const included=new Set(sc.map(s=>s._title));
    return{
      schedule:sc,
      excluded:pending.filter(t=>!included.has(t)),
      incompatiblePriorities,
      trueMax,
      maxWithPriorities,
      priorityCost,
      dayBalance:Math.round(dayBalance(sc)*10)/10
    };
  });
}

// ── SUGGESTIONS after saved agenda ──
function getSuggestions(){
  // ── Guards: necesitamos un plan activo ──
  // Fix Bug 1: no retornar vacío si saved.length===0 — puede haber días futuros libres
  if(!savedAgenda||!savedAgenda.schedule.length) return{};
  const saved=savedAgenda.schedule.filter(s=>!screeningPassed(s));
  // Si saved está vacío (todos los planes pasaron), seguimos para mostrar días futuros
  const savedTitles=new Set(saved.map(s=>s._title));

  // hardExclude: global — nunca mostrar lo que ya está en el plan o ya se vio
  const hardExclude=new Set([...savedTitles,...watched]);
  const byDay={};

  // ── Slots reservados: películas recientemente quitadas ──
  const currentSaved=savedAgenda?savedAgenda.schedule:[];
  lastRemovedSlots.forEach(rs=>{
    if(savedTitles.has(rs._title)||screeningPassed(rs)) return;
    const slotFree=!currentSaved.some(s=>screensConflict(s,rs));
    if(!slotFree) return;
    const day=rs.day;
    if(!byDay[day]) byDay[day]=[];
    byDay[day].push({...rs,gapCtx:'Restaurar al mismo horario',_isRestored:true});
    hardExclude.add(rs._title);
  });

  DAY_KEYS.forEach(day=>{
    // Fix Bug 2: seenDiscover y seenRecovery se reinician POR DÍA
    // Un film puede sugerirse en distintos días (son funciones distintas)
    // Solo hardExclude es global (ya en plan o ya visto)
    const seenDay=new Set([...hardExclude]);

    const dayItems=saved.filter(s=>s.day===day).sort((a,b)=>toMin(a.time)-toMin(b.time));

    // Calcular huecos del día
    const slots=[];
    if(dayItems.length===0){
      // Día completamente libre — toda la jornada disponible
      slots.push({start:0,end:25*60,ctx:'Día libre'});
    } else {
      if(toMin(dayItems[0].time)>60)
        slots.push({start:0,end:toMin(dayItems[0].time)-FESTIVAL_BUFFER,ctx:`Antes de ${(dayItems[0]._title||'').split(' ').slice(0,3).join(' ')}…`});
      for(let i=0;i<dayItems.length-1;i++){
        const a=dayItems[i],b=dayItems[i+1];
        const aEnd=toMin(a.time)+parseDur(a.duration)+FESTIVAL_BUFFER;
        const bStart=toMin(b.time)-FESTIVAL_BUFFER;
        if(bStart>aEnd)
          slots.push({start:aEnd,end:bStart,ctx:`Entre ${(a._title||'').split(' ').slice(0,3).join(' ')}… y ${(b._title||'').split(' ').slice(0,3).join(' ')}…`});
      }
      const last=dayItems[dayItems.length-1];
      const lastEnd=toMin(last.time)+parseDur(last.duration)+FESTIVAL_BUFFER;
      slots.push({start:lastEnd,end:25*60,ctx:`Después de ${(last._title||'').split(' ').slice(0,3).join(' ')}…`});
    }

    // Bloque 1 — Descubrimiento: cualquier film del festival que quepa
    // Fix Bug 3: watchlist NO excluida de Bloque 1 — se muestra todo lo disponible
    // El contexto 'De tu lista' se añade si está en watchlist
    if(slots.length){
      FILMS.forEach(f=>{
        if(seenDay.has(f.title)||screeningPassed(f)||f.day!==day||isScreeningBlocked(f)) return;
        const fStart=toMin(f.time),fEnd=fStart+parseDur(f.duration);
        const slot=slots.find(sl=>fStart>=sl.start&&fEnd<=sl.end&&fEnd-fStart>=20);
        if(slot){
          // Advertencia de viaje: verifica tiempo desde/hacia funciones adyacentes del plan
          let _travelWarn=null;
          const prevPlan=[...dayItems].filter(pi=>toMin(pi.time)+parseDur(pi.duration)<=fStart)
            .sort((a,b)=>toMin(b.time)-toMin(a.time))[0];
          const nextPlan=[...dayItems].filter(pi=>toMin(pi.time)>=fEnd)
            .sort((a,b)=>toMin(a.time)-toMin(b.time))[0];
          if(prevPlan&&f.venue&&prevPlan.venue){
            const tr=travelMins(_effectiveVenue(prevPlan),f.venue);
            const gap=fStart-(toMin(prevPlan.time)+parseDur(prevPlan.duration));
            if(tr>0&&gap<tr+FESTIVAL_BUFFER){
              const lbl=(_FEST_TRANSPORT==='walking'||(tr<=12&&_FEST_TRANSPORT==='mixed'))?UI.travel.walking:UI.travel.transit;
              _travelWarn=`▲ ~${tr} min ${lbl}`;
            }
          }
          if(!_travelWarn&&nextPlan&&f.venue&&nextPlan.venue){
            const tr=travelMins(f.venue,_effectiveVenue(nextPlan));
            const gap=toMin(nextPlan.time)-fEnd;
            if(tr>0&&gap<tr+FESTIVAL_BUFFER){
              const lbl=(_FEST_TRANSPORT==='walking'||(tr<=12&&_FEST_TRANSPORT==='mixed'))?UI.travel.walking:UI.travel.transit;
              _travelWarn=`▲ ~${tr} min ${lbl} a la siguiente`;
            }
          }
          seenDay.add(f.title);
          if(!byDay[day]) byDay[day]=[];
          const inWL=watchlist.has(f.title);
          byDay[day].push({...f,
            gapCtx: inWL ? 'De tu lista · cabe en tu agenda' : slot.ctx,
            _inWatchlist: inWL,
            _travelWarn
          });
        }
      });
    }
  });

  // ── Ordenar: watchlist primero, luego cronológico ──
  Object.keys(byDay).forEach(d=>{
    byDay[d].sort((a,b)=>{
      if(a._inWatchlist&&!b._inWatchlist) return -1;
      if(!a._inWatchlist&&b._inWatchlist) return 1;
      return toMin(a.time)-toMin(b.time);
    });
  });
  return byDay;
}

// ── POST-SELECTION SQUEEZE ─────────────────────────────────────────
// Tras elegir una opción, inserta películas excluidas de la watchlist
// que quepan en los huecos del plan elegido.
// ── POST-SELECTION SQUEEZE ──
// Tras elegir una opción, intenta insertar películas excluidas de la watchlist
// que quepan en los huecos reales del plan elegido (usando screensConflict ±10 min).
// Puede superar trueMax porque ese era el máximo dentro del árbol explorado,
// no el máximo real del calendario.
function squeezeExcluded(schedule, excludedTitles){
  const result=[...schedule];
  // Ordenar excluidas por score descendente — misma lógica que el algoritmo
  const scored=excludedTitles.map(t=>{
    const screens=FILMS.filter(f=>f.title===t&&!screeningPassed(f)&&!isScreeningBlocked(f));
    return{title:t,screens,score:scoreFilm(t,screens,prioritized.has(t),[...watchlist])};
  }).filter(g=>g.screens.length>0).sort((a,b)=>b.score-a.score);

  scored.forEach(({title,screens})=>{
    // Ordenar funciones por estrategia — menos conflictos + fin temprano
    const sorted=sortScreensByStrategy(screens,[...scored]);
    for(const s of sorted){
      if(!result.some(c=>screensConflict(c,s))){
        result.push({...s,_title:title,_squeezed:true});
        break; // encontró slot, pasar al siguiente título
      }
    }
  });
  return result;
}
