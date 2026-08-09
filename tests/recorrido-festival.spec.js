// @ts-check
// recorrido-festival.spec.js — el viaje completo de un usuario, festival por festival.
//
// POR QUÉ EXISTE
// `docs/QA-FULL.md` definió en mayo de 2026 un protocolo de 92 checks y dejó tres
// bloques escritos pero SIN ejecutar: E (Intereses), F (Planear) y G (Mi Plan).
// Corrió una vez. Pasaron cinco festivales y no volvió a correr. Que un protocolo
// manual se ejecute una vez en tres meses no es descuido: es la prueba de que lo
// manual no se sostiene. Estos son esos tres bloques, vueltos código.
//
// QUÉ CUBRE QUE NO CUBRÍA NADA
// Los specs existentes prueban piezas sueltas con un festival fijo (Leviza, Tribeca)
// y títulos hardcodeados. Acá se recorre el viaje ENTERO —intereses → prioridades →
// ya vistas → disponibilidad → Planear → auditar el plan → Mi Plan → sugerencias—
// y se hace CON CADA FESTIVAL del config. Un festival nuevo entra a la cobertura al
// agregar su entrada + su JSON: cero edición de specs (festivalTestIds).
//
// LA AUDITORÍA ES DEL DOMINIO, NO DEL DOM
// El plan que produce la UI se certifica con `verifyPlan` —el mismo certificador
// que usa el oráculo en CI y el chokepoint de escritura—. El DOM se usa para
// EJERCER el flujo (clicks reales en Planear), no para juzgar el resultado: un
// aserto sobre texto renderizado se rompe con cada cambio de copy y no dice nada
// sobre si el plan es correcto.
//
// Complementa, no duplica, tests/unit/plannerOracle.test.js: allá se prueba que el
// motor es óptimo con datos reales; acá, que la app CONECTA ese motor con lo que el
// usuario toca. Un motor perfecto mal cableado da el mismo plan malo.

const { test, expect } = require('@playwright/test');
const { enterFestival, festivalTestIds, goToPlanear } = require('./helpers');

const FESTIVALES = festivalTestIds();

// Semilla determinista por festival: mismo festival = misma selección de títulos.
// Sin esto un fallo no se puede reproducir, y un test que no se reproduce no se
// arregla: se silencia.
function elegirTitulos(titulos, cuantos, semillaTexto) {
  let s = [...semillaTexto].reduce((a, c) => (a * 31 + c.charCodeAt(0)) % 2147483648, 17);
  const rnd = () => (s = (s * 1103515245 + 12345) % 2147483648) / 2147483648;
  const orden = [...titulos].sort(); // orden estable antes de muestrear
  const out = [], usados = new Set();
  while (out.length < Math.min(cuantos, orden.length)) {
    const t = orden[Math.floor(rnd() * orden.length)];
    if (!usados.has(t)) { usados.add(t); out.push(t); }
  }
  return out;
}

