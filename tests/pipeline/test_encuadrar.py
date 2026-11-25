"""Encuadrar dos veces = encuadrar una (BOGOSHORTS, 24 nov 2026)."""
import importlib.util, json, os, shutil, subprocess, sys, tempfile, unittest
P = os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline')
sys.path.insert(0, P)
spec = importlib.util.spec_from_file_location('encuadrar', os.path.join(P, 'encuadrar-posters.py'))
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)


class Memoria(unittest.TestCase):
    def setUp(self):
        self.viejo, self.d = e.REPO, tempfile.mkdtemp()
        e.REPO = self.d
        os.makedirs(os.path.join(self.d, 'festivals', 'staging'))
        self.f = os.path.join(self.d, 'x.jpg')
        with open(self.f, 'wb') as fh:
            fh.write(b'uno')

    def tearDown(self):
        e.REPO = self.viejo
        shutil.rmtree(self.d)

    def test_recuerda_los_bytes_y_un_archivo_nuevo_se_procesa(self):
        e.anotar('f', [self.f])
        self.assertEqual(e.hechos('f')['x.jpg'], e.huella(self.f))
        with open(self.f, 'wb') as fh:
            fh.write(b'dos')
        self.assertNotEqual(e.hechos('f')['x.jpg'], e.huella(self.f))

    def test_dice_cuando_se_capturo_y_no_se_mezcla_con_los_afiches(self):
        e.anotar('f', [self.f])
        with open(e.libro('f')) as fh:
            self.assertTrue(json.load(fh)['_provenance']['capturado'])
        self.assertEqual(set(e.hechos('f')), {'x.jpg'})

    def test_un_libro_viejo_sin_procedencia_la_gana_sin_perder_nada(self):
        with open(e.libro('f'), 'w') as fh:
            json.dump({'y.jpg': 'abc'}, fh)
        e.anotar('f', [self.f])
        self.assertEqual(set(e.hechos('f')), {'x.jpg', 'y.jpg'})
        with open(e.libro('f')) as fh:
            self.assertIn('_provenance', json.load(fh))

    def test_sin_afiches_nuevos_tambien_gana_procedencia_y_luego_no_se_toca(self):
        with open(e.libro('f'), 'w') as fh:
            json.dump({'y.jpg': 'abc'}, fh)
        e.anotar('f', [])
        with open(e.libro('f')) as fh:
            d = json.load(fh)
        self.assertIn('_provenance', d)
        d['_provenance']['capturado'] = '2000-01-01'
        with open(e.libro('f'), 'w') as fh:
            json.dump(d, fh)
        e.anotar('f', [])
        with open(e.libro('f')) as fh:
            self.assertEqual(json.load(fh)['_provenance']['capturado'], '2000-01-01')

    def test_anotar_no_olvida_los_de_antes(self):
        e.anotar('f', [self.f])
        g = os.path.join(self.d, 'y.jpg')
        shutil.copy(self.f, g)
        e.anotar('f', [g])
        self.assertEqual(set(e.hechos('f')), {'x.jpg', 'y.jpg'})

    @unittest.skipUnless(shutil.which('sips'), 'sips solo existe en macOS')
    def test_un_afiche_de_fondo_liso_no_se_recorta_dos_veces(self):
        import struct, zlib
        os.makedirs(os.path.join(self.d, 'assets', 'f'))
        W, H = 300, 450                                    # fondo negro con un bloque al centro
        raw = b''.join(b'\0' + b''.join(b'\xff\xff\xff' if 130 < y < 320 and 80 < x < 220 and (x // 9 + y // 9) % 2 else b'\0\0\0' for x in range(W)) for y in range(H))
        ch = lambda t, d: struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d))
        png, jpg = os.path.join(self.d, 'a.png'), os.path.join(self.d, 'assets', 'f', 'a.jpg')
        with open(png, 'wb') as fh:
            fh.write(b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0)) + ch(b'IDAT', zlib.compress(raw)) + ch(b'IEND', b''))
        subprocess.run(['sips', '-s', 'format', 'jpeg', png, '--out', jpg], capture_output=True)
        with open(os.path.join(self.d, 'b.json'), 'w') as fh:
            json.dump({'films': [{'title': 'A', 'poster': '/assets/f/a.jpg', 'posterSource': 'oficial'}]}, fh)
        argv, sys.argv = sys.argv, ['x', 'f', '--aplicar', '--desde', os.path.join(self.d, 'b.json')]
        try:
            e.main()
            uno = e.huella(jpg)
            e.main()
            self.assertEqual(e.huella(jpg), uno)
        finally:
            sys.argv = argv


if __name__ == '__main__':
    unittest.main()
