# Tasks — Auditoría i18n strings hardcodeados

- [x] 1. Keys nuevas en bloque ES — ya estaban + 30 sincronizadas a es.json
- [x] 2. Keys nuevas en bloque EN — ya estaban + 30 sincronizadas a en.json
- [x] 3. Tipo A wiring: 'Quitar'→t('misc_quitar'), 'De vuelta en pendientes'→t('plan_vuelta_pendientes')
- [x] 4. Tipo B wiring: todas las demás ya usaban t()
- [x] 5. i18n/es.json + en.json: 265→295 keys. sync-i18n.py alineado ✓
- [x] 6. validate.py 13/13 ✓
- [x] 7. QA EN: 18 strings críticas verificadas via código — misc_quitar="Remove",
      plan_vuelta_pendientes="Moved back to Interests", bar_todo="All",
      lbl_prioridades="Priorities", notice_cancelada="CANCELED", etc. ✓
- [x] 8. QA ES: sin cambios — source of truth intacta ✓

## Post-feature fix (sesión 2026-05-14)
- [x] Fix: mplan-list-day usaba \${day} (raw key) → \${dayLabel(day)} (fd1469c)