for (const festId of FESTIVALES) {
  test(`R01 — ${festId}: recorrido completo (intereses → planear → mi plan)`, async ({ page }) => {
    const errores = [];
    page.on('pageerror', e => errores.push(e.message));

    // ── El festival, un día ANTES de empezar ──────────────────────────────────
    // Ancla temporal obligatoria: sin ella el resultado depende del día en que
    // corra la suite, y un festival ya pasado no tiene nada que planificar.
    await enterFestival(page, festId);
    const simTime = await page.evaluate((id) => {
      const cfg = FESTIVAL_CONFIG[id] || {};
      if (!cfg.festivalStartStr) return null;
      const inicio = new Date(cfg.festivalStartStr + (cfg.timezoneOffset || '-05:00'));
      return new Date(inicio.getTime() - 12 * 3600 * 1000).toISOString();
    }, festId);
    if (!simTime) { test.skip(true, `${festId}: sin festivalStartStr`); return; }
    await enterFestival(page, festId, simTime);

    // ── BLOQUE E — Intereses, prioridades, ya vistas ──────────────────────────
    const catalogo = await page.evaluate(() => {
      const planificables = [...new Set(FILMS
        .filter(f => f.day && f.time && !f.info && !f._cancelled)
        .map(f => f.title))];
      return { planificables, prioLimit: typeof PRIO_LIMIT !== 'undefined' ? PRIO_LIMIT : 4 };
    });
    if (catalogo.planificables.length < 3) {
      test.skip(true, `${festId}: menos de 3 obras planificables`);
      return;
    }

    const elegidos = elegirTitulos(catalogo.planificables, 6, festId);
    const prioridades = elegidos.slice(0, Math.min(2, catalogo.prioLimit));
    const yaVista = elegidos.length > 4 ? elegidos[elegidos.length - 1] : null;

    const estado = await page.evaluate(({ elegidos, prioridades, yaVista }) => {
      watchlist.clear(); prioritized.clear(); watched.clear();
      elegidos.forEach(t => watchlist.add(t));
      prioridades.forEach(t => prioritized.add(t));
      if (yaVista) watched.add(yaVista);
      // Disponibilidad: se veta el día ENTERO donde la watchlist tiene más
      // funciones — es decir, justo donde al planeador le duele.
      //
      // El primer borrador vetaba 09:00–13:00 del primer día. Pasaba en los 12
      // festivales… y también pasaba con un planeador MUTADO que ignoraba la
      // disponibilidad por completo: 10 de 11 planes no tenían nada en esa franja,
      // así que la restricción estaba puesta pero no apretaba. Una restricción que
      // no ata no prueba nada. Se elige el día de mayor presión para que atar sea
      // la única forma de pasar.
      //
      // INVARIANTE: `availability` tiene una entrada {blocks:[]} por CADA día del
      // festival (state/festival-context.js la siembra así). La vista cuenta con
      // eso —isFullDayBlocked lee availability[day].blocks sin guarda— mientras
      // que el dominio no. Se resetea COMO LO HACE LA APP: blocks a [], la clave
      // queda; vaciar el mapa rompía el render de Planear en los 12 festivales.
      DAY_KEYS.forEach(d => { availability[d] = { blocks: [] }; });
      let dia = null;
      if (DAY_KEYS.length > 1) {
        const porDia = {};
        FILMS.filter(f => f.day && f.time && watchlist.has(f.title))
             .forEach(f => { porDia[f.day] = (porDia[f.day] || 0) + 1; });
        dia = Object.keys(porDia).sort((a, b) => (porDia[b] - porDia[a]) || (DAY_KEYS.indexOf(a) - DAY_KEYS.indexOf(b)))[0] || null;
        if (dia) availability[dia] = { blocks: [{ from: '00:00', to: '23:59' }] };
      }
      saveState('wl', 'watched');
      // EXIGIBLES: una prioridad cuyas únicas funciones caen en el día vetado deja
      // de tener funciones utilizables, no entra a baseGroups y producción —con
      // razón— no la exige. Se calcula ACÁ, después de sembrar la disponibilidad,
      // con el dueño de la regla. El primer borrador exigía toda prioridad que
      // existiera en el catálogo y acusaba al planeador de dejar afuera obras que
      // el propio usuario había vetado: 7 de 11 festivales en rojo por un aserto
      // equivocado, no por un bug.
      // Se le PREGUNTA al dueño (plannableScreens) en vez de rearmar los cuatro
      // filtros a mano: cancelada, pasada, franja vetada y taller entero-o-nada.
      const exigibles = [...prioritized].filter(t => plannableScreens(t).length > 0);
      return { watchlist: watchlist.size, prioritized: prioritized.size, watched: watched.size, diaVetado: dia, exigibles };
    }, { elegidos, prioridades, yaVista });

    expect(estado.watchlist).toBeGreaterThan(0);
    expect(estado.prioritized).toBeGreaterThan(0);

    // ── BLOQUE F — Planear: el botón real, no una llamada interna ─────────────
    // Un festival multiciudad (FICDEH: Bogotá, Medellín, Ibagué…) abre el sheet de
    // ciudad al entrar, y ese sheet TAPA el botón de calcular. No es un estorbo del
    // test: es el primer paso real del usuario en esos festivales, y hay que
    // atravesarlo como él lo atraviesa. Sin esto, el recorrido de FICDEH —444
    // funciones, el catálogo más grande que tenemos— quedaría sin cobertura.
    // Se atraviesa ELIGIENDO una ciudad, que es el gesto real, no cerrando el sheet
    // por la puerta de atrás: así el recorrido también ejerce el drill-down
    // ciudad→sede. (La ciudad filtra lo que DESCUBRÍS, no lo que ya elegiste: la
    // watchlist y el plan no dependen de ella.)
    if (await page.locator('#city-sheet.open').count()) {
      await page.locator('#city-sheet .lugar-opt.city').first().click();
      await expect(page.locator('#city-sheet.open')).toHaveCount(0, { timeout: 5000 });
    }

    await goToPlanear(page);
    await expect(page.locator('.av-calc-btn')).toBeVisible({ timeout: 10000 });
    await page.locator('.av-calc-btn').click();
    await page.locator('#ag-result-wrap').waitFor({ state: 'visible', timeout: 30000 });

    const plan = await page.evaluate(() => {
      const sc = cachedResult && cachedResult.scenarios;
      if (!sc || !sc.length) return { vacio: true };
      const elegido = sc[0];
      return {
        vacio: false,
        n: elegido.schedule.length,
        trueMax: elegido.trueMax,
        maxWithPriorities: elegido.maxWithPriorities,
        incompatibles: elegido.incompatiblePriorities,
        // EL CERTIFICADO: el mismo verifyPlan del oráculo y del chokepoint.
        cert: verifyPlan(elegido.schedule, { checkPassed: true, catalog: FILMS }),
        titulos: elegido.schedule.map(s => s._title || s.title),
        dias: elegido.schedule.map(s => s.day),
        bloqueadas: elegido.schedule.filter(s => isScreeningBlocked(s)).map(s => (s._title || s.title) + ' @' + s.day + ' ' + s.time),
      };
    });

    if (plan.vacio) {
      // Legítimo solo si de verdad no había nada compatible: se declara, no se
      // esconde. Un plan vacío silencioso es indistinguible de un motor roto.
      const max = await page.evaluate(() => (cachedResult?.scenarios?.[0]?.trueMax) ?? 0);
      expect(max, `${festId}: cero escenarios pero trueMax=${max}`).toBe(0);
      return;
    }

    // El plan es VÁLIDO por las reglas del dominio.
    expect(plan.cert.violations, `${festId}: plan inválido`).toEqual([]);
    expect(plan.cert.ok).toBe(true);
    // Y es ÓPTIMO respecto de lo que la propia app calculó como máximo.
    const objetivo = (plan.maxWithPriorities > 0) ? plan.maxWithPriorities : plan.trueMax;
    expect(plan.n, `${festId}: el plan propuesto (${plan.n}) no alcanza el máximo (${objetivo})`).toBe(objetivo);

    // Las tres promesas al usuario, en el plan que la UI acaba de mostrar.
    if (yaVista) {
      expect(plan.titulos, `${festId}: «${yaVista}» está marcada como ya vista y entró al plan`).not.toContain(yaVista);
    }
    expect(plan.bloqueadas, `${festId}: hay funciones del plan en una franja no disponible`).toEqual([]);
    if (estado.diaVetado) {
      const enDiaVetado = plan.dias.filter(d => d === estado.diaVetado);
      expect(enDiaVetado, `${festId}: el día ${estado.diaVetado} está vetado entero y el plan pone ${enDiaVetado.length} función(es) ahí`).toEqual([]);
    }
    if (!plan.incompatibles && plan.maxWithPriorities > 0) {
      for (const p of estado.exigibles) {
        expect(plan.titulos, `${festId}: la prioridad «${p}» quedó afuera de un plan que podía incluirla`).toContain(p);
      }
    }

    // ── BLOQUE G — Mi Plan: guardar, ver, sugerir ────────────────────────────
    const miPlan = await page.evaluate(() => {
      const elegido = cachedResult.scenarios[0];
      // __PLAN_STRICT__: en producción el chokepoint REPORTA un plan inválido y
      // deja pasar (un plan raro no puede brickear al usuario); en tests TIRA.
      // Acá se quiere lo segundo — si el recorrido produce un plan inválido, el
      // CI lo tiene que ver, no la telemetría tres días después.
      globalThis.__PLAN_STRICT__ = true;
      try {
        // commitPlan recibe un MUTADOR (plan actual → plan siguiente), no un array.
        commitPlan(() => ({ schedule: elegido.schedule.map(s => ({ ...s })) }));
        saveSavedAgenda();
      } finally { delete globalThis.__PLAN_STRICT__; }
      switchMainNav('mnav-miplan'); showAgView();
      return {
        guardado: (savedAgenda && savedAgenda.schedule || []).length,
        // El plan guardado también tiene que ser válido: commitPlan es el
        // chokepoint de escritura, y lo que escribe es lo que el usuario vive.
        cert: verifyPlan((savedAgenda && savedAgenda.schedule) || [], { catalog: FILMS }),
      };
    });
    expect(miPlan.guardado, `${festId}: el plan no llegó a Mi Plan`).toBe(plan.n);
    expect(miPlan.cert.violations, `${festId}: el plan GUARDADO es inválido`).toEqual([]);
    await page.waitForSelector('#ag-view', { state: 'visible', timeout: 8000 });
    await expect(page.locator('.mplan-row, .saved-item').first()).toBeVisible({ timeout: 8000 });

    // Sugerencias: lo que la app OFRECE agregar no puede romper el plan que ya
    // tenés. Es la regresión más fácil de introducir y la más difícil de ver.
    const sugerencias = await page.evaluate(() => {
      if (typeof getSuggestions !== 'function') return { sinFuncion: true };
      // getSuggestions devuelve un mapa {día: [funciones]}, no un array plano.
      const porDia = getSuggestions() || {};
      const sug = Object.values(porDia).flat();
      const plan = (savedAgenda && savedAgenda.schedule) || [];
      return {
        sinFuncion: false,
        n: sug.length,
        chocan: sug.filter(s => plan.some(p => screensConflict(p, s))).map(s => s.title || s._title),
        yaEnPlan: sug.filter(s => plan.some(p => (p._title || p.title) === (s.title || s._title))).map(s => s.title || s._title),
      };
    });
    if (!sugerencias.sinFuncion) {
      expect(sugerencias.chocan, `${festId}: se sugiere una función que choca con el plan`).toEqual([]);
      expect(sugerencias.yaEnPlan, `${festId}: se sugiere algo que ya está en el plan`).toEqual([]);
    }

    // Ningún error de JS en todo el recorrido.
    const criticos = errores.filter(e => !e.includes('sentry') && !e.includes('clarity'));
    expect(criticos, `${festId}: errores JS durante el recorrido`).toEqual([]);

    // Qué se cubrió de verdad, en una línea. Un test verde que no dice cuánto
    // ejerció es indistinguible de uno que no ejerció nada: sin este rastro, un
    // plan vacío en los 12 festivales se leería igual que cobertura completa.
    console.log(`R01 ${festId}: intereses=${estado.watchlist} prio=${estado.prioritized} vistas=${estado.watched} · plan=${plan.n}/${plan.trueMax} · sugerencias=${sugerencias.n ?? 'n/a'}`);
  });
}
