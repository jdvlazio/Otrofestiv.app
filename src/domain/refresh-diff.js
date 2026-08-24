// domain/refresh-diff.js — clasificador del refresco de datos en caliente.
//
// PURO: recibe dos catálogos explotados (explodeScreenings) y el plan del
// usuario; no toca DOM ni state. Es la pieza que decide POR CUÁL de las tres
// reglas entra un cambio (capa 2, aprobada por Juan 24 ago 2026 con respaldo
// documentado — web.dev CLS, NN/g, patrón «N posts nuevos»):
//
//  1. VALORES  — la misma función cambió de sede u otro atributo en su casilla:
//     se aplica en silencio, en todas las superficies (patrón marcador
//     deportivo / tablero de aeropuerto: el usuario ESPERA ese dato vivo).
//  2. ESTRUCTURA — entran/salen funciones (o cambia el calendario): mueve el
//     layout → en la superficie visible se OFRECE (pill), nunca se inyecta
//     (CLS: perder el lugar, tocar el botón equivocado).
//  3. PLAN — una función DE TU PLAN cambió: aviso explícito con el hecho,
//     esté donde esté (doctrina T97: tu plan no cambia solo).
//
// Identidad de función: título+día+hora (la misma de syncScheduleWithCatalog:
// el plan guarda la ELECCIÓN título+día+hora). Un cambio de hora aparece como
// alta+baja (estructura) — correcto para el layout — y el clasificador del plan
// lo re-encuentra por título para poder DECIR «cambió el horario», no «se fue».

const _key = f => `${f.title}|${f.day}|${f.time}`;

// clasificarRefresco({oldFns, newFns, oldDays, newDays, plan}) →
//   { hay, estructural, calendario, valores:[{title,day,time,campo}], plan:[{title,tipo}] }
// plan: [{title,day,time}] — las elecciones del usuario (savedAgenda.schedule).
export function clasificarRefresco({ oldFns, newFns, oldDays, newDays, plan }){
  const om = new Map(), nm = new Map();
  (oldFns||[]).forEach(f => om.set(_key(f), f));
  (newFns||[]).forEach(f => nm.set(_key(f), f));

  // Calendario: días añadidos/quitados/reordenados. Cambio mayor: exige
  // reconstruir la tira de días → SIEMPRE se ofrece, nunca silencioso.
  const calendario = JSON.stringify(oldDays||[]) !== JSON.stringify(newDays||[]);

  // Valores: misma identidad, atributo distinto. Solo los campos que se ven en
  // la casilla — sede y duración. (Los avisos cancelada/reprogramada viajan por
  // NOTICES = código = build bump, no por acá.)
  const valores = [];
  for (const [k, f] of om) {
    const n = nm.get(k);
    if (!n) continue;
    if ((n.venue||'') !== (f.venue||'')) valores.push({ title: f.title, day: f.day, time: f.time, campo: 'venue' });
    else if ((n.duration||'') !== (f.duration||'')) valores.push({ title: f.title, day: f.day, time: f.time, campo: 'duration' });
  }

  // Estructura: identidades que solo existen en un lado.
  let estructural = calendario;
  if (!estructural) {
    for (const k of om.keys()) if (!nm.has(k)) { estructural = true; break; }
    if (!estructural) for (const k of nm.keys()) if (!om.has(k)) { estructural = true; break; }
  }

  // Plan: para cada elección del usuario, ¿su función sigue igual?
  const planCambios = [];
  for (const p of (plan||[])) {
    const k = `${p.title}|${p.day}|${p.time}`;
    const viva = nm.get(k);
    if (viva) {
      const vieja = om.get(k);
      if (vieja && (viva.venue||'') !== (vieja.venue||'')) planCambios.push({ title: p.title, tipo: 'sede' });
      continue;
    }
    // La identidad exacta murió: ¿se movió o se fue?
    const delTitulo = (newFns||[]).filter(f => f.title === p.title);
    if (!delTitulo.length) { planCambios.push({ title: p.title, tipo: 'retirada' }); continue; }
    if (delTitulo.some(f => f.day === p.day)) planCambios.push({ title: p.title, tipo: 'horario' });
    else planCambios.push({ title: p.title, tipo: 'dia' });
  }

  const hay = estructural || valores.length > 0 || planCambios.length > 0;
  return { hay, estructural, calendario, valores, plan: planCambios };
}
