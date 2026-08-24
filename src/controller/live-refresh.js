// controller/live-refresh.js — refresco de DATOS en caliente (capa 2, 24 ago 2026).
//
// La capa 1 (#735) garantiza que los cambios LLEGAN (canales de version.json →
// recarga). Esta capa gobierna CÓMO llegan cuando la app está en uso: el
// contenido se refresca sin recargar, según las tres reglas que Juan aprobó con
// respaldo documentado (web.dev CLS · NN/g · patrón «N posts nuevos» · tableros
// en vivo):
//
//   1. VALORES  → en silencio, en todas las superficies (el dato respira).
//   2. ESTRUCTURA visible → se OFRECE con el pill; jamás se inyecta bajo los
//      dedos. No visible → en silencio. Calendario cambiado → SIEMPRE pill, y
//      aplicar = loadFestival entero (la tira de días se reconstruye ahí).
//   3. TU PLAN  → aviso explícito con el hecho, esté donde esté (T97).
//
// Comparte los DUEÑOS ÚNICOS de loader.js (_ingerirDatosFestival +
// publicarCatalogo): no existe un segundo camino de ingesta. El diff lo decide
// el dominio puro (clasificarRefresco). El fetch va con 1 intento: esto corre
// en un poll — si la red falla, la próxima vuelta reintenta sola.
import { FESTIVAL_CONFIG, mergeFestivalSections } from '../config.js';
import { _fetchFestivalJson, _ingerirDatosFestival, festivalJsonUrl, loadFestival, publicarCatalogo } from './loader.js';
import { clasificarRefresco } from '../domain/refresh-diff.js';
import { _djb2, explodeScreenings, normTitle } from '../domain/film.js';
import { renderActiveView } from './pipeline.js';
import { showActionToast } from './sheets-controller.js';
import { showToast } from '../view/feedback.js';
import { state } from '../state/state.js';
import { t } from '../i18n/i18n.js';

let _refrescando = false;
let _ofrecido = 0;            // hash ya ofrecido — un pill por cambio, no por tick
let _pendiente = null;        // {id, data, calendario} esperando el tap del pill

// Los dos lados del diff con la MISMA normalización de título que la
// publicación (normTitle) — sin esto, una comilla tipográfica en el JSON nuevo
// fabricaría una «retirada» fantasma contra el plan ya normalizado.
const _explotar = films => explodeScreenings(films||[]).map(f => ({ ...f, title: normTitle(f.title) }));

export async function refrescarDatosFestival(){
  if (_refrescando) return false;
  const id = state.get('_activeFestId');
  if (!id) return false;                                  // splash: no hay qué refrescar
  const cfg = FESTIVAL_CONFIG[id];
  if (!cfg || !cfg.films || !cfg._rawHash) return false;  // aún sin carga completa
  _refrescando = true;
  try {
    const data = await _fetchFestivalJson(festivalJsonUrl(id), 1, 6000);
    const hash = _djb2(JSON.stringify(data));
    if (hash === cfg._rawHash) return false;

    const _plan = ((state.get('savedAgenda') || {}).schedule || [])
      .map(e => ({ title: e._title || e.title, day: e.day, time: e.time }));
    const cambio = clasificarRefresco({
      oldFns: _explotar(cfg._rawFilms), newFns: _explotar(data.films),
      oldDays: cfg._rawDayKeys, newDays: data.dayKeys || cfg._rawDayKeys,
      plan: _plan,
    });
    // Si el clasificador no ve estructura, TODO lo demás es un cambio de valor
    // (sede, duración, sinopsis, póster…): regla 1, se aplica en silencio — el
    // hash ya dijo que algo es distinto y el catálogo debe estar fresco.

    // Regla 2 — estructura: en pantalla visible del programa se ofrece, no se
    // aplica. Calendario cambiado → pill SIEMPRE (reconstruir la tira de días es
    // trabajo de loadFestival, que resetea contexto — jamás en silencio).
    // Splash en fade-out = ya NO es la pantalla: el usuario está viendo la
    // lista aparecer debajo (dismissSplash lo remueve recién al terminar la
    // transición — medido: el nodo sobrevive ~1s con .fade-out y sin este matiz
    // la ventana de entrada inyectaba estructura «en silencio» justo cuando el
    // usuario empieza a mirar).
    const _sp = document.getElementById('otrofestiv-splash');
    const _enSplash = !!_sp && !_sp.classList.contains('fade-out');
    const _programaVisible = (typeof activeMNav !== 'undefined' && activeMNav === 'mnav-cartelera')
      && document.visibilityState === 'visible' && !_enSplash;
    if (cambio.calendario || (cambio.estructural && _programaVisible)) {
      if (_ofrecido !== hash) {
        _ofrecido = hash;
        _pendiente = { id, data, calendario: cambio.calendario };
        showActionToast(t('refresco_programacion'), t('update_cta'), _aplicarPendiente, 12000);
      }
      // El plan se avisa igual (regla 3): el hecho ya ocurrió en el festival,
      // ofrecer el re-render no lo pospone.
      _avisarPlan(cambio.plan);
      return true;
    }

    _aplicar(id, cfg, data);
    _avisarPlan(cambio.plan);
    return true;
  } catch (e) { void e; return false; }                    // poll: la próxima vuelta reintenta
  finally { _refrescando = false; }
}

// Aplicación en caliente: mismos dueños que la carga (ingesta + publicación) y
// el re-render que ya preserva scroll y respeta la ficha abierta
// (renderActiveView → _renderProgramaContent(resetScroll=false)).
function _aplicar(id, cfg, data){
  _ingerirDatosFestival(id, cfg, data);
  mergeFestivalSections(cfg.sections);
  publicarCatalogo(id, cfg);
  renderActiveView();
}

function _aplicarPendiente(){
  const p = _pendiente; _pendiente = null;
  if (!p) return;
  if (p.calendario) {
    // La tira de días cambió: solo loadFestival sabe reconstruirla. El usuario
    // acaba de pedirlo con el tap — el reset de contexto es esperable.
    const cfg = FESTIVAL_CONFIG[p.id]; if (cfg) cfg.films = null;
    loadFestival(p.id);
    return;
  }
  const cfg = FESTIVAL_CONFIG[p.id]; if (!cfg) return;
  _aplicar(p.id, cfg, p.data);
}

// Regla 3 — el aviso del plan dice el HECHO. Uno solo: el cambio puntual con su
// obra; varios: el agregado (una notificación por refresco, no una lluvia).
function _avisarPlan(cambios){
  if (!cambios || !cambios.length) return;
  if (cambios.length === 1) {
    const c = cambios[0];
    const _keys = { sede: 'refresco_plan_sede', horario: 'refresco_plan_horario', dia: 'refresco_plan_dia', retirada: 'refresco_plan_retirada' };
    showToast(t(_keys[c.tipo] || 'refresco_plan_varias', { t: c.title, n: 1 }), 'info', 7000);
    return;
  }
  showToast(t('refresco_plan_varias', { n: cambios.length }), 'info', 7000);
}
