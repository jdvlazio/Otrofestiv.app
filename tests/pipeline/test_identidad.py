"""La identidad de una obra es su id, no su título ni su dirección (24 nov 2026)."""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import catalogo
import catalogo_construir as cc


def r(fest, titulo, director='', wid=None, **k):
    return {'fest': fest, 'titulo': titulo, 'director': director, 'wid': wid, 'anio': 2025, 'duracion': None, 'tmdb': None, 'lb': None, **k}


class Construir(unittest.TestCase):
    """Con revision-fase2 vacía: solo las reglas."""
    def setUp(self):
        self._id = cc._identidad
        cc._identidad = lambda: []

    def tearDown(self):
        cc._identidad = self._id

    def _g(self, *R):
        g, c = cc.construir(list(R))
        return sorted(sorted(x) for x in g), c

    def test_mismo_id_une_aunque_cambie_todo_el_texto(self):
        g, c = self._g(r('a', 'Uno', 'Ana Díaz', 'w_1'), r('b', 'One', 'Pedro Mutado', 'w_1'))
        self.assertEqual((g, c), ([[0, 1]], []))

    def test_dos_ids_no_se_funden_solos_ni_con_prueba(self):
        for k in ({'tmdb': 7}, {'lb': 'uno'}, {}):
            g, c = self._g(r('a', 'Uno', 'Ana Díaz', 'w_1', **k), r('b', 'Uno', 'Ana Díaz', 'w_2', **k))
            self.assertEqual((g, len(c) >= 1), ([[0], [1]], True), k)

    def test_tampoco_a_traves_de_una_tercera(self):
        g, c = self._g(r('a', 'Uno', 'Ana Díaz', 'w_1'), r('b', 'Uno', 'Ana Díaz', 'w_2'), r('c', 'Uno', 'Ana Díaz'))
        self.assertTrue(c)
        self.assertFalse(any({0, 1} <= set(x) for x in g))

    def test_la_nueva_se_une_a_la_que_ya_tiene_id(self):
        g, c = self._g(r('a', 'Uno', 'Ana Díaz', 'w_1'), r('b', 'Uno', 'Ana Díaz'))
        self.assertEqual((g, c), ([[0, 1]], []))

    def test_mismo_festival_y_titulo_con_otra_direccion_no_se_adivina(self):
        g, c = self._g(r('a', 'The End', 'Artavazd Pelechian'), r('a', 'The End', 'Niki Lindroth'))
        self.assertEqual((g, len(c)), ([[0], [1]], 1))

    def test_mismo_festival_y_titulo_sin_direccion_en_un_lado_si(self):
        self.assertEqual(self._g(r('a', 'Uno', 'Ana Díaz'), r('a', 'Uno'))[0], [[0, 1]])

    SEP = [{'a': ['a', 'The End', 'Artavazd Pelechian'], 'b': ['a', 'The End', 'Niki Lindroth'], 'misma': False}]

    def test_separada_por_declaracion_aunque_comparta_id(self):
        cc._identidad = lambda: self.SEP
        P, L = r('a', 'The End', 'Artavazd Pelechian', 'w_1'), r('a', 'The End', 'Niki Lindroth', 'w_1')
        self.assertEqual(self._g(P, L, dict(L)), ([[0], [1, 2]], []))

    def test_la_separacion_no_se_deshace_por_un_tercero(self):
        cc._identidad = lambda: self.SEP
        P, L = r('a', 'The End', 'Artavazd Pelechian', 'w_1'), r('a', 'The End', 'Niki Lindroth', 'w_1')
        for otro in (r('a', 'The End', '', 'w_1'), r('a', 'The End'), r('b', 'The End', 'Niki Lindroth', 'w_1'), r('b', 'The End', '')):
            for R in ((P, L, otro), (otro, P, L), (P, otro, L)):
                R = [dict(x) for x in R]
                g, _ = self._g(*R)
                p, l = (next(i for i, x in enumerate(R) if x['director'] == d and x['fest'] == 'a') for d in ('Artavazd Pelechian', 'Niki Lindroth'))
                self.assertFalse(any({p, l} <= set(x) for x in g), (otro, g))

    def test_la_otra_funcion_va_con_su_direccion(self):
        cc._identidad = lambda: self.SEP
        g, c = self._g(r('b', 'The End', 'Niki Lindroth', 'w_1'), r('a', 'The End', 'Artavazd Pelechian', 'w_1'), r('a', 'The End', 'Niki Lindroth', 'w_1'))
        self.assertEqual((g, c), ([[0, 2], [1]], []))

    def test_mismo_letterboxd_no_vence_a_la_declaracion(self):
        cc._identidad = lambda: self.SEP
        g, _ = self._g(r('a', 'The End', 'Artavazd Pelechian', lb='x'), r('a', 'The End', 'Niki Lindroth', lb='x'))
        self.assertEqual(g, [[0], [1]])

    def test_separar_entre_festivales(self):
        cc._identidad = lambda: [{'a': ['a', 'Uno'], 'b': ['b', 'Dos'], 'misma': False}]
        self.assertEqual(self._g(r('a', 'Uno', 'X Uno', 'w_1'), r('b', 'Dos', 'Y Dos', 'w_1')), ([[0], [1]], []))

    def test_un_id_con_dos_fichas_se_pregunta(self):
        g, c = self._g(r('a', 'Uno', 'Ana', 'w_1', tmdb=1), r('b', 'Dos', 'Eva', 'w_1', tmdb=2))
        self.assertIn('dos fichas', c[0][2])

    def test_juntar_dos_ids_por_declaracion(self):
        cc._identidad = lambda: [{'a': ['w_1'], 'b': ['w_2'], 'misma': True}]
        self.assertEqual(self._g(r('a', 'Uno', 'Ana', 'w_1'), r('a', 'Uno', 'Ana', 'w_2')), ([[0, 1]], []))

    def test_declaracion_ya_cumplida_no_rompe_la_corrida_siguiente(self):
        cc._identidad = lambda: [{'a': ['w_1'], 'b': ['w_2'], 'misma': True}]
        f, catalogo.fusiones = catalogo.fusiones, lambda *a: [{'absorbido': 'w_2', 'superviviente': 'w_1'}]
        try:
            self.assertEqual(self._g(r('a', 'Uno', 'Ana', 'w_1'), r('b', 'Uno', 'Ana', 'w_1')), ([[0, 1]], []))
        finally:
            catalogo.fusiones = f

    def test_de_un_id_partido_lo_ambiguo_se_pregunta(self):
        cc._identidad = lambda: self.SEP
        P, L = r('a', 'The End', 'Artavazd Pelechian', 'w_1'), r('a', 'The End', 'Niki Lindroth', 'w_1')
        for otro in (r('b', 'The End', '', 'w_1'), r('b', 'The End', 'Niki Lindrot', 'w_1')):
            for R in ((P, L, otro), (otro, P, L), (P, otro, L)):
                g, c = self._g(*[dict(x) for x in R])
                self.assertEqual((len(g), bool(c)), (3, True))

    def test_sin_direccion_no_es_puente(self):
        g, c = self._g(r('a', 'Uno', 'Ana Ruiz'), r('a', 'Uno'), r('a', 'Uno', 'Pedro Yepes'))
        self.assertTrue(c)
        self.assertFalse(any({0, 2} <= set(x) for x in g))


