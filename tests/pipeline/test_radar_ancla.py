"""El ancla del radar (docs/radar-ancla.json) es la fuente única del mapa de
festivales (28 oct 2026). Falla si se desincroniza: un festival de
FESTIVAL_CONFIG que no está en el ancla, un issue label:radar ABIERTO que no
está en el ancla, o un festival repetido (clave, id_config o issue en dos
entradas). La parte de issues necesita `gh` autenticado; sin él, se salta."""
import json, os, re, shutil, subprocess, unittest

RAIZ = os.path.join(os.path.dirname(__file__), '..', '..')
ANCLA = json.load(open(os.path.join(RAIZ, 'docs', 'radar-ancla.json')))['festivales']
CONFIG = re.findall(r"^\s{2}'([a-z0-9]+)'\s*:", open(os.path.join(RAIZ, 'src', 'config.js')).read(), re.M)
ESTADOS = {'en_app', 'radar', 'pasado_2026', 'descartado'}


def repetidos(valores):
    vistos, rep = set(), set()
    for v in valores:
        (rep if v in vistos else vistos).add(v)
    return sorted(rep)


class Ancla(unittest.TestCase):
    def test_config_esta_en_el_ancla(self):
        en_ancla = {c for e in ANCLA for c in (e.get('id_config') or [])}
        self.assertTrue(CONFIG, 'no se leyó FESTIVAL_CONFIG')
        self.assertEqual(sorted(set(CONFIG) - en_ancla), [], 'festivales de FESTIVAL_CONFIG sin entrada en docs/radar-ancla.json')

    def test_sin_duplicados(self):
        self.assertEqual(repetidos(e['clave'] for e in ANCLA), [], 'clave repetida')
        self.assertEqual(repetidos(c for e in ANCLA for c in (e.get('id_config') or [])), [], 'id_config en dos entradas')
        self.assertEqual(repetidos(n for e in ANCLA for n in (e.get('issue') or [])), [], 'issue en dos entradas')
        self.assertEqual(repetidos(re.sub(r'\W', '', e['nombre'].lower()) for e in ANCLA), [], 'nombre repetido')

    def test_estado_coherente(self):
        for e in ANCLA:
            self.assertIn(e['estado'], ESTADOS, e['clave'])
            self.assertEqual(e['estado'] == 'en_app', bool(e.get('id_config')), f"{e['clave']}: en_app ⇔ id_config")

    def test_issue_radar_abierto_esta_en_el_ancla(self):
        if not shutil.which('gh'):
            self.skipTest('sin gh')
        r = subprocess.run(['gh', 'issue', 'list', '-l', 'radar', '-s', 'open', '-L', '500', '--json', 'number,title'],
                           capture_output=True, text=True, cwd=RAIZ, timeout=60)
        if r.returncode:
            self.skipTest('gh sin sesión o sin red')
        abiertos = {i['number'] for i in json.loads(r.stdout) if i['title'].startswith('RADAR:')}
        en_ancla = {n for e in ANCLA for n in (e.get('issue') or [])}
        self.assertEqual(sorted(abiertos - en_ancla), [], 'issues label:radar abiertos sin entrada en docs/radar-ancla.json')


if __name__ == '__main__':
    unittest.main()
