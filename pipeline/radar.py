#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""radar.py <fest-id> — el issue de radar, como fuente del onboarding.

POR QUÉ EXISTE. El 16 sep 2026 monté #NarrarElFuturo mirando su web, su
Instagram y la agenda de la Cinemateca, y publiqué la sala del miércoles como
«Sala» —un rótulo, no un lugar— y seis conversatorios sin marcar. Las dos cosas
estaban escritas, con esas palabras, en el issue de radar del festival OCHO DÍAS
ANTES:

    «Tres posts del 8 SEP, todos bajo la franja #RTMeetTheCreators (proyección
     + conversatorio con quien la dirigió)»
    «mié 16 SEP | 3:00 p. m. | Aula Magistral 704-M16, U. Jorge Tadeo Lozano»

El radar no falló: vigiló el festival desde el 11 de agosto y registró cada
cambio. Falló el ENGANCHE — el onboarding no lo leía. Y lo que depende de que
alguien se acuerde, un día no pasa.

QUÉ HACE
  1. Baja el issue y TODOS sus comentarios a un sidecar versionado. El radar es
     una fuente como la web o Instagram, y las fuentes se guardan.
  2. Si existe el crudo, CRUZA: toda sala y toda hora que el radar nombró tiene
     que aparecer en lo que vamos a publicar. Una sala que el radar vio y
     nosotros no tenemos es casi siempre un dato que perdimos por el camino.

El número de issue se declara en el plan (`festival.radar`), no se busca a ojo:
un festival puede tener issues parecidos y el plan es donde viven las decisiones.

Lee   pipeline/<id>.plan.json  →  festival.radar
      festivals/staging/<id>-crudo.json  (si existe, para cruzar)
Esc.  festivals/staging/<id>-radar.json

