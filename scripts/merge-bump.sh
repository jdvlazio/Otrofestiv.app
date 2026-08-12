#!/usr/bin/env bash
# merge-bump.sh — driver de merge para los archivos que lleva el número de build.
#
# POR QUÉ EXISTE
# El 8 ago 2026, CINCO de los cinco conflictos del día fueron el mismo timestamp
# de 12 dígitos en index.html, src/main.js, sw.js y version.json. Ninguno fue un
# conflicto real de contenido. Y como tres de esos archivos TAMBIÉN llevan código,
# el conflicto parece trivial y no lo es: resolverlo con `checkout --theirs` se
# llevó por delante el markup del sheet de ciudad, `ticketBadgeTarget` y el CSS de
# `.fn-ciudad` en dos accidentes distintos de la misma semana.
#
# La colisión es estructural, no de coordinación: `bump-version.js` estampa el
# MISMO renglón en cada rama antes de cada push. Con dos ramas vivas, el conflicto
# no es probable — es seguro, una vez por PR.
#
# QUÉ HACE
# Reemplaza el build por un marcador en los tres lados, deja que git haga el merge
# de verdad, y estampa de vuelta el build MÁS ALTO de los dos lados. Resultado:
#   · conflicto que era SOLO el número  → se resuelve solo, con el build correcto.
#   · conflicto de contenido REAL       → sale con 1 y git deja los marcadores.
# Es decir: desaparece el ruido y sobrevive intacta la señal.
#
# Normaliza los patrones EXACTOS que escribe bump-version.js, nunca «cualquier
# número de 12 dígitos»: un regex ancho podría pisar una coordenada o un id.
#
# INSTALACIÓN
# El driver se declara en .gitattributes, pero registrarlo es config LOCAL de cada
# clon (git no ejecuta comandos que vengan del repo — es una defensa suya, no un
# descuido). Lo enchufa scripts/install-hooks.sh, y [merge-driver] en validate.py
# avisa si falta.
#
# USO (lo invoca git, no vos):
#     merge-bump.sh %O %A %B
#       %O = ancestro común   %A = nuestro lado (y archivo de salida)   %B = el otro
set -uo pipefail

BASE=${1:?falta %O}; OURS=${2:?falta %A}; THEIRS=${3:?falta %B}

# Los patrones del bump, uno por uno. Ver scripts/bump-version.js.
normalizar() {
  sed -E -e "s/BUILD_VERSION='[0-9]{12}'/BUILD_VERSION='@@BUILD@@'/g" \
         -e "s/otrofestiv-v[0-9]{12}/otrofestiv-v@@BUILD@@/g" \
         -e "s/BUILD = '[0-9]{12}'/BUILD = '@@BUILD@@'/g" \
         -e "s/\?v=[0-9]{12}/?v=@@BUILD@@/g" \
         -e "s/(\"(android|ios)\": \")[0-9]{12}\"/\1@@BUILD@@\"/g" \
         "$1"
}

# El build ganador: el mayor de los dos lados. Son timestamps YYYYMMDDHHmm, así que
# «mayor» es «más nuevo». Se lee SOLO de los patrones del bump —no de cualquier
# número de 12 dígitos del archivo—, por la misma razón que no se normalizan.
builds() {
  grep -hoE "BUILD_VERSION='[0-9]{12}'|otrofestiv-v[0-9]{12}|BUILD = '[0-9]{12}'|\?v=[0-9]{12}|\"(android|ios)\": \"[0-9]{12}\"" \
       "$1" 2>/dev/null | grep -oE "[0-9]{12}"
}
build=$( { builds "$OURS"; builds "$THEIRS"; } | sort -n | tail -1 )

tmp=$(mktemp -d) || exit 1
trap 'rm -rf "$tmp"' EXIT

normalizar "$BASE"   > "$tmp/base"
normalizar "$OURS"   > "$tmp/ours"
normalizar "$THEIRS" > "$tmp/theirs"

# El merge de verdad, ya sin el ruido del build.
if ! git merge-file -L ours -L base -L theirs "$tmp/ours" "$tmp/base" "$tmp/theirs" >/dev/null 2>&1; then
  # Queda contenido en conflicto: NO lo resolvemos por nuestra cuenta. Se escriben
  # los marcadores (con el build de vuelta) y se sale con 1 para que git lo marque
  # como pendiente. Que un conflicto real siga siendo un conflicto es el punto.
  if [ -n "$build" ]; then sed -E "s/@@BUILD@@/$build/g" "$tmp/ours" > "$OURS"; else cp "$tmp/ours" "$OURS"; fi
  exit 1
fi

if [ -n "$build" ]; then
  sed -E "s/@@BUILD@@/$build/g" "$tmp/ours" > "$OURS"
else
  cp "$tmp/ours" "$OURS"
fi
exit 0
