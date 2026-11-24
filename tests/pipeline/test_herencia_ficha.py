"""La FICHA viaja por el catálogo (herencia.py, 27 oct 2026).

«Caída libre» tenía en el catálogo xref.tmdb 1487969 (la publica Anibia) y
FICCALI la publicaba sin ficha: herencia.CAMPOS no llevaba el tmdb_id. Ahora se
hereda, pero solo con la obra corroborada por dirección o año: un homónimo no
se lleva la ficha de otro.

Mutación: con `ficha_corroborada` devolviendo siempre True cae
test_homonimo_no_hereda; sin 'tmdb_id' en CAMPOS/_VALOR cae test_hereda_*."""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import herencia
import heredar

W = {'id': 'w_X', 'titulo_original': 'Caída libre', 'anio': 2024, 'directores': ['Wilson Borja'],
     'presentaciones': ['anibia-2026', 'ficcali-2026'], 'xref': {'tmdb': 1487969}}


class Ficha(unittest.TestCase):
    def test_campo_declarado(self):
        self.assertEqual(herencia.CAMPOS.get('tmdb_id'), 'tmdb_id')

    def test_hereda_por_direccion(self):
        self.assertEqual(herencia.valor(W, 'tmdb_id', 'ficcali-2026', 'Caída libre',
                                        obra={'director': 'Wilson Borja', 'anio': 2025}), 1487969)

    def test_hereda_por_anio_sin_direccion(self):
        self.assertEqual(herencia.valor(W, 'tmdb_id', 'f', 'Caída libre', obra={'anio': 2025}), 1487969)

    def test_homonimo_no_hereda(self):
        self.assertIsNone(herencia.valor(W, 'tmdb_id', 'f', 'Caída libre',
                                         obra={'director': 'Otra Persona', 'anio': 2024}))

    def test_sin_con_que_corroborar_no_hereda(self):
        self.assertIsNone(herencia.valor(W, 'tmdb_id', 'f', 'Caída libre'))
        self.assertIsNone(herencia.valor(W, 'tmdb_id', 'f', 'Caída libre', obra={'anio': 2010}))

    def test_heredar_publicado_con_procedencia(self):
        d = {'films': [{'title': 'P', 'film_list': [
            {'title': 'Caída libre', 'director': 'Wilson Borja', 'year': 2024, 'work_id': 'w_X',
             'synopsis': 'x', 'poster': '/p.jpg', 'genre': 'g', 'title_en': 'Free Fall',
             'lbSlug': 'caida-libre', 'duration': '9 min', 'country': 'Colombia', 'synopsis_en': 'y'}]}]}
        cambios = heredar.heredar(d, 'ficcali-2026', {'w_X': W})
        o = d['films'][0]['film_list'][0]
        self.assertEqual(o['tmdb_id'], 1487969)
        self.assertIn('tmdb_id', o['_src']['heredado'])
        self.assertEqual([c[1] for c in cambios], ['tmdb_id'])


if __name__ == '__main__':
    unittest.main()
