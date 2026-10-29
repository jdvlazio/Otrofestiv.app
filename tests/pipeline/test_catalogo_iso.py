"""catalogo_construir._iso — «Colombia, Argentina» → ['CO', 'AR'].

Hasta el 17 oct 2026 recorría el TEXTO de banderas («🇨🇴🇦🇷») carácter por
carácter, y cada bandera son DOS letras regionales: salía ['C','O','A','R']. 1.348
obras del catálogo tenían el país partido en letras, y la herencia —con razón—
no heredaba ninguno (Ficcali, Vanguardias: «La Tinaja» sin país)."""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import catalogo_construir as cc


class Iso(unittest.TestCase):
    def test_dos_paises(self):
        self.assertEqual(cc._iso('Colombia, Argentina'), ['CO', 'AR'])

    def test_un_pais(self):
        self.assertEqual(cc._iso('Francia'), ['FR'])

    def test_nada(self):
        self.assertEqual(cc._iso(''), [])


if __name__ == '__main__':
    unittest.main()
