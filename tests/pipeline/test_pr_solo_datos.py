import importlib.util, pathlib, unittest

_p = pathlib.Path(__file__).resolve().parents[2] / 'scripts' / 'pr-solo-datos.py'
_s = importlib.util.spec_from_file_location('pr_solo_datos', _p)
g = importlib.util.module_from_spec(_s); _s.loader.exec_module(g)


class SoloDatos(unittest.TestCase):
    def test_datos_pasan(self):
        self.assertEqual(g.revisar(['festivals/staging/miradas-2026-afirmaciones.json',
                                    'pipeline/miradas-2026-verificar.py', 'docs/radar-ancla.json'], ''), [])

    def test_afiche_en_config_pasa(self):
        d = "-    keyArt:'/assets/keyart/miradas2026-v1.jpg',\n+    keyArt:'/assets/keyart/miradas2026-v2.jpg',\n"
        self.assertEqual(g.revisar(['src/config.js', 'assets/keyart/miradas2026-v2.jpg'], d), [])

    def test_otro_cambio_en_config_no_pasa(self):
        d = "+    keyArt:'/assets/keyart/x-v2.jpg',\n+    city:'Cali',\n"
        self.assertTrue(g.revisar(['src/config.js'], d))

    def test_una_lista_cortada_o_un_config_sin_diff_no_pasan(self):
        self.assertTrue(g.completo(['a'], 2, ''))
        self.assertTrue(g.completo(['src/config.js'], 1, ''))
        self.assertEqual(g.completo(['a'], 1, ''), [])

    def test_una_linea_que_empieza_por_mas_no_se_salta(self):
        self.assertTrue(g.revisar(['src/config.js'], '+++globalThis.x;'))

    def test_codigo_no_pasa(self):
        for a in ('validate.py', 'pipeline/ig_vigia.py', 'src/main.js', 'tests/unit/a.test.js', 'scripts/x.py'):
            self.assertTrue(g.revisar([a], ''), a)


if __name__ == '__main__':
    unittest.main()
