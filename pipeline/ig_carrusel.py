#!/usr/bin/env python3
"""Las láminas de un carrusel de Instagram, desde el embed público.

Un festival que publica «un post por sección» está publicando, dentro de cada
carrusel, una lámina por obra. El perfil se cierra a las ~12 publicaciones sin
sesión y la API pide login, pero el embed de un post concreto no: en su HTML
viaja un `contextJSON` con el GraphQL del media, y si el post es un carrusel
(GraphSidecar) ahí está `edge_sidecar_to_children`, con una entrada —y su
display_url en resolución original— por lámina.

Nada de esto identifica la obra: el título va PINTADO en la imagen. Quien use
este módulo tiene que leer las láminas y escribir el mapa a mano. El orden del
carrusel no es prueba de nada.

    python3 pipeline/ig_carrusel.py DcMlUyBILIO   # una línea JSON por post
"""
import json, re, sys, subprocess

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"


def _contexto(shortcode):
    # curl y no urllib: el Python del Mac no tiene el bundle de CA
    h = subprocess.run(
        ["curl", "-sSf", "--retry", "2", "--max-time", "45",
         "-A", UA, "-H", "Accept-Language: es-CO,es;q=0.9",
         f"https://www.instagram.com/p/{shortcode}/embed/captioned/"],
        capture_output=True, text=True, check=True).stdout
    i = h.find('"contextJSON"')
    if i < 0:
        # EL EMBED YA NO SIEMPRE TRAE LOS DATOS. Para algunos posts devuelve
        # una página de 600 KB sin imagen y sin pie —comprobado el 22 sep 2026
        # con el póster de «La creciente» de @eskala_films—. Antes esto
        # reventaba más abajo con un JSONDecodeError que no decía nada.
        #
        # El camino que sí funciona es el NAVEGADOR: la página renderizada
        # lleva la URL firmada del CDN. Se baja de ahí y se guarda en
        # `fuentes/`, declarando el POST como fuente —la URL del CDN caduca en
        # horas y no sirve para volver a mirarla—.
        raise SystemExit(
            f"{shortcode}: el embed ya no trae los datos ({len(h)//1024} KB sin "
            f"contextJSON). Bajarlo desde el navegador y guardarlo en fuentes/, "
            f"declarando el post como fuente.")
    # doble codificación: un string JSON cuyo contenido es a su vez JSON.
    # No sirve un regex: el string lleva comillas escapadas. Se decodifica
    # con el propio parser desde la comilla de apertura.
    j = h.index('"', h.index(':', i) + 1)
    try:
        crudo, _ = json.JSONDecoder().raw_decode(h[j:])
    except json.JSONDecodeError:
        # EL CANDADO DE ABAJO LLEGABA TARDE: comprobaba que el contenido no
        # estuviera vacío DESPUÉS de decodificarlo, y cuando el embed sirve
        # algo que no es JSON la decodificación revienta antes, con un
        # «Expecting value: line 1 column 1» que no dice nada de Instagram.
        raise SystemExit(
            f"{shortcode}: el embed trae contextJSON pero no es JSON "
            f"({len(h)//1024} KB). Bajarlo desde el NAVEGADOR —la página "
            f"renderizada lleva la URL firmada— y guardarlo en fuentes/, "
            f"declarando el post como fuente: la URL del CDN caduca en horas.")
    if not crudo.strip():
        # el embed existe pero viene sin datos: pasa cuando el post no es
        # público al mismo nivel (reel, o restringido). No es un carrusel vacío.
        raise SystemExit(f"{shortcode}: contextJSON VACÍO — leer el post en el navegador")
    try:
        return json.loads(crudo)
    except json.JSONDecodeError:
        # La doble codificación tiene DOS sitios donde romperse y el candado
        # solo cubría uno. Acá el string existe y no está vacío, pero su
        # contenido no es el JSON del post: es lo que devuelve el embed cuando
        # Instagram ya no lo sirve (comprobado el 22 sep 2026 con el póster de
        # «La creciente» de @eskala_films, 636 KB sin imagen ni pie).
        raise SystemExit(
            f"{shortcode}: el embed trae contextJSON pero su contenido no es "
            f"el post. Bajarlo desde el NAVEGADOR —la página renderizada lleva "
            f"la URL firmada del CDN— y guardarlo en fuentes/, declarando el "
            f"POST como fuente: la URL del CDN caduca en horas.")


def laminas(shortcode):
    ctx = _contexto(shortcode)
    media = ctx.get("gql_data", {}).get("shortcode_media") or ctx.get("shortcode_media")
    if not media:
        raise SystemExit(f"{shortcode}: contextJSON sin shortcode_media")
    hijos = media.get("edge_sidecar_to_children", {}).get("edges")
    nodos = [e["node"] for e in hijos] if hijos else [media]
    cap = ""
    ce = media.get("edge_media_to_caption", {}).get("edges") or []
    if ce:
        cap = ce[0]["node"]["text"]
    return {
        "shortcode": shortcode,
        "tipo": media.get("__typename"),
        "caption": cap,
        "laminas": [{
            "i": i,
            "video": bool(n.get("is_video")),
            "url": n.get("display_url"),
            "alt": (n.get("accessibility_caption") or "")[:200],
        } for i, n in enumerate(nodos, 1)],
    }


if __name__ == "__main__":
    for sc in sys.argv[1:]:
        d = laminas(sc)
        print(json.dumps(d, ensure_ascii=False))
