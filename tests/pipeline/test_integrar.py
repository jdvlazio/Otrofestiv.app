"""Integrar main sin perder nada, y las decisiones en un archivo por obra (25 nov 2026)."""
import contextlib, io, json, os, shutil, subprocess, sys, tempfile, unittest
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
        for c, v in (('reemplaza', 0), ('anteriores', [1]), ('a_mano', True), ('vistas', ['x'])):
            self.assertEqual(len(i.faltan_decisiones({'w': [D('w', 'anio', 1, **{c: v})]}, {'w': [D('w', 'anio', 1)]})[0]), 1, c)
        self.assertEqual(len(i.faltan_decisiones({'w': [D('w', 'anio', 1, antes={'a': 1, 'b': 1})]}, {'w': [D('w', 'anio', 1, antes={'a': 1})]})[0]), 1)


G = list(range(40))


class DePuntaAPunta(unittest.TestCase):
    """Un repo de verdad: main y una rama que cambian lo mismo y cosas distintas."""
    def setUp(self):
        self.d, self.viejo = tempfile.mkdtemp(), (i.REPO, i.MAIN)
        i.REPO, i.MAIN = self.d, 'main'
        self.g('init', '-q', '-b', 'main')
        for k, v in (('user.email', 'x@x'), ('user.name', 'x'), ('commit.gpgsign', 'false'), ('core.hooksPath', '/dev/null')):
            self.g('config', k, v)
        self.fest = {'films': [{'id': 'f1', 'title': 'P', 'time': '18:00', 'director': 'A'}, {'id': 'f2', 'title': 'Q', 'time': '20:00', 'director': 'B'}]}
        self.e('festivals/a.json', self.fest)
        self.e('festivals/staging/a-x.json', {'k': 1})
        self.e('catalogo/sellos.json', {'w_1': {'h': 'x', 'redacta': 'r'}})
        self.e('catalogo/decisiones/w_A.json', [D('w_A', 'anio', 1, antes={'a': 2})])
        self.commit('base')
        self.g('switch', '-qc', 'rama')

    def tearDown(self):
        i.REPO, i.MAIN = self.viejo
        shutil.rmtree(self.d)

    def g(self, *a, mal=False):
        r = subprocess.run(['git', *a], cwd=self.d, capture_output=True, text=True, env=i.ENTORNO)
        if r.returncode and not mal:
            raise AssertionError(a, r.stderr)
        return r

    def e(self, p, v):
        ruta = os.path.join(self.d, p)
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, 'w') as fh:
            fh.write(json.dumps(v, indent=1))

    def l(self, p):
        with open(os.path.join(self.d, p)) as fh:
            return json.load(fh)

    def commit(self, m='x'):
        self.g('add', '-A')
        self.g('commit', '-qm', m)

    def corre(self, f, *a):
        s = io.StringIO()
        with contextlib.redirect_stdout(s):
            r = f(*a)
        return r, s.getvalue()

    def en_main(self, **cambios):
        self.g('switch', '-q', 'main')
        for p, v in cambios.items():
            self.e(p.replace('__', '/') + '.json', v) if v is not None else self.g('rm', '-q', p.replace('__', '/') + '.json')
        self.commit('main')
        self.g('switch', '-q', 'rama')

    def test_mezcla_lo_distinto_y_queda_lista_para_commit(self):
        self.e('catalogo/sellos.json', {'w_1': {'h': 'x', 'redacta': 'r'}, 'w_2': {'h': 'y'}})
        self.e('catalogo/decisiones/w_A.json', [D('w_A', 'anio', 1, antes={'a': 2}), D('w_A', 'generos', ['X'])])
        self.commit()
        self.en_main(catalogo__sellos={'w_1': {'h': 'x', 'redacta': 'r'}, 'w_3': {'h': 'z'}},
                     catalogo__decisiones__w_A=[D('w_A', 'anio', 1, antes={'a': 2}), D('w_A', 'paises', ['CO'])])
        self.assertEqual(self.corre(i.integrar)[0], 0)
        self.g('commit', '-qm', 'mezcla')
        self.assertEqual(set(self.l('catalogo/sellos.json')), {'w_1', 'w_2', 'w_3'})
        self.assertEqual([d['campo'] for d in self.l('catalogo/decisiones/w_A.json')], ['anio', 'paises', 'generos'])
        self.assertEqual(self.corre(i.revisar, set())[0], 0)

    def test_con_choque_git_no_deja_hacer_el_commit_ni_se_retoma(self):
        for nombre, p, v1, v2 in (('decisiones', 'catalogo__decisiones__w_A', [D('w_A', 'anio', 2)], [D('w_A', 'anio', 3)]),
                                  ('festival', 'festivals__a', {'films': [], 'x': 1}, {'films': [], 'x': 2}),
                                  ('borrado en la rama', 'festivals__a', None, {'films': []}),
                                  ('lista sin clave', 'festivals__l', [1, 2], [1, 3]),
                                  ('git mezcla limpio y aquí choca', 'festivals__g', [9] + G[1:], G[:-1] + [9])):
            with self.subTest(nombre):
                self.tearDown()
                self.setUp()
                self.g('switch', '-q', 'main')
                self.e('festivals/g.json', G)
                self.commit()
                self.g('switch', '-q', 'rama')
                self.g('merge', '-q', 'main')
                f = p.replace('__', '/') + '.json'
                self.e(f, v1) if v1 is not None else self.g('rm', '-q', f)
                self.commit()
                self.en_main(**{p: v2})
                self.assertEqual(self.corre(i.integrar)[0], 1)
                self.assertEqual(self.l(f), v1 if v1 is not None else v2)
                self.assertNotEqual(self.g('commit', '-qm', 'x', mal=True).returncode, 0)
                self.assertIn(f, self.g('diff', '--name-only', '--diff-filter=U').stdout)
                self.e(f, v2)
                self.g('add', f)
                self.assertRaises(SystemExit, i.integrar)
                self.assertEqual(self.l(f), v2)
                self.g('commit', '-qm', 'x')

    def test_reparte_el_archivo_viejo_de_la_rama(self):
        self.g('rm', '-qr', 'catalogo/decisiones')
        self.e('catalogo/decisiones.json', [D('w_A', 'anio', 1, antes={'a': 2}), D('w_B', 'anio', 5)])
        self.commit()
        self.en_main(catalogo__decisiones__w_C=[D('w_C', 'anio', 1)])
        self.assertEqual(self.corre(i.integrar)[0], 0)
        self.g('commit', '-qm', 'x')
        self.assertEqual(sorted(os.listdir(os.path.join(self.d, 'catalogo', 'decisiones'))), ['w_A.json', 'w_B.json', 'w_C.json'])
        self.assertFalse(os.path.exists(os.path.join(self.d, 'catalogo', 'decisiones.json')))

    def test_revisar_frena_cada_perdida(self):
        otra = json.loads(json.dumps(self.fest))
        otra['films'] = otra['films'][:1]
        hora = json.loads(json.dumps(self.fest))
        hora['films'][0]['time'] = '19:00'
        for nombre, p, v in (('sello', 'catalogo/sellos.json', {}), ('sello a medias', 'catalogo/sellos.json', {'w_1': {'h': 'x'}}),
                             ('antes', 'catalogo/decisiones/w_A.json', [D('w_A', 'anio', 1)]),
                             ('vacío', 'catalogo/decisiones/w_A.json', [D('w_A', 'anio', None, antes={'a': 2})]),
                             ('decisión', 'catalogo/decisiones/w_A.json', [D('w_A', 'generos', ['x'])]),
                             ('función', 'festivals/a.json', otra), ('hora', 'festivals/a.json', hora)):
            with self.subTest(nombre):
                self.tearDown()
                self.setUp()
                self.e(p, v)
                self.commit()
                self.assertEqual(self.corre(i.revisar, set())[0], 1)
        self.assertEqual(self.corre(i.revisar, {'a'})[0], 0)                   # la hora, en lo propio, sí
        self.e('festivals/a.json', otra)
        self.commit()
        self.assertEqual(self.corre(i.revisar, {'a'})[0], 1)                   # perder una función, no
        r, s = self.corre(i.revisar, {'a'}, True)
        self.assertEqual((r, 'PERDIDO' in s), (0, True))
        self.g('rm', '-q', 'festivals/staging/a-x.json')
        self.commit()
        self.assertEqual(self.corre(i.revisar, {'a'}, True)[0], 1)

    def test_revisar_ve_lo_que_solo_tenia_la_rama(self):
        self.e('catalogo/decisiones/w_B.json', [D('w_B', 'anio', 1)])
        self.commit()
        self.en_main(festivals__b={'films': []})
        self.corre(i.integrar)
        self.g('commit', '-qm', 'mezcla')
        self.assertEqual(self.corre(i.revisar, set())[0], 0)
        self.g('rm', '-q', 'catalogo/decisiones/w_B.json')
        self.commit()
        r, s = self.corre(i.revisar, set())
        self.assertEqual((r, 'decisión de la rama perdida: w_B anio#0' in s), (1, True))

    def test_revisar_recuerda_las_mezclas_de_antes(self):
        self.e('catalogo/decisiones/w_B.json', [D('w_B', 'anio', 1)])
        self.e('catalogo/sellos.json', {'w_1': {'h': 'x', 'redacta': 'r'}, 'w_2': {'h': 'y'}})
        self.e('festivals/z.json', {'films': [{'id': 'q', 'title': 'Z'}]})
        self.commit()
        self.en_main(festivals__b={'films': []})
        self.corre(i.integrar)
        self.g('commit', '-qm', 'm1')
        self.g('rm', '-q', 'catalogo/decisiones/w_B.json')
        self.e('catalogo/sellos.json', {'w_1': {'h': 'x', 'redacta': 'r'}})
        self.e('festivals/z.json', {'films': []})
        self.commit()
        self.en_main(festivals__c={'films': []})
        self.corre(i.integrar)
        self.g('commit', '-qm', 'm2')
        r, s = self.corre(i.revisar, set())
        self.assertEqual((r, 'w_B anio#0' in s, 'sellos de la rama: falta w_2' in s, 'falta la función q' in s), (1, True, True, True))
        r, s = self.corre(i.revisar, {'z'}, True)
        self.assertEqual(('✗ festivals/z.json' in s, 'PERDIDO' in s), (False, True))

    def test_lo_que_main_ya_tiene_o_quito_no_es_perdida_de_la_rama(self):
        self.assertEqual(i.solo_rama({'a'}, {'a', 'b', 'c', 'd'}, {'c'}, {'d'}), ['b'])
        self.assertEqual(len(i.solo_rama(set(), {'a', ('a', 2)}, set(), set())), 2)

    def test_borrar_un_festival_de_main_frena(self):
        self.g('rm', '-q', 'festivals/a.json')
        self.commit()
        self.assertEqual(self.corre(i.revisar, {'a'}, True)[0], 1)

    def test_revisar_exige_arbol_limpio_y_main(self):
        self.e('festivals/n.json', {})
        self.assertRaises(SystemExit, i.revisar, set())
        self.commit()
        self.en_main(festivals__b={})
        self.assertRaises(SystemExit, i.revisar, set())


