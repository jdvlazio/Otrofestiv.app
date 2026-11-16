"""pipeline/sedes.py — la matriz de sedes (16 nov 2026)."""
import json, os, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import sedes as S


class Matriz(unittest.TestCase):
    def setUp(self):
        self.r = tempfile.mkdtemp()
        os.makedirs(f'{self.r}/festivals/staging')
        os.makedirs(f'{self.r}/catalogo')

    def geo(self, fid, d):
        json.dump(d, open(f'{self.r}/festivals/staging/{fid}-venues-geo.json', 'w'), ensure_ascii=False)

    def test_mismo_lugar_en_dos_festivales_es_uno(self):
        self.geo('a-2026', {'Cinemateca de Bogotá - Bogotá': {'lat': 4.6105, 'lng': -74.0705, '_prec': 'manual'}})
        self.geo('b-2026', {'Cinemateca de Bogotá': {'lat': 4.61051, 'lng': -74.07051, '_prec': 'nominatim'}})
        d = S.construir(self.r)
        self.assertEqual(len(d['sedes']), 1)
        e = next(iter(d['sedes'].values()))
        self.assertEqual((e['_prec'], e['festivales']), ('manual', ['a-2026', 'b-2026']))
        self.assertEqual(d['_divergentes'], {})

    def test_homonimos_de_pueblos_distintos_son_dos(self):
        self.geo('a-2026', {'Parque Principal': {'lat': 6.2343, 'lng': -75.1617}})
        self.geo('b-2026', {'Parque Principal': {'lat': 6.3776, 'lng': -75.4462}})
        self.assertEqual(len(S.construir(self.r)['sedes']), 2)

    def test_pines_que_no_coinciden_quedan_en_divergencia_y_no_se_reparten(self):
        self.geo('a-2026', {'Universidad Central': {'lat': 4.607459, 'lng': -74.07, '_prec': 'manual'}})
        self.geo('b-2026', {'Universidad Central': {'lat': 4.605955, 'lng': -74.068697, '_prec': 'manual'}})
        d = S.construir(self.r)
        self.assertEqual(len(d['_divergentes']), 1)
        self.assertIsNone(S.buscar('Universidad Central', (4.606, -74.069), raiz=self.r))
        sid = next(iter(d['_divergentes']))
        S.elegir(sid, 'b-2026', self.r)
        hit = S.buscar('Universidad Central', (4.606, -74.069), raiz=self.r)
        self.assertEqual((hit['lat'], hit['_prec']), (4.605955, 'matriz'))

    def test_buscar_por_nombre_y_cercania(self):
        self.geo('a-2026', {'Cinemateca Fontanar del Río': {'lat': 4.7561244, 'lng': -74.1110572,
                                                            '_prec': 'manual', 'address': 'Calle 146 # 138A-99'}})
        S.construir(self.r)
        hit = S.buscar('Cinemateca Fontanar del Rio - Bogotá', (4.71, -74.07), raiz=self.r)
        self.assertEqual((hit['lat'], hit['address']), (4.7561244, 'Calle 146 # 138A-99'))
        self.assertIsNone(S.buscar('Cinemateca Fontanar del Río', (6.24, -75.58), raiz=self.r))   # Medellín: otra ciudad

    def test_apartado_se_detecta(self):
        self.geo('a-2026', {'Teatro X': {'lat': 6.0, 'lng': -75.0, '_prec': 'manual'}})
        self.geo('b-2026', {'Teatro X': {'lat': 6.0, 'lng': -75.0, '_prec': 'manual'}})
        S.construir(self.r)
        self.geo('b-2026', {'Teatro X': {'lat': 6.002, 'lng': -75.0, '_prec': 'nominatim'}})   # ~220 m
        self.assertEqual([(a, c) for a, b, c, d in S.apartados(self.r)], [('b-2026', 'teatrox@6.0,-75.0')])


if __name__ == '__main__':
    unittest.main()
