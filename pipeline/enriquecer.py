# -*- coding: utf-8 -*-
"""enriquecer.py <fest-id> [--posters] — la ficha de cada obra, VERIFICADA.

Herramienta genérica sobre el formato intermedio. En FICMA esto fueron cuatro
scripts (tmdb, repesca, title-en, letterboxd); aquí es una pasada por obra:

  1. TMDB por título, aceptando SOLO lo que pasa ficha_verifica() — director ✓
     y (año ±1 o duración ±3 min). La lección Tribeca: sin match no se adivina.
  2. Del id verificado: póster, sinopsis ES y EN, género, y title_en cuando el
     título en en-US difiere del nuestro (si son iguales, el campo duplicaría).
  3. lbSlug por el atajo letterboxd.com/tmdb/<id> — el slug lo da Letterboxd
     desde su propio mapeo, nunca lo inferimos de un título (homónimos).

Lee   festivals/staging/<id>-crudo.json          (formato intermedio, lib.cargar_crudo)
Opc.  festivals/staging/<id>-correcciones.json   {"titulo_oficial":{}, "alias":{}}
        · titulo_oficial: el OCR o el programa escriben mal el título; se
          corrige contra el afiche («AA95» → «AA965»). El título CORREGIDO es
          el que se busca y el que sale en el reporte.
        · alias: el festival rebautizó la obra; se BUSCA por el nombre de
          distribución («Nina y los cuentos del Erizo» → «Nina et le secret du
          hérisson») pero el título del festival se conserva.
Esc.  festivals/staging/<id>-enriquecido.json
      assets/<id>/<slug>.jpg                     (con --posters, w780)

Requiere TMDB_API_KEY en el entorno.
"""
import datetime
import json, os, re, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import (asset_declarado, sin_tmdb_si_se_pide, cargar_crudo, ficha_verifica, norm, provenance, slug,
                 tmdb_get, tmdb_ficha, UA, ficha_tmdb, director_coincide, ya_publicada,
                 obras_publicadas)
import catalogo  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'



def es_programa(f):
    """¿La función es un programa de 2+ obras? (`obras` o `film_list`, los dos
    nombres que acepta el ensamblador). Con UNA obra la función ES esa obra."""
    return len([o for o in (f.get('obras') or f.get('film_list') or []) if o.get('titulo') or o.get('title')]) >= 2

def obras_a_buscar(funciones, tit_of, _para_verificar=lambda x: x):
    """Las obras que se buscan en TMDB: cada función que ES una obra y cada obra
    de dentro de un programa. Un programa de 2+ obras no se busca (es_programa)."""
    obras = {}
    for f in funciones:
        if not f.get('en_app', True):
            continue
        # UN PROGRAMA DE 2+ OBRAS NO ES UNA OBRA (20 oct 2026, BHFF): su título
        # («El Susurro + Esquirlas de Caracol») no es una película, y buscarlo en
        # TMDB le encontraba la ficha de UNA de ellas, que el ensamblador pegaba
        # al programa entero (lbSlug, año, género, descripción). Lo que se busca
        # son sus obras, de a una, aquí abajo.
        if f.get('tipo', 'film') in ('film', '') and not es_programa(f):
            t = tit_of.get(f['titulo'], f['titulo'])
            obras.setdefault(t, _para_verificar({**f, 'titulo': t}))
        # `film_list` es el otro nombre de `obras`: el ensamblador acepta los
        # dos desde siempre y este paso solo miraba uno. En Villa del Cine eso
        # dejó 104 cortos sin enriquecer y el reporte decía «1 obra» tan
        # tranquilo — el mismo fallo mudo de antes, por la otra puerta. Si dos
        # pasos leen la misma lista, tienen que aceptar los mismos nombres.
        for o in f.get('obras') or f.get('film_list') or []:
            if not o.get('titulo'):
                continue
            t = tit_of.get(o['titulo'], o['titulo'])
            # la obra hereda el día de su función solo para el reporte; lo que
            # verifica es su propia ficha (director, año, duración)
            obras.setdefault(t, _para_verificar({**o, 'titulo': t}))
    return obras


def variantes(titulo, alias):
    """Formas de buscar el mismo título: alias del festival, el entrecomillado
    interno («La Sirena (The Siren)» → ambos lados), y el título entero."""
    v = []
    if titulo in alias:
        v.append(alias[titulo])
    v.append(titulo)
    m = re.match(r'^(.+?)\s*\((.+)\)\s*$', titulo)
    if m:
        v += [m.group(2).strip(), m.group(1).strip()]
    return list(dict.fromkeys(v))


def lb_slug(tmdb_id):
    """302 de letterboxd.com/tmdb/<id> → slug. '' si no hay mapeo (y ese es el
    estado honesto: la UI oculta el botón; nunca se cuelga un homónimo)."""
    r = subprocess.run(['curl', '-s', '-o', '/dev/null', '-w', '%{redirect_url}',
                        '--max-time', '25', '-A', UA,
                        f'https://letterboxd.com/tmdb/{tmdb_id}/'], capture_output=True)
    m = re.match(r'https://letterboxd\.com/film/([^/]+)/?$', r.stdout.decode().strip())
    return m.group(1) if m else ''


