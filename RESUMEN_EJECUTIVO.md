# Otrofestiv — Resumen Ejecutivo
*Actualizado: abril 2026*

---

## Repo y credenciales

- **Repo:** `jdvlazio/Otrofestiv.app`
- **GitHub token:** `ghp_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`
- **TMDB API key:** `38f24e78b2f13970af3430eb0732f0ac`
- **Deploy:** GitHub Pages → `otrofestiv.app`
- **Último commit:** `b0b11ec`

---

## Qué es Otrofestiv

App de planificación de festivales de cine. Single-file HTML, vanilla JS, zero dependencias externas. Despliega en GitHub Pages.

**URL del festival activo:** `otrofestiv.app`
**Backstage (herramienta de producción):** `otrofestiv.app/backstage`
**Enricher:** `otrofestiv.app/enricher/`

---

## Festivales en producción

| Festival | ID | Archivo | Transport |
|---|---|---|---|
| AFF 2026 | `aff2026` | `festivals/aff-2026.json` | transit |
| FICCI 65 | `ficci65` | `festivals/ficci-65.json` | mixed |

---

## Arquitectura del código

### Archivo de deploy
`index.html` — 8,170 líneas. ES el archivo de producción. Se sube directamente a GitHub Pages.

### Código fuente modular (`src/`)
```
src/
  config.js      — UI, ICONS, FESTIVAL_CONFIG, VENUES, NOTICES
  posters.js     — poster generation
  auth.js        — Supabase auth
  utils.js       — time, venues, conflicts, travel
  state.js       — state, persistence
  actions.js     — user actions
  algo.js        — algoritmo + getSuggestions + squeezeExcluded
  renders/
    helpers.js   — parseProgramTitle, badges
    mi-lista.js  — Mi Lista
    mi-plan.js   — Mi Plan + contexto
    planear.js   — Planear + Agenda
    cartelera.js — Cartelera
    sheets.js    — Sheets
    programa.js  — Programa + render()
    init.js      — loadFestival, SW, splash
```

`node build.js` → genera `dist/index.html` desde `src/`. No despliega — `index.html` sigue siendo el deploy.

### Proceso de cambio
1. Editar en `src/` (fuente canónica)
2. Copiar el cambio también a `index.html` (producción)
3. Actualizar `version.json` y `sw.js` build number
4. `git push`

---

## Sistema de datos — Festival JSON

Cada festival vive en `festivals/<id>.json`:

```json
{
  "name": "Nombre Festival",
  "id": "id-año",
  "transport": "transit|walking|mixed",
  "venues": {
    "Nombre Sede - Ciudad": { "short": "...", "lat": 0, "lon": 0, "city": "..." }
  },
  "films": [...],
  "posters": {},
  "lbSlugs": {}
}
```

**Modos de transporte:**
- `walking` → Festival de Jardín (todo a pie)
- `mixed` → FICCI Cartagena (cerca a pie, lejos en carro)
- `transit` → AFF Medellín (Uber/Metro)

---

## Sistema de Notices (avisos de último momento)

```js
const NOTICES = [
  { title:'Film', festival:'aff2026', type:'cancelled', date:'2026-04-23' },
  { title:'Film', festival:'aff2026', type:'rescheduled', date:'2026-04-24', newVenue:'Nueva Sede' },
];
```

- `type: 'cancelled'` → badge CANCELADA, texto tachado
- `type: 'rescheduled'` + `newVenue` → badge REPROGRAMADA + nueva sede en todos los renders
- `date` → el banner desaparece al día siguiente automáticamente

**Función clave:** `_noticeVenue(title, originalVenue)` — devuelve la sede efectiva considerando notices. Se usa en TODOS los renders de venue.

---

## Reglas canónicas — NUNCA romper

### Venue
- **Venue tal cual lo pone el festival, siempre completo, nunca abreviado**
- `venueDisplay(v)` — función de display, solo quita "Sala X" del final
- `vcfg().short` es interno (filtros), nunca se muestra al usuario

### Iconografía
- Venue y tiempo: **siempre Lucide** (`ICONS.clock`, `ICONS.pin`)
- Excepciones incuestionables: flags de país, emoji 🎬 como placeholder de poster

### Badges
- Siempre mayúsculas, sin punto, sin abreviación
- `CANCELADA` · `REPROGRAMADA` · `Q&A` · `INSCRIPCIÓN`
- Clases: `.notice-badge` y `.meta-badge` — nunca inline ad-hoc

### Lenguaje
- Textos de navegación: **"actividad/actividades"**, "la siguiente", "entre actividades"
- Metadata de película: "función/funciones" es correcto (cuántas tiene en el festival)
- Q&A es la única excepción al español — convención universal del cine

### Posters
- `onerror="this.remove()"` — siempre, nunca `this.style.opacity`
- `getFilmPoster(f)` — fuente única de verdad
- Nunca fondo negro — usar `surf-2`

### CTAs
- Primario: fondo ámbar sólido, texto negro

### Algoritmo
- Conflictos siempre via `screensConflict()` (±10 min buffer = `FESTIVAL_BUFFER`)
- Q&A es **informativo**, no bloquea el algoritmo — aviso contextual en Mi Plan
- `getSuggestions()`: sin límite de cantidad, `seenDay` se reinicia por día

### Antes de cualquier fix
Buscar **todos** los renders que usan el mismo patrón antes de tocar uno. Un fix a medias es peor que ningún fix.

---

## UI — Objeto de textos

```js
const UI = {
  badge: { cancelled:'CANCELADA', rescheduled:'REPROGRAMADA', qa:'Q&A', inscription:'INSCRIPCIÓN' },
  travel: { walking:'a pie', transit:'en carro' },
  empty: { noActivity, noPending, planCovered, allPassed, overlap }
};
```

---

## Pipeline de producción

Ver `/pipeline/PROTOCOLO.md` — proceso completo para montar un festival nuevo.

Entradas: PDF (Claude lo parsea en el chat) o CSV del organizador.

---

## Service Worker y actualizaciones

Cada push debe actualizar `version.json` y `sw.js` (build number). Formato: `YYYYMMDDHHMI`.

```python
from datetime import datetime
import json, re
build = datetime.now().strftime('%Y%m%d%H%M')
# Actualizar version.json y sw.js
```

---

## Auditoría antes de hacer push

```bash
node -e "
const h=require('fs').readFileSync('index.html','utf8');
const s=[...h.matchAll(/<script(?![^>]*src)[^>]*>([\S\s]*?)<\/script>/g)];
let ok=0,e=[];
s.forEach((m,i)=>{if(m[0].includes('ld+json'))return;try{new Function(m[1]);ok++;}catch(err){e.push(err.message);}});
console.log('JS:',ok,'OK,',e.length,'errors');
console.log('CSS blocks:',h.split('<style>').length-1);
e.forEach(x=>console.log(' ✗',x));
"
```

---

## Próximos festivales

- **Festival de Cine de Jardín** (Sep 2026) — transport: `walking`
- **Cinemancia 6ta edición** (Sep 2026) — transport: `transit`, 20+ sedes

Para testear sin hacer público: `otrofestiv.app/?dev=cinemancia2025` (pendiente implementar).
