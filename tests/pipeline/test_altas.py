"""pipeline/altas.py — el registro de altas y sus guardianes (15 nov 2026,
BOGOSHORTS). Sin red: TMDB se reemplaza por un diccionario."""
import json, os, sys, tempfile, unicodedata, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import altas as A


def completa(**extra):
    return {'estado': 'sin_afiche',
            'fuentes': {k: {'url': f'https://x/{k}', 'fecha': '2026-11-15', 'resultado': 'nada'}
                        for k in A.FUENTES_OBLIGATORIAS}, **extra}


class Base(unittest.TestCase):
    def setUp(self):
        self.r = tempfile.mkdtemp()
        for d in ('festivals/staging', 'pipeline'):
            os.makedirs(os.path.join(self.r, d))
        self.w('pipeline/x.plan.json', {'festival': {}})
        self.w('festivals/staging/x-catalogo.json', {'obras': [
            {'titulo': 'Lluvia', 'director': 'Ana Pérez Gómez', 'anio': 2025, 'duracion_min': 12},
            {'titulo': 'Canción (Los Artistas)', 'director': 'Juan Ruiz'}]})
        self.w('festivals/staging/x-catalogo-enriquecido.json',
               {'obras': [], 'sin_ficha': ['Lluvia', 'Canción (Los Artistas)']})
        self.w('pipeline/altas-deuda.json', {})

    def w(self, p, d):
        json.dump(d, open(os.path.join(self.r, p), 'w', encoding='utf-8'), ensure_ascii=False)

    def rd(self, p):
        return json.load(open(os.path.join(self.r, p), encoding='utf-8'))


class Registro(Base):
    def test_pendientes_sin_registro_faltan_todas(self):
        p = A.pendientes('x', self.r)
        self.assertEqual(set(p), {'Lluvia', 'Canción (Los Artistas)'})
        self.assertIn('estado', p['Lluvia'])
        self.assertEqual(len(p['Lluvia']), 1 + len(A.FUENTES_OBLIGATORIAS))

    def test_videoclip_exige_canal_del_artista(self):
        self.assertIn('canal_oficial_artista', A.pendientes('x', self.r)['Canción (Los Artistas)'])
        self.assertTrue(A.es_videoclip('X', {'genero': 'Video clip'}))
        self.assertFalse(A.es_videoclip('Lluvia (2025)'))

    def test_fuente_sin_url_no_cuenta_y_na_con_porque_si(self):
        e = completa()
        e['fuentes']['imdb'] = {'resultado': 'miré'}
        e['fuentes']['letterboxd'] = {'na': True, 'por_que': ''}
        e['fuentes']['busqueda_imagenes'] = {'na': True, 'por_que': 'corto sin difusión'}
        self.w('festivals/staging/x-altas.json', {'obras': {'Lluvia': e}})
        self.assertEqual(A.pendientes('x', self.r)['Lluvia'], ['imdb', 'letterboxd'])

    def test_entrada_completa_sale_de_pendientes(self):
        self.w('festivals/staging/x-altas.json', {'obras': {'Lluvia': completa()}})
        self.assertNotIn('Lluvia', A.pendientes('x', self.r))

    def test_alta_posible_exige_afiche_que_pase(self):
        self.w('festivals/staging/x-altas.json', {'obras': {'Lluvia': completa(
            estado='alta_posible', afiche={'url': 'u', 'fuente': 'f', 'ratio': 0.9})}})
        self.assertIn('afiche (no pasa el criterio)', A.pendientes('x', self.r)['Lluvia'])

    def test_registro_lee_titulos_nfd_como_nfc(self):
        nfd = unicodedata.normalize('NFD', 'Canción (Los Artistas)')
        self.w('festivals/staging/x-altas.json', {'obras': {nfd: {}}})
        self.assertIn('Canción (Los Artistas)', A.leer_registro('x', self.r)['obras'])


    def test_obra_del_crudo_si_no_hay_catalogo(self):
        self.w('festivals/staging/x-crudo.json', {'funciones': [{'obras': [
            'Suelta', {'titulo': 'Niebla', 'director': 'Eva Ríos', 'anio': 2024, 'duracion_min': 9}]}]})
        o = A.obra_catalogo('x', 'Niebla', self.r)
        self.assertEqual((o['director'], o['anio']), ('Eva Ríos', 2024))
        self.assertEqual(A.obra_catalogo('x', 'Lluvia', self.r)['director'], 'Ana Pérez Gómez')
        self.assertEqual(A.obra_catalogo('x', 'Nada', self.r), {'titulo': 'Nada'})

