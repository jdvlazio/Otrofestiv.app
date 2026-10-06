#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""ig_sin_sesion.py <shortcode>... — leer posts de Instagram SIN la cuenta de Juan.

POR QUÉ EXISTE (6 oct 2026, issue #1016). El radar leía Instagram en el
navegador CON la sesión de Juan: ~6 perfiles y sus posts cada día. El 3 oct,
en el quinto perfil, Instagram pidió una verificación de seguridad de la
cuenta y la frenó tres días. Regla dura desde entonces: NUNCA se lee Instagram
con la cuenta de Juan, ni en el navegador integrado ni en Chrome.

CÓMO SE LEE AHORA, en dos pasos que no tocan ninguna cuenta:
  1. QUÉ HAY DE NUEVO: el perfil, abierto en un navegador SIN sesión (debe
     verse el botón «Log in»; si no se ve, NO se lee), enseña los ~12 posts más
     recientes. Una carga por perfil para sacar sus shortcodes; nada más.
  2. QUÉ DICE CADA POST: este script, por el EMBED público
     (/p/<sc>/embed/captioned/), sin navegador y sin cuenta: el pie (cortado a
     ~2170 caracteres sin sesión), la fecha y cuántas láminas tiene. Las
     láminas mismas las baja ig.py (bajar_laminas), también por el embed.

LO QUE CUIDA:
  · CACHÉ por post en fuentes/ig/<sc>/post.json: un post ya leído no se vuelve
    a pedir nunca (el pie de un post publicado casi no cambia; si hiciera
    falta, --refrescar).
  · PAUSA entre posts, y TOPE de posts por corrida.
  · FRENO al primer aviso: una respuesta que pide login, verificación o «espera
    unos minutos», o un HTTP 429, detiene TODA la lectura de la corrida con
    salida 3. No se reintenta: se anota y se sigue otro día. Un bloqueo así
    cae sobre la IP y por minutos, no sobre una cuenta.

Lo que sin sesión NO se puede: historias, destacados, cuentas privadas. Eso es
un vistazo manual de Juan, nunca su sesión.

    python3 pipeline/ig_sin_sesion.py DeH5TQzFeHV DeDWJs0Dmdw     # una línea JSON por post
"""
import html
import json
import os
import re
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = f'{REPO}/fuentes/ig'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 '
      '(KHTML, like Gecko) Version/17.0 Safari/605.1.15')
PAUSA_S = 3
TOPE_POSTS = 30
# lo que Instagram responde cuando frena: login, verificación, espera
FRENO = re.compile(r'require_login|Please wait a few minutes|accounts/login|challenge|'
                   r'checkpoint|update_risky_contactpoint|Try again later', re.I)


class Bloqueo(Exception):
    pass


def _bajar(sc):
    r = subprocess.run(['curl', '-sS', '--max-time', '40', '-A', UA, '-H', 'Accept-Language: es-CO,es;q=0.9',
                        '-w', '\n%{http_code}', f'https://www.instagram.com/p/{sc}/embed/captioned/'],
                       capture_output=True, text=True)
    cuerpo, _, codigo = (r.stdout or '').rpartition('\n')
    if codigo == '429' or (codigo != '200' and FRENO.search(cuerpo or '')):
        raise Bloqueo(f'{sc}: HTTP {codigo}')
    # un embed normal trae el post; uno que redirige a login o pide verificar, no
    if 'Caption' not in cuerpo and 'contextJSON' not in cuerpo and FRENO.search(cuerpo):
        raise Bloqueo(f'{sc}: el embed pide login o verificación')
    return codigo, cuerpo


def _media(h):
    """El post dentro del contextJSON del embed (doble codificación, ver
    ig_carrusel.py), o None si el embed no lo trae."""
    i = h.find('"contextJSON"')
    if i < 0:
        return None
    try:
        j = h.index('"', h.index(':', i) + 1)
        crudo, _ = json.JSONDecoder().raw_decode(h[j:])
        ctx = json.loads(crudo) if crudo.strip() else {}
    except (ValueError, json.JSONDecodeError):
        return None
    return ctx.get('gql_data', {}).get('shortcode_media') or ctx.get('shortcode_media')


def leer(sc, refrescar=False):
    """{shortcode, cuenta, fecha, pie, laminas} — de la caché o del embed."""
    p = f'{CACHE}/{sc}/post.json'
    if os.path.exists(p) and not refrescar:
        return json.load(open(p, encoding='utf-8'))
    codigo, h = _bajar(sc)
    media = _media(h)
    pie, cuenta, fecha, n_lam = '', None, None, 0
    if media:
        # el contextJSON del embed: pie entero (hasta donde lo da sin sesión),
        # cuenta, fecha y una entrada por lámina
        ce = media.get('edge_media_to_caption', {}).get('edges') or []
        pie = ce[0]['node']['text'] if ce else ''
        cuenta = (media.get('owner') or {}).get('username')
        # EL EMBED NO TRAE LA FECHA, pero el id del post la lleva adentro: los
        # 41 bits altos son milisegundos desde la época de Instagram (24 ago
        # 2011). Comprobado el 6 oct 2026 contra fechas conocidas (programación
        # de FILCMAR, 1 oct en la noche; carrusel v3 de Mamut, 29 sep). Hora de
        # Colombia, que es la de nuestros festivales.
        ts = media.get('taken_at_timestamp')
        if not ts and media.get('id'):
            ts = ((int(str(media['id']).split('_')[0]) >> 23) + 1314220021721) / 1000
        fecha = time.strftime('%Y-%m-%d %H:%M', time.gmtime(int(ts) - 5 * 3600)) if ts else None
        hijos = (media.get('edge_sidecar_to_children') or {}).get('edges')
        n_lam = len(hijos) if hijos else 1
    else:
        # sin contextJSON queda el pie del HTML (empieza por el usuario)
        m = re.search(r'class="Caption"[^>]*>(.*?)</div>', h, re.S)
        if m:
            pie = html.unescape(re.sub(r'<br\s*/?>', '\n', m.group(1)))
            pie = re.sub(r'<[^>]+>', '', pie).strip()
            pie = re.sub(r'View all \d* ?comments?$', '', pie).strip()
        cuenta = (re.search(r'class="UsernameText"[^>]*>([^<]+)<', h) or [None, None])[1]
    out = {'shortcode': sc, 'cuenta': cuenta, 'http': codigo, 'fecha': fecha,
           'pie': pie, 'laminas': n_lam,
           'leido': time.strftime('%Y-%m-%dT%H:%M:%S'), 'via': 'embed público, sin sesión'}
    if codigo == '200' and (pie or n_lam):
        os.makedirs(os.path.dirname(p), exist_ok=True)
        json.dump(out, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    refrescar = '--refrescar' in sys.argv
    if len(args) > TOPE_POSTS:
        sys.exit(f'✗ {len(args)} posts: el tope por corrida es {TOPE_POSTS}')
    pedidos = 0
    for sc in args:
        cacheado = os.path.exists(f'{CACHE}/{sc}/post.json') and not refrescar
        try:
            if pedidos and not cacheado:
                time.sleep(PAUSA_S)
            r = leer(sc, refrescar)
            pedidos += 0 if cacheado else 1
            print(json.dumps({**r, 'cache': cacheado}, ensure_ascii=False))
        except Bloqueo as e:
            print(f'✗ FRENO de Instagram — se detiene toda la lectura de esta corrida: {e}', file=sys.stderr)
            sys.exit(3)


if __name__ == '__main__':
    main()
