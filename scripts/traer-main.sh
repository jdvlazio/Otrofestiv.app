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

# Desde ago 2026 el driver `bump` (.gitattributes + scripts/merge-bump.sh) resuelve
# estos cuatro solo, así que lo normal es que este script no tenga nada que hacer.
# Se queda como red: en un clon sin `install-hooks.sh` corrido, el driver no está
# registrado y los conflictos vuelven. CLAUDE.md salió de la lista — ya no lo toca
# el bump.
BUMP=(index.html src/main.js sw.js version.json)
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

# LA VERIFICACIÓN — «¿siguen mis líneas?», no «¿cambió el archivo?».
# La primera versión comparaba el archivo contra el commit previo y marcaba
# cualquier diferencia: falso positivo garantizado, porque main APORTA cambios
# legítimos. Lo que hay que defender es lo MÍO: cada línea que agregué desde que
# la rama se separó de main tiene que seguir presente después del merge. Así se
# caza el accidente real —el CSS de .fn-ciudad y el markup del city-sheet
# desaparecieron sin que nadie los borrara a propósito—.
echo
echo "▸ verificando que no se perdió trabajo…"
base=$(git merge-base origin/main "$antes")
perdidas=0
for f in "${BUMP[@]}"; do
  [ -f "$f" ] || continue
  mias=$(git diff "$base" "$antes" -- "$f" | grep '^+' | grep -v '^+++' | sed 's/^+//' \
         | grep -vE '20[0-9]{10}|Último commit' | grep -vE '^[[:space:]]*$' || true)
  [ -z "$mias" ] && continue
  faltan=0
  while IFS= read -r linea; do
    [ -z "$linea" ] && continue
    grep -qF -- "$linea" "$f" || faltan=$((faltan+1))
  done <<< "$mias"
  if [ "$faltan" != "0" ]; then
    printf '    %-30s %s línea(s) TUYAS desaparecieron\n' "$f" "$faltan"
    perdidas=$((perdidas+1))
  fi
done

if [ "$perdidas" != "0" ]; then
  echo "✗ El merge se llevó trabajo tuyo por delante." >&2
  echo "  Deshacé con: git reset --hard $antes   ·   y resolvé los conflictos a mano." >&2
  exit 1
fi
echo "✓ ninguna línea propia se perdió en el merge."
echo "  Corré la suite antes de pushear: ./scripts/test.sh"
