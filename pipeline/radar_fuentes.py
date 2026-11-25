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
  resultado: encontro · nada · ilegible · no_aplica · extracto · no_mirada
  "encontro" y "nada" son de una página ABIERTA. Lo que solo se vio en el resultado de un
  buscador es "extracto" y sigue siendo hueco. "no_aplica" lleva nota con el porqué.
  Una búsqueda ("búsqueda: ...") cierra prensa, obras, anfitrión y boletería; web, redes,
  sede y convocatoria se cierran abriendo la página.
  "ilegible" es que existe y no se pudo leer: NO es "nada". "no_mirada" es un hueco.

CONCLUSIÓN (`conclusion`): montable · montado · sin_informacion · esperando · paso
  "sin_informacion" y el descarte por falta de programa exigen las ocho clases miradas,
  y que al menos un canal propio (web o redes) se haya podido leer. Si no, es "esperando".

    python3 pipeline/radar_fuentes.py            # lo que toca en los próximos 45 días
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
RESULTADOS = ('encontro', 'nada', 'ilegible', 'no_aplica', 'extracto', 'no_mirada')
CONCLUSIONES = ('montable', 'montado', 'sin_informacion', 'esperando', 'paso')
MAX_DIAS = 7        # una lectura más vieja que esto se repite
MAX_DIAS_CERCA = 2  # a PREMONTAJE días o menos, cada dos días
VIVAS = ('web', 'redes', 'sede', 'anfitrion', 'boleteria')  # donde aparecen las horas
PAGINA = ('web', 'redes', 'sede', 'convocatoria')           # una búsqueda no las cierra
LIMITE = 4          # se publica lo confirmado a más tardar 4 días antes
PREMONTAJE = 14     # a esta distancia el festival ya tiene archivo en festivals/
FECHA = re.compile(r'^\d{4}-\d\d-\d\d$')


def huecos(e):
    """Clases sin mirar."""
    m = e.get('fuentes_miradas') or {}
    return [c for c in CLASES if not any(cierra(c, x) for x in m.get(c) or [])]


def cierra(clase, x):
    """¿Esta lectura cierra la clase?"""
    if x.get('resultado') in (None, 'no_mirada', 'extracto'):
        return False
    if x['resultado'] in ('encontro', 'nada') and clase in PAGINA:
        return str(x.get('url') or '').startswith('http')
    return True


def viejas(e, hoy, falta):
    """Clases vivas cuya última lectura ya caducó. Por clase: un post de hoy no tapa una sede de hace un mes."""
    tope = MAX_DIAS_CERCA if falta <= PREMONTAJE else MAX_DIAS
    out = []
    for c in VIVAS:
        xs = [x for x in (e.get('fuentes_miradas') or {}).get(c) or [] if cierra(c, x)]
        if xs and not any(x['resultado'] == 'no_aplica' for x in xs):
            u = max(x['fecha'] for x in xs)
            if (hoy - datetime.date.fromisoformat(u)).days > tope:
                out.append(f'{c} ({u})')
    return out


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
            if x.get('resultado') == 'no_aplica' and not x.get('nota'):
                err.append(f'{clase}: "no_aplica" sin decir por qué')
            if x.get('resultado') in ('encontro', 'nada', 'ilegible', 'extracto') and not x.get('url'):
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


def publicado(e, repo=REPO):
    """El JSON publicado del festival, o None. Lo de festivals/staging/ es pre-montaje: no cuenta."""
    d = os.path.join(repo, 'festivals')
    for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if f.endswith('.json') and re.sub(r'\W', '', f[:-5]) in (e.get('id_config') or []):
            j = json.load(open(os.path.join(d, f), encoding='utf-8'))
            if isinstance(j, dict) and j.get('films'):
                return j
    return None


def sin_hora(j):
    return [x.get('title') for x in j['films'] if not x.get('time')]


def pendientes(ents, hoy, dias, repo=REPO):
    out = []
    for e in ents:
        if e['estado'] not in ('radar', 'en_app') or e.get('conclusion') == 'paso':
            continue
        j = publicado(e, repo)
        ini = e.get('inicio_2026') or (j and str(j.get('festivalStartStr') or '')[:10])
        if not ini or not FECHA.match(ini):
            continue
        falta = (datetime.date.fromisoformat(ini) - hoy).days
        if not 0 <= falta <= dias:
            continue
        que = []
        if j:
            # Publicado: solo queda en el control mientras tenga algo sin hora.
            s = sin_hora(j)
            if not s:
                continue
            que.append('publicado con obras sin hora: ' + ', '.join(map(str, s[:5])))
            if e.get('fuentes_miradas') and not huecos(e) and not viejas(e, hoy, falta):
                continue
        if huecos(e):
            que.append('sin mirar: ' + ', '.join(huecos(e)))
        if viejas(e, hoy, falta):
            que.append('releer: ' + ', '.join(viejas(e, hoy, falta)))
        if not j and falta <= PREMONTAJE and e.get('conclusion') in (None, 'montable'):
            que.append('sin publicar')
        if not j and falta <= LIMITE and e.get('conclusion') != 'sin_informacion':
            que.append(f'a {falta} días y sin publicar: montar lo confirmado')
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
    dias = int(argv[argv.index('--dias') + 1]) if '--dias' in argv else 45
    hoy = datetime.date.today()
    p = pendientes(ents, hoy, dias)
    for falta, n, que in p:
        print(f'· {n} (en {falta} días): ' + ' · '.join(que))
    sin = [e['nombre'] for e in ents if e['estado'] == 'radar' and not e.get('inicio_2026')
           and e.get('conclusion') != 'paso' and e.get('mes') in (hoy.month, hoy.month % 12 + 1)]
    if sin:
        print('· de este mes o el próximo y sin día de inicio anotado: ' + ', '.join(sin))
    if not p and not mal and not sin:
        print('✓ nada pendiente')
    return 1 if p or mal or sin else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
