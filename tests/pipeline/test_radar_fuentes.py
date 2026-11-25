import datetime, json, os, sys, tempfile, unittest
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
        self.assertIn('sin publicar', r.pendientes([e], HOY, 21)[0][2])
        e['conclusion'] = 'esperando'
        self.assertEqual(r.pendientes([e], HOY, 21), [])
        e['inicio_2026'] = '2026-12-10'
        self.assertTrue(r.pendientes([e], datetime.date(2026, 12, 5), 21), 'lectura vieja se repite')

    def test_fecha_y_url(self):
        self.assertTrue(r.forma({'fuentes_miradas': {'web': [{'resultado': 'nada', 'url': 'https://x'}]}}))
        self.assertTrue(r.forma({'fuentes_miradas': {'web': [{'resultado': 'nada', 'fecha': '2026-11-25'}]}}))

    def test_extracto_y_busqueda_no_cierran(self):
        e = {'fuentes_miradas': todo()}
        self.assertEqual(r.huecos(e), [])
        e['fuentes_miradas']['sede'] = [{'url': 'https://x', 'fecha': '2026-11-25', 'resultado': 'extracto'}]
        self.assertEqual(r.huecos(e), ['sede'])
        for c in r.PAGINA:
            e = {'fuentes_miradas': todo()}
            e['fuentes_miradas'][c] = [{'url': 'búsqueda: x', 'fecha': '2026-11-25', 'resultado': 'nada'}]
            self.assertEqual(r.huecos(e), [c])
        self.assertTrue(r.forma({'fuentes_miradas': {'sede': [{'fecha': '2026-11-25', 'resultado': 'no_aplica'}]}}))

    def test_caduca_por_clase(self):
        e = {'fuentes_miradas': todo()}
        e['fuentes_miradas']['sede'][0]['fecha'] = '2026-11-22'
        self.assertEqual(r.viejas(e, HOY, 14), ['sede (2026-11-22)'])
        self.assertEqual(r.viejas(e, HOY, 30), [])

    def test_limite_sin_publicar(self):
        e = {'estado': 'radar', 'nombre': 'a', 'inicio_2026': '2026-11-28',
             'conclusion': 'esperando', 'fuentes_miradas': todo()}
        self.assertIn('montar lo confirmado', str(r.pendientes([e], HOY, 45)))

    def test_caso_mhf(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, 'festivals', 'staging'))
            e = {'estado': 'en_app', 'nombre': 'mhf', 'id_config': ['mhf2026'], 'inicio_2026': '2026-11-26',
                 'conclusion': 'esperando', 'fuentes_miradas': todo()}
            j = {'festivalStartStr': '2026-11-26T00:00:00', 'films': [{'title': 'A', 'time': None}]}
            st = os.path.join(d, 'festivals', 'staging', 'mhf-2026.json')
            json.dump(j, open(st, 'w'))
            self.assertTrue(r.pendientes([e], HOY, 45, d), 'el pre-montaje no cuenta como publicado')
            pub = os.path.join(d, 'festivals', 'mhf-2026.json')
            json.dump(j, open(pub, 'w'))
            self.assertEqual(r.pendientes([e], HOY, 45, d), [])
            e['fuentes_miradas']['anfitrion'][0]['fecha'] = '2026-11-20'
            self.assertIn('sin hora', str(r.pendientes([e], HOY, 45, d)))
            j['films'][0]['time'] = '20:00'
            json.dump(j, open(pub, 'w'))
            self.assertEqual(r.pendientes([e], HOY, 45, d), [])


if __name__ == '__main__':
    unittest.main()
