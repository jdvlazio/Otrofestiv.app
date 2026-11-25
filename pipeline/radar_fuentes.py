#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""radar_fuentes.py — qué fuentes se miraron de cada festival, y cuáles faltan.

POR QUÉ (Juan, 25 nov 2026): Medellín Horror Fest llevaba meses en el radar y a un día
de abrir no estaba montado: se había mirado una fuente. Sus horas estaban en la revista
de su web y en la agenda de Comic Con, el evento anfitrión. "Sin información" se decía sin
dejar escrito dónde se buscó.

QUÉ GUARDA: en docs/radar-ancla.json, por festival, `inicio_2026` (AAAA-MM-DD) y
`fuentes_miradas`: {clase: [{url, fecha, resultado, nota?}]}.
  clases: web, redes, sede (recinto o sala), anfitrion (evento, alcaldía, universidad),
          boleteria, prensa, obras (realizadores, distribuidoras), convocatoria.
  resultado: encontro · nada · ilegible · no_aplica · no_mirada
  "ilegible" es que existe y no se pudo leer: NO es "nada". "no_mirada" es un hueco.

CONCLUSIÓN (`conclusion`): montable · montado · sin_informacion · esperando · paso
  "sin_informacion" y el descarte por falta de programa exigen las ocho clases miradas,
  y que al menos un canal propio (web o redes) se haya podido leer. Si no, es "esperando".

    python3 pipeline/radar_fuentes.py            # lo que toca en los próximos 21 días
    python3 pipeline/radar_fuentes.py --dias 35
    python3 pipeline/radar_fuentes.py --ci       # solo forma: no depende de la fecha
Sale con código 1 si hay algo por hacer. Lo que NO prueba: que la lectura se hizo bien.
"""
import datetime
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANCLA = os.path.join(REPO, 'docs', 'radar-ancla.json')
CLASES = ('web', 'redes', 'sede', 'anfitrion', 'boleteria', 'prensa', 'obras', 'convocatoria')
RESULTADOS = ('encontro', 'nada', 'ilegible', 'no_aplica', 'no_mirada')
CONCLUSIONES = ('montable', 'montado', 'sin_informacion', 'esperando', 'paso')
MAX_DIAS = 7        # una lectura más vieja que esto se repite
PREMONTAJE = 14     # a esta distancia el festival ya tiene archivo en festivals/
FECHA = re.compile(r'^\d{4}-\d\d-\d\d$')


def huecos(e):
    """Clases sin mirar."""
    m = e.get('fuentes_miradas') or {}
    return [c for c in CLASES if not any(x.get('resultado') not in (None, 'no_mirada') for x in m.get(c) or [])]


def propio_leido(e):
    m = e.get('fuentes_miradas') or {}
    return any(x.get('resultado') in ('encontro', 'nada') for c in ('web', 'redes') for x in m.get(c) or [])


def forma(e):
    """Errores de forma y conclusiones sin respaldo. No depende de la fecha de hoy."""
    err, c = [], e.get('conclusion')
    if e.get('inicio_2026') and not FECHA.match(str(e['inicio_2026'])):
        err.append('inicio_2026 no es AAAA-MM-DD')
    if c is not None and c not in CONCLUSIONES:
        err.append(f'conclusion desconocida: {c}')
    for clase, xs in (e.get('fuentes_miradas') or {}).items():
        if clase not in CLASES:
            err.append(f'clase desconocida: {clase}')
        for x in xs:
            if x.get('resultado') not in RESULTADOS:
                err.append(f'{clase}: resultado desconocido {x.get("resultado")}')
            if not FECHA.match(str(x.get('fecha') or '')):
                err.append(f'{clase}: sin fecha')
            if x.get('resultado') in ('encontro', 'nada', 'ilegible') and not x.get('url'):
                err.append(f'{clase}: sin url ni búsqueda')
    if c == 'sin_informacion':
        if huecos(e):
            err.append('"sin_informacion" sin mirar: ' + ', '.join(huecos(e)))
        if not propio_leido(e):
            err.append('"sin_informacion" sin leer ningún canal propio: es "esperando"')
    if e.get('motivo_descarte') and re.search(r'sin (informaci|programa)', e['motivo_descarte'], re.I) \
            and e.get('fuentes_miradas') is not None and huecos(e):
        err.append('descartado por falta de programa con fuentes sin mirar')
    return err


def montado(e, repo=REPO):
    d = os.path.join(repo, 'festivals')
    planos = {re.sub(r'\W', '', f[:-5]) for p in (d, os.path.join(d, 'staging')) if os.path.isdir(p)
              for f in os.listdir(p) if f.endswith('.json')}
    return any(i in planos for i in e.get('id_config') or [])


def pendientes(ents, hoy, dias, repo=REPO):
    out = []
    for e in ents:
        if e['estado'] not in ('radar', 'en_app') or e.get('conclusion') == 'paso' or not e.get('inicio_2026'):
            continue
        falta = (datetime.date.fromisoformat(e['inicio_2026']) - hoy).days
        if not 0 <= falta <= dias or (e['estado'] == 'en_app' and montado(e, repo)):
            continue
        que = []
        if huecos(e):
            que.append('sin mirar: ' + ', '.join(huecos(e)))
        fechas = [x['fecha'] for xs in (e.get('fuentes_miradas') or {}).values() for x in xs]
        if fechas and (hoy - datetime.date.fromisoformat(max(fechas))).days > MAX_DIAS:
            que.append(f'última lectura {max(fechas)}')
        if falta <= PREMONTAJE and e.get('conclusion') in (None, 'montable'):
            que.append('sin premontar')
        if que:
            out.append((falta, e['nombre'], que))
    return sorted(out)


def main(argv):
    ents = json.load(open(ANCLA, encoding='utf-8'))['festivales']
    mal = [(e['clave'], x) for e in ents for x in forma(e)]
    for c, x in mal:
        print(f'✗ {c}: {x}')
    if '--ci' in argv:
        return 1 if mal else 0
    dias = int(argv[argv.index('--dias') + 1]) if '--dias' in argv else 21
    p = pendientes(ents, datetime.date.today(), dias)
    for falta, n, que in p:
        print(f'· {n} (en {falta} días): ' + ' · '.join(que))
    sin = [e['nombre'] for e in ents if e['estado'] == 'radar' and not e.get('inicio_2026')
           and e.get('mes') == datetime.date.today().month]
    if sin:
        print('· de este mes y sin día de inicio anotado: ' + ', '.join(sin))
    if not p and not mal and not sin:
        print('✓ nada pendiente')
    return 1 if p or mal or sin else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
