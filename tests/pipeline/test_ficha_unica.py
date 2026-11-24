"""Un director, un año y un país por obra (24 nov 2026)."""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import ficha_unica as fu

DEC = [{'work_id': 'w_1', 'campo': 'directores', 'valor': ['Ana Díaz', 'Luz Paz']}, {'work_id': 'w_1', 'campo': 'anio', 'valor': 2025},
       {'work_id': 'w_1', 'campo': 'paises', 'valor': ['CO', 'FR']}]


class FichaUnica(unittest.TestCase):
    def test_lleva_lo_elegido_con_banderas_e_idempotente(self):
        o = {'title': 'X', 'work_id': 'w_1', 'director': 'Ana Diaz', 'year': 2026, 'country': 'Colombia', 'flags': '🇨🇴'}
        d = {'films': [{'title': 'P', 'film_list': [o]}]}
        self.assertEqual(len(fu.aplicar(d, DEC)), 3)
        self.assertEqual((o['director'], o['year'], o['country'], o['flags']), ('Ana Díaz, Luz Paz', 2025, 'Colombia, Francia', '🇨🇴🇫🇷'))
        self.assertEqual(fu.aplicar(d, DEC), [])

    def test_no_llena_vacios_ni_toca_otras_obras_ni_la_duracion(self):
        d = {'films': [{'title': 'X', 'work_id': 'w_1', 'duration': '20 min'}, {'title': 'Y', 'work_id': 'w_2', 'year': 2000}]}
        self.assertEqual(fu.aplicar(d, DEC), [])


if __name__ == '__main__':
    unittest.main()