class Sondar(Base):
    def setUp(self):
        super().setUp()
        self.api = {}
        self._orig = A._tmdb
        A._tmdb = lambda path, **p: self.api.get(path, {})

    def tearDown(self):
        A._tmdb = self._orig

    def test_sin_ficha_deja_evidencia_automatica(self):
        A.sondar('x', self.r)
        e = self.rd('festivals/staging/x-altas.json')['obras']['Lluvia']
        for k in ('tmdb_titulo', 'tmdb_alternos', 'tmdb_director'):
            self.assertTrue(A.revisada(e['fuentes'][k]), k)
        self.assertNotIn('estado', e)
        self.assertNotIn('imdb', e['fuentes'])          # sin id: queda para la mano

    def test_ficha_existente_solo_con_candado_y_va_a_fichas(self):
        self.api = {
            '/search/movie': {'results': [{'id': 7, 'title': 'Lluvia'}]},
            '/movie/7': {'release_date': '2025-03-01', 'runtime': 12,
                         'credits': {'crew': [{'job': 'Director', 'name': 'Ana Pérez Gómez'}]}}}
        A.sondar('x', self.r)
        e = self.rd('festivals/staging/x-altas.json')['obras']['Lluvia']
        self.assertEqual((e['estado'], e['tmdb_id']), ('ficha_existente', 7))
        f = self.rd('festivals/staging/x-correcciones.json')['fichas']['Lluvia']
        self.assertEqual((f['tmdb'], f['_registro']), (7, 'x-altas.json'))
        self.assertEqual(A.fichas_sin_registro(self.r), {})

    def test_homonimo_de_otro_director_no_entra(self):
        self.api = {
            '/search/movie': {'results': [{'id': 8, 'title': 'Lluvia'}]},
            '/movie/8': {'release_date': '2025-01-01', 'runtime': 12,
                         'credits': {'crew': [{'job': 'Director', 'name': 'Pedro Soto'}]}}}
        A.sondar('x', self.r)
        self.assertNotIn('estado', self.rd('festivals/staging/x-altas.json')['obras']['Lluvia'])
        self.assertFalse(os.path.exists(os.path.join(self.r, 'festivals/staging/x-correcciones.json')))


    def test_parcial_no_cuenta(self):
        A.anotar_fuente('x', 'Lluvia', 'organismo_nacional', url='https://www.google.com/search?q=lluvia',
                        resultado='búsqueda web', raiz=self.r, parcial='no se abrió el buscador de Proimágenes')
        e = self.rd('festivals/staging/x-altas.json')['obras']['Lluvia']
        self.assertFalse(A.revisada(e['fuentes']['organismo_nacional']))
        self.assertIn('organismo_nacional', A.pendientes('x', self.r)['Lluvia'])
        with self.assertRaises(SystemExit):
            A.anotar_fuente('x', 'Lluvia', 'imdb', url='https://imdb.com/x', raiz=self.r, parcial=' ')

    def _respaldo(self, parcial=None):
        A.anotar_fuente('x', 'Lluvia', 'imdb', url='https://www.imdb.com/title/tt1/', resultado='tt1', raiz=self.r)
        A.anotar_fuente('x', 'Lluvia', 'letterboxd', url='https://letterboxd.com/film/lluvia/',
                        resultado='TMDB 7', raiz=self.r, parcial=parcial)

    def test_ficha_a_mano_con_evidencia_y_respaldo(self):
        self._respaldo()
        self.api = {'/movie/7': {'credits': {'crew': [{'job': 'Director', 'name': 'Ana Pérez Gómez'}]}}}
        A.registrar_ficha('x', 'Lluvia', 7, 'misma directora y sinopsis', ['imdb', 'letterboxd'], self.r)
        e = self.rd('festivals/staging/x-altas.json')['obras']['Lluvia']
        self.assertEqual((e['estado'], e['tmdb_id']), ('ficha_existente', 7))
        self.assertEqual(self.rd('festivals/staging/x-correcciones.json')['fichas']['Lluvia']['tmdb'], 7)
        self.assertEqual(A.fichas_sin_registro(self.r), {})

    def test_ficha_a_mano_sin_respaldo_o_evidencia_o_director_no_entra(self):
        self._respaldo(parcial='solo búsqueda web')
        self.api = {'/movie/7': {'credits': {'crew': [{'job': 'Director', 'name': 'Ana Pérez Gómez'}]}}}
        for args in (('', ['imdb', 'letterboxd']),           # sin evidencia
                     ('misma directora', ['imdb']),          # una sola fuente
                     ('misma directora', ['imdb', 'letterboxd'])):  # letterboxd es parcial
            with self.assertRaises(SystemExit):
                A.registrar_ficha('x', 'Lluvia', 7, *args, raiz=self.r)
        self._respaldo()
        self.api = {'/movie/7': {'credits': {'crew': [{'job': 'Director', 'name': 'Otra Persona'}]}}}
        with self.assertRaises(SystemExit):
            A.registrar_ficha('x', 'Lluvia', 7, 'misma directora', ['imdb', 'letterboxd'], self.r)
        self.assertNotIn('fichas', self.rd('festivals/staging/x-correcciones.json') if os.path.exists(
            os.path.join(self.r, 'festivals/staging/x-correcciones.json')) else {})

