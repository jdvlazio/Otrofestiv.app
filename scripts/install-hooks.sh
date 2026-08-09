#!/bin/sh
# install-hooks.sh — enchufa en ESTE clon las barreras que el repo trae versionadas.
# Correr una vez después de clonar (y en cada worktree nuevo):
#     sh scripts/install-hooks.sh
#
# Dos cosas viven en el repo pero se activan localmente, porque git no ejecuta
# comandos que vengan del repositorio —es una defensa suya, no un descuido—:
#   1. .githooks/       (pre-commit, pre-push)  → core.hooksPath
#   2. el driver `bump` (.gitattributes)        → merge.bump.driver
#
# Ambas tienen aviso propio en validate.py ([hooks-activos], [merge-driver]) por
# si alguien clona y se olvida.
#
# NOTA HISTÓRICA: hasta ago 2026 este script escribía un pre-commit a mano en
# .git/hooks/. Quedó muerto sin que nadie lo notara: al adoptar core.hooksPath,
# git deja de mirar .git/hooks por completo. Los hooks de verdad son .githooks/*.

set -e
cd "$(git rev-parse --show-toplevel)"

git config core.hooksPath .githooks
echo "✓ hooks activos      → .githooks/ (pre-commit, pre-push)"

git config merge.bump.name   "build number: se resuelve solo, el contenido no"
git config merge.bump.driver "scripts/merge-bump.sh %O %A %B"
echo "✓ driver de merge    → scripts/merge-bump.sh (index.html, src/main.js, sw.js, version.json)"