def enriquecer_obra(f, key, alias):
    """→ dict verificado o None. `f` es una función del formato intermedio."""
    # EL TÍTULO ORIGINAL TAMBIÉN SE BUSCA (23 sep 2026). Un festival que
    # programa cine internacional lo rotula en su idioma y publica el original
    # al lado: Itagüí imprime «Tumbas al ras de la tierra / Título original:
    # Shallow Grave». Buscar solo por el título del festival dejaba a Danny
    # Boyle «sin ficha verificable» teniendo la llave impresa en la misma
    # lámina — y con él «Ciudad de los hombres», «Cine, aspirinas y buitres» y
    # «El año en que mis padres salieron de vacaciones».
    #
    # Va DESPUÉS del título del festival, no antes: el original es el plan B.
    # Y no relaja nada — lo que encuentre sigue pasando por ficha_verifica().
    consultas = list(variantes(f['titulo'], alias))
    # Y EL INGLÉS, de plan C (26 sep 2026). Fantasmagoría nombra dos cortos
    # animados en español en su catálogo y en inglés en su noticia
    # —«Bestias de la Muerte» / «Beasts of Death»—, y la ficha de TMDB de
    # un corto reciente suele estar solo con el de su país. Mismo candado.
    for extra in (f.get('titulo_original'), f.get('titulo_en')):
        extra = (extra or '').strip()
        if extra and norm(extra) != norm(f['titulo']):
            for q in variantes(extra, alias):
                if q not in consultas:
                    consultas.append(q)
    for q in consultas:
        for lang in ('es-ES', 'en-US'):
            res = tmdb_get('/search/movie', key, query=q, language=lang,
                           include_adult='false')
            for c in (res.get('results') or [])[:6]:
                det, out = ficha_de_tmdb(c['id'], key, f['titulo'])
                if not ficha_verifica(f, det):
                    continue
                out['_verificado'] = 'director✓ + año/duración'
                out['_busqueda'] = q
                return out
    return None


def ficha_de_tmdb(cid, key, titulo):
    """(ficha TMDB cruda, campos extraídos). DUEÑO ÚNICO de qué se saca de una
    ficha: lo llaman la búsqueda automática y la declaración a mano, que
    difieren solo en quién responde por el emparejamiento."""
    # por id: vacía por la red ya no se arma (lib.tmdb_ficha, 14 oct 2026)
    det = tmdb_ficha(cid, key, language='es-ES', append_to_response='credits')
    det_en = tmdb_ficha(cid, key, language='en-US', append_to_response='credits')
    # créditos de ambos idiomas: los en-US vienen romanizados
    # (宮崎吾朗 → «Goro Miyazaki») y sin ellos el director nunca casa
    det.setdefault('credits', {}).setdefault('crew', []).extend(
        det_en.get('credits', {}).get('crew', []))
    en = det_en.get('title') or ''
    # LA SINOPSIS QUE NO ESTÁ EN `es-ES` NI EN `en-US`. TMDB registra algunas
    # traducciones bajo el idioma pelado —`es`— y entonces las dos consultas
    # con región vuelven VACÍAS aunque el texto exista: «The Nation» (1714254)
    # tiene su sinopsis en `es` y salía sin una sola línea. Es la misma trampa
    # que el guárdian [cosecha-tmdb] describe para `es-CO`, por la otra puerta.
    # Solo se pregunta cuando las dos vinieron vacías: una llamada más, y solo
    # donde si no publicaríamos nada.
    _sin_es = not (det.get('overview') or '').strip()
    _sin_en = not (det_en.get('overview') or '').strip()
    _tr_es = _tr_en = ''
    if _sin_es and _sin_en:
        _tr = tmdb_get(f'/movie/{cid}/translations', key) or {}
        for _t in _tr.get('translations') or []:
            _o = ((_t.get('data') or {}).get('overview') or '').strip()
            if not _o:
                continue
            if _t.get('iso_639_1') == 'es' and not _tr_es:
                _tr_es = _o
            elif _t.get('iso_639_1') == 'en' and not _tr_en:
                _tr_en = _o
    # UN TÍTULO NO ES UNA SINOPSIS. TMDB guarda a veces el título traducido
    # como «overview»: «Born to Be Seed» (Nascemos para semente, Popayán) y
    # «When the waters meet» (Cuando las aguas se juntan, Jardín), sin que ese
    # texto figure como título en ningún campo de la ficha. Se descarta el
    # overview igual a un título, y el de cinco palabras o menos SIN punto
    # final: eso es un rótulo, no una frase.
    _titulos = {norm(x) for x in (det.get('title'), det.get('original_title'),
                                      det_en.get('title')) if x}

    def _sinopsis(txt):
        t = (txt or '').strip()
        if norm(t) in _titulos or (t and len(t.split()) <= 5 and t[-1] not in '.!?…»"'):
            return ''
        return t
    out = {'tmdb_id': cid,
           'titulo_original': det.get('original_title'),
           'poster_path': det.get('poster_path'),
           'synopsis_es': _sinopsis(det.get('overview')) or _sinopsis(_tr_es),
           'synopsis_en': _sinopsis(det_en.get('overview')) or _sinopsis(_tr_en),
           'genero': (det.get('genres') or [{}])[0].get('name', ''),
           'anio_tmdb': int((det.get('release_date') or '0')[:4] or 0),
           'duracion_tmdb': det.get('runtime') or 0,
           # EL PAÍS, que TMDB da y no guardábamos. En Villa del Cine faltaba
           # en 21 obras y para varias era el único sitio donde estaba: el PDF
           # no lo imprime en todas las fichas y la web solo en la mitad. Sin
           # país no hay bandera, y la app pinta un globo.
           'pais_tmdb': ', '.join(
               p.get('name', '') for p in (det.get('production_countries') or [])
               if p.get('name'))}
    if en and norm(en) not in (norm(titulo), norm(out['titulo_original'] or '')):
        out['title_en'] = en
    sl = lb_slug(cid)
    if sl:
        out['lbSlug'] = sl
    return det, out


_OBS = None


