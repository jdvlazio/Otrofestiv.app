import glob, json, os, sys, unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
import no_entra


def film(**k):
    return {'title': 'Una obra', 'day': '2026-11-11', 'time': '09:00', **k}


class NoEntra(unittest.TestCase):
    def test_cerrada_frena(self):
        self.assertTrue(no_entra.revisar([film(access='Solo para participantes aceptados')]))

    def test_sinopsis_no_cuenta(self):
        self.assertFalse(no_entra.revisar([film(synopsis='Un evento exclusivo en la selva')]))

    def test_fuera_por_prefijo(self):
        f = [film(title='Laboratorio Hibridaciones Convergentes')]
        self.assertTrue(no_entra.revisar(f, {'LABORATORIO HIBRIDACIONES': 'cerrado'}))

    def test_fuera_con_dia_solo_ese_dia(self):
        fuera = [{'titulo': 'Una obra', 'dia': '2026-10-01'}]
        self.assertFalse(no_entra.revisar([film()], fuera))
        self.assertTrue(no_entra.revisar([film(day='2026-10-01')], fuera))

    def test_titulo_corto_no_choca_por_prefijo(self):
        self.assertFalse(no_entra.revisar([film(title='Taller de cine')], {'Taller': 'x'}))

    def test_texto_libre_no_se_coteja(self):
        self.assertFalse(no_entra.revisar([film()], ['2026-10-03 Una obra: fuera del 16–25']))

    def test_lo_publicado_esta_limpio(self):
        errores = []
        for p in glob.glob(os.path.join(REPO, 'festivals', '*.json')):
            fest = os.path.basename(p)[:-5]
            with open(p, encoding='utf-8') as a:
                d = json.load(a)
            if isinstance(d, dict) and d.get('films'):
                errores += [f'{fest}: {e}' for e in no_entra.revisar_festival(fest, d['films'])]
        self.assertEqual(errores, [])


if __name__ == '__main__':
    unittest.main()
