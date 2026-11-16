"""pipeline/sedes.py — el almacén de sedes (16 nov 2026)."""
import json, os, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import sedes as S

MAPS = 'https://www.google.com/maps/place/X/@4.6,-74.0,17z'


class Base(unittest.TestCase):
    def setUp(self):
        self.r = tempfile.mkdtemp()
        os.makedirs(f'{self.r}/festivals/staging')
        os.makedirs(f'{self.r}/catalogo')
        os.makedirs(f'{self.r}/pipeline')

    def geo(self, fid, d, fin='2099-12-31'):
        json.dump(d, open(f'{self.r}/festivals/staging/{fid}-venues-geo.json', 'w'), ensure_ascii=False)
        json.dump({'festival': {'festivalEndStr': fin + 'T23:59:00'}}, open(f'{self.r}/pipeline/{fid}.plan.json', 'w'))

    def unico(self):
        d = S.leer(self.r)
        self.assertEqual(len(d['sedes']), 1, d['sedes'])
        return next(iter(d['sedes'].items()))


class Almacen(Base):
    def test_mismo_lugar_en_dos_festivales_es_uno_con_su_evidencia(self):
        self.geo('a-2026', {'Cinemateca de Bogotá - Bogotá': {'lat': 4.6105, 'lng': -74.0705, '_prec': 'manual'}})
        self.geo('b-2026', {'Cinemateca de Bogotá': {'lat': 4.61051, 'lng': -74.07051, '_prec': 'nominatim'}})
        S.construir(self.r)
        sid, e = self.unico()
        self.assertTrue(sid.startswith('s_'))
        self.assertEqual((e['evidencia']['nivel'], e['festivales']), ('manual', ['a-2026', 'b-2026']))
        self.assertIn('Cinemateca de Bogotá - Bogotá', e['alias'])

    def test_el_id_no_cambia_al_reconstruir(self):
        self.geo('a-2026', {'Teatro X': {'lat': 6.0, 'lng': -75.0, '_prec': 'manual'}})
        S.construir(self.r)
        sid, _ = self.unico()
        self.geo('b-2026', {'Teatro X': {'lat': 6.00001, 'lng': -75.0}})
        S.construir(self.r)
        self.assertEqual(self.unico()[0], sid)

    def test_homonimos_de_pueblos_distintos_son_dos(self):
        self.geo('a-2026', {'Parque Principal': {'lat': 6.2343, 'lng': -75.1617}})
        self.geo('b-2026', {'Parque Principal': {'lat': 6.3776, 'lng': -75.4462}})
        self.assertEqual(len(S.construir(self.r)['sedes']), 2)

    def test_mismo_fusiona_alias_y_redirige_el_id(self):
        self.geo('a-2026', {'MAMM': {'lat': 6.2232, 'lng': -75.5741, '_prec': 'manual'}})
        self.geo('b-2026', {'Museo de Arte Moderno de Medellín': {'lat': 6.2232, 'lng': -75.5741}})
        d = S.construir(self.r)
        self.assertEqual(len(d['sedes']), 2)
        self.assertEqual(len(S.cercanos(self.r)), 1)              # a 0 m sin decidir: el guardián frena
        S.declarar('mismo', 'MAMM', 'Museo de Arte Moderno de Medellín', 'sigla', self.r)
        sid, e = self.unico()
        self.assertEqual(S.cercanos(self.r), [])
        self.assertEqual(list(S.leer(self.r)['redirecciones'].values()), [sid])
        hit = S.buscar('Museo de Arte Moderno de Medellín', (6.22, -75.57), raiz=self.r)
        self.assertEqual(hit['_matriz'], sid)

    def test_distintos_cercanos_se_declaran(self):
        self.geo('a-2026', {'Teatro Otraparte': {'lat': 6.17, 'lng': -75.59}, 'Casa Museo Otraparte': {'lat': 6.17, 'lng': -75.59}})
        S.construir(self.r)
        self.assertEqual(len(S.cercanos(self.r)), 1)
        S.declarar('distintos', 'Teatro Otraparte', 'Casa Museo Otraparte', 'la casa y su teatro', self.r)
        self.assertEqual(S.cercanos(self.r), [])
        with self.assertRaises(SystemExit):
            S.declarar('distintos', 'Teatro Otraparte', 'Casa Museo Otraparte', '', self.r)

    def test_divergencia_no_se_reparte_hasta_resolverla_con_maps(self):
        self.geo('a-2026', {'Brisas': {'lat': 3.415857, 'lng': -76.562927, '_prec': 'manual'}})
        self.geo('b-2026', {'Brisas': {'lat': 3.416991, 'lng': -76.56774, '_prec': 'manual'}})
        d = S.construir(self.r)
        self.assertEqual(len(d['_divergentes']), 1)
        self.assertIsNone(S.buscar('Brisas', (3.41, -76.56), raiz=self.r))
        sid = next(iter(d['_divergentes']))
        with self.assertRaises(SystemExit):
            S.poner_evidencia(sid, 'https://ejemplo.com/x', raiz=self.r)   # solo Google Maps
        S.poner_evidencia(sid, MAPS, (3.416991, -76.56774), self.r)
        self.assertEqual(S.leer(self.r)['_divergentes'], {})
        self.assertEqual(S.buscar('Brisas', (3.41, -76.56), raiz=self.r)['lat'], 3.416991)
        self.assertEqual([x[0] for x in S.apartados(self.r)], ['a-2026'])  # el pin viejo de a, vivo, se aparta

    def test_campus_tolera_cada_edificio(self):
        self.geo('a-2026', {'Universidad Central': {'lat': 4.607459, 'lng': -74.07, '_prec': 'manual'}})
        self.geo('b-2026', {'Universidad Central': {'lat': 4.605955, 'lng': -74.068697, '_prec': 'manual'}})
        sid = next(iter(S.construir(self.r)['_divergentes']))
        with self.assertRaises(SystemExit):
            S.marcar_campus(sid, 2000, 'no', self.r)                   # un campus no mide 2 km
        S.marcar_campus(sid, 300, 'Sala Fundadores y Auditorio Caldas', self.r)
        self.assertEqual(S.leer(self.r)['_divergentes'], {})
        self.assertEqual(S.apartados(self.r), [])

    def test_archivado_no_se_mide(self):
        self.geo('a-2026', {'Teatro X': {'lat': 6.0, 'lng': -75.0, '_prec': 'manual'}})
        S.construir(self.r)
        sid, _ = self.unico()
        S.poner_evidencia(sid, MAPS, (6.0, -75.0), self.r)
        self.geo('viejo-2025', {'Teatro X': {'lat': 6.002, 'lng': -75.0}}, fin='2025-01-01')   # ~220 m
        self.geo('vivo-2026', {'Teatro X': {'lat': 6.002, 'lng': -75.0}})
        S.construir(self.r)
        self.assertEqual([x[0] for x in S.apartados(self.r)], ['vivo-2026'])

    def test_lugar_nuevo_sin_maps_es_falta_y_la_deuda_solo_baja(self):
        self.geo('a-2026', {'Teatro X': {'lat': 6.0, 'lng': -75.0}})
        S.construir(self.r)                                           # primera vez: lo viejo es deuda
        self.assertEqual(S.sin_evidencia_nueva(self.r), [])
        self.geo('b-2026', {'Sala Nueva': {'lat': 4.0, 'lng': -74.0}})
        S.construir(self.r)
        nuevo = S.sin_evidencia_nueva(self.r)
        self.assertEqual(len(nuevo), 1)
        S.poner_evidencia(nuevo[0], MAPS, raiz=self.r)
        self.assertEqual(S.sin_evidencia_nueva(self.r), [])


