# Trabajo en paralelo (varias sesiones a la vez)

Aprobado por Juan el 20 oct 2026, después de dos días de choques entre sesiones
(rama cambiada bajo los pies, la carpeta principal rota dos veces, `fuentes/`
desincronizada, archivos tocados por un agente que no era el dueño). Es el método
de la documentación oficial de Claude Code (code.claude.com/docs/en/worktrees).

## Las reglas

1. **Una sesión, una copia de trabajo.** Toda sesión de Otrofestiv trabaja en su
   propio worktree, creado por la app (interruptor **Worktree** al abrir la
   sesión, o un entorno guardado con Worktree encendido). Así, además, Claude Code
   bloquea que esa sesión edite o corra git sobre la carpeta principal.
2. **La carpeta principal (`~/Developer/Otrofestiv`) no se edita nunca.** Queda en
   `main`, solo como base de las copias.
3. **`fuentes/` es UNA carpeta compartida:** `~/Developer/Otrofestiv-fuentes`. Cada
   copia la ve por un enlace `fuentes/ → …/Otrofestiv-fuentes`. Lo que una sesión
   baja lo ven todas, y borrar una copia no se lleva nada.
4. **Una copia nueva se prepara sola:** el hook `SessionStart` de
   `.claude/settings.local.json` (carpeta principal) corre
   `scripts/preparar-copia.sh`: enlaza `fuentes/`, engancha el candado y corre
   `npm ci` si faltan los módulos. A mano: `sh scripts/preparar-copia.sh`.
5. **El número de build no va en el PR** (lo estampa `pages.yml` al publicar):
   dos PR ya no chocan por la versión.
6. **Se integra de a uno,** con auto-merge. Los chats NO se archivan solos (Juan,
   20 oct: sus chats son largos y llevan muchos PR; el auto-archivo de la app está
   apagado). La copia de trabajo de un PR ya mergeado la borra quien la creó
   (`git worktree remove`).

## Guardianes

- `[git-config-sano]` en validate.py: la config de git es UNA para todas las
  copias; si queda `core.bare = true` o un `core.worktree`, frena el push que lo
  causó y dice el comando para arreglarlo.
- `.githooks/pre-push` limpia `GIT_DIR`/`GIT_WORK_TREE` antes de validar (#1175).