def cascada_obra(o, key, alias, pub, obs=None):
    """La cascada con el catálogo único primero (docs/CATALOGO-OBRAS.md §5): si
    la obra ya está en catalogo/obras con ficha TMDB —reconocida por título,
    director y año, las reglas del constructor—, se toma esa ficha sin volver a
    buscar en TMDB. Si no, la cascada de siempre."""
    global _OBS
    if obs is None:
        _OBS = catalogo.obras() if _OBS is None else _OBS
        obs = _OBS
    wid, _ = catalogo.reconocer(obs, o.get('titulo'), o.get('director') or '',
                                o.get('anio'), o.get('duracion_min'))
    tid = ((obs.get(wid) or {}).get('xref') or {}).get('tmdb') if wid else None
    if tid:
        _det, e = ficha_de_tmdb(tid, key, o['titulo'])
        e['_verificado'] = f'el catálogo ya la tiene ({wid}, {", ".join(obs[wid]["presentaciones"])})'
        e['work_id'] = wid
        return e, 'catálogo'
    return cascada_tmdb(o, key, alias, pub)


def cascada_tmdb(o, key, alias, pub):
    """La ficha de TMDB por todos los caminos que la pueden verificar →
    (ficha, fuente) o (None, None). La usan el montaje (enriquecer.py) y el
    pre-onboarding (enriquecer_catalogo.py): un solo camino para los dos.

      1. el candado: director ✓ Y (año ±1 O duración ±3);
      2. título idéntico + director, cuando a cualquiera de los dos lados le
         faltan año y duración (lib.ficha_tmdb). «Lolita en Honda» está en
         TMDB sin fecha ni duración y el candado no tenía con qué corroborar;
      3. el tmdb_id con que ya la publicamos en otro festival (`pub`, de
         lib.ya_publicada), si TMDB confirma la dirección.
    """
    if o.get('anio') or o.get('duracion_min'):
        e = enriquecer_obra(o, key, alias)
        if e:
            return e, 'tmdb'
    if not o.get('director'):
        return None, None
    r = ficha_tmdb(o, key)
    if r:
        _det, e = ficha_de_tmdb(r[0]['id'], key, o['titulo'])
        e['_verificado'] = r[2]
        return e, 'tmdb (título idéntico)'
    for x in pub:
        if not x.get('tmdb_id'):
            continue
        cr = tmdb_get(f"/movie/{x['tmdb_id']}/credits", key) or {}
        dirs = [c['name'] for c in cr.get('crew', []) if c.get('job') == 'Director']
        if director_coincide(o['director'], dirs):
            _det, e = ficha_de_tmdb(x['tmdb_id'], key, o['titulo'])
            e['_verificado'] = (f'el tmdb_id con que ya la publicamos en '
                                f'{x["festival"]}, y TMDB confirma la dirección')
            return e, 'tmdb (ya publicada)'
    return None, None


