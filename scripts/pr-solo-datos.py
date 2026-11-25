#!/usr/bin/env python3
"""pr-solo-datos.py — ¿este PR es SOLO datos de festival? (guardián del merge solo)

POR QUÉ EXISTE (2 nov 2026). Juan pidió que los ajustes que anuncia un festival
—y los afiches— entren a producción sin esperar su OK: «no puedo estar todo el
tiempo pendiente de un celular». El merge automático es seguro solo si el PR no
trae código de la app. Este guardián lo decide mirando el diff, no el nombre de
la rama: una rama `data/*` con un cambio en `src/` no pasa.

QUÉ ACEPTA
  · festivals/, fuentes/, catalogo/, docs/radar-ancla.json
  · pipeline/<festival>-*.py|json (crudos, planes, verificadores) y
    pipeline/ig-vigia-cuentas.json
  · assets/ (afiches, keyArt, FECHAS.json, HUELLAS.txt)
  · src/config.js SOLO si cada línea cambiada es un `keyArt:'/assets/keyart/…'`

    python3 scripts/pr-solo-datos.py <PR>      # sale 0 si es solo datos, 1 si no
"""
import json, re, subprocess, sys

PERMITIDOS = (
    re.compile(r'^festivals/'),
    re.compile(r'^fuentes/'),
    re.compile(r'^catalogo/'),
    re.compile(r'^assets/'),
    re.compile(r'^docs/radar-ancla\.json$'),
    re.compile(r'^pipeline/ig-vigia-cuentas\.json$'),
    re.compile(r'^pipeline/[a-z0-9]+-20\d\d[-.][\w.-]*\.(py|json)$'),
)
LINEA_KEYART = re.compile(r"^\s*keyArt:'/assets/keyart/[\w.-]+\.(jpg|jpeg|webp|png)',?\s*$")


def revisar(archivos, diff_config):
    """Devuelve la lista de motivos por los que NO es solo datos (vacía = pasa)."""
    malos = [a for a in archivos if a != 'src/config.js' and not any(p.search(a) for p in PERMITIDOS)]
    motivos = [f'archivo fuera de datos: {a}' for a in malos]
    if 'src/config.js' in archivos:
        for l in diff_config.splitlines():
            if not l.startswith(('+', '-')):
                continue
            if not LINEA_KEYART.match(l[1:]):
                motivos.append(f'src/config.js cambia algo que no es keyArt: {l[:100]}')
    return motivos


def completo(archivos, total, diff):
    """`gh pr view --json files` da 100 y callaba: en BOGOSHORTS vio 100 de 929 (25 nov 2026)."""
    motivos = []
    if len(archivos) != total:
        motivos.append(f'no pude ver todos los archivos: {len(archivos)} de {total}')
    if 'src/config.js' in archivos and not diff:
        motivos.append('no pude ver el cambio de src/config.js')
    return motivos


def traer(pr):
    total = json.loads(subprocess.check_output(['gh', 'pr', 'view', pr, '--json', 'changedFiles']))['changedFiles']
    xs = [json.loads(l) for l in subprocess.check_output(
        ['gh', 'api', '--paginate', f'repos/{{owner}}/{{repo}}/pulls/{int(pr)}/files?per_page=100',
         '--jq', '.[] | {filename, previous_filename, patch: (if .filename == "src/config.js" then .patch else null end)}'],
        text=True).splitlines() if l]
    # un renombre también saca al archivo de donde estaba
    archivos = [x['filename'] for x in xs]
    viejos = [x['previous_filename'] for x in xs if x.get('previous_filename')]
    diff = next((x.get('patch') or '' for x in xs if x['filename'] == 'src/config.js'), '')
    if len(archivos) != total:
        return archivos, diff, total
    return archivos + viejos, diff, total + len(viejos)


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    pr = sys.argv[1]
    archivos, diff, total = traer(pr)
    motivos = revisar(archivos, diff) + completo(archivos, total, diff)
    if motivos:
        print(f'✗ PR {pr}: NO es solo datos — necesita a Juan')
        for m in motivos:
            print('  ·', m)
        sys.exit(1)
    print(f'✓ PR {pr}: solo datos ({len(archivos)} archivos) — se puede mergear solo')


if __name__ == '__main__':
    main()
