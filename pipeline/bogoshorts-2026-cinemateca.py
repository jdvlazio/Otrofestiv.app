#!/usr/bin/env python3
"""bogoshorts-2026-cinemateca.py — la boletería de la Cinemateca de Bogotá → sidecar.

LA FUENTE: el enlace «Boletería 24° BOGOSHORTS Cinemateca de Bogotá» del post de
@bogoshorts DfsqgASTGnw (14 nov 2026) → bit.ly/Cinemateca_24BSFF → la agenda de la
sede 11 del 30 nov al 9 dic. Cada obra de la agenda tiene su página
(/node/peliculas/<n>?sede=11) con una fila por función: fecha, hora, sala y su
enlace de TuBoleta. La sala manda en sala, hora y boletería (es la que vende).

Escribe festivals/staging/bogoshorts-2026-cinemateca.json:
  {"funciones": [{"dia","hora","sala","titulo_sala","ticket_url","pagina"}]}
que lee bogoshorts-2026-crudo.py. Re-bajar con --bajar (guarda en fuentes/).
"""
import html, json, os, re, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = f'{REPO}/fuentes/bogoshorts-2026/cinemateca'
OUT = f'{REPO}/festivals/staging/bogoshorts-2026-cinemateca.json'
BASE = 'https://cinematecadebogota.gov.co'
AGENDA = (BASE + '/agenda/11?field_date_interval_value%5Bmin%5D%5Bdate%5D=2026-11-30'
          '&field_date_interval_value%5Bmax%5D%5Bdate%5D=2026-12-09')
MESES = {'Noviembre': 11, 'Diciembre': 12}


def bajar(url, ruta):
    subprocess.run(['curl', '-sfL', '--max-time', '60', '-o', ruta, url], check=True)


def main():
    os.makedirs(F, exist_ok=True)
    ag = f'{F}/agenda.html'
    if '--bajar' in sys.argv or not os.path.exists(ag):
        bajar(AGENDA, ag)
    s = open(ag, encoding='utf-8').read()
    nodos = {}
    for n, t in re.findall(r'<a href="/node/peliculas/(\d+)\?sede=11">([^<]*\|[^<]*)</a>', s):
        nodos[n] = html.unescape(t).strip()
    out = []
    for n, titulo in sorted(nodos.items()):
        p = f'{F}/pelicula-{n}.html'
        if '--bajar' in sys.argv or not os.path.exists(p):
            bajar(f'{BASE}/node/peliculas/{n}?sede=11', p)
        t = open(p, encoding='utf-8').read()
        vistos = set()
        for m in re.finditer(r'(Noviembre|Diciembre) (\d\d) (\d{1,2}):(\d\d) (AM|PM)(.*?)href="(https://cinemateca\.checkout\.tuboleta\.com/[^"]+)"', t, re.S):
            sala = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', m[6]))).replace('#FFFFFF', '').split(' <')[0].strip()
            h = int(m[3]) % 12 + (12 if m[5] == 'PM' else 0)
            f = {'dia': f'2026-{MESES[m[1]]:02d}-{m[2]}', 'hora': f'{h:02d}:{m[4]}', 'sala': sala,
                 'titulo_sala': titulo, 'ticket_url': html.unescape(m[7]),
                 'pagina': f'{BASE}/node/peliculas/{n}?sede=11'}
            k = (f['dia'], f['hora'], f['sala'])
            if k not in vistos:
                vistos.add(k)
                out.append(f)
    json.dump({'_provenance': {'fuente': AGENDA, 'via': 'https://www.instagram.com/p/DfsqgASTGnw/',
                               'capturado': '2026-11-15'}, 'funciones': out},
              open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'✓ {len(out)} funciones con TuBoleta de {len(nodos)} páginas → {OUT}')


if __name__ == '__main__':
    main()
