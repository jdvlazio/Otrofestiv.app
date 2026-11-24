"""La sinopsis publicada es de esa película y alguien la leyó (24 nov 2026)."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import sello_obra as s

O = {'type': 'film', 'title': 'X', 'work_id': 'w_1', 'director': 'A', 'year': 2025, 'synopsis': 'Una mujer vuelve a su pueblo y encuentra un hotel.'}


class Sello(unittest.TestCase):
    def test_autoprueba(self):
        self.assertEqual(s.autoprueba(), [])

    def test_otro_festival_con_lo_mismo_no_lo_rompe(self):
        h = s.huella(s.publicadas({'a': {'films': [O]}})['w_1'])
        self.assertEqual(s.faltan({'a': {'films': [O]}, 'b': {'films': [dict(O, title='Otro título')]}}, {}, {'w_1': h}, {}), [])

    def test_otro_festival_con_otra_direccion_lo_rompe(self):
        h = s.huella(s.publicadas({'a': {'films': [O]}})['w_1'])
        self.assertTrue(s.faltan({'a': {'films': [O]}, 'b': {'films': [dict(O, director='Luc Besson')]}}, {}, {'w_1': h}, {}))

    def test_sin_sinopsis_no_pide_sello(self):
        self.assertEqual(s.faltan({'a': {'films': [dict(O, synopsis='')]}}, {}, {}, {}), [])

    def test_dato_malformado_no_revienta(self):
        self.assertEqual(s.publicadas({'a': {'films': [None, 'x', {'type': 'film', 'film_list': [None]}]}, 'b': None}), {})

    def test_sellar_exige_segundo_lector_fuente_y_veredicto(self):
        bien = {'work_id': 'w_1', 'redacta': 'a', 'verifica': 'b', 'contra': 'https://x', 'veredicto': 'fiel'}
        viejo = s.SELLOS
        s.SELLOS = os.path.join(tempfile.mkdtemp(), 's.json')
        try:
            for malo in ({'verifica': 'a'}, {'contra': ''}, {'redacta': ''}, {'verifica': 'A '}, {'veredicto': 'con ajuste'}, {'work_id': 'w_9'}, {'verifica': ''}):
                with self.assertRaises(SystemExit):
                    s.sellar([dict(bien, **malo)], {'a': {'films': [O]}})
            s.sellar([bien], {'a': {'films': [O]}})
            self.assertEqual(s.faltan({'a': {'films': [O]}}, None, {}, {}), [])
        finally:
            s.SELLOS = viejo

    def test_fusion_no_hereda_el_sello_de_la_absorbida(self):
        h = s.huella(s.publicadas({'a': {'films': [O]}})['w_1'])
        self.assertTrue(s.faltan({'a': {'films': [O]}}, {}, {'w_2': h}, {}))

    def test_la_base_que_la_app_usa_tambien_cuenta(self):
        d = dict(O, synopsis_es=O['synopsis'])
        h = s.huella(s.publicadas({'a': {'films': [d]}})['w_1'])
        self.assertTrue(s.faltan({'a': {'films': [dict(d, synopsis='Falsa.')]}}, {}, {'w_1': h}, {}))

    def test_un_espacio_no_rompe(self):
        h = s.huella(s.publicadas({'a': {'films': [O]}})['w_1'])
        self.assertEqual(s.faltan({'a': {'films': [dict(O, synopsis=O['synopsis'] + ' ')]}}, {}, {'w_1': h}, {}), [])

    def test_el_original_no_se_edita(self):
        viejo, s.ORIGINALES = s.ORIGINALES, os.path.join(tempfile.mkdtemp(), 'o.json')
        try:
            e = {'work_id': 'w_1', 'texto': 't', 'idioma': 'es', 'fuente': 'https://x'}
            s.guardar_originales([e])
            s.guardar_originales([e])
            for malo in ({'texto': 'otro'}, {'fuente': ''}):
                with self.assertRaises(SystemExit):
                    s.guardar_originales([dict(e, **malo)])
        finally:
            s.ORIGINALES = viejo

    def test_hoy_todo_sellado_o_en_deuda(self):
        from obra_unica import _festivales
        fs = _festivales()
        self.assertEqual((s.faltan(fs), s.gemelas(fs)), ([], set()))


if __name__ == '__main__':
    unittest.main()
