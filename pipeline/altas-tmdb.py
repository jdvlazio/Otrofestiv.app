# -*- coding: utf-8 -*-
"""altas-tmdb.py <fest-id> [salida.html] — la COLA de altas en TMDB de un festival,
lista para hacerse desde el celular.

POR QUÉ (24 sep 2026). Dar de alta «La creciente» desde el celular, en Jardín,
llevó diez minutos de teclear en un formulario que no está hecho para eso, con
todos los datos ya en nuestro JSON. TMDB no deja crear obras por API: el alta
es por su web y con sesión. Lo que sí se puede es no teclear nada: cada campo
con su botón de copiar, el afiche a un toque y el formulario enlazado.

No reimplementa nada:
  · las TRES sondas son las de pipeline/verificar-antes-de-alta.py (título,
    filmografía del director, Letterboxd) — se corre tal cual;
  · el veredicto del afiche es el de scripts/tmdb-gaps.py (≥500 px y
    proporción 0.66–0.71), el mismo que ya bloquea altas con afiche chico.

Lee   festivals/<id>.json  (lo PUBLICADO: es lo que la gente ve sin botón de LB)
Esc.  festivals/staging/<id>-altas.json   (la cola, con estado y motivo)
      <salida.html> (por defecto festivals/staging/<id>-altas.html) — la página

Estados: ALTA-OK (las tres sondas fallan y el afiche sirve) · BLOQUEADA (no
existe pero el afiche no pasa: se crearía una ficha huérfana) · REVISAR (una
sonda encontró algo parecido: lo decide una persona) · EXISTE (ya hay ficha;
falta enlazarla, no crearla).

Después del alta: declarar el id en festivals/staging/<id>-correcciones.json
(«fichas») y correr el enriquecimiento — la API tarda horas en ver una ficha nueva.
"""
import html, importlib.util, json, os, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROD = 'https://otrofestiv.app'


def _gaps():
    spec = importlib.util.spec_from_file_location('tmdb_gaps', f'{REPO}/scripts/tmdb-gaps.py')
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def _obras(d):
    """Cada obra una vez, con la PRIMERA función en que se proyecta (su estreno
    en el festival) — de ahí sale la fecha que pide TMDB."""
    out = {}
    for f in sorted(d['films'], key=lambda x: (x.get('day', ''), x.get('time', ''))):
        if f.get('type') == 'event':
            continue
        for o in (f['film_list'] if f.get('film_list') else [f]):
            if o.get('title') and o.get('director'):
                out.setdefault(o['title'], {**o, '_dia': f.get('day', '')})
    return out


def _minutos(dur):
    try: return int(str(dur).split()[0])
    except (ValueError, IndexError): return ''


