# -*- coding: utf-8 -*-
"""Relee las fichas de charlas y talleres para sacar DURACIÓN e INSCRIPCIÓN.

Las fichas de /charlas/<slug> y /talleres/<slug> publican un bloque de campos
—Ciudad, Ubicación, Fecha, Hora, Modalidad, Inscripción— que el primer barrido
no aprovechó: solo miró si existía un formulario de inscripción.

Lo que aporta:
  · «Hora : 09:00 a.m. - 12:00 M.» → duración REAL de la actividad. Sin esto,
    el dominio aplica 90 min por defecto y el plan encaja cosas imposibles
    detrás de un taller de tres horas.
  · «Inscripción : Formulario de inscripción» → requires_registration, ahora
    leído del campo y no de la presencia de un botón.

Los slugs salen de los índices /talleres y /charlas, no se adivinan.
"""
import json, os, re, html, subprocess, time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f'{REPO}/festivals/staging/ficdeh-2026-actividades-detalle.json'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')


def get(url):
    for _ in range(3):
        r = subprocess.run(['curl', '-sL', '--compressed', '--max-time', '35', '-A', UA, url],
                           capture_output=True)
        if r.returncode == 0 and len(r.stdout) > 3000:
            return r.stdout.decode('utf-8', 'ignore')
        time.sleep(1.2)
    return ''


def texto(h):
    h = re.sub(r'<script[^>]*>.*?</script>|<style[^>]*>.*?</style>', '', h, flags=re.S)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', h))).strip()


def minutos(h):
    m = re.match(r'(\d{1,2}):(\d{2})\s*([apm])', h.strip(), re.I)
    if not m:
        return None
    hh, mm, ap = int(m.group(1)), int(m.group(2)), m.group(3).lower()
    if ap == 'p' and hh != 12:
        hh += 12
    if ap == 'm' and hh == 12:      # «12:00 M.» = mediodía
        pass
    if ap == 'a' and hh == 12:
        hh = 0
    return hh * 60 + mm


def campo(t, nombre):
    m = re.search(rf'{nombre}\s*:\s*(.+?)(?=\s+(?:Ciudad|Ubicaci[óo]n|Fecha|Hora|Modalidad|Inscripci[óo]n|A[ñn]o|Panelistas|Talleristas?|M[áa]s )\s*:?|$)', t)
    return m.group(1).strip() if m else ''


def main():
    slugs = {}
    for seccion in ('talleres', 'charlas'):
        idx = get(f'https://www.ficdeh.com/{seccion}')
        for s in set(re.findall(rf'/{seccion}/([a-z0-9\-]+)', idx)):
            slugs[s] = seccion

    out = {}
    for i, (s, seccion) in enumerate(sorted(slugs.items()), 1):
        t = texto(get(f'https://www.ficdeh.com/{seccion}/{s}'))
        hora = campo(t, 'Hora')
        ini = fin = None
        r = re.match(r'(\d{1,2}:\d{2}\s*[apm]\.?\s*m?\.?)\s*[-–]\s*(\d{1,2}:\d{2}\s*[apmM]\.?\s*m?\.?)', hora, re.I)
        if r:
            ini, fin = minutos(r.group(1)), minutos(r.group(2))
        dur = (fin - ini) if (ini is not None and fin is not None and fin > ini) else None
        titulo = ''
        mt = re.search(r'FICDEH 2026 (.+?) (?:Selecci[óo]n oficial|Toda la)', t)
        out[s] = {'seccion': seccion, 'titulo_slug': s,
                  'hora': hora, 'duracion_min': dur,
                  'inscripcion': campo(t, 'Inscripci[óo]n'),
                  'requires_registration': bool(campo(t, 'Inscripci[óo]n')),
                  'ciudad': campo(t, 'Ciudad'), 'ubicacion': campo(t, 'Ubicaci[óo]n'),
                  'fecha': campo(t, 'Fecha'), 'modalidad': campo(t, 'Modalidad')}
        print(f'[{i:2}/{len(slugs)}] {seccion:9} {s[:44]:45} hora=«{hora[:26]:27}» dur={dur} insc={out[s]["requires_registration"]}', flush=True)
        time.sleep(0.25)

    json.dump({'_provenance': {
        'fuente': 'https://www.ficdeh.com/{talleres|charlas}/<slug> — bloque de campos de la ficha',
        'capturado': '2026-08-06',
        'que_aporta': 'DURACIÓN real (del rango «Hora : 9:00 a.m. - 12:00 M.») e INSCRIPCIÓN '
                      'leída del campo, no de la presencia de un botón.',
    }, 'actividades': out}, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    con = sum(1 for v in out.values() if v['duracion_min'])
    print(f'\n{len(out)} fichas · con duración real: {con} · con inscripción: {sum(1 for v in out.values() if v["requires_registration"])}')


if __name__ == '__main__':
    main()
