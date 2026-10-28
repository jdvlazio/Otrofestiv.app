#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""El camino corto (pipeline/corto.py, 28 oct 2026): arranca en el primer paso
que lee las afirmaciones y se salta lo pesado; el diff nombra lo que cambia."""
import importlib.util
import os
import unittest

AQUI = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_s = importlib.util.spec_from_file_location('corto', os.path.join(AQUI, 'pipeline', 'corto.py'))
corto = importlib.util.module_from_spec(_s)
_s.loader.exec_module(corto)

PASOS = [{'cmd': f'python3 pipeline/{n}.py x'} for n in
         ('radar', 'x-catalogo', 'enriquecer_catalogo', 'x-crudo', 'enriquecer', 'ensamblar', 'x-verificar')]


class PasoInicial(unittest.TestCase):
    def test_primer_paso_que_lee_afirmaciones(self):
        leer = lambda r: 'afirmaciones' if r.endswith(('x-crudo.py', 'ensamblar.py')) else ''
        self.assertEqual(corto.paso_inicial(PASOS, leer), 4)

    def test_sin_lector_arranca_en_ensamblar(self):
        self.assertEqual(corto.paso_inicial(PASOS, lambda r: ''), 6)

    def test_sin_ensamblar_no_hay_camino_corto(self):
        self.assertIsNone(corto.paso_inicial(PASOS[:5], lambda r: ''))


class Cambios(unittest.TestCase):
    A = {'films': [{'id': 'a', 'time': '14:00'}, {'id': 'b', 'time': '16:00'}]}

    def test_hora_cambiada(self):
        d = {'films': [{'id': 'a', 'time': '10:00'}, {'id': 'b', 'time': '16:00'}]}
        cs = corto.cambios(self.A, d)
        self.assertEqual([(c[0], c[2]) for c in cs], [('~', ['time'])])

    def test_entra_y_sale(self):
        d = {'films': [{'id': 'a', 'time': '14:00'}, {'id': 'c', 'time': '18:00'}]}
        self.assertEqual(sorted(c[0] for c in corto.cambios(self.A, d)), ['+', '−'])

    def test_igual_no_cambia(self):
        self.assertEqual(corto.cambios(self.A, self.A), [])


if __name__ == '__main__':
    unittest.main()
