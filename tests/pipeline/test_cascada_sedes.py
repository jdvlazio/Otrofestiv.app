"""La cascada de sedes (27 nov 2026): almacén → Google por nombre → dirección
publicada → variantes del nombre → búsqueda WEB → persona. Sin red."""
import os, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import gmaps
import geocodificar as G

CAMI = (6.1733762, -75.608795)


def geo(lat, lng, precisa=True):
    return {'lat': lat, 'lng': lng, 'precisa': precisa, 'direccion': 'Cra. 51 #51-55, Itagüí', 'place_id': 'dir1'}


def cand(nombre, lat, lng, pid='p1'):
    return {'nombre': nombre, 'lat': lat, 'lng': lng, 'place_id': pid, 'direccion': '', 'url': 'u',
            'tipos': ['point_of_interest', 'establishment']}


class Variantes(unittest.TestCase):
    def test_quita_ciudad_y_prefijo(self):
        v = gmaps.variantes('Auditorio Juan Carlos Escobar - Itagüí')
        self.assertEqual(v[:2], ['Auditorio Juan Carlos Escobar', 'Juan Carlos Escobar'])

    def test_parte_por_comas_y_parentesis(self):
        v = gmaps.variantes('Universidad Nacional, Edificio 303 (NEA)')
        self.assertIn('Edificio 303', v)
        self.assertIn('Universidad Nacional', v)

    def test_nombre_simple_no_inventa(self):
        self.assertEqual(gmaps.variantes('Cinemateca de Bogotá'), [])

    def test_consulta_web_pide_la_direccion(self):
        q = gmaps.consultas_web('Auditorio Juan Carlos Escobar - Itagüí', 'Itagüí')
        self.assertEqual(q[0], '"Auditorio Juan Carlos Escobar" Itagüí dirección')


class Pendientes(unittest.TestCase):
    def test_sin_busqueda_web_es_paso_5_con_ella_paso_6(self):
        g = {'_provenance': {}, 'A': {'_prec': 'sin verificar', 'n': 1},
             'B': {'_prec': 'sin verificar', 'n': 1, '_web': ['busqué X en alcaldía e IG del lugar']},
             'C': {'_prec': 'maps', 'lat': 1, 'lng': 2}}
        self.assertEqual([(s, p) for s, p, _ in G.pendientes(g)], [('A', 5), ('B', 6)])


class ConDireccion(unittest.TestCase):
    def base(self):
        return {'Auditorio Juan Carlos Escobar': {'_prec': 'sin verificar', 'n': 3, '_todo': 'x', '_buscar_web': []}}

    def test_direccion_precisa_sin_ficha_queda_en_la_direccion(self):
        g = self.base()
        n = G.con_direccion(g, 'Auditorio Juan Carlos Escobar', 'Cra. 51 #51-55', 'https://itagui.gov.co/x', 'Itagüí',
                            geocodificar=lambda d, c: geo(*CAMI), buscar=lambda *a: [])
        self.assertEqual((n['lat'], n['lng'], n['_prec'], n['_place_id']), (*CAMI, 'maps', 'dir1'))
        self.assertEqual(n['_fuente'], 'https://itagui.gov.co/x')
        self.assertNotIn('_todo', n)

    def test_con_ficha_con_nombre_en_ese_punto_toma_la_ficha(self):
        g = self.base()
        n = G.con_direccion(g, 'Auditorio Juan Carlos Escobar', 'Cra. 51 #51-55', 'https://x.co', 'Itagüí',
                            geocodificar=lambda d, c: geo(*CAMI),
                            buscar=lambda *a: [cand('Auditorio Juan Carlos Escobar', 6.17338, -75.6088, 'pX')])
        self.assertEqual(n['_place_id'], 'pX')

    def test_direccion_imprecisa_no_entra(self):
        with self.assertRaises(SystemExit):
            G.con_direccion(self.base(), 'Auditorio Juan Carlos Escobar', 'Itagüí', 'https://x.co', 'Itagüí',
                            geocodificar=lambda d, c: geo(*CAMI, precisa=False), buscar=lambda *a: [])

    def test_sin_fuente_no_entra(self):
        with self.assertRaises(SystemExit):
            G.con_direccion(self.base(), 'Auditorio Juan Carlos Escobar', 'Cra. 51 #51-55', '', 'Itagüí',
                            geocodificar=lambda d, c: geo(*CAMI), buscar=lambda *a: [])


if __name__ == '__main__':
    unittest.main()
