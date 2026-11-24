"""La regla de cada campo de una obra (24 nov 2026)."""
import json, os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import ficha_obra as fo


class Reglas(unittest.TestCase):
    def test_cada_regla_ve_su_cebo_y_la_sana_pasa(self):
        self.assertEqual(fo.autoprueba(), [])

    def test_son_21_generos(self):
        self.assertEqual((len(fo.GENEROS), len(set(fo.GENEROS))), (21, 21))

    def test_vacio_no_incumple(self):
        self.assertEqual(fo.revisar({'title': 'X'}), [])

    def test_nombres_legitimos_no_son_basura(self):
        for d in ('Arthur J. Bressan, Jr.', 'Cristian Camilo Camargo C.', 'Resk12', 'Colectivo Artefactum Suba', 'Óscar Ruiz Navia', "Seán O'Brien"):
            self.assertEqual(fo.revisar({'title': 'X', 'director': d}), [], d)

    def test_paises_con_y_o_guion_en_el_nombre(self):
        for c in ('Antigua y Barbuda', 'Bosnia y Herzegovina', 'Guinea-Bisáu', 'URSS', 'Hong Kong', 'Arabia Saudita, Estados Unidos'):
            self.assertEqual(fo.revisar({'title': 'X', 'country': c}), [], c)

    def test_synopsis_es_manda_sobre_la_base(self):
        o = {'title': 'X', 'synopsis': 'A woman returns to her village and finds that her house is now a hotel.', 'synopsis_lang': 'en',
             'synopsis_es': 'Una mujer vuelve a su pueblo y encuentra que su casa es ahora un hotel.'}
        self.assertEqual(fo.revisar(o), [])

    def test_mira_programas_y_eventos(self):
        e = {'title': 'Gala', 'type': 'event', 'film_list': [{'title': 'X', 'director': 'A', 'year': 2025, 'genre': 'Qatar'}]}
        p = {'title': 'Cortos', 'type': 'film', 'film_list': [{'title': 'Z', 'genre': 'Qatar'}]}
        self.assertEqual(set(fo.incumplen({'films': [e, p]})['género:fuera de lista'].values()), {'X', 'Z'})


class Deuda(unittest.TestCase):
    D = {'films': [{'title': 'X', 'type': 'film', 'genre': 'Qatar'}]}

    def test_el_techo_de_otro_festival_no_cubre(self):
        r = 'género:fuera de lista'
        self.assertEqual(fo.excedidos({'a': self.D}, {'a': {r: 1}}), [])
        self.assertEqual([x[:4] for x in fo.excedidos({'a': self.D}, {'b': {r: 9}})], [('a', r, 1, 0)])

    def test_hoy_nadie_la_supera(self):
        fs = fo._festivales()
        self.assertEqual(fo.excedidos(fs), [])

    def test_la_holgura_se_ve(self):
        self.assertEqual(fo.holgura({'a': self.D}, {'a': {'género:fuera de lista': 3}}), ['a género:fuera de lista 1<3'])


if __name__ == '__main__':
    unittest.main()
