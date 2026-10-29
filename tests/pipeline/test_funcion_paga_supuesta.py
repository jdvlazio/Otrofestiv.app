"""Festival `mixed`: la función que no dice cómo se entra es PAGA, y ahora lo
dice explícito (is_free: false, marca supuesto). Hasta hoy la app lo deducía de
la falta del dato; escribirlo no cambia nada en pantalla y deja el supuesto a
la vista (docs/FUNCION.md §4). Con invitación no hay nada que vender."""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import funcion


def f(**kw):
    return {'title': 'O', 'day': '2026-10-01', 'time': '19:00', 'venue': 'V', **kw}


class PagaSupuesta(unittest.TestCase):
    def test_mixed_sin_dato_es_paga_supuesta(self):
        fs = [f()]
        self.assertEqual(funcion.marcar_paga_supuesta(fs, 'mixed'), 1)
        self.assertIs(fs[0]['is_free'], False)
        self.assertEqual(fs[0]['_procedencia']['entrada']['marca'], 'supuesto')

    def test_lo_dicho_no_se_toca(self):
        fs = [f(is_free=True), f(is_free=False)]
        self.assertEqual(funcion.marcar_paga_supuesta(fs, 'mixed'), 0)
        self.assertEqual([x['is_free'] for x in fs], [True, False])
        self.assertNotIn('_procedencia', fs[0])

    def test_con_invitacion_no_hay_nada_que_vender(self):
        fs = [f(by_invitation=True)]
        self.assertEqual(funcion.marcar_paga_supuesta(fs, 'mixed'), 0)
        self.assertNotIn('is_free', fs[0])

    def test_sin_modelo_o_paid_no_se_toca(self):
        for m in (None, 'paid'):
            fs = [f()]
            self.assertEqual(funcion.marcar_paga_supuesta(fs, m), 0)
            self.assertNotIn('is_free', fs[0])

    def test_conserva_otras_procedencias(self):
        fs = [f(_procedencia={'sala': {'tipo': 'sala'}})]
        funcion.marcar_paga_supuesta(fs, 'mixed')
        self.assertIn('sala', fs[0]['_procedencia'])

    def test_idempotente(self):
        fs = [f()]
        funcion.marcar_paga_supuesta(fs, 'mixed')
        self.assertEqual(funcion.marcar_paga_supuesta(fs, 'mixed'), 0)


if __name__ == '__main__':
    unittest.main()
