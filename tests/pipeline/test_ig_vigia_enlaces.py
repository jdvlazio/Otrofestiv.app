"""pipeline/ig_vigia.py: las URLs escritas en el pie de un post entran al
inventario de fuentes (festivals/staging/<fid>-fuentes.json) como sin-revisar.
Caso real: @bogoshorts DfsqgASTGnw, 14 nov 2026 — la boletería se perdió."""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import fuentes_descubrir as fd  # noqa: E402
import ig_vigia as v  # noqa: E402

PIE = ('Catálogo: bit.ly/catalogo24bogo · Programación https://bit.ly/prog24. '
       'Boletería 24° BOGOSHORTS Cinemateca de Bogotá 👉 bit.ly/bole24, '
       'otra vez: https://bit.ly/prog24 — escríbenos a hola@bogoshorts.com')
REDIR = {'https://bit.ly/catalogo24bogo': 'https://bogoshorts.com/catalogo.pdf',
         'https://bit.ly/prog24': 'https://bogoshorts.com/programacion/?utm_source=ig',
         'https://bit.ly/bole24': 'https://cinematecadebogota.gov.co/agenda/11?evento=24'}
POST = 'https://www.instagram.com/p/DfsqgASTGnw/'


class Extraer(unittest.TestCase):
    def test_bitly_con_y_sin_esquema(self):
        self.assertEqual(v.extraer_urls(PIE), ['https://bit.ly/catalogo24bogo', 'https://bit.ly/prog24',
                                               'https://bit.ly/bole24'])

    def test_correo_no_es_url(self):
        self.assertEqual(v.extraer_urls('escríbenos a hola@bogoshorts.com'), [])

    def test_fid(self):
        self.assertEqual(v.fid_inventario('bogoshorts2026'), 'bogoshorts-2026')
        self.assertEqual(v.fid_inventario('bogoshorts-2026'), 'bogoshorts-2026')


class Registrar(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.p = mock.patch.object(fd, 'ruta', lambda f: os.path.join(self.tmp, f'{f}-fuentes.json'))
        self.p.start()
        self.addCleanup(self.p.stop)

    def inventario(self, items=None):
        json.dump({'_provenance': {}, 'raices': {'web': 'https://bogoshorts.com'}, 'items': items or {}},
                  open(fd.ruta('bogoshorts-2026'), 'w'))

    def leer(self):
        return json.load(open(fd.ruta('bogoshorts-2026')))['items']

    def test_resuelve_y_registra_sin_revisar(self):
        self.inventario()
        nuevas = v.registrar_enlaces('bogoshorts2026', POST, PIE, resolver=REDIR.get, t='2026-11-14T10:00')
        it = self.leer()
        bole = 'https://cinematecadebogota.gov.co/agenda/11?evento=24'
        self.assertIn(bole, nuevas)
        self.assertEqual(it[bole]['estado'], 'sin-revisar')
        self.assertEqual(it[bole]['visto_en'], POST)
        self.assertEqual(it[bole]['primera_vez'], '2026-11-14T10:00')
        self.assertEqual(it['https://bogoshorts.com/catalogo.pdf']['tipo'], 'pdf')
        self.assertEqual(len(it), 3)   # prog24 dos veces en el pie → una sola, sin utm

    def test_dedupe_por_url_final(self):
        self.inventario()
        nuevas = v.registrar_enlaces('bogoshorts2026', POST, 'bit.ly/a https://bit.ly/b',
                                     resolver=lambda u: 'https://x.org/misma/', t='t')
        self.assertEqual(nuevas, ['https://x.org/misma'])

    def test_no_readmite_inventariada_ni_revisada(self):
        self.inventario({'https://bogoshorts.com/catalogo.pdf': {'tipo': 'pdf', 'estado': 'descartada', '_por_que': 'viejo'},
                         'https://bogoshorts.com/programacion': {'tipo': 'pagina-programa', 'estado': 'usada'}})
        nuevas = v.registrar_enlaces('bogoshorts2026', POST, PIE, resolver=REDIR.get, t='t')
        self.assertEqual(nuevas, ['https://cinematecadebogota.gov.co/agenda/11?evento=24'])
        self.assertEqual(self.leer()['https://bogoshorts.com/catalogo.pdf']['estado'], 'descartada')
        self.assertEqual(v.registrar_enlaces('bogoshorts2026', POST, PIE, resolver=REDIR.get, t='t'), [])

    def test_resolucion_fallida_guarda_tal_cual(self):
        self.inventario()
        with mock.patch('urllib.request.urlopen', side_effect=OSError('sin red')):
            nuevas = v.registrar_enlaces('bogoshorts2026', POST, 'bit.ly/zz', t='t')
        self.assertEqual(nuevas, ['https://bit.ly/zz'])

    def test_sin_inventario_no_lo_crea(self):
        inf = {}
        with mock.patch.object(v, 'resolver', REDIR.get):
            v.anotar_enlaces(inf, ['otro2026'], POST, PIE)
        self.assertFalse(os.path.exists(fd.ruta('otro-2026')))
        self.assertEqual(len(inf['ENLACES_SIN_INVENTARIO']['otro2026']), 3)

    def test_informe_lista_fuentes_nuevas(self):
        self.inventario()
        inf = {}
        with mock.patch('urllib.request.urlopen', side_effect=OSError('sin red')):
            v.anotar_enlaces(inf, ['bogoshorts2026'], POST, 'bit.ly/zz')
        self.assertEqual(inf['FUENTES_NUEVAS'], {'bogoshorts-2026': ['https://bit.ly/zz']})


if __name__ == '__main__':
    unittest.main()
