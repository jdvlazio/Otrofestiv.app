#!/bin/sh
# preparar-copia.sh [carpeta] — deja lista una copia de trabajo (worktree) de
# Otrofestiv. Idempotente y rápido cuando ya está todo (20 oct 2026).
#
# POR QUÉ: cada sesión trabaja en su propia copia (una sesión, una copia). Una
# copia nueva arranca sin lo que no está en git, y eso se hacía a mano y se
# olvidaba: sin node_modules los tests fallaban con un MODULE_NOT_FOUND enterrado,
# y fuentes/ copiada a cada lado se desincronizaba (Fantasmagoría re-armó con la
# cartelera v2 cuando la vigente era la v26, sin ningún aviso).
#
# QUÉ HACE
#   1. fuentes/ → enlace a la carpeta COMPARTIDA ~/Developer/Otrofestiv-fuentes
#      (una sola copia para todas las sesiones; fuera de cualquier worktree, así
#      que borrar una copia no se lleva nada). Si ya hay una carpeta fuentes/
#      real, NO la toca: avisa (puede tener algo nuevo que hay que llevar).
#   2. hooks y driver de merge (install-hooks.sh).
#   3. node_modules: `npm ci` en segundo plano si faltan los de las pruebas.
#
# Lo corre solo el hook SessionStart de Claude Code (.claude/settings.json de la
# carpeta principal). A mano: sh scripts/preparar-copia.sh
set -e
dir=${1:-$(pwd)}
cd "$dir"
[ -f scripts/install-hooks.sh ] || exit 0          # no es una copia de Otrofestiv
comp="${OTF_FUENTES:-$HOME/Developer/Otrofestiv-fuentes}"
if [ -L fuentes ]; then :
elif [ -e fuentes ]; then
  echo "⚠ $dir/fuentes es una carpeta propia, no la compartida: llevá lo nuevo a $comp (rsync -a --update fuentes/ $comp/) y reemplazala por el enlace." >&2
elif [ -d "$comp" ]; then
  ln -s "$comp" fuentes
fi
sh scripts/install-hooks.sh >/dev/null 2>&1 || true
if [ ! -d node_modules/@playwright/test ] && [ -f package-lock.json ]; then
  ( npm ci --silent >/dev/null 2>&1 & )
  echo "· instalando node_modules en segundo plano (~1 min)" >&2
fi
exit 0