def main():
    if len(sys.argv) < 2:
        sys.exit('uso: TMDB_API_KEY=… python3 pipeline/altas-tmdb.py <fest-id> [salida.html]')
    fid = sys.argv[1]
    pub = f'{REPO}/festivals/{fid}.json'
    cola_p = f'{REPO}/festivals/staging/{fid}-altas.json'
    html_p = sys.argv[2] if len(sys.argv) > 2 else f'{REPO}/festivals/staging/{fid}-altas.html'
    d = json.load(open(pub, encoding='utf-8'))
    cfg_nombre = d.get('name') or d.get('festival', {}).get('name') or fid

    # 1 · las tres sondas, por el verificador de siempre
    sondas_p = f'{REPO}/festivals/staging/{fid}-altas-sondas.json'
    r = subprocess.run([sys.executable, f'{REPO}/pipeline/verificar-antes-de-alta.py', pub, sondas_p])
    if r.returncode:
        sys.exit('✗ falló la verificación de tres sondas')
    sondas = {s['title']: s for s in json.load(open(sondas_p, encoding='utf-8'))}

    # 2 · afiche, con el veredicto de tmdb-gaps
    g = _gaps()
    obras = _obras(d)
    cola = []
    for t, s in sondas.items():
        o = obras.get(t, {})
        apto, etiqueta = g._poster_status(o.get('poster'), REPO)
        estado = s['estado']
        if estado == 'ALTA-OK' and not apto:
            estado = 'BLOQUEADA'
        cola.append({
            'titulo': t, 'estado': estado,
            'motivo': {'ALTA-OK': 'no existe en TMDB ni en Letterboxd; afiche apto',
                       'BLOQUEADA': 'no existe, pero el afiche no pasa: ' + etiqueta,
                       'REVISAR': 'una sonda encontró algo parecido — míralo antes',
                       'EXISTE': 'ya tiene ficha: falta enlazarla, no crearla'}[estado],
            'afiche': etiqueta,
            'campos': {
                'titulo_original': t,
                'titulo_en': o.get('title_en') or '',
                'director': o.get('director', ''),
                'anio': o.get('year', ''),
                'duracion_min': _minutos(o.get('duration')),
                'pais': o.get('country', ''),
                'idioma': o.get('language', ''),
                'genero': o.get('genre', ''),
                'sinopsis_es': o.get('synopsis', ''),
                'sinopsis_en': o.get('synopsis_en', ''),
                'estreno': f"{o.get('_dia', '')} · {cfg_nombre}",
                'afiche_url': (PROD + o['poster']) if str(o.get('poster', '')).startswith('/') else o.get('poster', ''),
            },
            'tmdb': s.get('tmdb'), 'persona': s.get('persona'), 'lb': s.get('lb'),
        })
    orden = {'ALTA-OK': 0, 'REVISAR': 1, 'BLOQUEADA': 2, 'EXISTE': 3}
    cola.sort(key=lambda c: (orden[c['estado']], c['titulo']))
    json.dump(cola, open(cola_p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    open(html_p, 'w', encoding='utf-8').write(pagina(fid, cfg_nombre, cola))
    from collections import Counter
    print('\nCOLA:', dict(Counter(c['estado'] for c in cola)))
    print('->', cola_p); print('->', html_p)


# ── la página ──────────────────────────────────────────────────────────────────
_CAMPOS = [('titulo_original', 'Título original'), ('titulo_en', 'Título en inglés'),
           ('director', 'Dirección'), ('anio', 'Año'), ('duracion_min', 'Duración (min)'),
           ('pais', 'País'), ('idioma', 'Idioma original'), ('genero', 'Género'),
           ('sinopsis_es', 'Sinopsis (español)'), ('sinopsis_en', 'Sinopsis (inglés)'),
           ('estreno', 'Estreno')]


def _tarjeta(c):
    e = html.escape
    filas = ''.join(
        f'<div class="f"><div class="k">{e(lbl)}</div><div class="v">{e(str(c["campos"][k]))}</div>'
        f'<button class="cp" data-v="{e(str(c["campos"][k]), quote=True)}">Copiar</button></div>'
        for k, lbl in _CAMPOS if c['campos'].get(k))
    extra = ''
    if c['estado'] == 'REVISAR':
        extra = f'<pre class="pista">{e(json.dumps({"persona": c["persona"], "letterboxd": c["lb"]}, ensure_ascii=False, indent=1))}</pre>'
    if c['estado'] == 'EXISTE' and c.get('tmdb'):
        extra = f'<a class="lnk" href="https://www.themoviedb.org/movie/{c["tmdb"]["id"]}">Ver ficha existente ↗</a>'
    af = c['campos']['afiche_url']
    return f'''<details class="obra {c["estado"].lower()}"{" open" if c["estado"] == "ALTA-OK" else ""}>
<summary><span class="est">{e(c["estado"])}</span> <b>{e(c["titulo"])}</b><span class="mot">{e(c["motivo"])}</span></summary>
<div class="body">
{f'<a class="af" href="{e(af)}" download><img src="{e(af)}" alt=""><span>Abrir afiche · {e(c["afiche"])}</span></a>' if af else ''}
{filas}{extra}
{'<a class="go" href="https://www.themoviedb.org/movie/new" target="_blank">Abrir formulario de TMDB ↗</a>' if c["estado"] == "ALTA-OK" else ''}
</div></details>'''


def pagina(fid, nombre, cola):
    e = html.escape
    n = sum(1 for c in cola if c['estado'] == 'ALTA-OK')
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Altas TMDB {e(fid)}</title>
<style>
:root{{--bg:#0B0A08;--surf:#1B1917;--card:#24211E;--white:#F0EDE8;--gray:rgba(240,237,232,.6);--amber:#F59E0B;--green:#3AAA6E;--red:#E5534B;--bdr:rgba(240,237,232,.12)}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--white);font:15px/1.45 "Plus Jakarta Sans",-apple-system,sans-serif;padding:16px;max-width:680px;margin:auto}}
h1{{font-size:20px;margin:4px 0}} .sub{{color:var(--gray);font-size:13px;margin-bottom:16px}}
.pasos{{background:var(--surf);border-radius:12px;padding:12px 14px;font-size:13px;color:var(--gray);margin-bottom:16px}} .pasos b{{color:var(--white)}}
details.obra{{background:var(--surf);border:1px solid var(--bdr);border-radius:12px;margin-bottom:10px;overflow:hidden}}
summary{{padding:12px 14px;cursor:pointer;list-style:none}} summary::-webkit-details-marker{{display:none}}
.est{{font-size:10px;font-weight:800;letter-spacing:.08em;padding:2px 7px;border-radius:999px;background:var(--card)}}
.alta-ok .est{{background:var(--amber);color:#000}} .bloqueada .est{{color:var(--red)}} .existe .est{{color:var(--green)}}
.mot{{display:block;font-size:12px;color:var(--gray);margin-top:3px}}
.body{{padding:0 14px 14px}}
.af{{display:flex;gap:10px;align-items:center;color:var(--gray);font-size:12px;text-decoration:none;margin-bottom:10px}} .af img{{width:64px;border-radius:6px}}
.f{{display:grid;grid-template-columns:1fr auto;gap:2px 10px;padding:8px 0;border-top:1px solid var(--bdr)}}
.k{{grid-column:1;font-size:11px;color:var(--gray);text-transform:uppercase;letter-spacing:.06em}}
.v{{grid-column:1;font-size:14px;word-break:break-word}}
.cp{{grid-column:2;grid-row:1/3;align-self:center;background:var(--card);color:var(--white);border:1px solid var(--bdr);border-radius:999px;padding:8px 14px;font:600 13px inherit;min-height:40px}}
.cp.ok{{background:var(--green);color:#000}}
.go{{display:block;text-align:center;background:var(--amber);color:#000;font-weight:800;border-radius:999px;padding:12px;margin-top:12px;text-decoration:none}}
.lnk{{color:var(--amber)}} .pista{{font-size:11px;color:var(--gray);white-space:pre-wrap;background:var(--card);padding:8px;border-radius:8px}}
</style></head><body>
<h1>Altas en TMDB · {e(nombre)}</h1>
<div class="sub">{n} para crear · cada una verificada por título, por filmografía del director y en Letterboxd, con el afiche medido.</div>
<div class="pasos"><b>Por obra:</b> abre el formulario → pega título y sinopsis → en Verificación marca «I have reviewed» → duración → Guardar. Después, en <b>Editar</b>: idioma y país, fecha de estreno, Dirección («Crear» si es persona nueva), género y afiche. <b>Al terminar, mándale el enlace a Claude</b> y la obra se conecta en la app.</div>
{''.join(_tarjeta(c) for c in cola)}
<script>
document.addEventListener('click',async ev=>{{const b=ev.target.closest('.cp');if(!b)return;
try{{await navigator.clipboard.writeText(b.dataset.v);}}catch(e){{const t=document.createElement('textarea');t.value=b.dataset.v;document.body.appendChild(t);t.select();document.execCommand('copy');t.remove();}}
b.textContent='Copiado';b.classList.add('ok');setTimeout(()=>{{b.textContent='Copiar';b.classList.remove('ok')}},1400);}});
</script></body></html>'''


if __name__ == '__main__':
    main()
