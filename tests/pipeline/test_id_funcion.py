"""El id estable de la función (docs/FUNCION.md §11). Juan (18 oct): cuando un
cambio DOBLE termina en id nuevo, el aviso tiene que ser VISIBLE al publicar,
con la función vieja y la nueva — quien la tenía en su plan la pierde."""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import funcion


def f(title='Parapeto', dia='2026-10-22', hora='19:00', sede='Cine - Bogotá', sala=''):
    return {'title': title, 'day': dia, 'time': hora, 'venue': sede, 'sala': sala, '_ancla': (sede, dia, hora)}


class Doble(unittest.TestCase):
    def test_cambio_doble_avisa_con_vieja_y_nueva(self):
        _, reg, _ = funcion.asignar_ids([f()], {})
        out, _, avisos = funcion.asignar_ids([f(title='Parapeto 2', hora='20:00')], reg)
        dobles = [a for a in avisos if a.startswith('⚠ id nuevo')]
        self.assertEqual(len(dobles), 1)
        self.assertIn('Parapeto 2', dobles[0])
        self.assertIn('parapeto', dobles[0].lower())
        self.assertIn('19:00', dobles[0])
        self.assertIn('20:00', dobles[0])

    def test_movida_no_es_doble(self):
        _, reg, _ = funcion.asignar_ids([f()], {})
        _, _, avisos = funcion.asignar_ids([f(hora='20:00')], reg)
        self.assertFalse([a for a in avisos if a.startswith('⚠ id nuevo')])

    def test_solo_avisa_por_la_que_nace(self):
        # A se queda, B sale, C nace (cambio doble de B): el aviso es por C, no por A
        _, reg, _ = funcion.asignar_ids([f(), f(title='B', hora='21:00')], {})
        _, _, avisos = funcion.asignar_ids([f(), f(title='C', hora='22:00')], reg)
        dobles = [a for a in avisos if a.startswith('⚠ id nuevo')]
        self.assertTrue(dobles)
        self.assertTrue(all('«C»' in a for a in dobles))

    def test_funcion_nueva_sin_salida_no_es_doble(self):
        _, reg, _ = funcion.asignar_ids([f()], {})
        _, _, avisos = funcion.asignar_ids([f(), f(title='Otra', hora='21:00')], reg)
        self.assertFalse([a for a in avisos if a.startswith('⚠ id nuevo')])


if __name__ == '__main__':
    unittest.main()


def pub(*fs):
    return {'films': [dict(id=i, title=t, day=d, time=h, venue='V') for i, t, d, h in fs]}


class Estable(unittest.TestCase):
    """[id-funcion-estable]: contra main, un id publicado no desaparece ni cambia
    de función; uno nuevo es una función nueva."""
    R = {'funciones': {}}

    def p(self, a, b, reg=None):
        return funcion.ids_estables(a, b, reg or self.R)

    def test_igual_sano(self):
        self.assertEqual(self.p(pub(('f_1', 'A', 'd1', '19:00')), pub(('f_1', 'A', 'd1', '19:00'))), [])

    def test_movida_o_renombrada_sana(self):
        self.assertEqual(self.p(pub(('f_1', 'A', 'd1', '19:00')), pub(('f_1', 'A', 'd1', '20:00'))), [])
        self.assertEqual(self.p(pub(('f_1', 'A', 'd1', '19:00')), pub(('f_1', 'B', 'd1', '19:00'))), [])

    def test_id_que_desaparece_frena(self):
        self.assertTrue(self.p(pub(('f_1', 'A', 'd1', '19:00')), pub(('f_2', 'A', 'd1', '19:00'))))

    def test_desaparece_pero_registrado_ausente_sano(self):
        reg = {'funciones': {'f_1': {'ausente': True}}}
        self.assertEqual(self.p(pub(('f_1', 'A', 'd1', '19:00')), pub(), reg), [])

    def test_mismo_id_otra_funcion_frena(self):
        r = self.p(pub(('f_1', 'A', 'd1', '19:00')), pub(('f_1', 'B', 'd2', '21:00')))
        self.assertTrue(r and 'cambió de función' in r[0])

    def test_id_repetido_frena(self):
        self.assertTrue(self.p(pub(), pub(('f_1', 'A', 'd1', '19:00'), ('f_1', 'B', 'd1', '20:00'))))

    def test_sin_ids_en_main_no_mide(self):
        self.assertEqual(self.p({'films': [{'title': 'A'}]}, pub(('f_1', 'A', 'd1', '19:00'))), [])
