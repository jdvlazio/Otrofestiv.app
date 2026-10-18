#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C9: el informe de lo que decidió el modelo (docs/FUNCION.md §9). Escrito antes."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'pipeline'))
import funcion  # noqa: E402

PRIN = {'tipo': 'festival-web', 'fecha': '2026-09-26', 'url': 'https://festival.example/p'}


def f(**proc):
    return {'title': 'Hiperrealidad', 'day': '2026-10-23', 'time': '19:00', 'venue': 'Cine - Bogotá', '_fid': 'f_1',
            'sala': 'Sala 2', 'is_free': False, '_procedencia': {'day': PRIN, 'time': PRIN, **proc}}


class Informe(unittest.TestCase):
    def test_lista_lo_que_no_viene_de_la_fuente_principal(self):
        filas = funcion.informe([f(sala={'tipo': 'sala', 'fecha': '2026-10-15', 'url': 'https://sala.example/x'})], PRIN)
        self.assertEqual([(x['casilla'], x['tipo']) for x in filas], [('sala', 'sala')])
        self.assertEqual(filas[0]['valor'], 'Sala 2')

    def test_supuestos_y_estimados_aparecen(self):
        filas = funcion.informe([f(entrada={'tipo': 'regla', 'marca': 'supuesto', 'valor': 'boleta'})], PRIN)
        self.assertEqual(filas[0]['marca'], 'supuesto')

    def test_lo_de_la_fuente_principal_no_aparece(self):
        self.assertEqual(funcion.informe([f()], PRIN), [])

    def test_texto_legible(self):
        txt = funcion.informe_texto([f(sala={'tipo': 'sala', 'fecha': '2026-10-15', 'url': 'https://sala.example/x'})], PRIN)
        self.assertIn('Hiperrealidad', txt)
        self.assertIn('sala', txt)
        self.assertIn('https://sala.example/x', txt)


if __name__ == '__main__':
    unittest.main()
