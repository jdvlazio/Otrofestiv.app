"""pipeline/gmaps.py y su uso en sedes.py — Google Maps como única fuente de
pines (27 nov 2026). Respuestas con la forma real de Places (New) y Geocoding,
escritas a mano: corren sin red y sin clave real."""
import json, os, sys, tempfile, unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import gmaps
import sedes as S

BOG = (4.6097, -74.0817)


def lugar(pid, nombre, lat, lng, tipos=('point_of_interest', 'establishment'), dir_=''):
    return {'id': pid, 'displayName': {'text': nombre}, 'formattedAddress': dir_,
            'location': {'latitude': lat, 'longitude': lng}, 'types': list(tipos),
            'googleMapsUri': f'https://maps.google.com/?cid={pid}'}


def http_de(places=(), geo=None, detalle=None):
    def h(url, body=None, headers=None):
        if 'searchText' in url:
            return {'places': list(places)}
        if '/places/' in url:
            return detalle
        return geo or {'status': 'ZERO_RESULTS', 'results': []}
    return h


def geo_ok(lat, lng, tipo='ROOFTOP', parcial=False):
    r = {'geometry': {'location': {'lat': lat, 'lng': lng}, 'location_type': tipo},
         'formatted_address': 'Cl. 10 #5-32, Bogotá', 'place_id': 'g1'}
    if parcial:
        r['partial_match'] = True
    return {'status': 'OK', 'results': [r]}


class Clave(unittest.TestCase):
    def test_sin_clave_se_detiene_sin_adivinar(self):
        viejo = os.environ.pop('GOOGLE_MAPS_API_KEY', None)
        try:
            with self.assertRaises(SystemExit):
                gmaps.buscar_lugar('Teatro Colón', 'Bogotá', http=http_de())
        finally:
            if viejo is not None:
                os.environ['GOOGLE_MAPS_API_KEY'] = viejo


