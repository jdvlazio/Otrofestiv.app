# .specify/features/

Cada feature en desarrollo tiene su propio directorio con tres artefactos:

```
features/
  <nombre-feature>/
    spec.md     ← qué y por qué (sin mencionar implementación técnica)
    plan.md     ← cómo técnico (funciones a tocar, decisiones de arquitectura)
    tasks.md    ← lista atómica ejecutable para una sesión de trabajo
```

**Regla:** `spec.md` y `plan.md` se aprueban antes de empezar `tasks.md`.  
`tasks.md` se aprueba antes de tocar `index.html`.

## Features activas

- `nav-redesign/` — Rediseño de navegación (mockup aprobado, spec pendiente)
- `tribeca-2026/` — Festival Tribeca (datos en proceso)