class Ficha(Base):
    def test_ficha_desde_plan_publicado_y_funciones(self):
        self.geo('a-2026', {'Cinemateca de Bogotá - Bogotá': {'lat': 4.6105, 'lng': -74.0705, '_prec': 'manual'}})
        plan = {'festival': {'festivalEndStr': '2099-12-31T23:59:00', 'city': 'Bogotá',
                             'sedes': {'Cinemateca Sala 2': ['Cinemateca de Bogotá - Bogotá', 'Sala 2']}}}
        json.dump(plan, open(f'{self.r}/pipeline/a-2026.plan.json', 'w'))
        os.makedirs(f'{self.r}/festivals', exist_ok=True)
        json.dump({'venues': {'Cinemateca de Bogotá - Bogotá': {'short': 'Cinemateca', 'city': 'Bogotá',
                                                                'address': 'Cra. 3 # 19-10'}},
                   'films': [{'venue': 'Cinemateca de Bogotá - Bogotá', 'sala': 'Sala Capital'}]},
                  open(f'{self.r}/festivals/a-2026.json', 'w'), ensure_ascii=False)
        S.construir(self.r)
        sid, e = self.unico()
        self.assertEqual((e['ciudad'], e['corto'], e['address']), ('Bogotá', 'Cinemateca', 'Cra. 3 # 19-10'))
        self.assertEqual(e['salas'], ['Sala 2', 'Sala Capital'])
        self.assertIn('Cinemateca Sala 2', e['alias'])
        hit = S.buscar('Cinemateca Sala 2', (4.61, -74.07), raiz=self.r)          # la grafía cruda resuelve
        self.assertEqual((hit['_matriz'], hit['ciudad'], hit['corto']), (sid, 'Bogotá', 'Cinemateca'))

    def test_lo_fijado_a_mano_no_se_pisa(self):
        self.geo('a-2026', {'Teatro X - Cali': {'lat': 3.4, 'lng': -76.5}})
        S.construir(self.r)
        m = S.leer(self.r)
        sid = next(iter(m['sedes']))
        m['sedes'][sid]['corto'] = 'El Teatro'
        S._escribir(m, self.r)
        S.construir(self.r)
        self.assertEqual(S.leer(self.r)['sedes'][sid]['corto'], 'El Teatro')
        self.assertEqual(S.leer(self.r)['sedes'][sid]['ciudad'], 'Cali')


