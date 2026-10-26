"""Fuentes vivas (pipeline/fuentes_vivas.py, 20 oct 2026): un festival vigente no
se arma ni se publica contra fuentes vencidas, y una descarga mala no reemplaza
la buena. Sin red: el plan, el registro y las respuestas son de mentira."""
import datetime, json, os, sys, tempfile, unittest
from unittest import mock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import fuentes_vivas as fv

AHORA = datetime.datetime(2026, 10, 20, 9, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=-5)))


class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        os.makedirs(f'{self.d}/pipeline'); os.makedirs(f'{self.d}/fuentes/fest-2026')
        self.p = mock.patch.object(fv, 'REPO', self.d); self.p.start()

    def tearDown(self):
        self.p.stop()

    def plan(self, fuentes):
        json.dump({'pasos': [], 'fuentes_vivas': fuentes}, open(f'{self.d}/pipeline/fest-2026.plan.json', 'w'))

    def bajada(self, archivo, horas):
        r = fv.registro('fest-2026')
        r[archivo] = {'cuando': (AHORA - datetime.timedelta(hours=horas)).isoformat()}
        json.dump(r, open(f'{self.d}/fuentes/fest-2026/_bajadas.json', 'w'))


class Vencidas(Base):
    def test_sin_registro_cuenta_como_vencida(self):
        self.plan([{'archivo': 'fuentes/fest-2026/a.html', 'url': 'x', 'como': 'pagina'}])
        self.assertEqual(fv.vencidas('fest-2026', AHORA), [('fuentes/fest-2026/a.html', None)])

    def test_mas_de_24_horas_vence_y_menos_no(self):
        self.plan([{'archivo': 'fuentes/fest-2026/a.html'}, {'archivo': 'fuentes/fest-2026/b.json'}])
        self.bajada('fuentes/fest-2026/a.html', 25)
        self.bajada('fuentes/fest-2026/b.json', 3)
        self.assertEqual(fv.vencidas('fest-2026', AHORA), [('fuentes/fest-2026/a.html', 25)])

    def test_max_horas_propio(self):
        self.plan([{'archivo': 'fuentes/fest-2026/a.html', 'max_horas': 2}])
        self.bajada('fuentes/fest-2026/a.html', 3)
        self.assertEqual(len(fv.vencidas('fest-2026', AHORA)), 1)


class Freno(Base):
    def test_vigente_con_vencidas_frena_con_el_comando(self):
        self.plan([{'archivo': 'fuentes/fest-2026/a.html'}])
        with mock.patch.object(fv, 'vigente', return_value=True):
            m = fv.frenar_si_vencidas('fest-2026', 'python3 pipeline/correr.py fest-2026 --bajar')
        self.assertIn('VIGENTE', m)
        self.assertIn('correr.py fest-2026 --bajar', m)

    def test_no_vigente_no_frena(self):
        self.plan([{'archivo': 'fuentes/fest-2026/a.html'}])
        with mock.patch.object(fv, 'vigente', return_value=False):
            self.assertIsNone(fv.frenar_si_vencidas('fest-2026', 'x'))

    def test_sin_fuentes_declaradas_no_frena(self):
        self.plan([])
        self.assertIsNone(fv.frenar_si_vencidas('fest-2026', 'x'))


class Descarga(Base):
    def _resp(self, cuerpo, ctype, total=None, pags=None):
        h = {'Content-Type': ctype}
        if total is not None:
            h['X-WP-Total'] = str(total); h['X-WP-TotalPages'] = str(pags)
        return (cuerpo, h)

    def test_api_incompleta_no_reemplaza(self):
        ruta = f'{self.d}/fuentes/fest-2026/api.json'
        open(ruta, 'w').write('["vieja"]')
        f = {'archivo': 'fuentes/fest-2026/api.json', 'url': 'https://x/wp-json/wp/v2/t', 'como': 'wp-json'}
        # dice 3 en total pero la única página trae 2
        with mock.patch.object(fv, '_get', return_value=self._resp(b'[1,2]', 'application/json', 3, 1)):
            with self.assertRaises(fv.FuenteMala):
                fv.bajar_una('fest-2026', f)
        self.assertEqual(open(ruta).read(), '["vieja"]')
        self.assertEqual(fv.registro('fest-2026'), {})

    def test_api_paginada_completa_se_guarda_y_se_anota(self):
        f = {'archivo': 'fuentes/fest-2026/api.json', 'url': 'https://x/wp-json/wp/v2/t', 'como': 'wp-json'}
        pags = [self._resp(b'[1,2]', 'application/json', 3, 2), self._resp(b'[3]', 'application/json', 3, 2)]
        with mock.patch.object(fv, '_get', side_effect=pags):
            fv.bajar_una('fest-2026', f)
        self.assertEqual(json.load(open(f'{self.d}/fuentes/fest-2026/api.json')), [1, 2, 3])
        self.assertIn('fuentes/fest-2026/api.json', fv.registro('fest-2026'))

    def test_pagina_sin_el_texto_esperado_no_reemplaza(self):
        # un sitio que contesta 200 con otra cosa (comodín, error de WP) no pasa
        f = {'archivo': 'fuentes/fest-2026/p.html', 'url': 'https://x/', 'como': 'pagina', 'debe_contener': 'programacion'}
        with mock.patch.object(fv, '_get', return_value=self._resp(b'<html>' + b'x' * 3000, 'text/html')):
            with self.assertRaises(fv.FuenteMala):
                fv.bajar_una('fest-2026', f)
        self.assertFalse(os.path.exists(f'{self.d}/fuentes/fest-2026/p.html'))


class Vigente(unittest.TestCase):
    def _con(self, ini, fin, hoy):
        ficha = json.dumps({'festivalStartStr': ini, 'festivalEndStr': fin})
        with mock.patch.object(fv.subprocess, 'run', return_value=mock.Mock(returncode=0, stdout=ficha)):
            return fv.vigente('fest-2026', hoy)

    def test_ventana_de_dos_dias_antes_hasta_el_fin(self):
        i, f = '2026-10-16T00:00:00', '2026-10-25T23:59:00'
        self.assertFalse(self._con(i, f, datetime.date(2026, 10, 13)))
        self.assertTrue(self._con(i, f, datetime.date(2026, 10, 14)))
        self.assertTrue(self._con(i, f, datetime.date(2026, 10, 25)))
        self.assertFalse(self._con(i, f, datetime.date(2026, 10, 26)))


if __name__ == '__main__':
    unittest.main()
