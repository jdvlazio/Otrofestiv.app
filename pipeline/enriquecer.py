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
from lib import (cargar_crudo, ficha_verifica, norm, provenance, slug,
                 tmdb_get, UA, ficha_tmdb, director_coincide, ya_publicada,
                 obras_publicadas)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'


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
    orig = (f.get('titulo_original') or '').strip()
    if orig and norm(orig) != norm(f['titulo']):
        for q in variantes(orig, alias):
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
    det = tmdb_get(f'/movie/{cid}', key, language='es-ES',
                   append_to_response='credits')
    det_en = tmdb_get(f'/movie/{cid}', key, language='en-US',
                      append_to_response='credits')
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
    encuadrar-posters.py."""
    from PIL import Image
    im = Image.open(origen).convert('RGB')
    if lamina:
        c = int(im.width * lado)
        im = im.crop((c, 0, im.width - c, im.height)).resize((ancho, ancho * 3 // 2), Image.LANCZOS)
    im.save(destino, 'JPEG', quality=86, optimize=True)


def reuso_publicada(pub):
    """Sin ficha, pero ya la publicamos con afiche: se reusa el afiche y la
    sinopsis que mostramos entonces —ya pasaron por un montaje—. «Belleza letal»
    no está en ningún catálogo y FICCI 65 la tiene con afiche. Va en `obras`, no
    en `verificadas`: no es una ficha verificada, es lo nuestro."""
    # solo un afiche que EXISTE: un /assets/ que no está en disco es una
    # anotación vieja, y dos festivales que se reusan entre sí se quedan sin nada
    # …y que SEA un afiche: el `editorial` de otro festival es un fotograma 16:9
    # (La Mona en Jardín) y tapaba el afiche real que sí existe (29 sep)
    x = next((x for x in pub if x.get('poster') and x.get('posterSource') != 'editorial' and not (
        str(x['poster']).startswith('/assets/') and not os.path.exists(REPO + x['poster']))), None)
    # la SINOPSIS se reusa de donde esté, aunque el afiche de ese festival fuera
    # un fotograma: son dos datos distintos (Girardota perdía 2 sinopsis)
    s = next((y for y in pub if y.get('sinopsis')), None)
    if not x and not s:
        return None
    e = {'_ya_publicada': pub}
    if x:
        e['poster'] = x['poster']
        e['_verificado'] = f'ya publicada en {x["festival"]}: se reusa su afiche'
    else:
        e['_verificado'] = f'ya publicada en {s["festival"]}: se reusa su sinopsis'
    if s:
        e['sinopsis'] = s['sinopsis']
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

    obras = {}
    for f in crudo['funciones']:
        if not f.get('en_app', True):
            continue
        if f.get('tipo', 'film') in ('film', ''):
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
    if _huerf:
        sys.exit('ficha declarada para un título que no está en el programa: '
                 + ' · '.join(_huerf))
    for t, d in declaradas.items():
        if not d.get('_por_que'):
            sys.exit(f'la ficha declarada de «{t}» no dice por qué: falta _por_que')

    # lo que ya publicamos: se anota en cada obra y es el tercer camino de la
    # cascada (ver cascada_tmdb). El festival propio se excluye.
    publicadas = obras_publicadas(REPO, excluir=(fid,))
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
            _r = reuso_publicada(ya_publicada({**f, 'titulo': t}, publicadas))
            if _r:
                ok[t] = _r
            print(f'[{i:3}/{len(obras)}] ··  {t[:46]:48} sin ficha '
                  f'(caché del {c["fecha"]})', flush=True)
            continue

        pub = ya_publicada({**f, 'titulo': t}, publicadas)
        e, fuente = cascada_tmdb({**f, 'titulo': t}, key, alias, pub)
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
            _r = reuso_publicada(pub)
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
            _r = reuso_publicada(ya_publicada({**f, 'titulo': t}, publicadas))
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
            if e.get('poster_path') or (_p and not (_p.startswith('/assets/')
                                                     and not os.path.exists(REPO + _p))):
                continue
            os.makedirs(f'{REPO}/assets/{fid}', exist_ok=True)
            dest = f'{REPO}/assets/{fid}/{slug(t)}.jpg'
            origen = f'{REPO}/{d.get("lamina") or d["archivo"]}'
            if not os.path.exists(dest):
                a_poster(origen, dest, lamina=bool(d.get('lamina')))
            e = {**e, 'poster': f'/assets/{fid}/{slug(t)}.jpg',
                 'posterSource': 'custom' if d.get('lamina') else 'oficial',
                 '_afiche': f'declarado: {d["fuente"]}'}
            ok[t] = e
            declarados += 1
    if declarados:
        print(f'afiches declarados en {os.path.basename(_dec)}: {declarados}')

    if posters:
        os.makedirs(f'{REPO}/assets/{fid}', exist_ok=True)
        n = 0
        for t, e in ok.items():
            if not e.get('poster_path'):
                continue
            dest = f'{REPO}/assets/{fid}/{slug(t)}.jpg'
            if not (os.path.exists(dest) and os.path.getsize(dest) > 5000):
                subprocess.run(['curl', '-sL', '--max-time', '30', '-o', dest,
                                f'https://image.tmdb.org/t/p/w780{e["poster_path"]}'])
            if os.path.exists(dest) and os.path.getsize(dest) > 5000:
                n += 1
                # LA RUTA LOCAL, ESCRITA (23 sep 2026). Este paso bajaba el
                # archivo y no se lo decía a nadie: el sidecar guardaba el
                # `poster_path` de TMDB —que el ensamblador convierte en URL de
                # su CDN— y la imagen descargada en assets/ quedaba huérfana.
                # Itagüí salió con 17 afiches en disco y 0% de cobertura, y el
                # gate de pósters lo paró. El ensamblador ya sabe leer rutas
                # /assets/; solo que nadie se las escribía.
                e['poster'] = f'/assets/{fid}/{slug(t)}.jpg'
                e['posterSource'] = 'tmdb'
        print(f'pósters en assets/{fid}/: {n}')

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
