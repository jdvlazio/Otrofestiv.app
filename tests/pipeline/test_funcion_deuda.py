#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C9: la deuda que solo puede bajar (docs/FUNCION.md §6 y §9). Escritos antes."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'pipeline'))
import funcion  # noqa: E402


class Excepciones(unittest.TestCase):
    def _repo(self, archivos):
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, 'pipeline'))
        for n, t in archivos.items():
            open(os.path.join(d, 'pipeline', n), 'w').write(t)
        return d

    def test_una_tabla_de_hora_cuenta(self):
        d = self._repo({'zzz-2026-crudo.py': "HORA_DEL_IG = {('a','b'): '19:30'}\n"})
        self.assertEqual(funcion.excepciones_en_scripts(d), [('zzz-2026-crudo.py', 'HORA_DEL_IG')])

    def test_una_regex_o_un_texto_no_cuentan(self):
        d = self._repo({'zzz-2026-crudo.py': "import re\nHORA = re.compile('x')\nACCESO = 'Entrada libre'\n"})
        self.assertEqual(funcion.excepciones_en_scripts(d), [])

    def test_los_verificadores_no_cuentan(self):
        d = self._repo({'zzz-2026-verificar.py': "SALA = {'a': 'b'}\n"})
        self.assertEqual(funcion.excepciones_en_scripts(d), [])

    def test_las_genericas_no_cuentan(self):
        d = self._repo({'ensamblar.py': "DURACION_ERRATA = {'a': 1}\n"})
        self.assertEqual(funcion.excepciones_en_scripts(d), [])

    def test_la_deuda_solo_baja(self):
        hoy = [('a.py', 'X'), ('b.py', 'Y')]
        self.assertEqual(funcion.comparar_deuda(hoy, [('a.py', 'X'), ('b.py', 'Y')]), ([], []))
        nuevas, saldadas = funcion.comparar_deuda(hoy + [('c.py', 'Z')], hoy)
        self.assertEqual(nuevas, [('c.py', 'Z')])
        nuevas, saldadas = funcion.comparar_deuda([('a.py', 'X')], hoy)
        self.assertEqual(saldadas, [('b.py', 'Y')])


class Entrada(unittest.TestCase):
    def test_cuenta_las_funciones_sin_entrada(self):
        d = {'films': [{'title': 'a', 'is_free': True}, {'title': 'b', 'ticket_url': 'https://x'},
                       {'title': 'c'}, {'title': 'd', 'by_invitation': True}, {'title': 'e', 'is_free': False},
                       {'title': 'f', 'online': True}, {'title': 'g', 'requires_registration': True}]}
        self.assertEqual(funcion.sin_entrada(d), ['c', 'g'])


class Conflictos(unittest.TestCase):
    def test_lista_los_conflictos_abiertos(self):
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, 'festivals', 'staging'))
        self.assertEqual(funcion.conflictos_abiertos(d), [])
        open(os.path.join(d, 'festivals', 'staging', 'zzz-2026-conflictos.json'), 'w').write('{"conflictos":[{}]}')
        self.assertEqual(funcion.conflictos_abiertos(d), ['zzz-2026'])


if __name__ == '__main__':
    unittest.main()
