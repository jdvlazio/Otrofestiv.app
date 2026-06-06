# Plan — Auditoría i18n strings hardcodeados

## Arquitectura
Strings viven en bloques JSON inline en index.html (~L2685 ES, ~L3050 EN).
Función `t(key)` resuelve la clave según `_lang`.
Archivos espejo: `i18n/es.json`, `i18n/en.json`, `i18n/strings-reference.json`.

## Dos tipos de cambio

### Tipo A — Wiring (clave existe, código no la usa)
Solo cambiar el código. No tocar JSON.

| Línea | Hardcodeado | → Clave existente |
|---|---|---|
| L4796 | `'Quitar'` (modal btn) | `t('misc_quitar')` |
| L6191 | `'Quitar ... y añadir'` / `'Añadir'` | `t('conflict_anadir_verb')` / `t('misc_anadir')` |
| L6726 | `` `${ICONS.plus} Añadir` `` | `t('misc_anadir')` |
| L7216 | `se solapan en todas...` | `t('plan_solapan')` |
| L7699 | `'Sí, reemplazar'` | `t('misc_si_reemplazar')` |
| L9211 | `Pendiente nueva fecha` | `t('plan_fecha_pendiente')` |
| L9325 | `Pendiente nueva fecha` | `t('plan_fecha_pendiente')` |
| L9809 | `Este festival no está...` | `t('error_festival_nd')` |

### Tipo B — Keys nuevas (añadir a ambos JSON + wiring)
17 keys nuevas con copy aprobado por UX Writer:

```
plan_bloqueado_disp   ES: '"${t}" cae en horarios no disponibles — no podrá incluirse en el plan'
                      EN: '"${t}" conflicts with your unavailable hours'
plan_vuelta_pendientes ES: 'De vuelta en pendientes'
                       EN: 'Moved back to Interests'
plan_reemplazada_por   ES: 'Reemplazada por'    EN: 'Replaced with'
plan_anadida_al_plan   ES: 'añadida al plan'    EN: 'added to plan'
plan_sin_calificar     ES: '${n} sin calificar' EN: '${n} to rate'
plan_viste_n           ES: 'Viste ${n}'         EN: 'You watched ${n}'
  (pluralización: 'película'/'películas' y 'film'/'films' se resuelven inline en JS)
plan_una_pendiente     ES: 'Una pendiente de calificar.'  EN: 'One to rate.'
misc_manana            ES: 'mañana'             EN: 'tomorrow'
notice_cancelada       ES: 'CANCELADA'          EN: 'CANCELED'
notice_reprogramada    ES: 'REPROGRAMADA'       EN: 'RESCHEDULED'
notice_cancelada_short ES: 'Cancelada'          EN: 'Canceled'
notice_reprog_short    ES: 'Reprog.'            EN: 'Rescheduled'
notice_nueva_funcion   ES: 'Nueva función:'     EN: 'New screening:'
plan_reemplazar_plan   ES: 'Reemplazar plan'    EN: 'Replace plan'
plan_continuar_quitar  ES: '¿Continuar y quitar del plan?' EN: 'This will remove it from your plan.'
aria_marcar_pendiente  ES: 'Marcar como pendiente' EN: 'Mark as unwatched'
aria_marcar_vista      ES: 'Marcar como vista'     EN: 'Mark as seen'
```

## Archivos a tocar
1. `index.html` — bloques ES (~L2685) y EN (~L3050): añadir 17 keys nuevas
2. `index.html` — JS: 15 líneas de wiring (Tipo A + Tipo B)
3. `i18n/es.json` — añadir 17 keys
4. `i18n/en.json` — añadir 17 keys
5. `i18n/strings-reference.json` — añadir 17 entries
