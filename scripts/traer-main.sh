#!/usr/bin/env bash
# traer-main.sh — mergea origin/main en la rama actual SIN borrar trabajo.
#
# POR QUÉ EXISTE
# Dos veces en una semana resolví conflictos con `git checkout --theirs <archivo>`
# razonando «es solo la línea de versión». No lo es: git-checkout(1) dice que esas
# opciones sacan la etapa #2 o #3 del índice — el ARCHIVO ENTERO. Se llevaron por
# delante el markup del sheet de ciudad (8 referencias), `ticketBadgeTarget` del
# TEST BRIDGE (3) y, dos días después, el CSS de `.fn-ciudad`/`.fn-otra-ciudad`.
#
# La trampa es específica de este repo: `bump-version.js` toca CINCO archivos
# —index.html, src/main.js, sw.js, version.json, CLAUDE.md— y tres de ellos
# TAMBIÉN contienen código. Un conflicto ahí parece trivial y no lo es.
#
# QUÉ HACE DISTINTO
# 1. Exige el árbol limpio (con cambios sin commitear, un merge fallido es peor).
# 2. Los cinco archivos del bump no se resuelven eligiendo un lado: se toma la
#    versión de main y se RE-EJECUTA bump-version, que es quien sabe escribirlos.
# 3. Los conflictos REALES quedan intactos, para leerlos y resolverlos a mano.
# 4. Al final compara la rama contra su commit previo ignorando los números de
#    build: cualquier archivo que cambie sin que lo hayas tocado es trabajo
#    perdido. Esa verificación es la que me faltó las dos veces.
#
# USO
#     ./scripts/traer-main.sh
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"

BUMP=(index.html src/main.js sw.js version.json CLAUDE.md)
rama=$(git rev-parse --abbrev-ref HEAD)
[ "$rama" = "main" ] && { echo "Estás en main: no hay nada que traer."; exit 1; }

if [ -n "$(git status --porcelain)" ]; then
  echo "✗ Hay cambios sin commitear. Commiteálos o guardalos antes de mergear:" >&2
  git status --short | sed 's/^/    /' >&2
  exit 1
fi

antes=$(git rev-parse HEAD)
echo "▸ rama $rama · commit previo ${antes:0:8}"
git fetch -q origin
git merge origin/main --no-edit >/dev/null 2>&1 && { echo "✓ merge limpio, nada que resolver."; exit 0; }

conflictos=$(git diff --name-only --diff-filter=U)
echo "▸ conflictos:"; echo "$conflictos" | sed 's/^/    /'

# Los del bump: se toma main y se rehace el bump. NUNCA se elige un lado a ciegas.
for f in "${BUMP[@]}"; do
  if echo "$conflictos" | grep -qx "$f"; then
    git checkout --theirs -- "$f" 2>/dev/null && git add "$f"
    echo "    · $f → versión de main (el bump se rehace al final)"
  fi
done

restantes=$(git diff --name-only --diff-filter=U)
if [ -n "$restantes" ]; then
  echo
  echo "✋ Conflictos REALES para resolver a mano (tienen contenido de los dos lados):"
  echo "$restantes" | sed 's/^/    /'
  echo "   Resolvé, 'git add' cada uno, y volvé a correr este script para la verificación."
  exit 2
fi

git commit -q --no-edit
node scripts/bump-version.js >/dev/null 2>&1 && echo "▸ bump rehecho"
git add -u

# LA VERIFICACIÓN: nada tuyo puede haber cambiado salvo los números de build.
echo
echo "▸ verificando que no se perdió trabajo…"
perdidas=0
while IFS= read -r f; do
  [ -z "$f" ] && continue
  n=$(git diff "$antes" -- "$f" | grep -E '^[+-]' | grep -vE '^[+-]{3}' \
      | grep -viE '20[0-9]{10}|Último commit' | wc -l | tr -d ' ')
  if [ "$n" != "0" ]; then
    printf '    %-42s %s líneas distintas\n' "$f" "$n"
    perdidas=$((perdidas+1))
  fi
done < <(printf '%s\n' "${BUMP[@]}")

if [ "$perdidas" != "0" ]; then
  echo "✗ Alguno de los archivos del bump cambió MÁS que su número de versión." >&2
  echo "  Revisá con: git diff $antes -- <archivo>   ·   deshacé con: git merge --abort" >&2
  exit 1
fi
echo "✓ los 5 archivos del bump solo cambiaron su versión — no se perdió nada."
echo "  Corré la suite antes de pushear: ./scripts/test.sh"
