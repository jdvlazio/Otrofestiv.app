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


class Respaldo(unittest.TestCase):
    """2 nov 2026: un 502 de Apify tumbó la corrida; lobstr.io entra de respaldo."""

    def test_http_de_apify_no_tumba_la_corrida(self):
        orig = v._apify
        try:
            def falla(*a):
                raise OSError('HTTP Error 502: Bad Gateway')
            v._apify = falla
            items = v.apify(['a', 'b'], '2026-11-01T00:00:00', 't')
        finally:
            v._apify = orig
        self.assertEqual(set(v.clasificar(items, ['a', 'b'], {})[1]), {'a', 'b'})

    def test_lobstr_con_forma_de_apify(self):
        x = {'shortcode': 'DfOE', 'url': 'https://www.instagram.com/p/DfOE/', 'timestamp_datetime': '2026-11-02T00:10:02Z',
             'owner_username': 'productora', 'caption': 'programación', 'coauthors': [{'username': 'festivalmambe'}],
             'display_url': 'u0', 'child_post_1': {'display_url': 'u1'}, 'child_post_2': {'display_url': 'u2'}, 'child_post_3': ''}
        it = v.lobstr_a_apify(x)
        self.assertEqual((it['shortCode'], it['timestamp'], len(it['childPosts'])), ('DfOE', '2026-11-02T00:10:02Z', 2))
        # el colaborativo se reconoce igual que con Apify
        self.assertEqual([i['shortCode'] for i in v.clasificar([it], ['festivalmambe'], {})[0]['festivalmambe']], ['DfOE'])

    def test_carrusel_de_mas_de_10_se_completa_por_el_embed(self):
        x = {'shortcode': 'DfN9', 'timestamp_datetime': '2026-11-01T00:00:00Z', 'owner_username': 'a',
             'carousel_media_count': 12, **{f'child_post_{i}': {'display_url': f'u{i}'} for i in range(1, 11)}}
        it = v.completar_laminas(v.lobstr_a_apify(x),
                                 leer=lambda sc: {'laminas': [{'url': f'e{i}'} for i in range(1, 13)]})
        self.assertEqual(len(it['childPosts']), 12)
        def falla(sc):
            raise SystemExit('embed caído')
        it = v.completar_laminas(v.lobstr_a_apify(x), leer=falla)
        self.assertEqual((len(it['childPosts']), it['laminas_incompletas'][:8]), (10, '10 de 12'))


class Cascada(unittest.TestCase):
    """2 nov 2026: Bright Data → Apify → lobstr, de mayor a menor cupo."""

    def test_brightdata_con_forma_de_apify(self):
        x = {'shortcode': 'DfPb', 'url': 'u', 'date_posted': '2026-11-02T13:00:00.000Z', 'user_posted': 'otra',
             'description': 'pie', 'coauthor_producers': [{'username': 'fecisofest'}],
             'post_content': [{'url': f'l{i}'} for i in range(12)]}
        it = v.brightdata_a_apify(x)
        self.assertEqual((it['shortCode'], len(it['childPosts'])), ('DfPb', 12))
        self.assertEqual(len(v.clasificar([it], ['fecisofest'], {})[0]['fecisofest']), 1)

    def test_pasa_a_la_siguiente_solo_lo_que_no_se_leyo(self):
        llamadas = []
        def bd(cs, es, ah):
            llamadas.append(('bd', list(cs)))
            return [{'error': 'http', 'username': 'a'}, {'error': 'no_items', 'username': 'b'}]
        def ap(cs, es, ah):
            llamadas.append(('apify', list(cs)))
            return [{'ownerUsername': 'a', 'timestamp': '2026-11-02T10:00:00Z', 'shortCode': 'x'}]
        nuevos, sin_leer, via = v.cascada(['a', 'b'], {}, AHORA, [('brightdata', bd), ('apify', ap)])
        self.assertEqual(llamadas, [('bd', ['a', 'b']), ('apify', ['a'])])   # «b» no publicó: no se re-pide
        self.assertEqual((sin_leer, via), ({}, {'b': 'brightdata', 'a': 'apify'}))
        self.assertEqual([i['shortCode'] for i in nuevos['a']], ['x'])

    def test_todas_agotadas(self):
        caida = lambda cs, es, ah: [{'error': 'http', 'username': c} for c in cs]
        _, sin_leer, _ = v.cascada(['a'], {}, AHORA, [('brightdata', caida), ('lobstr', caida)])
        self.assertTrue(sin_leer['a'].startswith('lobstr'))

    def test_apify_bajo_el_piso_se_salta(self):
        nombres = [n for n, _ in v.fuentes_ig('t', 0.5)]
        self.assertNotIn('apify', nombres)


if __name__ == '__main__':
    unittest.main()
