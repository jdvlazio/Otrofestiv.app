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


class Encontrar(Base):
    """Como se le dice al lugar (26 nov 2026): «Colombo», «Sala del Colombo», «la Tadeo»."""
    def setUp(self):
        super().setUp()
        self.geo('viejo-2026', {'Centro Colombo Americano - Medellín': {'lat': 6.2500, 'lng': -75.5626, '_prec': 'manual'},
                                'Cinemateca de Bogotá - Bogotá': {'lat': 4.6105, 'lng': -74.0705, '_prec': 'manual'},
                                'Cinemateca Fontanar del Río - Bogotá': {'lat': 4.7600, 'lng': -74.0900, '_prec': 'manual'},
                                'Universidad Jorge Tadeo Lozano - Bogotá': {'lat': 4.6060, 'lng': -74.0690, '_prec': 'manual'},
                                'Colombo - Manizales': {'lat': 5.0600, 'lng': -75.4900, '_prec': 'manual'}})
        os.makedirs(f'{self.r}/festivals', exist_ok=True)
        json.dump({'films': [{'venue': 'Centro Colombo Americano - Medellín', 'sala': 'Sala 2'},
                             {'venue': 'Centro Colombo Americano - Medellín', 'sala': 'Sala 20'},
                             {'venue': 'Centro Colombo Americano - Medellín', 'sala': 'Aula'}]},
                  open(f'{self.r}/festivals/viejo-2026.json', 'w'))
        S.construir(self.r)
        self.sid = lambda n: next(s for s, e in S.leer(self.r)['sedes'].items() if e['nombre'] == n)

    def uno(self, texto, ciudad):
        r = S.encontrar(texto, ciudad=ciudad, raiz=self.r)
        return [(x['nombre'], x['nivel'], x.get('sala'), x['firme']) for x in r]

    def test_las_formas_de_decirle_a_un_lugar(self):
        for texto in ('Colombo', 'el Colombo', 'Sala del Colombo', 'Colombo Americano'):
            r = self.uno(texto, 'Medellín')
            self.assertEqual([(x[0], x[3]) for x in r], [('Centro Colombo Americano', True)], texto)

    def test_la_sala_sale_aparte_y_entera(self):
        self.assertEqual(self.uno('Colombo Americano sala 2', 'Medellín'), [('Centro Colombo Americano', 'sin ciudad', 'Sala 2', True)])
        self.assertEqual(self.uno('Colombo Americano sala 20', 'Medellín')[0][2], 'Sala 20')    # «sala 2» no se come «sala 20»
        self.assertIsNone(self.uno('Colombo Americano sala 7', 'Medellín')[0][2])               # sala que el lugar no conoce
        self.assertEqual(self.uno('Colombo Americano Aula', 'Medellín')[0][2], 'Aula')
        self.assertFalse([x for x in self.uno('Colombo Paula', 'Medellín') if x[2]])             # «aula» dentro de otra palabra no es la sala

    def test_la_ciudad_acota_y_no_cruza(self):
        self.assertEqual([x[0] for x in self.uno('Colombo', 'Manizales')], ['Colombo'])
        self.assertEqual(self.uno('Colombo', 'Bogotá'), [])

    def test_dos_candidatos_del_mismo_peso_no_son_firmes(self):
        self.geo('otro-2026', {'Cinemateca Sur - Bogotá': {'lat': 4.5600, 'lng': -74.1300, '_prec': 'manual'}})
        S.construir(self.r)
        r = self.uno('Cinemateca', 'Bogotá')
        self.assertEqual(r[0], ('Cinemateca de Bogotá', 'sin ciudad', None, True))      # quitando la ciudad, es ese
        self.assertEqual(sorted(x[0] for x in r[1:]), ['Cinemateca Fontanar del Río', 'Cinemateca Sur'])
        r = self.uno('la Cinemateca del Río', 'Bogotá')
        self.assertEqual([(x[0], x[3]) for x in r][:1], [('Cinemateca Fontanar del Río', True)])
        self.geo('cali-2026', {'Cine Norte Azul - Cali': {'lat': 3.4500, 'lng': -76.5300, '_prec': 'manual'},
                               'Cine Norte Verde - Cali': {'lat': 3.4700, 'lng': -76.5200, '_prec': 'manual'}})
        S.construir(self.r)
        r = self.uno('Norte', 'Cali')
        self.assertEqual((len(r), [x[1] for x in r], any(x[3] for x in r)), (2, ['contenida', 'contenida'], False))

    def test_una_palabra_corta_o_vacia_no_encuentra(self):
        self.assertEqual(self.uno('la sala del centro', 'Medellín'), [])
        self.assertEqual(self.uno('Río', 'Bogotá'), [])                                   # 3 letras sola: demasiado poco

    def test_parecida_es_pista_nunca_firme(self):
        r = self.uno('Universidad Tadeo Lozanno', 'Bogotá')
        self.assertEqual([(x[0], x[1], x[3]) for x in r], [('Universidad Jorge Tadeo Lozano', 'parecida', False)])

    def test_nombrar_guarda_la_variante_y_sobrevive_al_reconstruir(self):
        sid = self.sid('Universidad Jorge Tadeo Lozano')
        self.assertIsNone(S.buscar('Utadeo', (4.606, -74.069), raiz=self.r))
        S.nombrar(sid, 'Utadeo', 'así se firma la universidad', self.r)
        S.construir(self.r)
        self.assertEqual(S.buscar('Utadeo', (4.606, -74.069), raiz=self.r)['_matriz'], sid)
        self.assertEqual(S.leer(self.r)['decisiones']['nombrado'], [[sid, 'Utadeo', 'así se firma la universidad']])

    def test_nombrar_no_roba_el_nombre_de_un_vecino_ni_va_sin_motivo(self):
        sid = self.sid('Cinemateca Fontanar del Río')
        with self.assertRaises(SystemExit):
            S.nombrar(sid, 'Cinemateca de Bogotá', 'x', self.r)
        with self.assertRaises(SystemExit):
            S.nombrar(sid, 'Fontanar', '', self.r)
        with self.assertRaises(SystemExit):
            S.nombrar('s_noexiste', 'Fontanar', 'x', self.r)

    def test_resolver_propone_con_sala_y_al_aceptar_la_escribe(self):
        json.dump({'funciones': [{'sede': 'Colombo sala 2'}]}, open(f'{self.r}/festivals/staging/nuevo-2026-crudo.json', 'w'))
        json.dump({'festival': {'city': 'Medellín', 'festivalEndStr': '2099-12-31T23:59:00', 'sedes': {}}},
                  open(f'{self.r}/pipeline/nuevo-2026.plan.json', 'w'))
        r = S.resolver('nuevo-2026', self.r)
        self.assertEqual((r['conocida'], [c for c, _ in r['parecida']]), ([], ['Colombo sala 2']))   # no entra sola
        self.assertEqual(r['parecida'][0][1][0][2], 'Centro Colombo Americano / Sala 2')
        S.resolver('nuevo-2026', self.r, escribir=True, aceptar={'Colombo sala 2': self.sid('Centro Colombo Americano')})
        plan = json.load(open(f'{self.r}/pipeline/nuevo-2026.plan.json'))['festival']['sedes']
        self.assertEqual(plan['Colombo sala 2'], ['Centro Colombo Americano - Medellín', 'Sala 2'])


