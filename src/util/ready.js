// ── src/util/ready.js ─────────────────────────────────────────────────────────
// Guards de readiness para código que corre en módulos ES INYECTADOS.
//
// POR QUÉ EXISTE: desde el store-gate, `main.js` se carga como
// `<script type="module">` inyectado dinámicamente (bootApp en index.html), NO
// como script estático del HTML. Un módulo inyectado tarde NO bloquea
// `DOMContentLoaded` ni `load` — esos eventos ya dispararon cuando el módulo se
// evalúa. Registrar un `addEventListener('DOMContentLoaded', …)` normal ahí es
// registrar para un evento PASADO → el callback nunca corre (fue la causa del
// bug de idioma: la UI estática se quedaba en el HTML hardcodeado).
//
// Estos helpers ejecutan YA MISMO si el DOM ya alcanzó el estado necesario, o
// esperan el evento si todavía no. Idempotentes, once. Regla: en `src/`, todo
// listener de DOMContentLoaded/load pasa por acá (lo enforcea validate.py
// [dom-ready-guard]).

// DOM parseado (interactive o complete) — para leer/mutar el DOM.
export function onDomReady(fn){
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fn, { once: true });
  else fn();
}

// Página + subrecursos cargados (complete) — para depender de un <script> CDN
// externo (ej. el global `supabase`) que puede no existir aún al evaluar.
export function onWindowLoad(fn){
  if(document.readyState === 'complete') fn();
  else window.addEventListener('load', fn, { once: true });
}
