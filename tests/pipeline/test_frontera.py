#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/frontera.sh, dueño único de la frontera código/datos (CI + candado
local, 28 oct 2026). Repo real en una carpeta temporal."""
import os
import subprocess
import tempfile
import unittest

AQUI = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SH = os.path.join(AQUI, 'scripts', 'frontera.sh')


def _g(cwd, *a):
    return subprocess.run(['git', '-C', cwd, *a], check=True, capture_output=True, text=True).stdout.strip()


class Frontera(unittest.TestCase):
    def setUp(self):
        self.r = tempfile.mkdtemp()
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        subprocess.run(['git', 'init', '-q', self.r], check=True, env=env)
        _g(self.r, 'config', 'user.email', 't@t'); _g(self.r, 'config', 'user.name', 't')
        for f in ('validate.py', 'festivals/x.json', 'src/config.js', 'src/a.js'):
            os.makedirs(os.path.dirname(os.path.join(self.r, f)) or self.r, exist_ok=True)
            open(os.path.join(self.r, f), 'w').write('0\n')
        _g(self.r, 'add', '-A'); _g(self.r, 'commit', '-qm', 'base')
        self.base = _g(self.r, 'rev-parse', 'HEAD')

    def _cambia(self, *archivos, etiqueta=False):
        for f in archivos:
            open(os.path.join(self.r, f), 'a').write('1\n')
        _g(self.r, 'commit', '-qam', 'c')
        env = {**{k: v for k, v in os.environ.items() if not k.startswith('GIT_')},
               'ETIQUETADO': 'true' if etiqueta else 'false'}
        return subprocess.run(['bash', SH, self.base, 'HEAD'], cwd=self.r, env=env,
                              capture_output=True, text=True).returncode

    def test_mezcla_frena(self):            # el caso de #1338
        self.assertEqual(self._cambia('validate.py', 'festivals/x.json'), 1)

    def test_solo_datos_pasa(self):
        self.assertEqual(self._cambia('festivals/x.json'), 0)

    def test_solo_codigo_pasa(self):
        self.assertEqual(self._cambia('src/a.js'), 0)

    def test_config_es_de_datos(self):
        self.assertEqual(self._cambia('src/config.js', 'festivals/x.json'), 0)

    def test_etiqueta_deja_pasar(self):
        self.assertEqual(self._cambia('validate.py', 'festivals/x.json', etiqueta=True), 0)


if __name__ == '__main__':
    unittest.main()