class Preparar(Base):
    def img(self, w, h):
        from PIL import Image, ImageDraw
        p = os.path.join(self.r, f'a{w}x{h}.png')
        import random
        random.seed(1)
        im = Image.new('RGB', (w, h), 'white')
        d = ImageDraw.Draw(im)
        for _ in range(4000):                             # contenido en todas las filas
            x, y = random.randrange(w), random.randrange(h)
            d.rectangle([x, y, x + w // 20, y + h // 30], fill=(random.randrange(256), 0, 0))
        im.save(p)
        return p

    def test_recorte_centrado_jpg_y_nfc(self):
        nfd = unicodedata.normalize('NFD', 'Canción (Los Artistas)')
        out = A.preparar('x', nfd, self.img(1000, 1000), 'web del artista', self.r)
        self.assertEqual(out['titulo'], 'Canción (Los Artistas)')
        self.assertEqual(out['wiz']['title'], unicodedata.normalize('NFC', nfd))
        e = A.leer_registro('x', self.r)['obras']['Canción (Los Artistas)']
        a = e['afiche']
        self.assertTrue(A.RATIO[0] <= a['ratio'] <= A.RATIO[1])
        self.assertTrue(a['recorte']['centrado'])
        self.assertEqual(a['recorte']['caja'][0], (1000 - 667) // 2)
        self.assertTrue(a['archivo'].endswith('.jpg'))
        self.assertEqual(e['estado'], 'alta_posible')
        self.assertEqual(out['personas'], {'Juan Ruiz': 'Director'})

    def test_afiche_chico(self):
        A.preparar('x', 'Lluvia', self.img(200, 300), 'f', self.r)
        self.assertEqual(A.leer_registro('x', self.r)['obras']['Lluvia']['estado'], 'afiche_chico')

    def test_registrar_alta_escribe_ficha(self):
        A.preparar('x', 'Lluvia', self.img(600, 900), 'f', self.r)
        A.registrar_alta('x', 'Lluvia', 99, self.r)
        self.assertEqual(self.rd('festivals/staging/x-correcciones.json')['fichas']['Lluvia']['tmdb'], 99)
        self.assertEqual(A.fichas_sin_registro(self.r), {})


class Guardianes(Base):
    """Mutación: cada guardián falla con el error que vigila y pasa sin él."""
    def test_alta_sin_evidencia(self):
        v = A.verificar(self.r)['alta-sin-evidencia']
        self.assertTrue(v and v[0].startswith('x: 2'))
        self.w('festivals/staging/x-altas.json', {'obras': {'Lluvia': completa(),
                                                           'Canción (Los Artistas)': completa(
            fuentes={**completa()['fuentes'], 'canal_oficial_artista': {'url': 'https://yt'}})}})
        self.assertEqual(A.verificar(self.r)['alta-sin-evidencia'], [])

    def test_alta_sin_evidencia_publicado_no_se_mide(self):
        self.w('festivals/x.json', {'films': []})
        self.assertEqual(A.verificar(self.r)['alta-sin-evidencia'], [])

    def test_deuda_tolera_hasta_su_numero(self):
        self.w('pipeline/altas-deuda.json', {'alta_sin_evidencia': {'x': 2}})
        self.assertEqual(A.verificar(self.r)['alta-sin-evidencia'], [])

    def test_ficha_a_mano_falla_y_congelada_no(self):
        self.w('festivals/staging/x-correcciones.json', {'fichas': {'Lluvia': {'tmdb': 5, '_por_que': 'a mano'}}})
        self.assertEqual(A.verificar(self.r)['ficha-sin-registro'], ['x: «Lluvia»'])
        self.w('pipeline/altas-deuda.json', {'fichas_sin_registro': {'x': ['Lluvia']}})
        self.assertEqual(A.verificar(self.r)['ficha-sin-registro'], [])

    def test_ficha_con_otro_id_que_el_registro_falla(self):
        self.w('festivals/staging/x-correcciones.json', {'fichas': {'Lluvia': {'tmdb': 5}}})
        self.w('festivals/staging/x-altas.json', {'obras': {'Lluvia': {'estado': 'alta_hecha', 'tmdb_id': 6}}})
        self.assertEqual(len(A.verificar(self.r)['ficha-sin-registro']), 1)

    def test_titulo_nfd_falla(self):
        self.assertEqual(A.verificar(self.r)['titulo-nfc'], [])
        self.w('festivals/staging/x-crudo.json', {'funciones': [{'titulo': unicodedata.normalize('NFD', 'Ubuntú')}]})
        self.assertEqual(len(A.verificar(self.r)['titulo-nfc']), 1)

    def test_congelar_nunca_sube(self):
        A.congelar(self.r)       # sin deuda previa: congela lo de hoy
        self.assertEqual(A.deuda(self.r)['alta_sin_evidencia'], {'x': 2})
        self.w('pipeline/altas-deuda.json', {'alta_sin_evidencia': {'x': 1}})
        A.congelar(self.r)
        self.assertEqual(A.deuda(self.r)['alta_sin_evidencia'], {'x': 1})


if __name__ == '__main__':
    unittest.main()