def a_poster(origen, destino, lamina=False, ancho=500, lado=0.06):
    """Una imagen declarada → el JPEG del póster. Una LÁMINA de carrusel es 4:5
    y el póster 2:3: 6% de recorte por lado y el resto de estirón (la regla de
    SiembraFest: recortarlo todo deja el título al borde, estirarlo todo lo
    deforma un 20%). Cualquier otra imagen va tal cual; el encuadre a 2:3 es de
    encuadrar-posters.py.

    Una lámina CUADRADA (Popayán, 29 sep) se estira entera: cualquier recorte le
    corta el título, que va de borde a borde. Decisión de Juan, «por ahora»."""
    from PIL import Image
    im = Image.open(origen).convert('RGB')
    if lamina:
        c = 0 if im.width == im.height else int(im.width * lado)
        im = im.crop((c, 0, im.width - c, im.height)).resize((ancho, ancho * 3 // 2), Image.LANCZOS)
    im.save(destino, 'JPEG', quality=86, optimize=True)


def afiche_tmdb(e, fid, base, key):
    """El afiche de TMDB de la obra en assets/<fid>/ → su ruta, o None.

    EL AFICHE DE TMDB TAMBIÉN PUEDE NO SERLO (7 oct 2026): el de «La libertad
    doble» en español es un rectángulo verde con el título, y las otras tres
    imágenes de la ficha son afiches. Si el archivo —nuevo o ya bajado— no pasa
    pipeline/afiche_criterio.py, se prueban las demás imágenes de la ficha.

    El reemplazo va a un NOMBRE NUEVO (`<slug>-v2.jpg`, -v3…): el service worker
    guarda /assets/ como inmutable, y pisar el archivo dejaría a quien ya lo vio
    con el rectángulo para siempre (la misma regla que los keyArt)."""
    from afiche_criterio import veredicto
    import glob as _glob
    versiones = sorted(_glob.glob(f'{REPO}/assets/{fid}/{base}-v*.jpg'),
                       key=lambda x: int(re.search(r'-v(\d+)\.jpg$', x).group(1)))
    dest = versiones[-1] if versiones else f'{REPO}/assets/{fid}/{base}.jpg'

    def bajar(pp, a):
        subprocess.run(['curl', '-sL', '--max-time', '30', '-o', a, f'https://image.tmdb.org/t/p/w780{pp}'])
        return os.path.exists(a) and os.path.getsize(a) > 5000

    if not (os.path.exists(dest) and os.path.getsize(dest) > 5000) and not bajar(e['poster_path'], dest):
        return None
    m = veredicto(dest)
    if not m:
        return dest
    e['_afiche_rechazado'] = f'TMDB {e["poster_path"]}: {m}'
    alt = [i['file_path'] for i in (tmdb_get(f"/movie/{e['tmdb_id']}/images", key,
                                             include_image_language='es,null,en') or {}).get('posters', [])
           if i['file_path'] != e['poster_path']]
    n = int(re.search(r'-v(\d+)\.jpg$', dest).group(1)) + 1 if re.search(r'-v\d+\.jpg$', dest) else 2
    os.remove(dest)
    nuevo = f'{REPO}/assets/{fid}/{base}-v{n}.jpg'
    for pp in alt:
        if bajar(pp, nuevo) and not veredicto(nuevo):
            e['poster_path'] = pp
            return nuevo
        if os.path.exists(nuevo):
            os.remove(nuevo)
    # ninguna pasa: sin afiche (el ensamblador convertiría el `poster_path` en
    # la URL del rectángulo)
    e['poster_path'] = None
    return None


from herencia import afiche_ajeno_vale  # noqa: E402  (dueño: herencia.py)


def _min_de(v):
    m = re.search(r'\d+', str(v or ''))
    return int(m.group()) if m else None


def reuso_publicada(pub, fid=None):
    """Sin ficha, pero ya la publicamos con afiche: se reusa el afiche y la
    sinopsis que mostramos entonces —ya pasaron por un montaje—. «Belleza letal»
    no está en ningún catálogo y FICCI 65 la tiene con afiche. Va en `obras`, no
    en `verificadas`: no es una ficha verificada, es lo nuestro."""
    # solo un afiche que EXISTE: un /assets/ que no está en disco es una
    # anotación vieja, y dos festivales que se reusan entre sí se quedan sin nada
    # …y que SEA un afiche: el `editorial` de otro festival es un fotograma 16:9
    # (La Mona en Jardín) y tapaba el afiche real que sí existe (29 sep)
    # …y que no sea EL NUESTRO de vuelta: otro festival que reusó el afiche de
    # este (Girardota tomó el de «La Rebelión de un Fantasma» de Popayán) lo
    # devolvía como «ya publicado» y pisaba la procedencia de la lámina
    # declarada (custom → oficial, 30 sep); lo propio lo pone lo declarado
    # …y que sea UN AFICHE (afiche_criterio.py, 7 oct): nueve tarjetas de sección
    # de SiembraFest, marcadas `oficial`, se publicaron como afiche en otros cuatro
    # festivales; la etiqueta no lo dice, la imagen sí
    x = next((x for x in pub if x.get('poster') and x.get('posterSource') != 'editorial' and not (
        str(x['poster']).startswith('/assets/') and not os.path.exists(REPO + x['poster']))
        and not (fid and str(x['poster']).startswith(f'/assets/{fid}/'))
        and not (str(x['poster']).startswith('/assets/') and not afiche_ajeno_vale(x['poster']))), None)
    # la SINOPSIS se reusa de donde esté, aunque el afiche de ese festival fuera
    # un fotograma: son dos datos distintos (Girardota perdía 2 sinopsis)
    s = next((y for y in pub if y.get('sinopsis')), None)
    # y lo demás que ya mostramos (17 oct 2026), de donde esté: cada dato del
    # primer festival que lo tenga
    _de = lambda c: next((y[c] for y in pub if y.get(c)), None)
    resto = {k: v for k, v in (('pais', _de('country')), ('anio', _de('year')),
                                ('duracion_tmdb', _min_de(_de('duration'))),
                                ('genero', _de('genre')), ('synopsis_en', _de('synopsis_en')),
                                ('lbSlug', _de('lbSlug'))) if v}
    # LA FICHA (27 oct 2026): el tmdb_id con que ya la publicamos se quedaba
    # atrás —139 presentaciones sin ficha que otro festival nuestro tiene—.
    # Solo si es UNO: con dos ids distintos, heredar uno sería elegir.
    _ids = {y['tmdb_id'] for y in pub if y.get('tmdb_id')}
    if len(_ids) == 1:
        resto['tmdb_id'] = _ids.pop()
        resto['_ficha_de'] = 'ya publicada en ' + next(y['festival'] for y in pub if y.get('tmdb_id'))
    if not x and not s and not resto:
        return None
    e = {'_ya_publicada': pub}
    if x:
        e['_afiche_de'] = f'ya publicada en {x["festival"]}'
    if s:
        e['_sinopsis_de'] = f'ya publicada en {s["festival"]}'
    if x:
        e['poster'] = x['poster']
        e['_verificado'] = f'ya publicada en {x["festival"]}: se reusa su afiche'
    elif s:
        e['_verificado'] = f'ya publicada en {s["festival"]}: se reusa su sinopsis'
    if s:
        e['sinopsis'] = s['sinopsis']
    if not x and not s:
        e['_verificado'] = f'ya publicada en {pub[0]["festival"]}: se reusan sus datos'
    e.update(resto)
    return e


def ficha_declarada(titulo, dec, key):
    """La ficha que declara una persona, con su porqué. NO pasa por
    ficha_verifica(): quien declara responde por el emparejamiento, y por eso
    la declaración exige un `_por_que` y queda escrita en el sidecar.

    POR QUÉ EXISTE (23 sep 2026). El candado pide director ✓ Y (año ±1 O
    duración ±3). Cuando TMDB no tiene NI año NI duración no hay con qué
    corroborar, y una coincidencia de dirección perfecta se rechaza igual que
    una falsa: «Inolvidable Heidi» (TMDB 1289382, Marcela Citterio y Andrés
    Valencia, las dos exactas) salió sin afiche, sin país y sin sinopsis
    teniendo la ficha entera a un id de distancia. No se afloja el candado
    —aflojarlo cuelga homónimos, que es la lección Tribeca—: se le da salida a
    la persona que ya miró.
    """
    o = {k: v for k, v in dec.items() if not k.startswith('_')}
    cid = o.pop('tmdb', None)
    if cid:
        _det, out = ficha_de_tmdb(cid, key, titulo)
        out.update(o)
        o = out
    o['_verificado'] = 'declarada a mano: ' + dec['_por_que']
    return o


def main():
    if len(sys.argv) < 2:
        sys.exit('uso: TMDB_API_KEY=… python3 pipeline/enriquecer.py <fest-id> [--posters]')
    fid, posters = sys.argv[1], '--posters' in sys.argv
    key = os.environ.get('TMDB_API_KEY') or sys.exit('falta TMDB_API_KEY')

    crudo = cargar_crudo(f'{ST}/{fid}-crudo.json')
    corr_p = f'{ST}/{fid}-correcciones.json'
    corr = json.load(open(corr_p, encoding='utf-8')) if os.path.exists(corr_p) else {}
    tit_of = corr.get('titulo_oficial', {})
    alias = corr.get('alias', {})
    # las fichas que declaró una persona, por título del festival
    declaradas = corr.get('fichas', {})

    # TODAS las obras, no solo las de nivel superior. Hasta hoy esto recorría
    # únicamente `funciones`, así que en un festival con programas de cortos el
    # enriquecido cubría el programa y NINGUNO de los cortos que lo componen
    # —en #NarrarElFuturo, 17 obras miradas y 85 ignoradas—. Las obras de dentro
    # son obras: tienen título, dirección, año y duración, que es justo lo que
    # ficha_verifica() necesita. El candado no cambia: lo que no verifica, no
    # entra; un corto sin ficha en TMDB simplemente sale en `sin_ficha`.
    # `duracion_obra` es la duración de la OBRA, que puede no ser la de la
    # función: una película de 113 minutos en una casilla de 120 se publica
    # con 120 —la sala está ocupada ese rato— pero se verifica con 113, que
    # es lo que TMDB conoce. Sin esta distinción, los largos programados con
    # holgura no verificaban y se quedaban sin ficha ni póster.
    def _para_verificar(x):
        return {**x, 'duracion_min': x.get('duracion_obra') or x.get('duracion_min')}

    obras = obras_a_buscar(crudo['funciones'], tit_of, _para_verificar)

    # ── LA CACHÉ ────────────────────────────────────────────────────────────
    # Sondear TMDB cuesta. Medido en Villa del Cine: 111 obras a ~6 s por
    # llamada son 40 minutos, y el paso se re-corre en cada pasada del plan
    # aunque no haya cambiado nada. Con caché, la misma corrida da el MISMO
    # resultado en menos de un segundo.
    #
    # DOS REGLAS, y la segunda es la que importa:
    #   · un ACIERTO no caduca — el tmdb_id de una obra es el que es;
    #   · un FALLO caduca a los 7 días — TMDB gana fichas todas las semanas, y
    #     una caché que recuerde «no está» para siempre convierte un paso de
    #     verificación en un paso que dejó de verificar.
    # La clave es TÍTULO + DIRECTOR: si la fuente corrige cualquiera de los
    # dos, la respuesta vieja deja de valer. `--refrescar` la ignora entera.
    _hoy = datetime.date.today().isoformat()

    def _vig(fecha, dias=7):
        try:
            return (datetime.date.today()
                    - datetime.date.fromisoformat(fecha)).days < dias
        except (TypeError, ValueError):
            return False

    prev_ok, prev_no = {}, {}
    _dest = f'{ST}/{fid}-enriquecido.json'
    if '--refrescar' not in sys.argv and os.path.exists(_dest):
        _p = json.load(open(_dest, encoding='utf-8'))
        prev_ok = {t: e for t, e in (_p.get('verificadas') or {}).items()
                   if e.get('_sondeado')}
        prev_no = {t: v for t, v in (_p.get('_sin_ficha_sondeo') or {}).items()
                   if _vig(v.get('fecha'))}

    # UNA DECLARACIÓN QUE NO CASA CON NINGUNA OBRA ES UN ERROR, NO UN SILENCIO.
    # Un título mal copiado en el sidecar no haría nada y nadie se enteraría —
    # el mismo fallo mudo de siempre, escribir un dato que nadie lee.
    _huerf = [t for t in declaradas if t not in obras]
    # …salvo la obra que el festival SÍ tiene en su catálogo pero no proyecta en
    # ninguna función pública (FICICA, «Ma-ma»: solo en colegios, 18 oct). Eso no
    # es un título mal copiado: se avisa y se sigue
    _cat_p = f'{ST}/{fid}-catalogo.json'
    if _huerf and os.path.exists(_cat_p):
        _en_cat = {norm(o.get('titulo') or '') for o in json.load(open(_cat_p, encoding='utf-8')).get('obras') or []}
        for t in [t for t in _huerf if norm(t) in _en_cat]:
            print(f'  · ficha declarada de «{t}»: está en el catálogo del festival y no en una función pública; no se usa')
        _huerf = [t for t in _huerf if norm(t) not in _en_cat]
    if _huerf:
        sys.exit('ficha declarada para un título que no está en el programa: '
                 + ' · '.join(_huerf))
    for t, d in declaradas.items():
        if not d.get('_por_que'):
            sys.exit(f'la ficha declarada de «{t}» no dice por qué: falta _por_que')

    # lo que ya publicamos: se anota en cada obra y es el tercer camino de la
    # cascada (ver cascada_tmdb). El festival propio se excluye.
    publicadas = obras_publicadas(REPO, excluir=(fid,))
    _obs = catalogo.obras()
    ok, sin, sin_sondeo, reuso = {}, [], {}, 0
    for i, (t, f) in enumerate(sorted(obras.items()), 1):
        _dir = (f.get('director') or '').strip()
        if t in declaradas:
            e = ficha_declarada(t, declaradas[t], key)
            e['_director'], e['_sondeado'] = _dir, _hoy
            ok[t] = e
            print(f'[{i:3}/{len(obras)}] ✋  {t[:46]:48} '
                  f'{"tmdb " + str(e["tmdb_id"]) if e.get("tmdb_id") else "campos"}'
                  ' (declarada a mano)', flush=True)
            continue
        c = prev_ok.get(t)
        if c and c.get('_director') == _dir:
            # el afiche PRESTADO (de lo publicado o declarado) no se cachea: se
            # recalcula abajo cada vez, que la regla puede haber cambiado —el
            # fotograma de Jardín quedó pegado a La Mona desde la caché—
            if c.get('_afiche'):
                c = {k: v for k, v in c.items() if k not in ('poster', 'posterSource', '_afiche')}
            # lo mismo la sinopsis declarada: si se retira del sidecar, se va
            if c.get('_sinopsis'):
                c = {k: v for k, v in c.items() if k not in ('sinopsis', '_sinopsis')}
            # y lo HEREDADO del catálogo (14 oct 2026): leído de la caché pasaba
            # por dato de TMDB y ya no se volvía a juzgar — el título en inglés
            # malo de Cinemancia quedaba pegado aunque el candado lo rechazara.
            # Se borra y se recalcula abajo, con el catálogo de hoy
            _her = set(c.get('_heredado') or ()) | ({'genero'} if c.get('_genero_de') else set())
            if _her:
                c = {k: v for k, v in c.items() if k not in _her | {'_heredado', '_genero_de'}}
            ok[t] = c
            reuso += 1
            print(f'[{i:3}/{len(obras)}] ··  {t[:46]:48} tmdb {c["tmdb_id"]} '
                  f'(caché del {c["_sondeado"]})', flush=True)
            continue
        c = prev_no.get(t)
        if c and c.get('director') == _dir:
            sin.append(t)
            sin_sondeo[t] = c
            reuso += 1
            # el reúso de lo publicado TAMBIÉN desde la caché: la primera
            # versión solo lo hacía al sondear, y la segunda corrida de
            # Girardota perdía 4 afiches (29 sep 2026, lo paró publicar.py)
            _r = reuso_publicada(ya_publicada({**f, 'titulo': t}, publicadas), fid)
            if _r:
                ok[t] = _r
            print(f'[{i:3}/{len(obras)}] ··  {t[:46]:48} sin ficha '
                  f'(caché del {c["fecha"]})', flush=True)
            continue

        pub = ya_publicada({**f, 'titulo': t}, publicadas)
        e, fuente = cascada_obra({**f, 'titulo': t}, key, alias, pub, _obs)
        if e:
            e['_director'], e['_sondeado'] = _dir, _hoy
            if pub:
                e['_ya_publicada'] = pub
                # TMDB SIN SINOPSIS EN ESPAÑOL, PERO YA LA PUBLICAMOS CON UNA:
                # se reusa la nuestra —ya pasó por un montaje— antes de dejar la
                # obra solo con la inglesa (Mamut, 28 sep 2026).
                if not (e.get('synopsis_es') or '').strip():
                    x = next((x for x in pub if x.get('sinopsis')), None)
                    if x:
                        e['synopsis_es'] = x['sinopsis']
                        e['_sinopsis_de'] = f'ya publicada en {x["festival"]}'
            ok[t] = e
            print(f'[{i:3}/{len(obras)}] OK  {t[:46]:48} {fuente} {e["tmdb_id"]}'
                  f'{"  lb✓" if e.get("lbSlug") else ""}'
                  f'{"  en✓" if e.get("title_en") else ""}', flush=True)
        else:
            sin.append(t)
            sin_sondeo[t] = {'director': _dir, 'fecha': _hoy}
            _r = reuso_publicada(pub, fid)
            if _r:
                ok[t] = _r
            print(f'[{i:3}/{len(obras)}] —   {t[:46]:48} sin ficha verificable'
                  f'{"  · afiche de " + _r["_ya_publicada"][0]["festival"] if _r else ""}', flush=True)
        time.sleep(0.2)

    # ── EL AFICHE QUE TMDB NO TIENE ─────────────────────────────────────────
    # La cascada del afiche es: TMDB → lo que ya publicamos → lo DECLARADO.
    # (1) Una obra CON ficha de TMDB pero sin póster allí no miraba lo nuestro:
    #     el reúso solo corría para las obras sin ficha. «La asociación» tiene
    #     ficha sin póster y SiembraFest la publicó con su lámina (29 sep).
    # (2) Lo declarado: festivals/staging/<fid>-afiches.json, afiches que se
    #     buscaron y se MIRARON fuera de TMDB —la lámina oficial del festival
    #     (carrusel de IG, una por obra), la página del director— y que ningún
    #     paso automático encuentra. Entra solo donde no hay nada de lo anterior.
    for t, f in obras.items():
        e = ok.get(t)
        if e and not e.get('poster_path') and not e.get('poster'):
            _r = reuso_publicada(ya_publicada({**f, 'titulo': t}, publicadas), fid)
            if _r and _r.get('poster') and not _r['poster'].startswith(f'/assets/{fid}/'):
                e['poster'] = _r['poster']
                e['_afiche'] = _r['_verificado']
    _dec = f'{ST}/{fid}-afiches.json'
    declarados = 0
    if os.path.exists(_dec):
        for t, d in (json.load(open(_dec, encoding='utf-8')).get('afiches') or {}).items():
            e = ok.get(t) or {}
            _p = e.get('poster') or ''
            # manda lo de arriba… si EXISTE: un afiche anotado de una corrida
            # anterior, o el de otro festival nuestro que a su vez apunta aquí
            # (La Rebelión de un Fantasma, en Girardota y en Popayán), no cuenta
            # si el archivo no está en disco
            # `sobre_tmdb: true` — el afiche que mandó el festival reemplaza la
            # imagen de TMDB que una persona ya rechazó (Trizas: fotograma según
            # el catálogo; el formulario de MIDBO trajo el afiche, 20 oct 2026)
            if d.get('sobre_tmdb'):
                e, _p = sin_tmdb_si_se_pide(e, d), ''
            if e.get('poster_path') or (_p and not (_p.startswith('/assets/')
                                                     and not os.path.exists(REPO + _p))):
                continue
            os.makedirs(f'{REPO}/assets/{fid}', exist_ok=True)
            # `asset`: nombre propio cuando el de siempre ya está tomado por otra
            # imagen publicada (los assets son write-once)
            _nom = asset_declarado(t, d)
            dest = f'{REPO}/assets/{fid}/{_nom}'
            origen = f'{REPO}/{d.get("lamina") or d["archivo"]}'
            # `editorial: true` — un still 16:9 OFICIAL (el que el festival manda
            # como «afiche» de una obra que no tiene uno vertical): va ENTERO, sin
            # recorte, y la app lo enmarca con la banda de sección (POSTERS.md,
            # regla dura 1: el 16:9 se respeta entero). No pasa por el criterio de
            # afiche, que está hecho para piezas 2:3 (FICPA, 13 oct)
            if not os.path.exists(dest):
                a_poster(origen, dest, lamina=bool(d.get('lamina')))
                from afiche_criterio import veredicto
                _m = None if d.get('editorial') else veredicto(dest)
                if _m:
                    os.remove(dest)
                    print(f'   afiche declarado RECHAZADO · {t}: {_m}')
                    continue
            e = {**e, 'poster': f'/assets/{fid}/{_nom}',
                 'posterSource': 'editorial' if d.get('editorial') else 'custom' if d.get('lamina') else 'oficial',
                 '_afiche': f'declarado: {d["fuente"]}'}
            ok[t] = e
            declarados += 1
    if declarados:
        print(f'afiches declarados en {os.path.basename(_dec)}: {declarados}')
    # LA SINOPSIS DECLARADA: festivals/staging/<fid>-sinopsis.json, texto
    # OFICIAL (página del festival, catálogo, productora) copiado literal y con
    # su URL. Entra solo donde no hay ninguna; no toca la ficha de TMDB.
    _sdec = f'{ST}/{fid}-sinopsis.json'
    if os.path.exists(_sdec):
        n_s = 0
        for t, d in (json.load(open(_sdec, encoding='utf-8')).get('sinopsis') or {}).items():
            if t not in obras:
                sys.exit(f'sinopsis declarada para un título que no está en el programa: {t}')
            e = ok.get(t) or {}
            # `idioma: en`: la única sinopsis que existe está en inglés; va a
            # synopsis_en tal cual (no se traduce) y solo si no hay ninguna
            if d.get('idioma') == 'en':
                if e.get('sinopsis') or e.get('synopsis_es') or e.get('synopsis_en'):
                    continue
                ok[t] = {**e, 'synopsis_en': d['texto'], '_sinopsis': d['fuente']}
                n_s += 1
                continue
            # `texto_en`: la oficial en inglés junto a la española (traducción
            # nuestra); el inglés no se pierde al declarar el español
            if d.get('texto_en') and not e.get('synopsis_en'):
                e = {**e, 'synopsis_en': d['texto_en']}
                ok[t] = e
            if e.get('sinopsis') or e.get('synopsis_es'):
                continue
            ok[t] = {**e, 'sinopsis': d['texto'], '_sinopsis': d['fuente']}
            n_s += 1
        print(f'sinopsis declaradas en {os.path.basename(_sdec)}: {n_s}')

    if posters:
        os.makedirs(f'{REPO}/assets/{fid}', exist_ok=True)
        n = 0
        for t, e in ok.items():
            if not e.get('poster_path'):
                continue
            dest = afiche_tmdb(e, fid, slug(t), key)
            if dest:
                n += 1
                # LA RUTA LOCAL, ESCRITA (23 sep 2026). Este paso bajaba el
                # archivo y no se lo decía a nadie: el sidecar guardaba el
                # `poster_path` de TMDB —que el ensamblador convierte en URL de
                # su CDN— y la imagen descargada en assets/ quedaba huérfana.
                # Itagüí salió con 17 afiches en disco y 0% de cobertura, y el
                # gate de pósters lo paró. El ensamblador ya sabe leer rutas
                # /assets/; solo que nadie se las escribía.
                e['poster'] = dest[len(REPO):]
                e['posterSource'] = 'tmdb'
        print(f'pósters en assets/{fid}/: {n}')

    # LO QUE EL CATÁLOGO YA SABE (14 oct 2026), donde TMDB y la fuente callan.
    # Hasta hoy del catálogo solo se tomaba el id de TMDB: La paga salió «Drama»
    # en Cinemancia 2025 y vacía en FILCMAR y MUBI, y nada lo medía (guardián
    # [dato-que-no-viaja]). Cada campo se hereda SOLO si está vacío y si el
    # catálogo da UN valor: con dos géneros distintos («Drama» / «Ficción») o
    # dos títulos en inglés, heredar uno sería elegir por los festivales. Vale
    # también para las obras sin ficha de TMDB: son las que más lo necesitan.
    # LAS REGLAS viven en herencia.py (las usa también heredar.py)
    import herencia
    # lo que la FUENTE ya trae manda: no se hereda encima (el ensamblador
    # tampoco lo pisaría, pero así lo heredado no queda anotado de mentira)
    _DE_LA_FUENTE = {'synopsis_es': ('sinopsis', 'synopsis_es'), 'synopsis_en': ('sinopsis_en', 'synopsis_en'),
                     'poster': ('poster',), 'genero': ('genero',), 'title_en': ('title_en',),
                     'lbSlug': ('lbSlug',), 'anio': ('anio',),
                     'director_heredado': ('director',), 'duracion_tmdb': ('duracion_min',),
                     'pais_heredado': ('pais',)}
    _hered = {}
    for t, f in obras.items():
        e = ok.get(t) or {}
        # primero LA PRESENTACIÓN (18 oct 2026): si el catálogo ya lista esta obra
        # en este festival —una decisión de identidad la unió, FICICA: «Khazana»
        # sin director, la misma que Ficcali con director—, esa es la obra. Solo
        # si no, se reconoce por título + director, que sin director no puede
        wid = (e.get('work_id') or catalogo.obra_de(_obs, fid, t, e.get('tmdb_id'))
               or catalogo.reconocer(_obs, t, f.get('director') or '', f.get('anio'), f.get('duracion_min'))[0])
        w = _obs.get(wid) if wid else None
        if not w:
            continue
        de = f'catálogo {wid} ({", ".join(w["presentaciones"])})'
        # EL FOTOGRAMA DECLARADO (15 oct 2026): si una decisión del catálogo dice
        # que la imagen de TMDB de esta obra es un fotograma (Trizas: un rostro
        # sin título ni créditos, la única imagen de su ficha), no se publica
        # aunque afiche_criterio la deje pasar — lo vio una persona
        _af = w.get('afiche') or {}
        _pp = e.get('poster_path') or ''
        if _af.get('veredicto') == 'fotograma' and _pp and str(_af.get('archivo') or '').endswith(_pp):
            e['_afiche_rechazado'] = f'TMDB {_pp}: fotograma según el catálogo ({wid})'
            e['poster_path'] = None
            if str(e.get('poster') or '').startswith('/assets/') and e.get('posterSource') == 'tmdb':
                e.pop('poster', None)
                e.pop('posterSource', None)
        for campo in herencia.CAMPOS:
            # el año ya puede venir de TMDB (anio_tmdb) o de la fuente (anio)
            if campo == 'anio' and (e.get('anio_tmdb') or f.get('anio')):
                continue
            if (str(e.get(campo) or '')).strip():
                continue
            if any(f.get(x) for x in _DE_LA_FUENTE.get(campo, ())):
                continue
            # la española también puede estar ya como `sinopsis` (lo publicado),
            # y el afiche como `poster_path` (TMDB)
            if campo == 'synopsis_es' and (e.get('sinopsis') or '').strip():
                continue
            if campo == 'poster' and e.get('poster_path'):
                continue
            v = herencia.valor(w, campo, fid, t, e.get('tmdb_id'), key,
                               obra={'director': f.get('director') or e.get('_director'),
                                     'anio': f.get('anio') or e.get('anio_tmdb')})
            if v:
                e[campo] = v
                if campo == 'tmdb_id':
                    e['_ficha_de'] = de
                if campo == 'poster':
                    e['posterSource'] = herencia.poster_source(w, v)
                    e['_heredado']= {**e.get('_heredado', {}), 'posterSource': de}
                e.setdefault('_heredado', {})[campo] = de
                _hered[campo] = _hered.get(campo, 0) + 1
        if e.get('_heredado') and t not in ok:
            ok[t] = e
    if _hered:
        print('heredado del catálogo: ' + ', '.join(f'{c} {n}' for c, n in _hered.items()))

    json.dump({'_provenance': provenance(
        'TMDB + letterboxd.com/tmdb/<id>, emparejado con ficha_verifica() '
        '(director + año ±1 o duración ±3 min). Lo que no verifica no entra.'),
        # `obras` es la LISTA que lee el ensamblador y exige cargar_plan (lib.
        # _forma_sidecar): hasta hoy este archivo solo traía el diccionario
        # `verificadas`, así que el plan que lo declaraba no cumplía su contrato
        # y el enriquecido no llegaba a la app. Se escriben las dos formas.
        'obras': [{'titulo': t, **e} for t, e in ok.items()],
        # `verificadas` solo las que una fuente verificó: una obra sin ficha que
        # ya publicamos va en `obras` (con el afiche que se reusa), no acá —
        # si no, la caché la tomaría por verificada en la próxima corrida.
        'verificadas': {t: e for t, e in ok.items() if t not in sin},
        'sin_ficha': sorted(sin),
        # la fecha de cada sondeo fallido, que es lo que hace caducar la caché
        '_sin_ficha_sondeo': sin_sondeo},
        open(f'{ST}/{fid}-enriquecido.json', 'w', encoding='utf-8'),
        ensure_ascii=False, indent=1)
    print(f'\n{len(obras)} obras · verificadas {len(ok) - len([t for t in ok if t in sin])} · sin ficha {len(sin)}'
          f' ({len([t for t in ok if t in sin])} con el afiche de un festival nuestro)'
          f' · {reuso} de la caché, {len(obras) - reuso} sondeadas hoy'
          f'{" (--refrescar)" if "--refrescar" in sys.argv else ""}')
    print(f'  con póster {sum(1 for e in ok.values() if e.get("poster_path"))} · '
          f'con lbSlug {sum(1 for e in ok.values() if e.get("lbSlug"))} · '
          f'con title_en {sum(1 for e in ok.values() if e.get("title_en"))}')


if __name__ == '__main__':
    main()
