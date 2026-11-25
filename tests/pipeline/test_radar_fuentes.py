import datetime, json, os, sys, unittest
RAIZ = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, os.path.join(RAIZ, 'pipeline'))
import radar_fuentes as r  # noqa: E402

HOY = datetime.date(2026, 11, 25)


def todo(resultado='nada'):
    return {c: [{'url': 'https://x', 'fecha': '2026-11-25', 'resultado': resultado}] for c in r.CLASES}


class RadarFuentes(unittest.TestCase):
    def test_ancla_real_bien_formada(self):
        for e in json.load(open(r.ANCLA, encoding='utf-8'))['festivales']:
            self.assertEqual(r.forma(e), [], e['clave'])

    def test_sin_informacion_exige_todo(self):
        e = {'conclusion': 'sin_informacion', 'fuentes_miradas': todo()}
        self.assertEqual(r.forma(e), [])
        e['fuentes_miradas']['anfitrion'] = []
        self.assertTrue(r.forma(e))
        e['fuentes_miradas']['anfitrion'] = [{'fecha': '2026-11-25', 'resultado': 'no_mirada'}]
        self.assertTrue(r.forma(e))
        self.assertTrue(r.forma({'conclusion': 'sin_informacion', 'fuentes_miradas': todo('ilegible')}))

    def test_ventana(self):
        e = {'estado': 'radar', 'nombre': 'a', 'inicio_2026': '2026-12-01'}
        self.assertEqual(len(r.pendientes([e], HOY, 21)), 1)
        e.update(fuentes_miradas=todo(), conclusion='montable')
        self.assertIn('sin premontar', r.pendientes([e], HOY, 21)[0][2])
        e['conclusion'] = 'esperando'
        self.assertEqual(r.pendientes([e], HOY, 21), [])
        e['inicio_2026'] = '2026-12-10'
        self.assertTrue(r.pendientes([e], datetime.date(2026, 12, 5), 21), 'lectura vieja se repite')

    def test_fecha_y_url(self):
        self.assertTrue(r.forma({'fuentes_miradas': {'web': [{'resultado': 'nada', 'url': 'https://x'}]}}))
        self.assertTrue(r.forma({'fuentes_miradas': {'web': [{'resultado': 'nada', 'fecha': '2026-11-25'}]}}))


if __name__ == '__main__':
    unittest.main()
