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

# ── ¿PUEDE esta máquina decir la verdad? (10 ago 2026) ───────────────────────
# Medido: con la máquina libre la suite da 0 fallos a 5 workers, dos corridas
# seguidas. Con carga externa —otra sesión de Claude corriendo SUS tests en la
# misma máquina— la MISMA suite falló 11 veces, y 5, y 6, con tests distintos cada
# vez. El puerto propio (arriba) aisló el servidor, pero no aísla la CPU.
#
# Esto no bloquea: avisa. Un rojo bajo carga no es un rojo de la app, y un test
# que "pasa al segundo intento" no distingue "la máquina estaba ocupada" de "la
# app falla una de cada tres veces". Si el banner aparece, el resultado de esta
# corrida no es evidencia de nada — repetila con la máquina quieta.
nucleos=$(sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo 1)
carga=$(uptime | sed -E 's/.*averages?:? *//' | awk '{print $1}' | tr -d ',')
# `|| true` NO es decorativo: con `set -o pipefail` (arriba), un pgrep sin
# coincidencias devuelve 1 y `set -e` mataba el script ANTES de correr un solo
# test — el modo de fallo más tonto posible: cero salida, exit 1, nada que leer.
otras=$(pgrep -f 'playwright test' 2>/dev/null | wc -l | tr -d ' ' || true)
cargada=$(awk -v c="$carga" -v n="$nucleos" 'BEGIN{print (c+0 > n*0.7) ? 1 : 0}' 2>/dev/null || echo 0)
sospechosa=0
if [ "$cargada" = "1" ] || [ "${otras:-0}" -gt 0 ]; then
  sospechosa=1
  echo ""
  echo "  ⚠  MÁQUINA CARGADA — esta corrida puede reportar fallos FALSOS"
  # `${otras:+…}` se expandía con otras=0 («0 corrida(s) ya en curso»): "0" no es
  # cadena vacía. La condición es sobre el NÚMERO, no sobre si la variable existe.
  _otras_txt=""
  [ "${otras:-0}" -gt 0 ] && _otras_txt=" · $otras corrida(s) de Playwright ya en curso"
  echo "     carga $carga sobre $nucleos núcleos$_otras_txt"
  echo "     Los tests que fallen acá pueden ser de la CPU, no de la app."
  echo "     Para un veredicto confiable: esperá a que la máquina esté quieta y repetí."
  echo ""
fi

echo "▸ puerto $puerto · resultados en $PLAYWRIGHT_JSON_OUTPUT_NAME"
_salida="$(mktemp)"
set +e
npx playwright test --output="test-results-$puerto" "$@" 2>&1 | tee "$_salida"
_code=${PIPESTATUS[0]}
set -e

# ── Veredicto explícito ──────────────────────────────────────────────────────
# `flaky` NO se lee como verde: un test que pasó al reintento es una pregunta sin
# responder, no un éxito. Se nombra acá para que nadie lo confunda con 0 fallos.
# SIN ancla `^`: el reporter `line` reescribe la línea con secuencias de escape del
# terminal (ESC[1A ESC[2K) ANTES del texto, así que `^  1 flaky` NUNCA casaba y el
# aviso no salía aunque Playwright sí reportara el flaky. Probado con un test que
# falla en el 1er intento y pasa en el 2º.
_nflaky=$(grep -oE '[0-9]+ flaky' "$_salida" 2>/dev/null | awk '{print $1}' | tail -1 || true)
if [ -n "${_nflaky:-}" ] && [ "${_nflaky:-0}" -gt 0 ]; then
  echo ""
  echo "  ⚠  $_nflaky test(s) FLAKY — pasaron al reintento."
  echo "     Un flaky no es un test que pasa: es un test que no sabe si pasa."
  grep -oE '\[chromium\][^\n]*' "$_salida" | tail -12 || true
fi
if [ "$sospechosa" = "1" ] && [ "$_code" != "0" ]; then
  echo ""
  echo "  ⚠  Hubo fallos Y la máquina estaba cargada: NO concluyas nada de esta corrida."
fi
rm -f "$_salida"
exit "$_code"