class Corto(Base):
    """Un lugar, un nombre en la app (fase 2, 26 nov 2026)."""
    def setUp(self):
        super().setUp()
        self.geo('a-2026', {'Museo de Arte Moderno de Medellín - Medellín': {'lat': 6.2241, 'lng': -75.5734, '_prec': 'manual'}})
        S.construir(self.r)
        S.enlazar(self.r)
        self.sid = next(iter(S.leer(self.r)['sedes']))

    def test_fijar_guarda_motivo_y_deja_el_viejo_como_variante(self):
        S._escribir({**S.leer(self.r), 'sedes': {self.sid: {**S.leer(self.r)['sedes'][self.sid], 'corto': 'Cine MAMM'}}}, self.r)
        e = S.fijar_corto(self.sid, 'MAMM', 'así lo conoce la gente', self.r, fecha='2026-11-26')
        self.assertEqual((e['corto'], e['corto_decidido']['por_que']), ('MAMM', 'así lo conoce la gente'))
        self.assertIn('Cine MAMM', e['alias'])
        S.construir(self.r)
        self.assertEqual(S.leer(self.r)['sedes'][self.sid]['corto'], 'MAMM')          # reconstruir no lo pisa
        self.assertEqual(S.encontrar('Cine MAMM', ciudad='Medellín', raiz=self.r)[0]['sid'], self.sid)

    def test_sin_motivo_o_sin_nombre_no(self):
        for txt, pq in (('MAMM', ''), ('  ', 'x')):
            with self.assertRaises(SystemExit):
                S.fijar_corto(self.sid, txt, pq, self.r)
        with self.assertRaises(SystemExit):
            S.fijar_corto('s_noexiste', 'MAMM', 'x', self.r)

    def test_ensamblar_publica_el_decidido_y_el_guardian_ve_el_distinto(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
        import ensamblar
        g = json.load(open(f'{self.r}/festivals/staging/a-2026-venues-geo.json'))['Museo de Arte Moderno de Medellín - Medellín']
        json.dump({'venues': {'Museo de Arte Moderno de Medellín - Medellín': {'short': 'Museo de Arte Moderno de Medellín'}}},
                  open(f'{self.r}/festivals/a-2026.json', 'w'))
        self.assertEqual(S.cortos_distintos(self.r), [])                                    # sin decisión, nada que avisar
        S.fijar_corto(self.sid, 'MAMM', 'x', self.r)
        self.assertEqual(S.cortos_distintos(self.r), [('a-2026', 'Museo de Arte Moderno de Medellín - Medellín',
                                                        'Museo de Arte Moderno de Medellín', 'MAMM')])
        orig = S.REPO
        try:
            S.REPO = self.r
            S.lugar.__defaults__ = (self.r, None)
            self.assertEqual(ensamblar._desde_almacen(g)['short'], 'MAMM')
        finally:
            S.REPO = orig
            S.lugar.__defaults__ = (orig, None)


class Normalizar(Base):
    def test_salas_compuestas_fuera_y_variantes_juntas(self):
        e = {'nombre': 'MAMM', 'corto': 'MAMM'}
        canon, var = S.normalizar_salas({'Teatro MAMM': 5, 'Teatro': 1, 'teatro': 1, 'Salas 2, 3 y Capital': 2,
                                         'Laboratorios 1 y 2': 1, 'Salón Montreal, 3.er piso': 1, 'Salón Montreal': 3}, e)
        self.assertEqual(canon, ['Salón Montreal', 'Teatro'])                 # sin el nombre del lugar dentro
        self.assertEqual(var, {'Salón Montreal, 3.er piso': 'Salón Montreal', 'Teatro MAMM': 'Teatro', 'teatro': 'Teatro'})

    def test_ciudad_que_no_es_ciudad(self):
        self.assertIsNone(S.limpia_ciudad('Universidad Nacional'))
        self.assertEqual(S.limpia_ciudad('Perímetro Urbano Santa Marta'), 'Santa Marta')

    def test_completar_ciudades_vecino_o_reverso(self):
        self.geo('a-2026', {'Teatro A - Manizales': {'lat': 5.068, 'lng': -75.517},
                            'Plaza B': {'lat': 5.0685, 'lng': -75.5175},
                            'Finca Lejana': {'lat': 5.3, 'lng': -75.9}})
        S.construir(self.r)
        hechas = {n: (c, f) for n, c, f in S.completar_ciudades(self.r, reverso=lambda a, b: 'Perímetro Urbano Neira')}
        self.assertEqual(hechas['Plaza B'][0], 'Manizales')
        self.assertIn('vecino', hechas['Plaza B'][1])
        self.assertEqual(hechas['Finca Lejana'], ('Neira', 'Nominatim reverso'))
        S.construir(self.r)                                                    # reconstruir no la borra
        self.assertEqual(next(e for e in S.leer(self.r)['sedes'].values() if e['nombre'] == 'Plaza B')['ciudad'], 'Manizales')


class Enlazar(Base):
    def test_enlaza_y_ensamblar_toma_el_pin_del_almacen(self):
        self.geo('a-2026', {'Brisas - Cali': {'lat': 3.415857, 'lng': -76.562927, '_prec': 'manual'}})
        S.construir(self.r)
        sid, _ = self.unico()
        S.poner_evidencia(sid, MAPS, (3.416991, -76.56774), self.r)
        self.assertEqual([x[1] for x in S.sin_enlace(self.r)], ['Brisas - Cali'])
        self.assertEqual(S.enlazar(self.r), {'a-2026': 1})
        self.assertEqual(S.sin_enlace(self.r), [])
        g = json.load(open(f'{self.r}/festivals/staging/a-2026-venues-geo.json'))['Brisas - Cali']
        self.assertEqual(g['_matriz'], sid)
        self.assertEqual(S.lugar(sid, self.r)['lat'], 3.416991)       # el que ensamblar.py usa

    def test_lugar_sigue_las_redirecciones(self):
        self.geo('a-2026', {'MAMM': {'lat': 6.2232, 'lng': -75.5741, '_prec': 'manual'}})
        self.geo('b-2026', {'Museo de Arte Moderno de Medellín': {'lat': 6.2232, 'lng': -75.5741}})
        viejos = list(S.construir(self.r)['sedes'])
        S.declarar('mismo', 'MAMM', 'Museo de Arte Moderno de Medellín', 'sigla', self.r)
        for v in viejos:
            self.assertEqual(S.lugar(v, self.r)['nombre'], 'MAMM')


class EnlaceManda(Base):
    def test_maps_mueve_lejos_y_no_se_duplica(self):
        self.geo('a-2026', {'Antimateria Libros y Café - Medellín': {'lat': 6.20062, 'lng': -75.56368, '_prec': 'aproximado'}})
        self.geo('b-2026', {'Librería Antimateria': {'lat': 6.2514371, 'lng': -75.5911408, '_prec': 'manual'}})
        d = S.construir(self.r)
        S.enlazar(self.r)
        sa = next(s for s, e in d['sedes'].items() if e['nombre'].startswith('Antimateria'))
        S.poner_evidencia(sa, MAPS, (6.2514371, -75.5911408), self.r)       # Maps lo mueve 6,4 km
        S.declarar('mismo', 'Antimateria Libros y Café', 'Librería Antimateria', 'mismo local', self.r)
        m = S.leer(self.r)
        self.assertEqual(len(m['sedes']), 1, m['sedes'])
        self.assertEqual(S.cercanos(self.r), [])
        e = next(iter(m['sedes'].values()))
        self.assertEqual(e['lat'], 6.2514371)
        self.assertEqual(e['festivales'], ['a-2026', 'b-2026'])


if __name__ == '__main__':
    unittest.main()
