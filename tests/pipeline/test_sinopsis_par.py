"""La sinopsis se lee en español e inglés (24 nov 2026)."""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import sinopsis_par as sp


def fest(**o):
    return {'films': [dict({'type': 'film', 'title': 'X', 'work_id': 'w_1'}, **o)]}


class Par(unittest.TestCase):
    def test_autoprueba(self):
        self.assertEqual(sp.autoprueba(), [])

    def test_lo_anotado_no_frena_y_lo_nuevo_si(self):
        f = {'a': fest(synopsis='Una.')}
        self.assertEqual(sp.excedidos(f, {'a': ['w_1:en']}), [])
        self.assertEqual(sp.excedidos(f, {'a': ['w_1:es']}), [('a', ['X (en)'])])
        self.assertEqual(sp.excedidos({'b': fest(synopsis='Una.')}, {'a': ['w_1:en']}), [('b', ['X (en)'])])

    def test_lo_arreglado_se_avisa(self):
        self.assertEqual(sp.holgura({'a': fest(synopsis='Una.', synopsis_en='A.')}, {'a': ['w_1:en']}), ['a 1'])

    def test_mira_los_cortos_de_un_programa(self):
        d = {'films': [{'type': 'film', 'is_cortos': True, 'title': 'P', 'film_list': [{'title': 'C', 'work_id': 'w_2', 'synopsis_en': 'A.'}]}]}
        self.assertEqual(sp.faltan(d), {'w_2:es': 'C'})

    def test_funcion_nueva_sin_enlazar_de_una_obra_anotada(self):
        d = fest(synopsis='Una.')
        d['films'].append({'type': 'film', 'title': 'x', 'director': 'A', 'year': 2025, 'synopsis': 'Una.'})
        self.assertEqual(sp.excedidos({'a': d}, {'a': ['w_1:en']}), [])
        d['films'][1]['title'] = 'Otra'
        self.assertEqual(sp.excedidos({'a': d}, {'a': ['w_1:en']}), [('a', ['Otra (en)'])])

    def test_obra_fusionada_sigue_anotada(self):
        import catalogo
        fus = catalogo.fusiones()
        viejo = fus[0]['absorbido']
        f = {'a': fest(synopsis='Una.', work_id=catalogo.redirige(viejo, fus))}
        self.assertEqual((sp.excedidos(f, {'a': [viejo + ':en']}), sp.holgura(f, {'a': [viejo + ':en']})), ([], []))

    def test_traducir_de_a_uno_no_frena(self):
        f = {'a': fest(synopsis='Uma.', synopsis_lang='pt', synopsis_es='Una.')}
        self.assertEqual(sp.excedidos(f, {'a': ['w_1:en', 'w_1:es']}), [])

    def test_dato_malformado_no_revienta(self):
        self.assertEqual(sp.faltan({'films': [None, 'x', {'type': 'film', 'title': 'P', 'film_list': [None]}]}), {})

    def test_la_deuda_es_lo_publicado(self):
        self.assertEqual((sp.excedidos(__import__('obra_unica')._festivales())), [])

    def test_un_evento_no_cuenta(self):
        self.assertEqual(sp.faltan({'films': [{'type': 'event', 'title': 'Taller', 'synopsis': 'Un taller.'}]}), {})


if __name__ == '__main__':
    unittest.main()
