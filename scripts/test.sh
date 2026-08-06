#!/usr/bin/env bash
# test.sh — corre la suite Playwright AISLADA de cualquier otra corrida.
#
# POR QUÉ EXISTE (6 ago 2026)
# Playwright mata el servidor que él levantó al terminar. Con
# `reuseExistingServer` (local), una segunda corrida reusa ese servidor en vez de
# levantar el suyo — y si la primera termina antes, la segunda se queda sin
# servidor a mitad de camino: net::ERR_CONNECTION_REFUSED y una cascada de
# timeouts de 30s en specs que no tienen nada que ver entre sí.
# Medido: la misma suite da 21/21 sola y 1/21 con otra corrida solapada. Ese era
# el "flaky" que llevábamos meses tapando con `retries`.
#
# Pasaba a diario sin que se notara: dos sesiones de Claude Code trabajando en
# esta carpeta, o simplemente dos corridas encimadas en la misma sesión.
#
# QUÉ HACE
# Un puerto libre por corrida → servidor propio → cero colisión. Y de paso aísla
# los artefactos, que también se pisaban (el JSON de resultados es un único
# archivo: dos corridas simultáneas se sobreescriben el informe).
#
# USO
#     ./scripts/test.sh                      # toda la suite
#     ./scripts/test.sh tests/programa.spec.js
#     ./scripts/test.sh -g "T51"
# Cualquier argumento se pasa tal cual a `playwright test`.
set -euo pipefail
cd "$(dirname "$0")/.."

# Primer puerto libre desde 3000. El rango da margen de sobra: cada corrida toma
# uno y lo suelta al terminar.
puerto=""
for p in $(seq 3000 3099); do
  if ! (exec 3<>"/dev/tcp/127.0.0.1/$p") 2>/dev/null; then puerto=$p; break; fi
  exec 3>&- 2>/dev/null || true
done
if [ -z "$puerto" ]; then
  echo "No hay puertos libres entre 3000 y 3099 — ¿quedaron servidores huérfanos?" >&2
  exit 1
fi

export PW_PORT="$puerto"
# Artefactos por corrida: el JSON, el informe HTML y los adjuntos de fallo.
export PLAYWRIGHT_JSON_OUTPUT_NAME="test-results-$puerto.json"
export PLAYWRIGHT_HTML_REPORT="playwright-report-$puerto"

echo "▸ puerto $puerto · resultados en $PLAYWRIGHT_JSON_OUTPUT_NAME"
npx playwright test --output="test-results-$puerto" "$@"
