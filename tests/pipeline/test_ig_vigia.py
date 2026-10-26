"""pipeline/ig_vigia.py: qué cuentas se miran, cada cuánto, y que nada se lea dos veces."""
import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import ig_vigia as v  # noqa: E402

CONFIG = """
const FESTIVAL_CONFIG = {
  vivo1: {
    instagram:'cuentaviva', festivalStartStr:'2026-10-20T00:00:00',festivalEndStr:'2026-10-25T23:59:00',
  },
  sinig: {
    festivalStartStr:'2026-10-20T00:00:00',festivalEndStr:'2026-10-25T23:59:00',
  },
  termino: {
    instagram:'cuentaterm', festivalStartStr:'2026-10-10T00:00:00',festivalEndStr:'2026-10-15T23:59:00',
  },
  viejo: {
    instagram:'cuentavieja', festivalStartStr:'2026-09-01T00:00:00',festivalEndStr:'2026-09-05T23:59:00',
  },
};
"""
CUENTAS = {'festivales': {'sinig': 'cuentaextra', 'vivo1': 'no_manda'},
           'preonboarding': [{'id': 'pre', 'cuenta': 'cuentapre', 'inicio': '2026-10-26', 'fin': '2026-10-30'},
                             {'id': 'lejos', 'cuenta': 'cuentalejos', 'inicio': '2026-12-01', 'fin': '2026-12-05'}]}
AHORA = datetime(2026, 10, 21, 13, 0)


class Vigilados(unittest.TestCase):
    def setUp(self):
        self.vig = {x['id']: x for x in v.vigilados(v.festivales_config(CONFIG), CUENTAS, AHORA)}

    def test_tiers(self):
        self.assertEqual(self.vig['vivo1']['tier'], 'vivo')
        self.assertEqual(self.vig['termino']['tier'], 'terminado')
        self.assertEqual(self.vig['pre']['tier'], 'camino')      # empieza en 5 días: una vez al día
        self.assertNotIn('viejo', self.vig)                      # terminó hace > 8 días
        self.assertNotIn('lejos', self.vig)

    def test_palmares_cerrado_deja_de_mirarse(self):
        vig = {x['id'] for x in v.vigilados(v.festivales_config(CONFIG), CUENTAS, AHORA, {'termino': {}})}
        self.assertNotIn('termino', vig)
        self.assertIn('vivo1', vig)

    def test_config_manda_sobre_el_json(self):
        self.assertEqual(self.vig['vivo1']['cuenta'], 'cuentaviva')
        self.assertEqual(self.vig['sinig']['cuenta'], 'cuentaextra')

    def test_camino_una_vez_al_dia(self):
        c = self.vig['pre']
        self.assertTrue(v.toca(c, {}, AHORA))
        self.assertFalse(v.toca(c, {'cuentapre': {'consultado': '2026-10-21T07:00:00'}}, AHORA))

    def test_terminado_una_vez_al_dia(self):
        t = self.vig['termino']
        self.assertTrue(v.toca(t, {}, AHORA))
        self.assertFalse(v.toca(t, {'cuentaterm': {'consultado': '2026-10-21T07:00:00'}}, AHORA))
        self.assertTrue(v.toca(t, {'cuentaterm': {'consultado': '2026-10-20T13:00:00'}}, AHORA))
        self.assertTrue(v.toca(self.vig['vivo1'], {'cuentaviva': {'consultado': '2026-10-21T12:59:00'}}, AHORA))


class SinCuenta(unittest.TestCase):
    def test_lista_los_vivos_y_proximos_sin_cuenta(self):
        cfg = v.festivales_config(CONFIG)
        self.assertEqual(v.sin_cuenta(cfg, {'festivales': {}}, AHORA), ['sinig'])
        self.assertEqual(v.sin_cuenta(cfg, CUENTAS, AHORA), [])


