"""catalogo_construir.py --comprobar (21 oct 2026): el catálogo es DERIVADO de los
festivales. Si nadie lo re-arma, el próximo --escribir arrastra archivos ajenos
(FICCALI #1218/#1219). `distintas` es lo que compara; sin red ni TMDB."""
import os, sys, tempfile, unittest
from unittest import mock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import catalogo_construir as cc


class Distintas(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.p = mock.patch.object(cc, 'REPO', self.d); self.p.start()
        os.makedirs(f'{self.d}/catalogo/obras')
        open(f'{self.d}/catalogo/obras/w_A.json', 'w').write('{"a": 1}')
        open(f'{self.d}/catalogo/obras/w_B.json', 'w').write('{"b": 1}')

    def tearDown(self):
        self.p.stop()

    def test_igual_no_reporta(self):
        out = {f'{self.d}/catalogo/obras/w_A.json': '{"a": 1}'}
        self.assertEqual(cc.distintas(out), [])

    def test_contenido_distinto_obra_nueva_y_borrada(self):
        out = {f'{self.d}/catalogo/obras/w_A.json': '{"a": 2}',      # cambió
               f'{self.d}/catalogo/obras/w_C.json': '{"c": 1}',      # nueva
               f'{self.d}/catalogo/obras/w_B.json': None}            # se borra
        self.assertEqual(cc.distintas(out), ['catalogo/obras/w_A.json', 'catalogo/obras/w_B.json',
                                             'catalogo/obras/w_C.json'])

    def test_borrar_lo_que_no_existe_no_reporta(self):
        self.assertEqual(cc.distintas({f'{self.d}/catalogo/obras/w_Z.json': None}), [])


if __name__ == '__main__':
    unittest.main()