class Posiciones(unittest.TestCase):
    def test_campo_repetido_o_reemplaza_en_los_dos_lados_choca(self):
        mal = []
        i.mezclar_decisiones([D('w', 'anio', 1), D('w', 'anio', 2, reemplaza=0)], [D('w', 'anio', 2)],
                             [D('w', 'anio', 1), D('w', 'anio', 2, reemplaza=0), D('w', 'anio', 3, reemplaza=1)], 'w', mal)
        self.assertEqual(len(mal), 1)

    def test_si_solo_un_lado_cambio_se_toma_entero(self):
        b, t = [D('w', 'anio', 1)], [D('w', 'anio', 1), D('w', 'anio', 2, reemplaza=0)]
        mal = []
        self.assertEqual((i.mezclar_decisiones(b, b, t, 'w', mal), mal), (t, []))

    def test_orden_de_los_dos_lados(self):
        mal = []
        self.assertEqual((i.fusionar_orden(['a', 'b'], ['a', 'n', 'b'], ['a', 'b', 'm'], '', mal), mal), (['a', 'n', 'b', 'm'], []))
        i.fusionar_orden(['a', 'b', 'c'], ['b', 'a', 'c'], ['a', 'c', 'b'], 'x', mal)
        self.assertEqual(mal, ['x (orden)'])

    def test_obras_repetidas_no_se_tapan(self):
        o = lambda t, w: {'title': t, 'work_id': w}
        a = {'films': [{'id': '1', 'title': 'P', 'film_list': [o('T', 'a'), o('T', 'b'), o('Z', 'c')]}]}
        b = {'films': [{'id': '1', 'title': 'P', 'film_list': [o('T', 'a'), o('Z', 'c'), o('N', 'x')]}]}
        self.assertEqual(len(i.comparar(a, b)[0]), 1)

    def test_una_fusion_con_otro_destino_frena(self):
        self.assertEqual(len(i.faltan_entradas('fusiones', [{'absorbido': 'a', 'superviviente': 'b'}], [{'absorbido': 'a', 'superviviente': 'c'}])), 1)


if __name__ == '__main__':
    unittest.main()