class Facebook(unittest.TestCase):
    PAG = [{'id': 'fz', 'url': 'https://www.facebook.com/pagina/', 'inicio': '2026-10-25', 'fin': '2026-10-27'}]

    def test_ventana(self):
        self.assertEqual(len(v.paginas_fb({'facebook': self.PAG}, AHORA)), 1)
        lejos = [dict(self.PAG[0], inicio='2026-12-01', fin='2026-12-03')]
        self.assertEqual(v.paginas_fb({'facebook': lejos}, AHORA), [])

    def test_clasifica_por_pagina_y_no_relee(self):
        est = {'fb:fz': {'ultimo_post': '2026-10-21T10:00:00'}}
        items = [{'inputUrl': 'https://www.facebook.com/pagina', 'time': '2026-10-21T10:00:00.000Z', 'postId': 'viejo'},
                 {'inputUrl': 'https://www.facebook.com/pagina/', 'time': '2026-10-21T12:00:00.000Z', 'postId': 'nuevo'},
                 {'error': 'blocked', 'inputUrl': 'https://www.facebook.com/otra'}]
        nuevos, sin_leer = v.clasificar_fb(items, self.PAG, est)
        self.assertEqual([i['postId'] for i in nuevos['fz']], ['nuevo'])
        self.assertIn('*', sin_leer)

    def test_facebook_cuenta_como_cuenta(self):
        cfg = v.festivales_config(CONFIG)
        cu = {'festivales': {}, 'facebook': [{'id': 'sinig', 'url': 'x', 'inicio': '2026-10-20', 'fin': '2026-10-25'}]}
        self.assertEqual(v.sin_cuenta(cfg, cu, AHORA), [])


class Historial(unittest.TestCase):
    def test_desde_es_la_consulta_mas_vieja(self):
        est = {'a': {'consultado': '2026-10-21T07:00:00'}, 'b': {'consultado': '2026-10-20T19:00:00'}}
        self.assertEqual(v.desde(['a', 'b'], est, AHORA), '2026-10-20T18:00:00')
        self.assertEqual(v.desde(['a', 'nueva'], est, AHORA), '2026-10-18T13:00:00')

    def test_no_relee_ni_toma_etiquetados(self):
        est = {'a': {'ultimo_post': '2026-10-21T10:00:00'}}
        items = [{'ownerUsername': 'a', 'timestamp': '2026-10-21T10:00:00.000Z', 'shortCode': 'visto'},
                 {'ownerUsername': 'a', 'timestamp': '2026-10-21T11:00:00.000Z', 'shortCode': 'nuevo'},
                 {'ownerUsername': 'otra', 'timestamp': '2026-10-21T12:00:00.000Z', 'shortCode': 'etiq'}]
        nuevos, sin_leer = v.clasificar(items, ['a'], est)
        self.assertEqual([i['shortCode'] for i in nuevos['a']], ['nuevo'])
        self.assertEqual(sin_leer, {})

    def test_colaborativo_cuenta_como_del_festival(self):
        items = [{'ownerUsername': 'productora', 'timestamp': '2026-10-24T18:22:00.000Z', 'shortCode': 'colab',
                  'coauthorProducers': [{'username': 'otra'}, {'username': 'a'}]}]
        self.assertEqual([i['shortCode'] for i in v.clasificar(items, ['a'], {})[0]['a']], ['colab'])

    def test_no_items_es_sin_novedades_no_bloqueo(self):
        items = [{'error': 'no_items', 'errorDescription': 'Empty or private data for provided input', 'username': 'a'}]
        self.assertEqual(v.clasificar(items, ['a'], {})[1], {})

    def test_bloqueo_no_es_sin_novedades(self):
        items = [{'error': 'blocked', 'username': 'a'}]
        self.assertIn('a', v.clasificar(items, ['a', 'b'], {})[1])
        self.assertIn('*', v.clasificar([], ['a', 'b', 'c'], {})[1])
        self.assertEqual(v.clasificar([], ['a'], {})[1], {})


if __name__ == '__main__':
    unittest.main()
