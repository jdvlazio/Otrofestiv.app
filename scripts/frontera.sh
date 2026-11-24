#!/usr/bin/env bash
# frontera.sh <base> <head> — «un cambio toca código o toca datos, no las dos cosas».
# DUEÑO ÚNICO de la regla (28 oct 2026): lo corren el CI (frontera.yml) y el
# candado local (.githooks/pre-push). Antes vivía solo en el CI y una mezcla se
# veía recién tras subir y 20 min de pruebas: así se trabaron las horas de Miradas
# (#1338, una línea de validate.py dentro de un PR de datos).
# ETIQUETADO=true (la etiqueta frontera-ok del PR) deja pasar la mezcla.
set -uo pipefail
BASE_SHA="$1"; HEAD_SHA="$2"; ETIQUETADO="${ETIQUETADO:-false}"
CHANGED=$(git diff --name-only "$BASE_SHA...$HEAD_SHA")
echo "Archivos cambiados:"; echo "$CHANGED"; echo "---"

# Código: la app. src/config.js NO cuenta — es donde se registra un festival.
CAND=$(printf '%s\n' "$CHANGED" | grep -E '^(src/|index\.html$|sw\.js$|validate\.py$|tests/|scripts/)' \
      | grep -vx 'src/config.js' || true)

# …ni cuenta el CHURN DEL BUMP DE VERSIÓN. `scripts/bump-version.js` reescribe
# la cadena de build en index.html, sw.js y src/main.js, y publicar EXIGE el
# bump — así que sin este filtro el guardián se disparaba en TODO PR de
# festival y pedía la etiqueta cada vez. Medido en el PR #703: los tres
# archivos tenían CERO líneas cambiadas que no fueran la versión.
# Los patrones son los cinco que escribe el script, con sus 12 dígitos; un
# archivo solo se descarta si TODAS sus líneas cambiadas son de esa forma,
# así que un cambio real en el mismo archivo sigue contando.
BUMP='(otrofestiv-v[0-9]{12}|BUILD = .[0-9]{12}.|BUILD_VERSION=.[0-9]{12}.|main\.js\?v=[0-9]{12}|favicon(-192)?\.png\?v=[0-9]{12})'
COD=''
for f in $CAND; do
  REAL=$(git diff "$BASE_SHA...$HEAD_SHA" -- "$f" \
         | grep -E '^[+-]' | grep -vE '^(\+\+\+|---)' \
         | grep -vE "$BUMP" || true)
  if [ -n "$REAL" ]; then
    COD="$COD$f"$'\n'
  else
    echo "· $f: solo bump de versión, no cuenta como código"
  fi
done
COD=$(printf '%s' "$COD" | sed '/^$/d')
# Datos: el material de un festival.
DAT=$(printf '%s\n' "$CHANGED" | grep -E '^(festivals/|assets/)' || true)

if [ -z "$COD" ] || [ -z "$DAT" ]; then
  echo "✓ El PR se queda de un solo lado de la frontera."
  exit 0
fi

echo "Código:"; printf '%s\n' "$COD" | sed 's/^/    /'
echo "Datos:";  printf '%s\n' "$DAT" | sed 's/^/    /'

if [ "$ETIQUETADO" = "true" ]; then
  echo "⚠ Mezcla código+datos, permitida por la etiqueta 'frontera-ok'."
  exit 0
fi

echo "::error::Este PR mezcla código de la app con datos de festival. Separalos en dos PR (primero el de app, para que el dato nunca llegue a producción antes del código que sabe leerlo). Si la mezcla es deliberada, etiquetá el PR como 'frontera-ok'."
exit 1