class Heredar(unittest.TestCase):
    V = {'films': [{'id': 'f_1', 'title': 'Uno', 'director': 'Ana Díaz', 'work_id': 'w_1', 'day': '1', 'time': '2', 'venue': 'V'},
                   {'id': 'f_2', 'title': 'P', 'film_list': [{'title': 'A', 'director': 'X A', 'work_id': 'w_a'}, {'title': 'B', 'director': 'Y B', 'work_id': 'w_b'}]}]}

    def _h(self, *fs):
        d = {'films': list(fs)}
        catalogo.heredar_ids(d, self.V)
        return [o.get('work_id') for f in d['films'] for o in (f.get('film_list') or [f])]

    def test_por_id_y_por_horario(self):
        self.assertEqual(self._h({'id': 'f_1', 'title': 'Título nuevo', 'director': 'Ana Díaz'}), ['w_1'])
        self.assertEqual(self._h({'title': 'Título nuevo', 'director': 'Ana Díaz', 'day': '1', 'time': '2', 'venue': 'V'}), ['w_1'])

    def test_otra_obra_en_esa_funcion_no_hereda(self):
        self.assertEqual(self._h({'id': 'f_1', 'title': 'Otra', 'director': 'Pedro Yepes'}), [None])
        self.assertEqual(self._h({'id': 'f_1', 'title': 'Otra'}), [None])

    def test_dentro_del_programa(self):
        self.assertEqual(self._h({'id': 'f_2', 'title': 'P', 'film_list': [{'title': 'B', 'director': 'Y B'}, {'title': 'A renombrada', 'director': 'X A'}]}), ['w_b', 'w_a'])