Necesita `gh` autenticado.
"""
import io, json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import norm, provenance

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'

# Una SALA es un nombre propio detrás de su clase. El tope de palabras evita
# tragarse la frase entera: «Aula Magistral 704-M16, U. Jorge Tadeo» son tres.
RE_SALA = re.compile(r'\b((?:Sala|Aula|Hemiciclo|Laboratorios?|Teatro|Auditorio)'
                     r'(?:\s+[A-ZÁÉÍÓÚÑ0-9][\w\-áéíóúñ]*){0,3})')
RE_HORA = re.compile(r'\b(\d{1,2}):(\d{2})\s*(?:([ap])\.?\s*m|h)\b', re.I)
# Ruido conocido: clases sueltas y las salas de OTRAS ediciones que el radar cita
IGNORA = {'sala', 'aula', 'teatro', 'auditorio', 'laboratorio', 'laboratorios'}


def plan(fid):
    p = f'{REPO}/pipeline/{fid}.plan.json'
    return json.load(io.open(p, encoding='utf-8')) if os.path.exists(p) else {}


def gh_issue(n):
    r = subprocess.run(['gh', 'issue', 'view', str(n), '--json', 'title,body,comments,state,url'],
                       capture_output=True, text=True, cwd=REPO)
    if r.returncode:
        sys.exit(f'✗ no se pudo leer el issue #{n}: {(r.stderr or "").strip()[:160]}')
    return json.loads(r.stdout)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    fid = sys.argv[1]
    P = plan(fid)
    cfg = P.get('festival', {})
    # La declaración vive en la RAÍZ del plan: tres planes no tienen bloque
    # `festival` —los de pre-onboarding, que aún no tienen festival que armar—
    # y el radar se vigila desde antes de que exista la parrilla.
    n = P.get('radar', cfg.get('radar'))
    if n is None and 'radar' in P:
        sys.exit(f'✗ {fid}: el plan declara `radar: null`.\n'
                 f'  {P.get("radar_nota", "sin issue de radar: hay que crearlo")}')
    if not n:
        sys.exit(f'✗ {fid}: el plan no declara `festival.radar`.\n'
                 f'  El issue de radar es una FUENTE del onboarding, no un adorno: añadí\n'
                 f'  "radar": <número> al bloque `festival` del plan.')

    destino = P.get('radar_volcado') or cfg.get('radar_volcado') or f'festivals/staging/{fid}-radar.json'
    iss = gh_issue(n)
    os.makedirs(ST, exist_ok=True)
    io.open(f'{REPO}/{destino}', 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance(f'issue de radar #{n} — {iss.get("url")}',
                                  titulo=iss.get('title'), estado=iss.get('state'),
                                  comentarios=len(iss.get('comments') or [])),
        'issue': n, 'titulo': iss.get('title'), 'estado': iss.get('state'),
        'cuerpo': iss.get('body'),
        'comentarios': [{'fecha': c.get('createdAt', '')[:10], 'cuerpo': c['body']}
                        for c in iss.get('comments') or []],
    }, ensure_ascii=False, indent=1) + '\n')
    # El cruce lee el VOLCADO, no lo que acaba de bajar: así el paso se puede
    # repetir sin red, y el archivo versionado es de verdad la fuente y no una
    # copia de cortesía que nadie mira.
    volc = json.load(io.open(f'{REPO}/{destino}', encoding='utf-8'))
    texto = '\n\n'.join([volc.get('cuerpo') or ''] + [c['cuerpo'] for c in volc['comentarios']])
    print(f'── radar #{n}: {len(volc["comentarios"])} comentarios → {os.path.basename(destino)}')

    crudo_p = f'{ST}/{fid}-crudo.json'
    if not os.path.exists(crudo_p):
        print('   (sin crudo todavía: el cruce corre cuando exista)')
        return
    crudo = json.load(io.open(crudo_p, encoding='utf-8'))
    nuestras_salas = {norm(f.get('sala')) for f in crudo['funciones']} | \
                     {norm(f.get('sede')) for f in crudo['funciones']}
    nuestras_horas = {f.get('hora') for f in crudo['funciones']}

    # Una sala solo cuenta si está CERCA DE UNA SEDE NUESTRA. El radar cita de
    # pasada otros festivales —«Teatro los Fundadores – Sala Olimpia
    # (Manizales)» es de FICMA— y sin este cerco cada corrida traería ruido
    # ajeno, que es la forma más rápida de que un aviso deje de leerse.
    sedes = {norm(f.get('sede')) for f in crudo['funciones'] if f.get('sede')}
    sedes |= {norm(s.split(' - ')[0]) for s in sedes}
    salas = {}
    for m in RE_SALA.finditer(texto):
        s = m.group(1).strip()
        if norm(s) in IGNORA:
            continue
        # la captura puede quedarse corta («Aula Magistral» por «Aula Magistral
        # 704-M16»): cuenta como presente si una contiene a la otra
        if any(norm(s) in x or x in norm(s) for x in nuestras_salas if x):
            continue
        cerca = norm(texto[max(0, m.start() - 140):m.end() + 140])
        if not any(sede in cerca for sede in sedes if sede):
            continue
        salas.setdefault(norm(s), s)
    # Las HORAS se informan, no bloquean: el radar escribe rangos («9:00 a. m. –
    # 1:00 p. m.») y fechas de cierre de convocatoria, y el final de un rango no
    # es el comienzo de una función. Se descartan las precedidas de guion o «a».
    horas = set()
    for m in RE_HORA.finditer(texto):
        if re.search(r'(–|—|-|\ba)\s*$', texto[max(0, m.start() - 4):m.start()]):
            continue
        h, mm, ap = m.groups()
        h24 = f'{int(h) % 12 + (12 if (ap or "").lower() == "p" else 0):02d}:{mm}'
        if h24 not in nuestras_horas:
            horas.add(h24)

    if salas:
        print(f'   ✗ SALAS que el radar nombró y no están en el crudo ({len(salas)}):')
        for s in sorted(salas.values()):
            print(f'      «{s}»')
    else:
        print('   ✓ toda sala nombrada por el radar existe en el crudo')
    if horas:
        print(f'   ⚠ horas del radar sin función nuestra: {", ".join(sorted(horas))}'
              f'  (puede ser de otra edición: mirar)')
    if salas:
        sys.exit(1)


if __name__ == '__main__':
    main()