class Regla(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault('GOOGLE_MAPS_API_KEY', 'prueba')

    def cands(self, *ps):
        return gmaps.buscar_lugar('x', 'Bogotá', BOG, http=http_de(ps))

    def test_nombre_distintivo_y_ciudad(self):
        c, por = gmaps.elegir('Teatro Colón', self.cands(lugar('p1', 'Teatro Colón Bogotá', 4.5967, -74.0744)), BOG, 30000)
        self.assertEqual(c['place_id'], 'p1')

    def test_otro_lugar_con_palabras_genericas_no_entra(self):
        # «Teatro» y «Municipal» no distinguen: el Colón no es «Teatro Municipal»
        c, por = gmaps.elegir('Teatro Libre', self.cands(lugar('p1', 'Teatro Colón', 4.5967, -74.0744)), BOG, 30000)
        self.assertIsNone(c)
        self.assertIn('no comparte nombre', por)

    def test_fuera_de_la_ciudad_no_entra(self):
        c, por = gmaps.elegir('Teatro Colón', self.cands(lugar('p1', 'Teatro Colón', 6.2, -75.5)), BOG, 30000)
        self.assertIsNone(c)

    def test_un_barrio_nunca_es_una_sede(self):
        # FICMA: «Fundadores» el teatro aterrizaba en el BARRIO Fundadores
        b = lugar('p1', 'Fundadores', 4.61, -74.08, tipos=('neighborhood', 'political'))
        self.assertIsNone(gmaps.elegir('Teatro Fundadores', self.cands(b), BOG, 30000)[0])
        self.assertIsNotNone(gmaps.elegir('Teatro Fundadores', self.cands(b), BOG, 30000, barrio_ok=True)[0])

    def test_lejos_de_la_direccion_publicada_va_a_revision(self):
        c = self.cands(lugar('p1', 'Biblioteca Las Ferias', 4.6716, -74.0982))
        dirg = gmaps.geocodificar('Cra. 69J #73-29', 'Bogotá', http=http_de(geo=geo_ok(4.6838, -74.0893)))
        self.assertTrue(dirg['precisa'])
        x, por = gmaps.elegir('Biblioteca Pública Las Ferias', c, BOG, 30000, direccion=dirg)
        self.assertIsNone(x)
        self.assertIn('de la dirección publicada', por)

    def test_direccion_imprecisa_no_decide(self):
        c = self.cands(lugar('p1', 'Biblioteca Las Ferias', 4.6716, -74.0982))
        dirg = gmaps.geocodificar('Las Ferias', 'Bogotá', http=http_de(geo=geo_ok(4.6838, -74.0893, 'APPROXIMATE')))
        self.assertFalse(dirg['precisa'])
        self.assertIsNotNone(gmaps.elegir('Biblioteca Pública Las Ferias', c, BOG, 30000, direccion=dirg)[0])

    def test_ciudad_de(self):
        r = {'status': 'OK', 'results': [{'address_components': [
            {'long_name': 'La Ceja', 'types': ['locality', 'political']}]}]}
        self.assertEqual(gmaps.ciudad_de(6.03, -75.43, http=http_de(geo=r)), 'La Ceja')


class Almacen(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault('GOOGLE_MAPS_API_KEY', 'prueba')
        self.r = tempfile.mkdtemp()
        for d in ('festivals/staging', 'catalogo', 'pipeline'):
            os.makedirs(f'{self.r}/{d}')

    def geo(self, fid, d):
        json.dump(d, open(f'{self.r}/festivals/staging/{fid}-venues-geo.json', 'w'), ensure_ascii=False)
        json.dump({'festival': {'festivalEndStr': '2099-12-31T23:59:00'}}, open(f'{self.r}/pipeline/{fid}.plan.json', 'w'))

    def test_pin_de_google_entra_con_su_place_id_y_su_enlace(self):
        self.geo('a-2026', {'Teatro Colón': {'lat': 4.5967, 'lng': -74.0744, '_prec': 'maps', '_place_id': 'p1',
                                            '_maps_url': 'https://maps.google.com/?cid=p1'}})
        S.construir(self.r)
        e = next(iter(S.leer(self.r)['sedes'].values()))
        self.assertEqual((e['evidencia']['nivel'], e['evidencia']['place_id']), ('maps', 'p1'))
        self.assertTrue(e['evidencia']['url'])
        self.assertEqual(S.sin_evidencia_nueva(self.r), [])   # un pin de Google no frena

    def test_refrescar_renueva_las_vencidas_y_deja_las_frescas(self):
        self.geo('a-2026', {'Teatro Colón': {'lat': 4.5967, 'lng': -74.0744, '_prec': 'maps', '_place_id': 'p1'}})
        S.construir(self.r)
        m = S.leer(self.r)
        sid = next(iter(m['sedes']))
        m['sedes'][sid]['coords_fecha'] = '2026-10-01'
        S._escribir(m, self.r)
        r = S.refrescar(self.r, hoy=date(2026, 11, 27),
                        detalle=lambda pid: gmaps._lugar(lugar(pid, 'Teatro Colón', 4.59675, -74.0744)))
        self.assertEqual(len(r), 1)
        self.assertEqual(S.leer(self.r)['sedes'][sid]['coords_fecha'], '2026-11-27')
        self.assertEqual(S.refrescar(self.r, hoy=date(2026, 11, 28), detalle=lambda pid: 1 / 0), [])

    def test_enlazar_google_solo_con_candidato_seguro(self):
        self.geo('a-2026', {'Teatro Colón': {'lat': 4.5967, 'lng': -74.0744, '_prec': 'manual'},
                            'Casa B': {'lat': 4.55, 'lng': -74.10, '_prec': 'manual'}})
        S.construir(self.r)
        m = S.leer(self.r)
        for e in m['sedes'].values():
            e['evidencia'] = {'nivel': 'maps', 'url': 'https://www.google.com/maps/place/x'}
        S._escribir(m, self.r)
        respuestas = {'Teatro Colón': [lugar('p1', 'Teatro Colón Bogotá', 4.59675, -74.0744)],
                      'Casa B': [lugar('p2', 'Casa B', 4.5919, -74.0733)]}   # a 5 km del pin: no
        h, sin = S.enlazar_google(self.r, buscar_lugar=lambda n, c, centro, r: [gmaps._lugar(x) for x in respuestas[n]])
        self.assertEqual([n for _, n in h], ['Teatro Colón'])
        self.assertEqual([n for _, n, _ in sin], ['Casa B'])


if __name__ == '__main__':
    unittest.main()
