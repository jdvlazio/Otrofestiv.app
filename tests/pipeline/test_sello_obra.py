"""La sinopsis publicada es de esa película y alguien la leyó (24 nov 2026)."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import sello_obra as s

LIT = lambda o, obra=None: ('literal', 'x')
O = {'type': 'film', 'title': 'X', 'work_id': 'w_1', 'director': 'A', 'year': 2025, 'synopsis': 'Una mujer vuelve a su pueblo y encuentra un hotel.'}


O2 = dict(O, synopsis_en='A woman returns to her town and finds a hotel.')


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
        viejo, viejo_o = s.SELLOS, s.ORIGINALES
        s.SELLOS, s.ORIGINALES = os.path.join(tempfile.mkdtemp(), 's.json'), os.path.join(tempfile.mkdtemp(), 'o.json')
        try:
            for malo in ({'verifica': 'a'}, {'contra': ''}, {'redacta': ''}, {'verifica': 'A '}, {'veredicto': 'con ajuste'}, {'work_id': 'w_9'}, {'verifica': ''}):
                with self.assertRaises(SystemExit):
                    s.sellar([dict(bien, **malo)], {'a': {'films': [O2]}}, comprobar=LIT)
            with self.assertRaises(SystemExit):           # sin el original, no hay contra qué leer
                s.sellar([bien], {'a': {'films': [O2]}}, comprobar=LIT)
            s.guardar_originales([{'work_id': 'w_1', 'texto': 't', 'idioma': 'es', 'fuente': 'https://x'}])
            s.sellar([bien], {'a': {'films': [O2]}}, comprobar=LIT)
            self.assertEqual(s.faltan({'a': {'films': [O2]}}, None, {}, None), [])
        finally:
            s.SELLOS, s.ORIGINALES = viejo, viejo_o

    def temporal(self):
        viejo = (s.SELLOS, s.ORIGINALES, s.DEUDA)
        d = tempfile.mkdtemp()
        s.SELLOS, s.ORIGINALES, s.DEUDA = (os.path.join(d, n) for n in ('s.json', 'o.json', 'd.json'))
        self.addCleanup(lambda: setattr(s, 'SELLOS', viejo[0]) or setattr(s, 'ORIGINALES', viejo[1]) or setattr(s, 'DEUDA', viejo[2]))
        s.guardar_originales([{'work_id': 'w_1', 'texto': 't', 'idioma': 'es', 'fuente': 'https://x'}])
        return {'work_id': 'w_1', 'redacta': 'a', 'verifica': 'b', 'contra': 'https://x', 'veredicto': 'fiel'}

    def test_no_sella_si_el_original_no_esta_en_su_fuente(self):
        bien = self.temporal()
        for estado in ('no está', 'ilegible'):
            with self.assertRaises(SystemExit):
                s.sellar([bien], {'a': {'films': [O2]}}, comprobar=lambda o, obra=None: (estado, 'x'))
        self.assertEqual(s.sellos(), {})

    def test_fuente_ilegible_se_sella_si_dice_donde_se_leyo(self):
        bien = self.temporal()
        with self.assertRaises(SystemExit):                       # «no está» no se arregla a mano
            s.sellar([dict(bien, literal_a_mano='catálogo p. 3')], {'a': {'films': [O2]}}, comprobar=lambda o, obra=None: ('no está', 'x'))
        s.sellar([dict(bien, literal_a_mano='catálogo impreso, p. 3')], {'a': {'films': [O2]}}, comprobar=lambda o, obra=None: ('ilegible', 'x'))
        self.assertEqual(s.sellos()['w_1']['comprobado'], 'a mano: catálogo impreso, p. 3')

    def test_exige_los_dos_idiomas_y_cortos(self):
        bien = self.temporal()
        for o in (O, dict(O2, synopsis_en='A' * 351), dict(O2, synopsis='Á' * 351)):
            with self.assertRaises(SystemExit):
                s.sellar([bien], {'a': {'films': [o]}}, comprobar=LIT)
        s.sellar([bien], {'a': {'films': [O2]}}, comprobar=LIT)
        self.assertEqual(s.sellos()['w_1']['comprobado'], 'máquina: x')

    def test_retirar_vuelve_a_la_deuda_con_motivo(self):
        bien = self.temporal()
        s.sellar([bien], {'a': {'films': [O2]}}, comprobar=LIT)
        with self.assertRaises(SystemExit):
            s.retirar([{'work_id': 'w_1'}], {'a': {'films': [O2]}})
        s.retirar([{'work_id': 'w_1', 'motivo': 'el original no está en TMDB'}], {'a': {'films': [O2]}})
        self.assertEqual(s.sellos(), {})
        d = s._leer(s.DEUDA)
        self.assertEqual(d['retirados'], {'w_1': 'el original no está en TMDB'})
        self.assertEqual(s.faltan({'a': {'films': [O2]}}, None, None, None), [])
        self.assertTrue(s.faltan({'a': {'films': [dict(O2, synopsis_en='Other.')]}}, None, None, None))

    def test_corregir_original_exige_que_este_y_guarda_el_anterior(self):
        self.temporal()
        nuevo = {'work_id': 'w_1', 'texto': 'u', 'idioma': 'en', 'fuente': 'https://y', 'motivo': 'el anterior no estaba'}
        with self.assertRaises(SystemExit):
            s.corregir_original([nuevo], comprobar=lambda o, obra=None: ('no está', 'y'))
        with self.assertRaises(SystemExit):
            s.corregir_original([dict(nuevo, motivo='')], comprobar=LIT)
        s.corregir_original([nuevo], comprobar=LIT)
        o = s.originales()['w_1']
        self.assertEqual((o['texto'], o['anteriores'][0]['texto'], o['anteriores'][0]['motivo']), ('u', 't', 'el anterior no estaba'))

    def test_auditar_cuenta_cada_sello(self):
        bien = self.temporal()
        s.sellar([bien], {'a': {'films': [O2]}}, comprobar=LIT)
        self.assertEqual(s.auditar(lambda o, obra=None: ('no está', 'z')), [{'work_id': 'w_1', 'estado': 'no está', 'donde': 'z'}])

    def test_sin_red_o_sin_clave_no_sella_ni_a_mano(self):
        import sello_fuente
        bien = self.temporal()
        def corta(o, obra=None):
            raise sello_fuente.SinLeer('falta TMDB_API_KEY')
        with self.assertRaises(SystemExit):
            s.sellar([dict(bien, literal_a_mano='lo vi')], {'a': {'films': [O2]}}, comprobar=corta)
        self.assertEqual(s.sellos(), {})

    def test_la_url_con_punto_final_se_lee_bien(self):
        import sello_fuente as f
        vistas = []
        L = {'web': lambda u: vistas.append(u) or ('x ' * 300 + 'Página Una mujer vuelve a su pueblo'), 'local': lambda p: '', 'tmdb': lambda i: [], 'instagram': lambda c: ''}
        self.assertEqual(f.comprobar({'texto': 'Una mujer vuelve a su pueblo', 'fuente': 'Web: https://a.co/page.'}, L, {'titulos': ['Página']})[0], 'literal')
        self.assertEqual(vistas, ['https://a.co/page'])

    def test_un_sello_sin_comprobar_solo_vale_si_es_de_antes(self):
        self.temporal()
        h = s.huella(s.publicadas({'a': {'films': [O2]}})['w_1'], s.originales()['w_1'])
        viejo = {'huella': h, 'redacta': 'a', 'verifica': 'b', 'contra': 'https://x', 'veredicto': 'fiel', 'fecha': '2026-11-24'}
        s._escribir(s.SELLOS, {'w_1': viejo})
        self.assertTrue(s.faltan({'a': {'films': [O2]}}))                      # escrito a mano, sin comprobar: no vale
        s._escribir(s.DEUDA, {'sin_comprobar': ['w_1']})
        self.assertEqual(s.faltan({'a': {'films': [O2]}}), [])               # de antes de la regla: vale
        s.retirar([{'work_id': 'w_1', 'motivo': 'x'}], {'a': {'films': [O2]}})
        self.assertEqual(s._leer(s.DEUDA)['sin_comprobar'], [])              # y la lista solo baja

    def test_la_comprobacion_ve(self):
        import sello_fuente
        self.assertEqual(sello_fuente.autoprueba(), [])

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
