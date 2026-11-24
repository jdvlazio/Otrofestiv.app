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

    def test_llena_lo_que_identifica_la_obra_y_nada_mas(self):
        d = {'films': [{'title': 'X', 'work_id': 'w_1', 'duration': '20 min'}, {'title': 'Y', 'work_id': 'w_2', 'year': 2000}, {'title': 'T', 'type': 'event', 'work_id': 'w_1'}]}
        decs = [{'work_id': 'w_1', 'campo': 'directores', 'valor': ['Radu Jude']}, {'work_id': 'w_1', 'campo': 'anio', 'valor': 2025},
                {'work_id': 'w_1', 'campo': 'paises', 'valor': ['RO']}, {'work_id': 'w_1', 'campo': 'generos', 'valor': ['Drama']}]
        fu.aplicar(d, decs)
        self.assertEqual(d['films'][0], {'title': 'X', 'work_id': 'w_1', 'duration': '20 min', 'director': 'Radu Jude', 'year': 2025, 'country': 'Rumania', 'flags': '🇷🇴'})
        self.assertEqual(d['films'][1:], [{'title': 'Y', 'work_id': 'w_2', 'year': 2000}, {'title': 'T', 'type': 'event', 'work_id': 'w_1'}])
        self.assertEqual(fu.aplicar(d, decs), [])


if __name__ == '__main__':
    unittest.main()
