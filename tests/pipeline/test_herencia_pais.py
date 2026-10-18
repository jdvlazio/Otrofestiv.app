"""herencia: el PAÍS del catálogo (ISO) llega con su nombre en español, desde la
tabla generada pipeline/paises.json (18 oct 2026: Vanguardias de Ficcali, 4
cortos sin país que el catálogo sí sabía)."""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import herencia


class Pais(unittest.TestCase):
    def test_dos_paises(self):
        self.assertEqual(herencia._VALOR['pais_heredado']({'paises': ['CO', 'AR']}), 'Colombia, Argentina')

    def test_sin_paises(self):
        self.assertIsNone(herencia._VALOR['pais_heredado']({}))

    def test_codigo_desconocido_no_inventa(self):
        self.assertIsNone(herencia._VALOR['pais_heredado']({'paises': ['ZZ']}))


if __name__ == '__main__':
    unittest.main()
