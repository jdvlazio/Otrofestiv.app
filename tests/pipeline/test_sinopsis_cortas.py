"""La sinopsis corta: lo que el código mide y quién la verifica (Juan, 23 nov 2026)."""
import copy
import os
import sys
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import sinopsis_cortas as sc

O = ('Chena, de 26 años, se une cada año a la diáspora de campesinos que recogen café por Colombia. Viajar y trabajar '
     'son la base de su autonomía. Sus dos hijos esperan en Pasto.')
C = 'Cada año, Chena, de 26 años, recorre Colombia recogiendo café: en ese viaje está su autonomía.'
D = {'work_id': 'w1', 'campo': 'sinopsis.es', 'titulo': 'Andariega', 'valor': C, 'original': O,
     'sintesis': {'redacta': 'a', 'verifica': 'b', 'veredicto': 'fiel', 'huella': sc.huella(O, C)}}


class Revisar(unittest.TestCase):
    def test_buena(self):
        self.assertEqual(sc.revisar(O, C), [])

    def test_lo_medible(self):
        for c, d in ((C.replace('Colombia', 'Ecuador'), 'nombre que el original no trae: Ecuador'),
                     (C.replace('26', '27'), 'cifra que el original no trae: 27'),
                     ('Los tres hijos de Chena esperan en Pasto mientras ella recoge café.', 'cifra que el original no trae: 3'),
                     (C[:-1], 'no cierra la frase'),
                     (C + ' Café.' * 70, 'máximo 350')):
            self.assertIn(d, ' '.join(sc.revisar(O, c)), c[:40])

    def test_numero_en_letra_o_cifra(self):
        self.assertEqual(sc.revisar(O, 'Los 2 hijos de Chena esperan en Pasto mientras ella recoge café.'), [])

    def test_la_primera_palabra_no_es_nombre(self):
        self.assertEqual(sc.revisar(O, 'Mientras viaja, Chena busca autonomía. Recoge café y sus hijos la esperan.'), [])

    def test_original_cortado(self):
        self.assertIn('el ORIGINAL está cortado: recuperarlo antes', sc.revisar(O + ' Sin embargo, el último obstáculo', C))


class Verificada(unittest.TestCase):
    def _mal(self, f):
        d = copy.deepcopy(D)
        f(d)
        return ' '.join(sc.invalidas([d]))

    def test_buena(self):
        self.assertEqual(sc.invalidas([D]), [])

    def test_sin_veredicto(self):
        self.assertIn('veredicto', self._mal(lambda d: d['sintesis'].update(veredicto='con ajuste')))

    def test_no_se_verifica_uno_mismo(self):
        self.assertIn('redacta', self._mal(lambda d: d['sintesis'].update(verifica='a')))

    def test_tocar_el_texto_vence_el_veredicto(self):
        self.assertIn('cambió después', self._mal(lambda d: d.update(valor=C.replace('recogiendo', 'cosechando'))))
        self.assertIn('cambió después', self._mal(lambda d: d.update(original=O + ' Espera volver a casa.')))

    def test_permitido_con_porque(self):
        c = C.replace('Colombia', 'Ecuador')
        d = {**D, 'valor': c, 'sintesis': {**D['sintesis'], 'huella': sc.huella(O, c)}}
        self.assertTrue(sc.invalidas([d]))
        d['sintesis']['permitido'] = {'nombre que el original no trae: Ecuador': 'está en la ficha'}
        self.assertEqual(sc.invalidas([d]), [])

    def test_las_elegidas_sin_sintesis_no_cuentan(self):
        self.assertEqual(sc.invalidas([{'work_id': 'w2', 'campo': 'sinopsis.es', 'valor': O * 5}]), [])


if __name__ == '__main__':
    unittest.main()
