"""Una sinopsis por obra y cuándo una nueva la reemplaza (Juan, 23 nov 2026).
Los casos defectuosos estaban PUBLICADOS ese día."""
import os
import sys
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import sinopsis_unicas as su

BIEN = 'Kari es una niña emberá que teme reír. Un día conoce a Kera, una joven que decide contarle el mito de Kiraparamia.'
OTRA = 'Una abuela y su nieto heredan historias de hambre y migración, al intentar descubrir dónde pertenece una familia entre dos mundos.'


class Defectos(unittest.TestCase):
    def test_una_buena_no_tiene(self):
        self.assertEqual(su.defectos(BIEN), [])
        self.assertEqual(su.defectos(OTRA), [])

    def test_los_publicados(self):
        for s, d in ((BIEN + ' Enlace para comprar entrada para la función en el Teatro', 'habla del evento'),
                     ('Narrafilms: Proyección con autodescripción – Personas con discapacidad visual.', 'habla del evento'),
                     (BIEN + ' Q&A con el director', 'habla del evento'),
                     ('Each year, she joins the traveling diaspora of peasants who move around Colombia working as coffee harvesters', 'en inglés'),
                     ('Três amigos esperam construir uma fábrica, mas seus planos são ameaçados pela política e pelo caso de amor de um dos sócios em sua vida', 'en portugués'),
                     ('Alejandra Castaño Arias, Wildier Tascón Tascón, Roxana Panchí Gutierrez, Alexa Yagarí Panchí, Laura Giraldo Mira', 'parece una lista de nombres'),
                     (BIEN + ' (FILMAFFINITY)', 'crédito de otra base'),
                     ('Lamentos es un cortometraje experimental colombiano dirigido por Hans Chispas y posee una duración exacta de 4 minutos.', 'ficha técnica'),
                     ('Músicos: Rosalina Cañate, Emelia Reyes, Felipa Tejedor, Brenda Torres.', 'ficha técnica'),
                     (BIEN + ' Trailer', 'resto de página web'),
                     ('Vive con su abuela y su gata Cris- tal. Una noche la Muerte llega inesperadamente para llevarse su alma.', 'texto roto'),
                     ('Con la presencia de la directora', 'habla del evento')):
            self.assertIn(d, su.defectos(s), s[:50])


class Criterio(unittest.TestCase):
    def test_falta_y_entra(self):
        self.assertEqual(su.decidir('', BIEN), 'entra')

    def test_la_defectuosa_nunca_entra(self):
        self.assertEqual(su.decidir('', BIEN + ' Q&A con el director'), 'mantener')
        self.assertEqual(su.decidir(BIEN, BIEN + ' Conversatorio con su directora'), 'mantener')

    def test_mismo_texto_con_otra_puntuacion(self):
        self.assertEqual(su.decidir(BIEN, BIEN.replace('.', ' —').upper()), 'mantener')

    def test_la_mas_completa_reemplaza(self):
        self.assertEqual(su.decidir(BIEN, BIEN + ' Kari decide confrontar a los niños que la oprimen.'), 'reemplazar')
        self.assertEqual(su.decidir(BIEN + ' Kari decide confrontar a los niños.', BIEN), 'mantener')

    def test_reemplaza_a_una_defectuosa(self):
        self.assertEqual(su.decidir(BIEN + ' Q&A con el director', OTRA), 'reemplazar')

    def test_texto_distinto_se_revisa(self):
        self.assertEqual(su.decidir(BIEN, OTRA), 'revisar')

    def test_lo_elegido_a_mano_no_se_reemplaza_solo(self):
        self.assertEqual(su.decidir(BIEN, BIEN + ' Kari decide confrontar a los niños que la oprimen.', a_mano=True), 'revisar')


if __name__ == '__main__':
    unittest.main()
