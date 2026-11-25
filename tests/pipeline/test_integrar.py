"""Integrar main sin perder nada, y las decisiones en un archivo por obra (25 nov 2026)."""
import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import catalogo as c
import integrar as i

D = lambda w, k, v, **z: {'work_id': w, 'campo': k, 'valor': v, **z}


class PorObra(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def test_ida_y_vuelta_con_reemplaza_y_sin_obra(self):
        xs = [D('w_B', 'anio', 1), D('w_A', 'anio', 2), D('', 'ficha-ok', 7), D('w_B', 'anio', 3, reemplaza=0)]
        c.escribir_decisiones(xs, self.d)
        ys = c.decisiones(self.d)
        self.assertEqual(len(ys), 4)
        r = next(y for y in ys if 'reemplaza' in y)
        self.assertEqual((r['valor'], ys[r['reemplaza']]['valor']), (3, 1))
        with open(os.path.join(self.d, 'decisiones', 'w_B.json')) as fh:
            self.assertEqual(json.load(fh)[1]['reemplaza'], 0)
        self.assertEqual(c.escribir_decisiones(ys, self.d), 0)

    def test_solo_toca_lo_que_cambia_y_borra_lo_vacio(self):
        c.escribir_decisiones([D('w_A', 'anio', 1), D('w_B', 'anio', 1)], self.d)
        self.assertEqual(c.escribir_decisiones([D('w_A', 'anio', 2)], self.d), 2)
        self.assertEqual(os.listdir(os.path.join(self.d, 'decisiones')), ['w_A.json'])

    def test_para_si_vuelve_el_archivo_viejo_o_una_decision_en_casa_ajena(self):
        c.escribir_decisiones([D('w_A', 'anio', 1)], self.d)
        p = os.path.join(self.d, 'decisiones', 'w_B.json')
        with open(p, 'w') as fh:
            json.dump([D('w_A', 'anio', 1)], fh)
        self.assertRaises(ValueError, c.decisiones, self.d)
        os.remove(p)
        with open(os.path.join(self.d, 'decisiones.json'), 'w') as fh:
            fh.write('[]')
        self.assertRaises(ValueError, c.decisiones, self.d)

    def test_no_reemplaza_la_de_otra_obra_ni_acepta_una_ruta(self):
        self.assertRaises(ValueError, c.escribir_decisiones, [D('w_A', 'anio', 1), D('w_B', 'anio', 2, reemplaza=0)], self.d)
        self.assertRaises(ValueError, c.escribir_decisiones, [D('../x', 'anio', 1)], self.d)


class Mezcla(unittest.TestCase):
    def m(self, b, o, t):
        mal = []
        return i.mezclar(b, o, t, '', mal), mal

    def test_cada_lado_agrega_y_cambia_lo_suyo(self):
        self.assertEqual(self.m({'a': 1, 'b': 1}, {'a': 2, 'b': 1, 'c': 1}, {'a': 1, 'b': 3, 'd': 1}),
                         ({'a': 2, 'b': 3, 'd': 1, 'c': 1}, []))

    def test_el_mismo_dato_distinto_es_choque(self):
        self.assertEqual(self.m({'a': 1}, {'a': 2}, {'a': 3}), ({'a': 2}, ['/a']))

    def test_borrar_contra_cambiar_es_choque_y_borrar_solo_no(self):
        self.assertEqual(self.m({'a': 1}, {}, {'a': 3})[1], ['/a'])
        self.assertEqual(self.m({'a': 1}, {'a': 3}, {})[1], ['/a'])
        self.assertEqual(self.m({'a': 1, 'b': 1}, {'b': 2}, {'a': 1, 'b': 1}), ({'b': 2}, []))

    def test_listas_por_id(self):
        f = lambda *xs: [{'id': k, 'v': v} for k, v in xs]
        out, mal = self.m(f(('x', 1), ('y', 1)), f(('x', 2), ('y', 1), ('n', 1)), f(('x', 1), ('m', 1), ('y', 5)))
        self.assertEqual((sorted((d['id'], d['v']) for d in out), mal), ([('m', 1), ('n', 1), ('x', 2), ('y', 5)], []))

    def test_listas_sin_clave_distintas_chocan(self):
        self.assertEqual(self.m([1], [1, 2], [1, 3])[1], [''])

    def test_decisiones_de_una_obra(self):
        mal = []
        out = i.mezclar_decisiones([D('w', 'anio', 1)], [D('w', 'anio', 2), D('w', 'generos', ['A'])],
                                   [D('w', 'anio', 1), D('w', 'no-es', 'w_Z')], 'w', mal)
        self.assertEqual((sorted((d['campo'], str(d['valor'])) for d in out), mal),
                         ([('anio', '2'), ('generos', "['A']"), ('no-es', 'w_Z')], []))

    def test_dos_no_es_distintos_no_chocan(self):
        mal = []
        out = i.mezclar_decisiones([], [D('w', 'no-es', 'w_1')], [D('w', 'no-es', 'w_2')], 'w', mal)
        self.assertEqual((len(out), mal), (2, []))

    def test_reparte_el_archivo_viejo_con_su_reemplaza(self):
        p = i.por_obra([D('w_A', 'anio', 1), D('w_B', 'anio', 1), D('w_B', 'anio', 2, reemplaza=1)])
        self.assertEqual(p['w_B'][1]['reemplaza'], 0)


class Revision(unittest.TestCase):
    A = {'films': [{'id': 'f1', 'title': 'P', 'time': '18:00', 'film_list': [{'title': 'X', 'work_id': 'w_1', 'director': 'A', 'year': 2020}]}]}

    def con(self, **z):
        b = json.loads(json.dumps(self.A))
        b['films'][0]['film_list'][0].update(z)
        return i.comparar(self.A, b)

    def test_dato_de_obra_se_lista_y_no_frena(self):
        self.assertEqual([len(x) for x in self.con(director='B')], [0, 0, 1])

    def test_perder_un_dato_frena(self):
        self.assertEqual(len(self.con(year=None)[0]), 1)

    def test_cambiar_la_hora_o_quitar_la_funcion_frena(self):
        b = json.loads(json.dumps(self.A))
        b['films'][0]['time'] = '19:00'
        self.assertEqual(len(i.comparar(self.A, b)[1]), 1)
        self.assertEqual(len(i.comparar(self.A, {'films': []})[0]), 1)

    def test_quitar_una_obra_del_programa_frena(self):
        b = json.loads(json.dumps(self.A))
        b['films'][0]['film_list'] = []
        self.assertEqual(len(i.comparar(self.A, b)[0]), 1)

    def test_una_fusion_cambia_el_id_y_no_es_perdida(self):
        self.assertEqual([len(x) for x in self.con(work_id='w_2')], [0, 0, 1])

    def test_sinopsis_mudada_no_es_perdida(self):
        a = {'films': [{'id': '1', 'synopsis_es': 'x', 'synopsis': 'en', 'synopsis_lang': 'en'}]}
        b = {'films': [{'id': '1', 'synopsis': 'x', 'synopsis_lang': 'es'}]}
        self.assertEqual(i.comparar(a, b)[0], [])

    def test_decisiones_perdidas_y_cambiadas(self):
        p, o = i.faltan_decisiones({'w': [D('w', 'anio', 1), D('w', 'generos', ['A'])]}, {'w': [D('w', 'anio', 2)]})
        self.assertEqual((len(p), len(o)), (1, 1))


if __name__ == '__main__':
    unittest.main()
