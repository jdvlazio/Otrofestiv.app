"""El cruce con lo publicado como GUARDIÁN (lib.cruce_faltantes,
lib.razones_que_mienten, lib.obras_publicadas_estricto; publicar.py trabajo 5).

27 oct 2026: Miradas declaró «La mona», «Madres de nacimiento», «Refracción» y
«Luis Antonio» «sin afiche: no está en otro festival nuestro» y estaban en 3 a 7
festivales nuestros. El cruce las encontraba; nadie lo contrastaba al publicar.

Mutación: con `coincidencias` devolviendo [] (sin cruce) estos tests fallan."""
import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import lib
import enriquecer

OTRO = {'films': [{'title': 'Programa 1', 'type': 'film', 'film_list': [
    {'title': 'La Mona', 'director': 'Laura Gutiérrez Ardila', 'year': 2025, 'duration': '18 min',
     'poster': '/assets/jardin-2026/la-mona.jpg', 'tmdb_id': 1444298, 'synopsis': 'La Mona…'},
    {'title': 'Programa de Cortos 2', 'director': 'Varios', 'year': 2025,
     'poster': '/assets/jardin-2026/p2.jpg'}]}]}


def _idx(festivales):
    d = tempfile.mkdtemp()
    os.makedirs(f'{d}/festivals')
    for fid, j in festivales.items():
        with open(f'{d}/festivals/{fid}.json', 'w', encoding='utf-8') as fh:
            fh.write(j if isinstance(j, str) else json.dumps(j))
    return d


class Cruce(unittest.TestCase):
    def setUp(self):
        self.idx = lib.obras_publicadas_estricto(_idx({'jardin-2026': OTRO}), excluir=('miradas-2026',))

    def test_obra_sin_afiche_ficha_ni_sinopsis_que_otro_tiene(self):
        films = [{'title': 'La mona', 'director': 'Laura Gutiérrez', 'year': 2025, 'duration': '18 min'}]
        faltas = {k: de for _, k, de in lib.cruce_faltantes('miradas-2026', films, self.idx)}
        self.assertEqual(faltas, {'afiche': ['jardin-2026'], 'ficha': ['jardin-2026'],
                                  'sinopsis': ['jardin-2026']})

    def test_por_tmdb_id_aunque_el_titulo_cambie(self):
        films = [{'title': 'Heat Wave', 'tmdb_id': 1444298}]
        self.assertEqual([k for _, k, _ in lib.cruce_faltantes('m', films, self.idx)],
                         ['afiche', 'sinopsis'])

    def test_homonimo_sin_corroborar_no_cruza(self):
        films = [{'title': 'La mona', 'director': 'Otra Persona', 'year': 2010}]
        self.assertEqual(lib.cruce_faltantes('m', films, self.idx), [])

    def test_titulo_generico_no_cruza(self):
        films = [{'title': 'Programa de Cortos 2', 'director': 'Varios', 'year': 2025}]
        self.assertEqual(lib.cruce_faltantes('m', films, self.idx), [])

    def test_no_heredar_declarado(self):
        films = [{'title': 'La mona', 'director': 'Laura Gutiérrez', 'year': 2025}]
        self.assertEqual(lib.cruce_faltantes('m', films, self.idx, {lib.norm('La mona')}), [])

    def test_razon_sin_afiche_que_miente(self):
        films = [{'title': 'P', 'film_list': [{'title': 'La mona', 'director': 'Laura Gutiérrez', 'year': 2025}]}]
        sa = {'La mona': {'_por_que': 'sin afiche: no está en TMDB ni en otro festival nuestro'}}
        self.assertEqual(lib.razones_que_mienten('m', films, sa, self.idx), [('La mona', ['jardin-2026'])])
        sa = {'La mona': {'_por_que': 'el festival no publicó afiche'}}
        self.assertEqual(lib.razones_que_mienten('m', films, sa, self.idx), [])


class FallaCerrado(unittest.TestCase):
    def test_json_ilegible(self):
        with self.assertRaises(lib.CruceIlegible):
            lib.obras_publicadas_estricto(_idx({'a': OTRO, 'b': '{roto'}), excluir=('m',))

    def test_sin_otros_festivales(self):
        with self.assertRaises(lib.CruceIlegible):
            lib.obras_publicadas_estricto(_idx({'m': OTRO}), excluir=('m',))

    def test_sin_carpeta(self):
        with self.assertRaises(lib.CruceIlegible):
            lib.obras_publicadas_estricto('/no/existe', excluir=())


class Publicador(unittest.TestCase):
    """El cableado en publicar.py: bloquea, y sin otros festivales legibles no publica."""
    def setUp(self):
        import publicar
        self.p, self.viejo = publicar, publicar.REPO

    def tearDown(self):
        self.p.REPO = self.viejo

    def test_bloquea_la_obra_que_otro_festival_tiene(self):
        self.p.REPO = _idx({'jardin-2026': OTRO})
        films = [{'title': 'La mona', 'director': 'Laura Gutiérrez', 'year': 2025}]
        self.assertEqual(len(self.p._cruce_con_lo_publicado('miradas-2026', films)), 3)

    def test_ilegible_no_publica(self):
        self.p.REPO = _idx({'jardin-2026': '{roto'})
        with self.assertRaises(SystemExit):
            self.p._cruce_con_lo_publicado('miradas-2026', [])


class Herencia(unittest.TestCase):
    def test_hereda_la_ficha_con_su_procedencia(self):
        e = enriquecer.reuso_publicada([{'festival': 'jardin-2026', 'titulo': 'La Mona',
                                         'tmdb_id': 1444298, 'sinopsis': 'La Mona…'}])
        self.assertEqual((e['tmdb_id'], e['_ficha_de'], e['_sinopsis_de']),
                         (1444298, 'ya publicada en jardin-2026', 'ya publicada en jardin-2026'))

    def test_dos_ids_distintos_no_elige(self):
        e = enriquecer.reuso_publicada([{'festival': 'a', 'titulo': 't', 'tmdb_id': 1},
                                        {'festival': 'b', 'titulo': 't', 'tmdb_id': 2}])
        self.assertIsNone(e)


if __name__ == '__main__':
    unittest.main()
