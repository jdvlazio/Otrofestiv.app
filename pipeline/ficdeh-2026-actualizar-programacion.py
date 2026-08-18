# -*- coding: utf-8 -*-
"""Aplica al sidecar que consume el ensamblador los cambios del barrido de hoy.

CONTEXTO — por qué existe este script:

El barrido (`ficdeh-2026-extraer-programacion.py`) escribe
`ficdeh-2026-programacion-canonica.json`, pero el ensamblador lee
`ficdeh-2026-programacion-oficial.json`, que se produjo a mano el 5 ago cuando
Vercel bloqueaba curl. Dos nombres para lo mismo: el barrido quedó sin
consumidor y sus actualizaciones no llegaban al festival. Se descubrió el 8 ago
al revisar Tunja.

Este script cierra el circuito sin reescribir el ensamblador: lee la canónica,
la coteja contra la oficial y aplica SOLO lo decidido, dejando el diff a la
vista. Lo estructural —que el barrido escriba directamente el formato que el
ensamblador espera— queda para el lote de guardianes del pipeline.

DECISIONES APLICADAS (Juan, 8 ago 2026):

  · Medellín manda el PDF; el resto de ciudades, la web.
  · Las actividades de INDUSTRIA siguen fuera. Solo entraron las de Medellín
    que se confirmaron oficialmente; del resto no hubo confirmación.
  · Manizales: si la web quitó funciones, se les cree y se quitan.
"""
import json, os, re, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
OFI = f'{ST}/ficdeh-2026-programacion-oficial.json'
CAN = f'{ST}/ficdeh-2026-programacion-canonica.json'

# Correcciones NUESTRAS que la web no refleja y deben sobrevivir: salen de la
# guía en PDF de Medellín y de los pósters oficiales, que mandan sobre la web.
# Medellín NO se toca desde la web: su fuente es la guía en PDF. La web todavía
# publica funciones que el PDF corrigió —incluida la Akababuru del Banco de la
# República, que quitamos como duplicada en el PR #511— y dejarla entrar aquí
# desharía esa corrección. Solo se le añaden salas, que el ensamblador subordina
# al PDF de todos modos.
CIUDAD_CON_PDF = {'Medellín'}

PROTEGIDAS = {
    ('Medellín', '2026-08-16', '13:00'),   # Los frutos que dan vida (día 1)
    ('Medellín', '2026-08-17', '13:00'),   # Los frutos que dan vida (día 2)
    ('Medellín', '2026-08-18', '16:30'),   # ¿Cómo filmar un país en guerra?
    ('Medellín', '2026-08-18', '18:00'),   # Lo que sentimos — La Pascasia
}


# [lib-unica] renombrada desde `norm` el 17 ago 2026.
# Corta el título en el guion largo («… — Jueves» → «…»). `lib.norm` no corta.
def norm_hasta_guion(s):
    s = ''.join(c for c in unicodedata.normalize('NFD', (s or '').lower())
                if unicodedata.category(c) != 'Mn')
    return ' '.join(re.sub(r'[^a-z0-9]', ' ', s).split()[:5])


def main():
    ofi = json.load(open(OFI, encoding='utf-8'))
    can = json.load(open(CAN, encoding='utf-8'))
    can = can.get('funciones') or can
    F = ofi['funciones']

    k_o = lambda x: (x['ciudad'], x['dia'], x['hora'], norm_hasta_guion(x['titulo_programacion']))
    k_c = lambda x: (x['ciudad'], x['dia'], x['hora'], norm_hasta_guion(x['titulo']))
    O = {k_o(x): x for x in F}
    C = {k_c(x): x for x in can if x.get('en_app', True)}
    # El catálogo dice qué títulos son OBRAS. Lo que la web trae y no está en él
    # es actividad de industria y se queda fuera: no hubo confirmación oficial.
    catalogo = {norm_hasta_guion(x['titulo_programacion']) for x in F}

    salas = quitadas = nuevas = 0

    # 1 · salas que la web publica y el sidecar no tenía. Medellín incluido:
    #     el ensamblador ya le da prioridad al PDF sobre este campo.
    for k, c in C.items():
        o = O.get(k)
        if o is not None and c.get('sala') and not o.get('sala'):
            o['sala'] = c['sala']
            o['_src_sala'] = 'web ficdeh.com, barrido 8 ago'
            salas += 1

    # 2 · funciones que la web retiró. Se les cree, salvo las protegidas y las
    #     de las ciudades cuya fuente es el PDF.
    for k, o in list(O.items()):
        if k in C or not o.get('en_app', True) or o.get('_motivo_exclusion'):
            continue
        if (k[0], k[1], k[2]) in PROTEGIDAS or k[0] in CIUDAD_CON_PDF:
            continue
        o['en_app'] = False
        o['_motivo_exclusion'] = 'retirada de la web del festival (barrido 8 ago)'
        quitadas += 1

    # 3 · funciones nuevas, SOLO de obras que ya están en el catálogo.
    for k, c in C.items():
        if k in O or k[3] not in catalogo or k[0] in CIUDAD_CON_PDF:
            continue
        base = next(x for x in F if norm_hasta_guion(x['titulo_programacion']) == k[3])
        F.append({**{campo: base.get(campo, '') for campo in
                     ('titulo_programacion', 'director_programacion', 'obra_catalogo',
                      'tipo', 'poster_url')},
                  'ciudad': c['ciudad'], 'dia': c['dia'], 'hora': c['hora'],
                  'sede': c['sede'], 'direccion': c.get('direccion', ''),
                  'sala': c.get('sala', ''), 'ingreso': c.get('acceso', ''),
                  'en_app': True,
                  '_src': 'web ficdeh.com, barrido 8 ago — función que la web añadió'})
        nuevas += 1

    ofi.setdefault('_provenance', {})['actualizado'] = (
        '8 ago 2026 desde el barrido de la web (pipeline/ficdeh-2026-actualizar-'
        'programacion.py): salas añadidas, funciones retiradas por el festival y '
        'funciones nuevas de obras ya catalogadas. Industria sigue fuera.')
    json.dump(ofi, open(OFI, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'salas añadidas {salas} · funciones retiradas {quitadas} · nuevas {nuevas}')
    for x in F:
        if x.get('_motivo_exclusion', '').startswith('retirada'):
            print(f'  − {x["ciudad"]:12} {x["dia"]} {x["hora"]}  {x["titulo_programacion"][:40]}')
        if x.get('_src', '').startswith('web ficdeh.com, barrido 8 ago —'):
            print(f'  + {x["ciudad"]:12} {x["dia"]} {x["hora"]}  {x["titulo_programacion"][:40]}  {x["sede"][:26]}')


if __name__ == '__main__':
    main()