class Enlazar(unittest.TestCase):
    OBS = {'w_1': {'titulo_original': 'Uno', 'directores': ['Ana Díaz'], 'presentaciones': ['f-1']},
           'w_2': {'titulo_original': 'The End', 'directores': ['Artavazd Pelechian'], 'presentaciones': ['f-1']},
           'w_3': {'titulo_original': 'The End', 'directores': ['Niki Lindroth'], 'presentaciones': ['f-1']}}

    def _e(self, **o):
        catalogo.enlazar({'films': [o]}, 'f-1', self.OBS)
        return o.get('work_id')

    def test_conserva_el_id_aunque_cambie_titulo_o_direccion(self):
        self.assertEqual(self._e(title='Título nuevo', director='Ana Díaz', work_id='w_1'), 'w_1')
        self.assertEqual(self._e(title='Título nuevo', director='Otra Grafía', work_id='w_1'), 'w_1')

    def test_el_mismo_titulo_se_resuelve_por_direccion(self):
        self.assertEqual(self._e(title='The End', director='Niki Lindroth'), 'w_3')
        self.assertEqual(self._e(title='The End', director='Niki Lindroth', work_id='w_2'), 'w_3')

    def test_dos_titulos_de_la_misma_direccion_que_se_separaron(self):
        obs = {'w_1': {'titulo_original': 'Uno', 'directores': ['Ana Díaz'], 'presentaciones': ['f-1']},
               'w_2': {'titulo_original': 'Dos', 'directores': ['Ana Díaz'], 'presentaciones': ['f-1']}}
        o = {'title': 'Dos', 'director': 'Ana Díaz', 'work_id': 'w_1'}
        catalogo.enlazar({'films': [o]}, 'f-1', obs)
        self.assertEqual(o['work_id'], 'w_2')

    def test_un_id_que_no_existe_no_se_cree(self):
        self.assertIsNone(self._e(title='Nada', director='X', work_id='w_9'))


class Real(unittest.TestCase):
    """Sobre lo publicado: alterar el texto de una función no parte la obra."""
    def test_mutar_direccion_titulo_o_anio_no_crea_obras(self):
        R = cc.registros()
        n = len(cc.construir([dict(x) for x in R])[0])
        multi = [i for i, x in enumerate(R) if x['wid'] and sum(y['wid'] == x['wid'] for y in R) > 1][::400]
        self.assertGreater(len(multi), 4)
        M = [dict(x) for x in R]
        for k, i in enumerate(multi):
            M[i].update([{'director': 'Persona Mutada'}, {'titulo': 'Título Mutado Entero'}, {'anio': 1900}][k % 3])
        self.assertEqual(len(cc.construir(M)[0]), n)

    def test_hoy_cada_id_es_un_grupo_y_no_hay_candidatos(self):
        R = cc.registros()
        g, c = cc.construir(R)
        self.assertEqual(c, [])
        self.assertTrue(all(len({R[i]['wid'] for i in x}) == 1 for x in g))


if __name__ == '__main__':
    unittest.main()
