"""[preonboarding-completo]: un catálogo de un festival que todavía no salió no
pasa sin afiche o sin su porqué en cada obra (18 oct 2026, FICICA)."""
import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import preonboarding as P


class Pre(unittest.TestCase):
    def setUp(self):
        self.r = tempfile.mkdtemp()
        for d in ('festivals/staging', 'pipeline'):
            os.makedirs(os.path.join(self.r, d))
        self.w('festivals/staging/x-catalogo.json', {'obras': [{'titulo': 'A'}, {'titulo': 'B'}]})
        self.w('pipeline/x.plan.json', {'festival': {}})

    def w(self, p, d):
        json.dump(d, open(os.path.join(self.r, p), 'w'))

    def test_sin_enriquecido_faltan_todas(self):
        self.assertEqual(P.medir(self.r), {'x': ['A', 'B']})

    def test_con_afiche_o_porque_pasa(self):
        self.w('festivals/staging/x-catalogo-enriquecido.json', {'obras': [{'titulo': 'A', 'poster_path': '/a.jpg'}]})
        self.w('festivals/staging/x-correcciones.json', {'sin_afiche': {'B': 'no hay afiche público'}})
        self.assertEqual(P.medir(self.r), {'x': []})

    def test_afiche_recortado_cuenta_solo_si_esta_en_el_repo(self):
        os.makedirs(os.path.join(self.r, 'assets', 'x'))
        open(os.path.join(self.r, 'assets', 'x', 'a.jpg'), 'w').write('jpg')
        self.w('festivals/staging/x-catalogo.json', {'obras': [{'titulo': 'A', 'afiche': 'assets/x/a.jpg'},
                                                              {'titulo': 'B', 'afiche': 'fuentes/x/b.jpg'}]})
        self.assertEqual(P.medir(self.r), {'x': ['B']})

    def test_publicado_no_se_mide_aca(self):
        self.w('festivals/x.json', {'films': [{'title': 'A'}]})
        self.assertEqual(P.medir(self.r), {})

    def test_sin_plan_no_es_festival(self):
        os.remove(os.path.join(self.r, 'pipeline', 'x.plan.json'))
        self.assertEqual(P.medir(self.r), {})

    def test_deuda_solo_baja(self):
        self.assertEqual(P.comparar({'x': ['A']}, {}), ({'x': 1}, {}))
        self.assertEqual(P.comparar({'x': []}, {'x': 2}), ({}, {'x': 0}))


if __name__ == '__main__':
    unittest.main()
