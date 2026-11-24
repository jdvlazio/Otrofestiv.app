"""Un afiche por obra y cuándo uno nuevo lo reemplaza (Juan, 23 nov 2026).
Dueño: pipeline/afiches_unicos.py."""
import os
import random
import sys
import tempfile
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
try:
    import numpy  # noqa: F401
    from PIL import Image, ImageDraw
except ImportError:
    Image = None
import afiches_unicos as au


def dibujo(semilla, w=600, h=900):
    rnd = random.Random(semilla)
    im = Image.new('RGB', (600, 900), (30, 30, 60))
    d = ImageDraw.Draw(im)
    for _ in range(40):
        x, y = rnd.randint(0, 600), rnd.randint(0, 900)
        d.ellipse((x - 70, y - 70, x + 70, y + 70), fill=tuple(rnd.randint(0, 255) for _ in range(3)))
    return im.resize((w, h), Image.LANCZOS)


def lado(im, fuente='oficial', **k):
    p = tempfile.NamedTemporaryFile(suffix='.png', delete=False).name
    im.save(p)
    x = au.abrir(p)
    os.unlink(p)
    return dict(x=x, fuente=fuente, **k)


@unittest.skipIf(Image is None, 'sin PIL/numpy')
class Criterio(unittest.TestCase):
    def test_misma_imagen_se_mantiene(self):
        self.assertEqual(au.decidir(lado(dibujo(1)), lado(dibujo(1))), 'mantener')

    def test_misma_imagen_mas_grande_reemplaza(self):
        self.assertEqual(au.decidir(lado(dibujo(1, 300, 450)), lado(dibujo(1))), 'reemplazar')

    def test_un_recorte_no_reemplaza_a_la_completa(self):
        rec = dibujo(1).crop((48, 72, 552, 828)).resize((1000, 1500))
        self.assertNotEqual(au.decidir(lado(dibujo(1)), lado(rec)), 'reemplazar')

    def test_la_completa_reemplaza_al_recorte(self):
        rec = dibujo(1).crop((48, 72, 552, 828))
        self.assertEqual(au.decidir(lado(rec), lado(dibujo(1))), 'reemplazar')

    def test_otro_diseno_se_revisa(self):
        self.assertEqual(au.decidir(lado(dibujo(1)), lado(dibujo(2))), 'revisar')

    def test_lo_que_no_es_afiche_nunca_entra(self):
        self.assertEqual(au.decidir(lado(dibujo(1)), lado(dibujo(2, 1600, 900))), 'mantener')
        self.assertEqual(au.decidir(lado(dibujo(1)), lado(dibujo(2), tarjeta=True)), 'mantener')
        self.assertEqual(au.decidir(lado(dibujo(1)), lado(dibujo(2), 'editorial')), 'mantener')

    def test_un_afiche_reemplaza_al_fotograma(self):
        self.assertEqual(au.decidir(lado(dibujo(2, 1600, 900)), lado(dibujo(1))), 'reemplazar')

    def test_lo_elegido_a_mano_no_se_reemplaza_solo(self):
        self.assertEqual(au.decidir(lado(dibujo(1, 300, 450)), lado(dibujo(1)), a_mano=True), 'revisar')


class Aplicar(unittest.TestCase):
    DEC = [{'work_id': 'w_1', 'campo': 'afiche', 'valor': {'archivo': '/assets/a/x.jpg', 'veredicto': 'oficial'}, 'vistas': ['/assets/b/x.jpg']},
           {'work_id': 'w_2', 'campo': 'afiche', 'valor': {'archivo': 'https://t/y.jpg', 'veredicto': 'fotograma'}, 'vistas': ['/assets/b/y.jpg']}]

    def _d(self, w, u, **k):
        return {'films': [{'title': 'X', 'film_list': [{'title': 'X', 'work_id': w, 'poster': u, 'posterSource': 'editorial', **k}]}]}

    def test_lleva_el_elegido_con_su_fuente_y_es_idempotente(self):
        d = self._d('w_1', '/assets/b/x.jpg', posterPosition='top')
        self.assertEqual(len(au.aplicar(d, self.DEC)), 1)
        o = d['films'][0]['film_list'][0]
        self.assertEqual((o['poster'], o['posterSource'], 'posterPosition' in o), ('/assets/a/x.jpg', 'oficial', False))
        self.assertEqual(au.aplicar(d, self.DEC), [])

    def test_lo_no_comparado_lo_vacio_y_el_fotograma_no_se_tocan(self):
        for w, u in (('w_1', '/assets/c/nuevo.jpg'), ('w_1', None), ('w_2', '/assets/b/y.jpg'), ('w_9', '/assets/b/x.jpg')):
            self.assertEqual(au.aplicar(self._d(w, u), self.DEC), [])


if __name__ == '__main__':
    unittest.main()
