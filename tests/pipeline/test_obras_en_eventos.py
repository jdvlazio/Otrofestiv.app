"""Las obras que se proyectan dentro de un evento también son obras (24 nov 2026)."""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import catalogo

OBS = {'w_1': {'titulo_original': 'Bartolo', 'directores': ['Sergio Fernández'], 'anio': 2025, 'presentaciones': ['f-1']}}


def noche(*obras):
    return {'title': 'Noche inaugural', 'type': 'event', 'film_list': list(obras)}


class ObrasEnEventos(unittest.TestCase):
    def test_entra_la_que_trae_direccion_y_anio(self):
        a = {'title': 'Venecia', 'director': 'F. Sossai', 'year': 2025}
        self.assertEqual(catalogo.obras_de(noche(a, {'title': 'Videomapping', 'director': 'Colectivo'})), [a])

    def test_el_evento_solo_no_es_obra(self):
        self.assertEqual(catalogo.obras_de({'title': 'Charla', 'type': 'event', 'director': 'X', 'year': 2025}), [])

    def test_enlaza_la_que_el_festival_ya_lista_aunque_no_traiga_anio(self):
        o, taller = {'title': 'Bartolo', 'director': 'Sergio Fernández'}, {'title': 'Taller', 'director': 'X'}
        self.assertEqual(catalogo.enlazar({'films': [noche(o, taller)]}, 'f-1', OBS), [])
        self.assertEqual((o.get('work_id'), taller.get('work_id')), ('w_1', None))

    def test_la_nueva_con_ficha_falta(self):
        o = {'title': 'Nueva', 'director': 'Y', 'year': 2026}
        self.assertEqual(catalogo.enlazar({'films': [noche(o)]}, 'f-1', OBS), ['Nueva'])


if __name__ == '__main__':
    unittest.main()
