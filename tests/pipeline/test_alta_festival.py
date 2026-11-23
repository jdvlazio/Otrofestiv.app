"""Alta de un festival en la app desde su plan (20 nov 2026, lección del Under).
Dueño: pipeline/alta-festival.py."""
import importlib.util, os, unittest

_p = os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline', 'alta-festival.py')
_spec = importlib.util.spec_from_file_location('alta_festival', _p)
alta = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(alta)

PLAN = {'name': 'Under Medellín', 'displayName': 'Under Medellín',
        'fullName': 'XXII Festival Transterritorial de Cine Underground', 'shortName': 'UNDER',
        'tagline': 'Festival Transterritorial de Cine Underground', 'city': 'Medellín', 'country': 'CO',
        'dates': '25 NOV–3 DIC', 'dates_en': 'NOV 25–DEC 3', 'year': 2026, 'timezoneOffset': '-05:00',
        'festivalStartStr': '2026-11-25T00:00:00', 'festivalEndStr': '2026-12-03T23:59:00'}


class Id(unittest.TestCase):
    def test_id_de_la_app(self):
        self.assertEqual(alta.id_app('under-2026'), 'under2026')
        self.assertEqual(alta.id_app('ficci-65'), 'ficci65')


class EntradaConfig(unittest.TestCase):
    def setUp(self):
        self.e = alta.entrada_config('under-2026', PLAN)

    def test_los_dias_salen_de_las_fechas(self):
        self.assertIn("dayKeys:['2026-11-25',", self.e)
        self.assertIn("'2026-12-03']", self.e)
        self.assertEqual(self.e.count("{k:'"), 9)                      # 25 nov – 3 dic: 9 días

    def test_rotulos_de_dia_correctos(self):
        self.assertIn("{k:'2026-11-25',d:25,lbl:'MIÉ'}", self.e)        # 25 nov 2026 es miércoles
        self.assertIn("'2026-12-01':'TUE 1'", self.e)
        self.assertIn("'2026-11-29':'Domingo 29 de noviembre'", self.e)
        self.assertIn("'2026-12-03':'Jueves 3 de diciembre'", self.e)   # cambio de mes

    def test_lo_editorial_se_copia_del_plan(self):
        self.assertIn("tagline:'Festival Transterritorial de Cine Underground'", self.e)
        self.assertIn("shortName:'UNDER'", self.e)
        self.assertIn("keyArt:'/assets/keyart/under2026.jpg'", self.e)

    def test_comillas_escapadas(self):
        e = alta.entrada_config('x-2026', {**PLAN, 'name': "L'Atalante"})
        self.assertIn("name:'L\\'Atalante'", e)


class Plan(unittest.TestCase):
    def test_sin_lo_editorial_no_escribe_la_config(self):
        import json, tempfile, shutil
        raiz = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(raiz, 'pipeline'))
            sin = {k: v for k, v in PLAN.items() if k != 'tagline'}
            json.dump({'festival': sin}, open(os.path.join(raiz, 'pipeline', 'zz-2099.plan.json'), 'w'))
            viejo = alta.REPO
            alta.REPO = raiz
            try:
                hecho, pend, _ = alta.alta('zz-2099', escribir=False)
            finally:
                alta.REPO = viejo
            self.assertTrue(any('tagline' in x for x in pend), pend)
            self.assertTrue(any('no se escribe' in x for x in pend), pend)
        finally:
            shutil.rmtree(raiz)


if __name__ == '__main__':
    unittest.main()
