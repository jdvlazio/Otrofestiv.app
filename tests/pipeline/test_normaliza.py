"""Escribir bien lo que ya se sabe, sin agregar ni perder nada (24 nov 2026). Casos reales."""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import ficha_obra as fo
import ficha_unica as fu
import normaliza as n


class Pais(unittest.TestCase):
    def test_casos_reales(self):
        for a, b in (('Canadá/Colombia', 'Canadá, Colombia'), ('United States', 'Estados Unidos'), ('. Italia', 'Italia'), ('Irán/UK/Francia', 'Irán, Reino Unido, Francia'),
                     ('España (Canarias)', 'España'), ('Escocia (Reino Unido)', 'Reino Unido'), ('Chipre, Macedonia y Estados Unidos', 'Chipre, Macedonia del Norte, Estados Unidos'),
                     ('Antigua y Barbuda', 'Antigua y Barbuda'), ('Guinea-Bissau', 'Guinea-Bisáu'), ('Colombia-México', 'Colombia, México'), ('URSS', 'URSS'),
                     ('Rumanía, Francia', 'Rumania, Francia'), ('Colombia / Barranquilla', 'Colombia'), ('Varios', None)):
            self.assertEqual(n.pais(a), b, a)

    def test_lo_que_no_reconoce_queda_igual(self):
        for c in ('Narnia', 'Colombia, Narnia', 'English, Hebrew'):
            self.assertEqual(n.pais(c), c)


class Genero(unittest.TestCase):
    def test_casos_reales(self):
        for a, b in (('Thriller', 'Suspenso'), ('Documentary', 'Documental'), ('Drama / Comedia', 'Drama'), ('Documental / derechos humanos / memoria / género', 'Documental'),
                     ('Fábula y Animación', 'Animación'), ('Docu-ficción', 'Documental híbrido'), ('Ficción', None), ('VR 360', None), ('Eco Corto', None), ('Terror', 'Terror')):
            self.assertEqual(n.genero(a), b, a)

    def test_todo_lo_que_sale_es_de_la_lista(self):
        for g in n._GENERO.values():
            self.assertTrue(g is None or g in fo.GENEROS, g)

    def test_lo_que_no_reconoce_queda_igual(self):
        self.assertEqual(n.genero('Qatar'), 'Qatar')


class Director(unittest.TestCase):
    def test_casos_reales(self):
        for a, b in (('Ana Díaz y Luz Paz', 'Ana Díaz, Luz Paz'), ('A. Attie, J. Goldwater, and M. Attie', 'A. Attie, J. Goldwater, M. Attie'), ('Dirección: Entramados', 'Entramados'),
                     ('Dir. Manuela Saavedra / Resonancia Cromática', 'Manuela Saavedra, Resonancia Cromática'), ('Tamra Davis and Tamra Davis', 'Tamra Davis'),
                     ('Inês Pedrosa e Melo', 'Inês Pedrosa e Melo'), ('Colectivo Pix & Hertz', 'Colectivo Pix & Hertz'), ('Arthur J. Bressan, Jr.', 'Arthur J. Bressan, Jr.'),
                     ('Daniel Gonzalez , Ana Bernal', 'Daniel Gonzalez, Ana Bernal'), ('Varios', None)):
            self.assertEqual(n.director(a), b, a)

    def test_un_apellido_no_es_un_cargo(self):
        for d in ('Cura Dávila', 'Cura Perez', 'Dir Pérez', 'Directo Ruiz'):
            self.assertEqual(n.director(d), d)


class Otros(unittest.TestCase):
    def test_anio_y_duracion(self):
        self.assertEqual((n.anio('2022'), n.anio(2022), n.anio('s.f.')), (2022, 2022, 's.f.'))
        self.assertEqual((n.duracion(24), n.duracion('~6 min'), n.duracion("15'"), n.duracion('1 h 20')), ('24 min', '~6 min', '15 min', '1 h 20'))

    def test_todo_punto_fijo(self):
        for f in n.CAMPOS.values():
            for x in ('Canadá/Colombia', 'Ana Díaz y Luz Paz', 'Drama / Comedia', '2022', 24, *n._EXACTO, *n._EXACTO.values()):
                a = f(x)
                self.assertEqual(f(a) if a is not None else None, a, (f.__name__, x))

    def test_hoy_lo_publicado_ya_esta_bien_escrito(self):
        self.assertEqual([x for d in fo._festivales().values() for x in fu.aplicar(d)], [])

    def test_lo_que_se_quita_desaparece_con_sus_banderas_al_dia(self):
        o = {'title': 'X', 'genre': 'Ficción', 'country': 'Chile/EEUU', 'flags': '🇨🇱'}
        n.normalizar(o)
        self.assertEqual(o, {'title': 'X', 'country': 'Chile, Estados Unidos', 'flags': '🇨🇱🇺🇸'})


class FichaDeOtraObra(unittest.TestCase):
    def test_xref_decidido_reemplaza_y_none_quita(self):
        d = {'films': [{'title': 'X', 'type': 'film', 'work_id': 'w_1', 'tmdb_id': 5, 'lbSlug': 'malo'}]}
        fu.aplicar(d, [{'work_id': 'w_1', 'campo': 'xref.tmdb', 'valor': 7}, {'work_id': 'w_1', 'campo': 'xref.letterboxd', 'valor': None}])
        self.assertEqual((d['films'][0]['tmdb_id'], 'lbSlug' in d['films'][0]), (7, False))


if __name__ == '__main__':
    unittest.main()
