"""El veredicto de tres métodos (2 nov 2026): se aplica solo si Vision,
Tesseract y la mirada leen la hora y cada texto del dato en la lámina."""
import importlib.util, os, unittest

R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
spec = importlib.util.spec_from_file_location('ig_lecturas', os.path.join(R, 'pipeline', 'ig-lecturas.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

LAM = 'Miércoles 4 de noviembre, 7:30 p. m. Centro Colombo Americano, Sala 1'
DATO = {'lamina': '02.jpg', 'hora': '19:30', 'textos': ['Centro Colombo Americano', '4 de noviembre']}


def lecturas(vision, tess):
    return {'A·vision': {'02.jpg': vision}, 'T·tesseract': {'02.jpg': tess}}


class Veredicto(unittest.TestCase):
    def test_tres_coinciden(self):
        ok, _ = m.veredicto(lecturas(LAM, LAM.replace('é', 'e')), {'02.jpg': LAM}, DATO)
        self.assertTrue(ok)

    def test_un_metodo_lee_otra_hora(self):
        ok, res = m.veredicto(lecturas(LAM, LAM.replace('7:30', '7:50')), {'02.jpg': LAM}, DATO)
        self.assertFalse(ok)
        self.assertFalse(res['Tesseract']['19:30'])

    def test_sin_mirada_no_pasa(self):
        ok, _ = m.veredicto(lecturas(LAM, LAM), {}, DATO)
        self.assertFalse(ok)

    def test_dato_vacio_no_pasa(self):
        ok, _ = m.veredicto(lecturas(LAM, LAM), {'02.jpg': LAM}, {'lamina': '02.jpg'})
        self.assertFalse(ok)

    def test_lee_tolera_un_error_de_ocr_pero_no_otro_nombre(self):
        self.assertTrue(m.lee('Centro Colombo Amerlcano', 'Centro Colombo Americano'))
        self.assertFalse(m.lee('Teatro Pablo Tobón', 'Centro Colombo Americano'))


class HoraSinMinutos(unittest.TestCase):
    def test_4_pm_es_16_00(self):
        # la grilla del MAMM (Miradas, 2 nov) escribe «4 p.m.», sin minutos
        self.assertEqual(m.tokens('Relicto 2 p.m. y Moscas 7 p.m.')['horas'], {'14:00', '19:00'})

    def test_no_pisa_horas_con_minutos(self):
        self.assertEqual(m.tokens('7:30 p. m.')['horas'], {'19:30'})


if __name__ == '__main__':
    unittest.main()
