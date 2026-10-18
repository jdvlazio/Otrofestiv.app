"""El actualizador (docs/FUNCION.md §5.2): publica SOLO, sin preguntar, cuando
la fuente estructurada del propio festival movió día, hora o sala. Todo lo
demás frena. Estos tests son la frontera de lo que puede hacer sin Juan."""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import actualizar


def f(title='Critters', day='2026-10-17', time='19:00', venue='Planetario - Medellín', **kw):
    return {'title': title, 'day': day, 'time': time, 'venue': venue, 'sala': 'Auditorio',
            '_src': {'base_version': 21}, 'day_order': 1, **kw}


def fest(*films, **kw):
    return {'name': 'X', 'films': list(films), 'sections': {'A': {'order': 1}}, '_provenance': {'v': 1}, **kw}


class Comparar(unittest.TestCase):
    def c(self, a, b, tope=5):
        return actualizar.comparar(a, b, tope)

    def test_igual_no_hay_cambios(self):
        self.assertEqual(self.c(fest(f()), fest(f())), ([], []))

    def test_cambia_la_hora_es_permitido(self):
        cam, frenos = self.c(fest(f()), fest(f(time='17:00')))
        self.assertEqual(frenos, [])
        self.assertEqual(cam, [{'title': 'Critters', 'campo': 'time', 'antes': '19:00', 'ahora': '17:00', 'day': '2026-10-17'}])

    def test_cambia_dia_y_sala_es_permitido(self):
        cam, frenos = self.c(fest(f()), fest(f(day='2026-10-18', sala='Sala 2')))
        self.assertEqual(frenos, [])
        self.assertEqual({x['campo'] for x in cam}, {'day', 'sala'})

    def test_lo_interno_no_cuenta(self):
        b = fest(f(_src={'base_version': 26}, day_order=3), sections={'A': {'order': 2}}, _provenance={'v': 2})
        self.assertEqual(self.c(fest(f()), b), ([], []))

    def test_otro_campo_frena(self):
        _, frenos = self.c(fest(f()), fest(f(synopsis='otra')))
        self.assertTrue(frenos and 'synopsis' in frenos[0])

    def test_funcion_nueva_frena(self):
        _, frenos = self.c(fest(f()), fest(f(), f(title='Vida')))
        self.assertTrue(any('nueva' in x for x in frenos))

    def test_funcion_que_sale_frena(self):
        _, frenos = self.c(fest(f(), f(title='Vida')), fest(f()))
        self.assertTrue(any('sale' in x for x in frenos))

    def test_cambio_en_la_raiz_frena(self):
        _, frenos = self.c(fest(f()), fest(f(), name='Y'))
        self.assertTrue(any('name' in x for x in frenos))

    def test_sobre_el_tope_frena(self):
        a = fest(*[f(title=f'O{i}') for i in range(6)])
        b = fest(*[f(title=f'O{i}', time='17:00') for i in range(6)])
        _, frenos = self.c(a, b, tope=5)
        self.assertTrue(any('tope' in x for x in frenos))

    def test_en_el_tope_pasa(self):
        a = fest(*[f(title=f'O{i}') for i in range(5)])
        b = fest(*[f(title=f'O{i}', time='17:00') for i in range(5)])
        self.assertEqual(self.c(a, b, tope=5)[1], [])

    def test_reordenar_no_es_cambio(self):
        self.assertEqual(self.c(fest(f(), f(title='Vida')), fest(f(title='Vida'), f())), ([], []))

    def test_misma_obra_dos_funciones_se_empareja_por_hora_cercana(self):
        # dos funciones de la misma obra en la misma sede: una cambia de hora
        a = fest(f(day='2026-10-17'), f(day='2026-10-18'))
        b = fest(f(day='2026-10-17', time='17:00'), f(day='2026-10-18'))
        cam, frenos = self.c(a, b)
        self.assertEqual(frenos, [])
        self.assertEqual([(x['day'], x['campo']) for x in cam], [('2026-10-17', 'time')])


class Emparejar(unittest.TestCase):
    def test_la_que_no_se_movio_no_se_reporta(self):
        # dos funciones; la del 18 pasa al 16 y queda PRIMERA en el orden. Sin
        # emparejar primero las idénticas, el orden cruzaría las dos y reportaría
        # dos cambios donde hay uno
        a = fest(f(day='2026-10-17', time='19:00'), f(day='2026-10-18', time='18:00'))
        b = fest(f(day='2026-10-16', time='10:00'), f(day='2026-10-17', time='19:00'))
        cam, frenos = actualizar.comparar(a, b, 5)
        self.assertEqual(frenos, [])
        self.assertEqual(sorted((x['campo'], x['antes'], x['ahora']) for x in cam),
                         [('day', '2026-10-18', '2026-10-16'), ('time', '18:00', '10:00')])


class Config(unittest.TestCase):
    def test_apagado_no_actua(self):
        self.assertIn('apagado', actualizar.puede({'activo': False, 'festivales': {'x': {'pasos': [1]}}}, 'x'))

    def test_festival_no_habilitado(self):
        self.assertIn('no está habilitado', actualizar.puede({'activo': True, 'festivales': {}}, 'x'))

    def test_habilitado(self):
        self.assertIsNone(actualizar.puede({'activo': True, 'festivales': {'x': {'pasos': [1]}}}, 'x'))


if __name__ == '__main__':
    unittest.main()