class Resolver(Base):
    def setUp(self):
        super().setUp()
        self.geo('viejo-2026', {'Cinemateca de Bogotá - Bogotá': {'lat': 4.6105, 'lng': -74.0705, '_prec': 'manual'},
                                'CEFE Chapinero - Bogotá': {'lat': 4.6480, 'lng': -74.0630, '_prec': 'manual'},
                                'Teatro Colsubsidio - Bogotá': {'lat': 4.6400, 'lng': -74.0700, '_prec': 'manual'}})
        os.makedirs(f'{self.r}/festivals', exist_ok=True)
        json.dump({'films': [{'venue': 'Cinemateca de Bogotá - Bogotá', 'sala': 'Sala Capital'}]},
                  open(f'{self.r}/festivals/viejo-2026.json', 'w'))
        S.construir(self.r)
        json.dump({'funciones': [{'sede': s} for s in ('Cinemateca de Bogotá', 'Cinemateca Sala Capital', 'CEFE',
                                                        'Teatro Inventado del Sur')]},
                  open(f'{self.r}/festivals/staging/nuevo-2026-crudo.json', 'w'), ensure_ascii=False)
        json.dump({'festival': {'city': 'Bogotá', 'festivalEndStr': '2099-12-31T23:59:00', 'sedes': {}}},
                  open(f'{self.r}/pipeline/nuevo-2026.plan.json', 'w'))

    def test_clasifica_y_escribe_solo_las_conocidas(self):
        r = S.resolver('nuevo-2026', self.r)
        self.assertEqual(sorted(c for c, _ in r['conocida']), ['Cinemateca Sala Capital', 'Cinemateca de Bogotá'])
        self.assertEqual([c for c, _ in r['parecida']], ['CEFE'])
        self.assertEqual([c for c, _ in r['nueva']], ['Teatro Inventado del Sur'])
        self.assertIn('google.com/maps/search', r['nueva'][0][1])
        self.assertFalse(os.path.exists(f'{self.r}/festivals/staging/nuevo-2026-venues-geo.json'))   # sin --escribir no toca
        S.resolver('nuevo-2026', self.r, escribir=True)
        plan = json.load(open(f'{self.r}/pipeline/nuevo-2026.plan.json'))['festival']['sedes']
        self.assertEqual(plan['Cinemateca Sala Capital'], ['Cinemateca de Bogotá - Bogotá', 'Sala Capital'])
        geo = json.load(open(f'{self.r}/festivals/staging/nuevo-2026-venues-geo.json'))
        self.assertEqual((geo['Cinemateca de Bogotá - Bogotá']['lat'], geo['Cinemateca de Bogotá - Bogotá']['_prec']), (4.6105, 'matriz'))
        self.assertNotIn('CEFE', plan)                                                        # la parecida no entra sola
        r2 = S.resolver('nuevo-2026', self.r)
        self.assertEqual(len(r2['ya']), 2)

    def test_aceptar_una_parecida(self):
        sid = next(s for s, e in S.leer(self.r)['sedes'].items() if e['nombre'] == 'CEFE Chapinero')
        S.resolver('nuevo-2026', self.r, escribir=True, aceptar={'CEFE': sid})
        plan = json.load(open(f'{self.r}/pipeline/nuevo-2026.plan.json'))['festival']['sedes']
        self.assertEqual(plan['CEFE'], ['CEFE Chapinero - Bogotá', ''])

    def test_ciudad_que_no_cuadra_con_el_mapa_se_quita(self):
        self.geo('multi-2026', {'Universidad Lejana': {'lat': 6.2464, 'lng': -75.5641}})
        plan = json.load(open(f'{self.r}/pipeline/multi-2026.plan.json'))
        plan['festival']['city'] = 'Bogotá'
        json.dump(plan, open(f'{self.r}/pipeline/multi-2026.plan.json', 'w'))
        m = S.construir(self.r)
        e = next(e for e in m['sedes'].values() if e['nombre'] == 'Universidad Lejana')
        self.assertNotIn('ciudad', e)
        self.assertEqual(e['_ciudad_dudosa'], 'Bogotá')


if __name__ == '__main__':
    unittest.main()
