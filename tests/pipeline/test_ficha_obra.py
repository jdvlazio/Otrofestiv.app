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
        for d in ('Arthur J. Bressan, Jr.', 'Cristian Camilo Camargo C.', 'Resk12', 'Colectivo Artefactum Suba', 'Óscar Ruiz Navia', 'Inês Pedrosa e Melo', 'Colectivo Pix & Hertz', "Seán O'Brien"):
            self.assertEqual(fo.revisar({'title': 'X', 'director': d}), [], d)

    def test_paises_con_y_o_guion_en_el_nombre(self):
        for c in ('Antigua y Barbuda', 'Bosnia y Herzegovina', 'Guinea-Bisáu', 'URSS', 'Costa de Marfil', 'Hong Kong', 'Arabia Saudita, Estados Unidos'):
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
    R = 'género:fuera de lista'

    def _d(self, *gs):
        return {'films': [{'title': f'X{i}', 'type': 'film', 'work_id': f'w_{i}', 'genre': g} for i, g in gs]}

    def _techo(self, d):
        return {'a': {r: sorted(o) for r, o in fo.incumplen(d).items()}}

    def test_lo_anotado_pasa_y_el_de_otro_festival_no_cubre(self):
        d = self._d((1, 'Qatar'))
        self.assertEqual(fo.excedidos({'a': d}, self._techo(d)), [])
        self.assertEqual([x[:2] for x in fo.excedidos({'b': d}, self._techo(d))], [('b', self.R)])

    def test_un_malo_nuevo_no_se_tapa_arreglando_otro(self):
        techo = self._techo(self._d((1, 'Qatar')))
        self.assertEqual(fo.excedidos({'a': self._d((1, 'Drama'), (2, 'Italia'))}, techo), [('a', self.R, ['X2'])])

    def test_ni_cambiando_un_malo_por_otro_malo(self):
        techo = self._techo(self._d((1, 'Qatar')))
        self.assertEqual(fo.excedidos({'a': self._d((1, 'Italia'))}, techo), [('a', self.R, ['X1'])])

    def test_otra_funcion_de_una_obra_endeudada_no_bloquea(self):
        d = self._d((1, 'Qatar'))
        techo = self._techo(d)
        d['films'] += [dict(d['films'][0]), {'title': 'X1', 'type': 'film', 'genre': 'Qatar'}]   # repetida, y aún sin enlazar
        self.assertEqual(fo.excedidos({'a': d}, techo), [])

    def test_hoy_nadie_la_supera(self):
        self.assertEqual(fo.excedidos(fo._festivales()), [])

    def test_lo_arreglado_se_ve(self):
        self.assertEqual(fo.holgura({'a': self._d((1, 'Drama'))}, self._techo(self._d((1, 'Qatar')))), [f'a {self.R} 1'])

    def test_datos_ilegibles_no_tumban(self):
        for d in ({'films': None}, {'films': [None]}, {'films': [{'title': 'P', 'type': 'film', 'film_list': [None]}]}, None):
            fo.incumplen(d)


if __name__ == '__main__':
    unittest.main()
