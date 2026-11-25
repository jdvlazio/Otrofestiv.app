"""TMDB da 404 en español y la ficha en inglés («Chingona», 25 nov 2026)."""
import copy, os, sys, unittest
from unittest import mock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import enriquecer as e

EN = {'id': 7, 'title': 'Bold', 'original_title': 'Chingona', 'poster_path': '/a.jpg', 'runtime': 3,
      'release_date': '2025-01-02', 'genres': [{'name': 'Music'}], 'tagline': 'x',
      'production_countries': [{'iso_3166_1': 'US', 'name': 'United States of America'}],
      'overview': 'She moves with fearless determination through the town.',
      'credits': {'crew': [{'job': 'Director', 'name': 'A B'}]}}


class UnIdioma(unittest.TestCase):
    def ficha(self, es, en):
        with mock.patch.object(e, 'tmdb_ficha', lambda c, k, language, **z: copy.deepcopy(es if language == "es-ES" else en)), \
             mock.patch.object(e, 'lb_slug', lambda c: ''):
            return e.ficha_de_tmdb(7, 'k', 'Chingona')

    def test_toma_lo_neutro_y_nada_en_ingles(self):
        det, o = self.ficha({}, EN)
        self.assertEqual((o['poster_path'], o['anio_tmdb'], o['duracion_tmdb'], o['titulo_original']),
                         ('/a.jpg', 2025, 3, 'Chingona'))
        self.assertEqual((o['genero'], o['synopsis_es'], o['pais_tmdb']), ('', '', 'Estados Unidos'))
        self.assertIn('fearless', o['synopsis_en'])
        self.assertEqual(len(det['credits']['crew']), 1)

    def test_un_pais_sin_nombre_no_deja_la_lista_a_medias(self):
        _, o = self.ficha({}, {**EN, 'production_countries': [{'iso_3166_1': 'US'}, {'iso_3166_1': 'ZZ'}]})
        self.assertEqual(o['pais_tmdb'], '')

    def test_con_ficha_en_espanol_manda_la_espanola(self):
        _, o = self.ficha({**EN, 'poster_path': '/es.jpg', 'genres': [{'name': 'Música'}]}, EN)
        self.assertEqual((o['poster_path'], o['genero']), ('/es.jpg', 'Música'))


if __name__ == '__main__':
    unittest.main()
