# tasks.md — estado de tareas

## Onboarding · Olhar de Cinema 2026 (`olhar-2026`)

Festival #1 onboardeado con el pipeline nuevo y el **método A2 (SPA client-rendered)**.
Curitiba, Brasil · 4–13 jun 2026 · 80 films · 58 entries (46 films + 12 programas) · 6 sedes.

### Completo ✅
- [x] Extracción A2 (80 films, loop auto-avanzante por DOM renderizado)
- [x] Posters 80/80 (og:image, binding verificado por UUID — 0 falsos)
- [x] synopsis (PT, del cuerpo) 80/80 · synopsis_en 80/80 (sitio bilingüe)
- [x] duration 80/80 · country PT→ES + flags 80/80
- [x] Funciones (day/time/venue/day_order ISO) + has_qa (film-level)
- [x] Agrupación de cortos/programas: 12 programas (11 `is_cortos` + 1 `is_programa`), 0 slots compartidos
- [x] Títulos de programa = nombres oficiales del sitio (8 PGM exactos; 3 Acessibilidade desambiguadas por familia; 1 doble construido)
- [x] Geocoding 6/6 sedes (verificado en Curitiba)
- [x] `FESTIVAL_CONFIG['olhar2026']` en `src/config.js` + config root en el JSON
- [x] `synopsis_es` 46/46 films solos (traducción PT→ES inline en chat, gate aprobado)
- [x] 5 checks de corrupción en `validate-festivals.js` (+ negative tests) · `docs/FESTIVAL-CHECKLIST.md` · `festival-template.json` reconciliado · `tools/enricher.html` actualizado
- [x] `validate-festivals.js` 0 errores · `validate.py` OK para push

### Downstream (no bloqueante) ⏳
- [ ] `genre` (0/47) — enriquecimiento TMDB estricto (year confiable → matching seguro)
- [ ] `lbSlug` — Letterboxd (método Chrome tab, verificar cada slug)
- [ ] Section emoji + orden curatorial (Fase 2/5, Content-Designer)
- [ ] `tools/enricher.html` — agregar `olhar-2026` a la lista FESTIVALS
- [ ] Posters de los 12 programas (generativo/editorial)

### Deuda de pipeline detectada
- `geocode-venues.py`: falla en nombres de sublocal (Nominatim) → necesita campo `geo_query` override.
- `festival-template.json` dice JSON={venues,films}-only, pero `validate.py` + loader exigen config en el JSON → reconciliar el template.
- `has_qa` es film-level (el loader no transporta Q&A por-función) → Olhar perdió granularidad.

## Deuda i18n — keys muertas (limpieza, no urgente · PR aparte)

Detectadas durante el onboarding de PT (Lote 3). Existen en `_I18N` (es **y** en)
pero **ningún código las consume** (verificado: grep de `t('...')` + `data-i18n`
en todo `src/` e `index.html` → 0 usos). Candidatas a borrar de los 3 bloques.

- `label_director` — el sheet muestra el director inline en la metaline, sin label.
- `label_synopsis` — el sheet usa `label_sinopsis` (minúscula); esta nunca se llama.
- `label_duracion` — la duración sale como "NN min" inline, sin label.
- `label_valoracion` — el sheet usa el CTA "Calificar"; no hay label "Tu valoración".

> No se tradujeron a PT (sería copy invisible). Al borrarlas, tocar es/en/pt juntos.
