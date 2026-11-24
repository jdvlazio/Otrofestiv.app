"""pipeline/titulos.py y catalogo.reconocer: dobles apellidos (24 nov 2026)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import catalogo as c  # noqa: E402
import titulos as t  # noqa: E402


def o(titulo, *dirs):
    return {'titulo_original': titulo, 'directores': list(dirs), 'presentaciones': ['x-2026']}


OBS = {'a': o('Aitana', 'Isabella Cárdenas'), 'b': o('Animero: son de la muerte', 'Nadine Holguín'),
       'r': o('Refracción', 'Otra Persona'), 's': o('Suelo', 'Eduar Yosniel Pájaro')}


class Titulos(unittest.TestCase):
    def test_doble_apellido_es_la_misma_persona(self):
        self.assertEqual(c.reconocer(OBS, 'Aitana', 'Isabella Cárdenas Marín')[0], 'a')
        self.assertEqual(c.reconocer(OBS, 'Suelo', 'Eduar Yosniel Pájaro Peña')[0], 's')

    def test_no_basta_el_nombre_sin_apellido(self):
        for d in ('Isabella', 'Isabella Marín', 'Laura Cárdenas Marín', 'Isabella Gómez Marín', 'Muestra'):
            self.assertIsNone(c.reconocer(OBS, 'Aitana', d)[0], d)

    def test_el_homonimo_es_candidata_y_no_se_hereda(self):
        r = t.clasificar(OBS, [{'titulo': 'Refracción', 'director': 'Isabella Palacio Mesa'}])
        self.assertEqual(r['candidata'], [('Refracción', [('r', 'mismo título')])])

    def test_titulo_parecido_se_pregunta(self):
        r = t.clasificar(OBS, [{'titulo': 'Animero', 'director': 'Nadine Holguín Urrego'}])
        self.assertEqual(r['candidata'][0][1][0][0], 'b')

    def test_nueva(self):
        self.assertEqual(t.clasificar(OBS, [{'titulo': 'Persiguiendo sueños', 'director': 'Chhamber y Lexx'}])['nueva'],
                         ['Persiguiendo sueños'])


if __name__ == '__main__':
    unittest.main()
