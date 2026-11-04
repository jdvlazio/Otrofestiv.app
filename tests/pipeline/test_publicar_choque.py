#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dos publicaciones cruzadas (el job de main y un publicar-datos a mano) no
fallan con 409: la segunda rehace su commit sobre la punta nueva y reintenta,
sin pisar lo que publicó la otra (28 oct 2026). Repo real con origin local."""
import importlib.util
import os
import subprocess
import tempfile
import unittest
import urllib.error

AQUI = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _cargar():
    spec = importlib.util.spec_from_file_location('publicar_datos', os.path.join(AQUI, 'pipeline', 'publicar-datos.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _g(cwd, *a):
    return subprocess.run(['git', '-C', cwd, *a], check=True, capture_output=True, text=True).stdout.strip()


class Choque(unittest.TestCase):
    def setUp(self):
        t = tempfile.mkdtemp()
        self.origen, self.yo, self.otro = (os.path.join(t, n) for n in ('origen.git', 'yo', 'otro'))
        subprocess.run(['git', 'init', '-q', '--bare', '-b', 'main', self.origen], check=True)
        for d in (self.yo, self.otro):
            subprocess.run(['git', 'clone', '-q', self.origen, d], check=True, capture_output=True)
            _g(d, 'config', 'user.email', 't@t'); _g(d, 'config', 'user.name', 't')
        open(os.path.join(self.yo, 'a'), 'w').write('a')
        _g(self.yo, 'add', 'a'); _g(self.yo, 'commit', '-qm', 'base'); _g(self.yo, 'push', '-q', 'origin', 'main')
        _g(self.yo, 'push', '-q', 'origin', 'main:datos')
        self.m = _cargar()
        self.m.REPO = self.yo
        self.m.time.sleep = lambda s: None

    def _otro_publica(self, ruta):
        _g(self.otro, 'fetch', '-q', 'origin')
        _g(self.otro, 'checkout', '-q', '-B', 'datos', 'origin/datos')
        open(os.path.join(self.otro, ruta), 'w').write(ruta)
        _g(self.otro, 'add', ruta); _g(self.otro, 'commit', '-qm', ruta); _g(self.otro, 'push', '-q', 'origin', 'datos')

    def test_409_rehace_sobre_la_punta_nueva(self):
        llamadas = []
        def llamar(cuerpo):
            llamadas.append(cuerpo['sha'])
            if len(llamadas) == 1:          # la otra corrida publica justo antes de la función
                self._otro_publica('otro.json')
                raise self.m.Choque('la función respondió 409')
            return {'ok': True}
        self.m._llamar = llamar
        sha, res = self.m._publicar({'mio.json': b'{}'}, 'mio', {'festival': 'x'})
        self.assertEqual(res, {'ok': True})
        self.assertEqual(len(llamadas), 2)
        punta = _g(self.origen, 'rev-parse', 'datos')
        self.assertEqual(sha, punta)
        archivos = _g(self.origen, 'ls-tree', '--name-only', 'datos').split()
        self.assertIn('otro.json', archivos)   # no pisó a la otra
        self.assertIn('mio.json', archivos)

    def test_push_rechazado_tambien_reintenta(self):
        real = self.m._commit_en_datos
        veces = []
        def commit(archivos, mensaje):
            if not veces:                   # la otra empuja entre nuestro fetch y nuestro push
                veces.append(1)
                orig_git = self.m.git
                def git(*a, **k):
                    if a and a[0] == 'commit-tree':
                        self._otro_publica('otro.json')
                    return orig_git(*a, **k)
                self.m.git = git
                try:
                    return real(archivos, mensaje)
                finally:
                    self.m.git = orig_git
            return real(archivos, mensaje)
        self.m._commit_en_datos = commit
        self.m._llamar = lambda c: {'ok': True}
        sha, _ = self.m._publicar({'mio.json': b'{}'}, 'mio', {'festival': 'x'})
        self.assertEqual(sha, _g(self.origen, 'rev-parse', 'datos'))
        self.assertIn('otro.json', _g(self.origen, 'ls-tree', '--name-only', 'datos').split())

    def test_otro_error_no_reintenta(self):
        def llamar(cuerpo):
            raise urllib.error.HTTPError('u', 500, 'x', {}, None)
        self.m.urllib.request.urlopen = lambda *a, **k: (_ for _ in ()).throw(
            urllib.error.HTTPError('u', 500, 'x', {}, __import__('io').BytesIO(b'boom')))
        with self.assertRaises(SystemExit):
            self.m._publicar({'mio.json': b'{}'}, 'mio', {'festival': 'x'})

    def test_409_real_de_la_funcion_es_choque(self):
        import io
        self.m.urllib.request.urlopen = lambda *a, **k: (_ for _ in ()).throw(
            urllib.error.HTTPError('u', 409, 'x', {}, io.BytesIO(b'el sha no es la punta')))
        with self.assertRaises(self.m.Choque):
            self.m._llamar({'festival': 'x', 'sha': 'y'})


if __name__ == '__main__':
    unittest.main()
