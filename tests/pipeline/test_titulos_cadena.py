"""Cadenas de renombres en ensamblar._titulos_anteriores (20 oct 2026): A→B→C
llega a C (MUBI), y una ida y vuelta X→Y→X no traba el armado."""
import json, os, sys, tempfile, unittest
from unittest import mock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import ensamblar


def armar(renombres, titulos):
    d = tempfile.mkdtemp(); os.makedirs(f'{d}/festivals/staging')
    json.dump({'renombres': renombres}, open(f'{d}/festivals/staging/f-2026-titulos-anteriores.json', 'w'))
    films = [{'title': t} for t in titulos]
    with mock.patch.object(ensamblar, 'REPO', d):
        ensamblar._titulos_anteriores('f-2026', films)
    return films


class Cadena(unittest.TestCase):
    def test_a_b_c_llega_a_c(self):
        fs = armar([{'antes': 'A', 'ahora': 'B'}, {'antes': 'B', 'ahora': 'C'}], ['C'])
        self.assertEqual(fs[0]['titulos_anteriores'], ['A', 'B'])

    def test_ida_y_vuelta_no_traba(self):
        fs = armar([{'antes': 'X', 'ahora': 'Y'}, {'antes': 'Y', 'ahora': 'X'}], ['X'])
        self.assertEqual(fs[0].get('titulos_anteriores'), ['Y'])

    def test_un_renombre_a_nada_sigue_frenando(self):
        with self.assertRaises(SystemExit):
            armar([{'antes': 'A', 'ahora': 'Z'}], ['C'])


if __name__ == '__main__':
    unittest.main()
