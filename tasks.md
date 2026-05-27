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

## Deuda i18n — keys muertas (RESUELTA ✅)

Detectadas durante el onboarding de PT (Lote 3): `label_director`, `label_synopsis`,
`label_duracion`, `label_valoracion` existían en `_I18N` (es+en) pero ningún código
las consumía (0 usos de `t()`/`data-i18n`). **Borradas de es/en** en el PR de
limpieza tras cerrar PT. Nunca se tradujeron a PT (habría sido copy invisible).
Resultado: `_I18N` queda en 340 keys es/en/pt — paridad total, 100% pt-BR.

## Deuda i18n — `DAY_A` + header "Tu {día} en" (RESUELTA ✅)

`DAY_A` hardcodeado (4 sitios: `agenda.js` + 3× `sheets-controller.js`) eliminado y
enrutado por `dayLabel()` lang-aware con `DAY_SHORT_PT` (mapa ES→PT en `loader.js`).
Header → `t('plan_tu_dia_en',{dia})` + nombre del festival; fallback `'Hoy'` → `t('bar_hoy')`.
Bonus: `DAY_A` nunca matcheaba festivales con claves ISO → ahora funciona para todos.

## Deuda i18n — ternarios binarios ES/EN que caen a ES en PT (RESUELTA ✅)

Tres últimos leaks de hardcode/ternario que no pasaban por `t()` y caían a ES en PT,
arreglados en un PR combinado (`feat/fix-lang-ternarios`):

1. **`dayChip()`** (`helpers.js`) tenía el mismo patrón binario que tenía `dayLabel()`:
   `_ds = _lang==='en' ? DAY_SHORT_EN : DAY_SHORT` → en PT caía a `DAY_SHORT` (ES) y además
   priorizaba `DAY_ABBR[key]` (abreviatura ES del festival). Day-chips mostraban abreviatura
   ES en PT (MIÉ en vez de QUA). Fix: 3-way usando `DAY_SHORT_PT`, análogo a `dayLabel()`.
2. **dtab labels** (`loader.js`): el build del dtab era binario (`_dtabLbl=_lang==='en'?...`)
   y el fallback legado de `_applyI18nDOM` (`i18n.js`) solo leía `lblEn`/`lblEs`. Fix:
   `_dtabLblPT` + `dataset.lblPt` + ramas PT en ambos sitios.
3. **`_kindMap`** (`components.js`): `_lang==='en'?_kindMapEN:_kindMapES` → PT caía a ES.
   Fix: `_lang==='es'?_kindMapES:_kindMapEN` (PT reutiliza EN, términos internacionales).

> El leak del **countdown** (`misc_days`) se arregló en el PR del countdown (#116) y el del
> header + `DAY_A` en el refactor `dayLabel()` (#117).
