#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Un build que viene de una corrida FALLIDA no se publica (16 oct 2026: dos
veces se publicó en local un build cuyo verificador había fallado). Escrito antes."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'pipeline'))
import lib  # noqa: E402


class Sello(unittest.TestCase):
    def setUp(self):
        self.r = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.r, 'festivals', 'staging'))
        os.makedirs(os.path.join(self.r, 'pipeline'))
        json.dump({'pasos': [{'cmd': 'a'}, {'cmd': 'b'}]}, open(os.path.join(self.r, 'pipeline', 'zzz-2026.plan.json'), 'w'))
        json.dump({'films': []}, open(os.path.join(self.r, 'festivals', 'staging', 'zzz-2026-build.json'), 'w'))
        lib.sellar_build('zzz-2026', 1, 'a', repo=self.r)

    def build(self):
        return json.load(open(os.path.join(self.r, 'festivals', 'staging', 'zzz-2026-build.json')))

    def test_sellado_es_valido(self):
        self.assertTrue(lib.sello_valido('zzz-2026', self.build(), repo=self.r)[0])

    def test_un_paso_fallido_despues_del_sello_lo_invalida(self):
        lib.marcar_fallo('zzz-2026', 2, 'b', repo=self.r)
        ok, motivo = lib.sello_valido('zzz-2026', self.build(), repo=self.r)
        self.assertFalse(ok)
        self.assertIn('paso 2', motivo)

    def test_repetir_el_paso_con_exito_lo_limpia(self):
        lib.marcar_fallo('zzz-2026', 2, 'b', repo=self.r)
        lib.limpiar_fallo('zzz-2026', 2, repo=self.r)
        self.assertTrue(lib.sello_valido('zzz-2026', self.build(), repo=self.r)[0])

    def test_otro_paso_con_exito_no_limpia_el_fallo(self):
        lib.marcar_fallo('zzz-2026', 2, 'b', repo=self.r)
        lib.limpiar_fallo('zzz-2026', 1, repo=self.r)
        self.assertFalse(lib.sello_valido('zzz-2026', self.build(), repo=self.r)[0])

    def test_un_sello_nuevo_no_borra_un_fallo_posterior(self):
        # paso 2 falla; correr --paso 1 vuelve a escribir el build: el fallo del 2 sigue
        lib.marcar_fallo('zzz-2026', 2, 'b', repo=self.r)
        lib.sellar_build('zzz-2026', 1, 'a', repo=self.r)
        self.assertFalse(lib.sello_valido('zzz-2026', self.build(), repo=self.r)[0])


if __name__ == '__main__':
    unittest.main()
