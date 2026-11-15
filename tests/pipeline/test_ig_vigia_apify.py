"""14 nov 2026: Apify (US$5/mes) no se gasta cuando Bright Data puede leer."""
import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import ig_vigia as v  # noqa: E402

AHORA = datetime(2026, 11, 14, 12, 0)
# Texto real de Bright Data el 14 nov 2026 para @festicinerio y @cineoriente
SIN_POSTS = {'input': {'url': 'https://www.instagram.com/festicinerio/'},
             'error': 'There are no public posts in the profile for the specified period',
             'error_code': 'dead_page'}


class BrightDataSinNovedades(unittest.TestCase):
    def setUp(self):
        self._orig = v._brightdata

    def tearDown(self):
        v._brightdata = self._orig

    def test_cuenta_sin_posts_es_leida_sin_novedades(self):
        v._brightdata = lambda *a, **k: [SIN_POSTS]
        items = v.brightdata_por_cuentas(['festicinerio'], {}, AHORA, 'k')
        self.assertEqual(items, [{'error': 'no_items', 'username': 'festicinerio'}])
        nuevos, sin_leer = v.clasificar(items, ['festicinerio'], {})
        self.assertEqual((nuevos, sin_leer), ({'festicinerio': []}, {}))

    def test_cuenta_privada_si_es_fallo(self):
        v._brightdata = lambda *a, **k: [dict(SIN_POSTS, error='Profile is private')]
        items = v.brightdata_por_cuentas(['festicinerio'], {}, AHORA, 'k')
        self.assertEqual(items[0]['error'], 'http')

    def test_textos_de_sin_novedades(self):
        for txt in ('There are no public posts in the profile for the specified period',
                    'no posts found', 'No results', '0 posts'):
            self.assertTrue(v.es_sin_novedades(txt), txt)
        for txt in ('Profile is private', 'Page does not exist', 'rate limited', ''):
            self.assertFalse(v.es_sin_novedades(txt), txt)


class GuardianApify(unittest.TestCase):
    def test_no_llama_apify_si_bright_data_leyo(self):
        llamadas = []
        v_bd = lambda cs, es, ah: [{'error': 'no_items', 'username': c} for c in cs]
        def ap(cs, es, ah):
            llamadas.append(cs)
            return []
        _, sin_leer, via = v.cascada(['festicinerio', 'cineoriente'], {}, AHORA,
                                     [('brightdata', v_bd), ('apify', ap)])
        self.assertEqual((llamadas, sin_leer), ([], {}))
        self.assertEqual(set(via.values()), {'brightdata'})

    def test_guardian_frena_apify_sin_fallo_real(self):
        with self.assertRaises(v.ApifyIndebido):
            v.guardia_apify({}, {'a': 'brightdata: There are no public posts in the profile'}, ['a'])
        with self.assertRaises(v.ApifyIndebido):
            v.guardia_apify({'a': 'brightdata'}, {'a': 'brightdata: http'}, ['a'])
        with self.assertRaises(v.ApifyIndebido):
            v.guardia_apify({}, {}, ['a'])
        v.guardia_apify({}, {'a': 'brightdata: Profile is private'}, ['a'])   # fallo real: pasa


class FacebookCascada(unittest.TestCase):
    PAG = [{'id': 'ficoconcepcion2026', 'url': 'https://www.facebook.com/cineoriente/',
            'inicio': '2026-11-13', 'fin': '2026-11-16'}]

    def informe(self, fuentes):
        inf = {'NO_PUDE_LEER': {}}
        orig = v.SALIDA
        v.SALIDA = os.path.join(os.path.dirname(__file__), '_tmp_fb')
        os.makedirs(v.SALIDA, exist_ok=True)
        try:
            v.vigilar_fb({'facebook': self.PAG}, {}, AHORA, 't', inf, fuentes=fuentes)
        finally:
            import shutil
            shutil.rmtree(v.SALIDA, ignore_errors=True)
            v.SALIDA = orig
        return inf

    def test_apify_bajo_el_piso_no_se_usa_en_fb(self):
        os.environ.pop('BRIGHTDATA_API_KEY', None)
        self.assertEqual(v.fuentes_fb('t', 0.04), [])
        self.assertEqual([n for n, _ in v.fuentes_fb('t', 4.0)], ['apify'])

    def test_fb_sin_fuentes_sale_en_no_pude_leer(self):
        inf = self.informe([])
        self.assertIn('bajo el piso', inf['NO_PUDE_LEER']['fb:ficoconcepcion2026'])

    def test_fb_bright_data_primero_y_apify_no_se_toca(self):
        x = {'input': {'url': self.PAG[0]['url']}, 'post_id': '1785', 'url': 'https://fb/p',
             'date_posted': '2026-11-12T23:26:38.000Z', 'content': 'Tenemos noticias', 'attachments': [{}]}
        llamadas = []
        bd = lambda ps, es, ah: [v.brightdata_fb_a_apify(x)]
        ap = lambda ps, es, ah: llamadas.append(ps) or []
        inf = self.informe([('brightdata', bd), ('apify', ap)])
        self.assertEqual(llamadas, [])
        self.assertEqual(inf['via_facebook'], {'ficoconcepcion2026': 'brightdata'})
        self.assertEqual(inf['nuevos_facebook'][0]['texto'], 'Tenemos noticias')

    def test_fb_bright_data_sin_posts_no_cae_a_apify(self):
        orig = v._brightdata
        v._brightdata = lambda *a, **k: [{'input': {'url': self.PAG[0]['url']},
                                          'error': 'There are no public posts in the profile for the specified period'}]
        try:
            bd = lambda ps, es, ah: v.brightdata_fb(ps, es, ah, 'k')
            llamadas = []
            inf = self.informe([('brightdata', bd), ('apify', lambda ps, es, ah: llamadas.append(ps) or [])])
        finally:
            v._brightdata = orig
        self.assertEqual((llamadas, inf['NO_PUDE_LEER']), ([], {}))


if __name__ == '__main__':
    unittest.main()
