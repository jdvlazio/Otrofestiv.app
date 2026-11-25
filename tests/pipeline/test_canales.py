"""pipeline/canales.py: el caso FECILI (24 nov 2026) no vuelve a pasar en silencio."""
import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import canales as c  # noqa: E402

PRE = [{'id': 'x', 'cuenta': 'x', 'inicio': '2026-12-04', 'fin': '2026-12-07'}]
BIEN = {'redes': {'instagram': 'i', 'facebook': 'f', 'web': None}, 'activo': 'facebook', 'ultimo_post': '2026-11-23',
        'fechas': {'inicio': '2026-12-04', 'fin': '2026-12-07', 'fuente': 'https://facebook.com/x'}, 'revisado': '2026-11-24'}
HOY = date(2026, 11, 24)


def m(**k):
    f = c.faltas({'preonboarding': PRE, 'canales': {'x': {**BIEN, **k}}}, HOY)
    return ' '.join(f[0][2]) if f else ''


class Canales(unittest.TestCase):
    def test_bien(self):
        self.assertEqual(m(), '')

    def test_fecili_una_sola_red_y_fecha_de_festhome(self):
        t = m(redes={'instagram': 'i'}, activo='instagram', ultimo_post=None,
              fechas={'inicio': '2026-12-04', 'fuente': 'https://filmmakers.festhome.com/festival/2287'})
        for x in ('su facebook', 'su web', 'no publica', 'sin confirmar'):
            self.assertIn(x, t)

    def test_sin_ficha_frena(self):
        self.assertTrue(c.faltas({'preonboarding': PRE}, HOY))

    def test_la_fecha_confirmada_manda(self):
        f = c.faltas({'preonboarding': PRE, 'canales': {'x': {**BIEN, 'revisado': '2026-11-20',
                     'fechas': {**BIEN['fechas'], 'inicio': '2026-11-26'}}}}, HOY)
        self.assertEqual(f[0][1], 2)

    def test_funcion_fuera_del_afiche(self):
        cu = {'canales': {'x2026': BIEN}}
        f = {'festivalStartStr': '2026-12-04T00:00:00', 'festivalEndStr': '2026-12-07T23:59:00', 'films': [{'day': '2026-12-04'}]}
        self.assertEqual(c.fuera_de_fechas(cu, 'x-2026', f), [])
        f['films'].append({'day': '2026-12-03'})
        self.assertEqual(c.fuera_de_fechas(cu, 'x-2026', f), ['2026-12-03'])

    def test_a_siete_dias_mudo_se_desecha(self):
        self.assertNotIn('DESECHAR', m(ultimo_post='2026-09-01'))
        self.assertIn('DESECHAR', m(ultimo_post='2026-09-01', fechas={**BIEN['fechas'], 'inicio': '2026-12-01'}))


if __name__ == '__main__':
    unittest.main()
