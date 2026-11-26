"""Lo publicado de una obra es lo decidido (24 nov 2026). Las mutaciones van sobre los datos REALES."""
import copy, os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import catalogo
import obra_unica as ou


class Mutacion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fs, cls.decs = ou._festivales(), catalogo.decisiones()
        cls.vals, _ = ou.publicado(cls.fs)
        cls.eleg = ou.elegidos(cls.decs)

    def _mutar(self, w, k):
        """Cambia UNA presentación de esa obra en memoria y dice si el guardián la ve."""
        fid = next(f for f in sorted(self.fs) for x in self.fs[f]['films'] for o in catalogo.obras_de(x) if o.get('work_id') == w and o.get(k))
        fs = dict(self.fs, **{fid: copy.deepcopy(self.fs[fid])})
        o = next(o for x in fs[fid]['films'] for o in catalogo.obras_de(x) if o.get('work_id') == w and o.get(k))
        if k == 'synopsis':
            o.pop('synopsis_es', None)
        o[k] = 1900 if k == 'year' else 'MUTADO'
        return any(x[0] == w and x[2] == k for x in ou.divergencias(fs, self.decs))

    def test_cada_campo_decidido_y_sin_decidir(self):
        for k in ou.CAMPO:
            con = next((w for w in self.vals if k in self.eleg.get(w, {}) and k in self.vals[w] and (w, k) not in ou.EXCEPCIONES), None)
            self.assertTrue(con and self._mutar(con, k), f'{k} decidido')
            # sin decisión: dos funciones de la misma obra que hoy coinciden
            sin = next(w for w in self.vals if k not in self.eleg.get(w, {}) and (w, k) not in ou.EXCEPCIONES
                       and len(next(iter(self.vals[w].get(k, {'': []}).values()))) > 1)
            self.assertTrue(self._mutar(sin, k), f'{k} sin decidir')

    def test_hoy_no_hay_divergencias(self):
        self.assertEqual([ou.texto(x) for x in ou.divergencias(self.fs, self.decs)], [])


class Reglas(unittest.TestCase):
    def test_autoprueba_ve_todos_los_campos(self):
        self.assertEqual(ou.autoprueba(), [])

    def test_vacio_no_es_divergencia(self):
        a = {'title': 'X', 'type': 'film', 'work_id': 'w_1', 'genre': 'Drama'}
        self.assertEqual(ou.divergencias({'f': {'films': [a, {'title': 'X', 'type': 'film', 'work_id': 'w_1'}]}}, [], {}), [])

    def test_ve_synopsis_es_que_es_lo_que_se_lee(self):
        a = {'title': 'X', 'type': 'film', 'work_id': 'w_1', 'synopsis': 's', 'synopsis_es': 'otra'}
        d = [{'work_id': 'w_1', 'campo': 'sinopsis.es', 'valor': 's'}]
        self.assertEqual([x[2] for x in ou.divergencias({'f': {'films': [a]}}, d, {})], ['synopsis'])

    def test_excepcion_por_campo_no_tapa_los_demas(self):
        a = {'title': 'X', 'type': 'film', 'work_id': 'w_1', 'genre': 'A', 'director': 'A'}
        fs = {'f': {'films': [a, dict(a, genre='B', director='B')]}}
        self.assertEqual([x[2] for x in ou.divergencias(fs, [], {('w_1', 'genre'): ''})], ['director'])

    def test_mira_las_obras_dentro_de_eventos(self):
        e = {'title': 'Gala', 'type': 'event', 'film_list': [{'title': 'X', 'work_id': 'w_1', 'director': 'B', 'year': 2025}]}
        a = {'title': 'X', 'type': 'film', 'work_id': 'w_1', 'director': 'A', 'year': 2025}
        self.assertEqual([x[2] for x in ou.divergencias({'f': {'films': [a, e]}}, [], {})], ['director'])

    def test_excepcion_que_sobra_se_ve(self):
        self.assertEqual(len(ou.excepciones_de_mas({}, [])), len(ou.EXCEPCIONES))
        self.assertEqual(ou.excepciones_de_mas(ou._festivales(), catalogo.decisiones()), [])   # hoy, todas hacen falta


class Decidir(unittest.TestCase):
    V = {'w_1': {'genre': {'Drama': ['f-1', 'f-2'], 'Ficción': ['f-3']}, 'poster': {'/a': ['f-1'], '/b': ['f-2']}, 'synopsis': {'s': ['f-1']}}}

    def _d(self, decs, campo, valor):
        return ou.decidir(decs, self.V, 'w_1', campo, valor, 'm', 'q', '2026-11-24')

    def test_guarda_lo_que_publicaba_cada_festival(self):
        decs = []
        d = self._d(decs, 'generos', 'Drama')
        self.assertEqual(d['antes'], {'f-1': 'Drama', 'f-2': 'Drama', 'f-3': 'Ficción'})
        d2 = self._d(decs, 'generos', 'Ficción')          # cambiarla no pierde el original
        self.assertEqual((len(decs), d2['valor'], d2['antes']['f-3']), (1, ['Ficción'], 'Ficción'))

    def test_afiche_queda_listo_para_viajar(self):
        with self.assertRaises(SystemExit):
            self._d([], 'afiche', '/a')                    # nuevo, sin veredicto
        with self.assertRaises(SystemExit):
            self._d([], 'afiche', '/assets/no-existe.jpg')
        with self.assertRaises(SystemExit):
            ou.decidir([], self.V, 'w_1', 'afiche', '/a', 'm', 'q', 'f', veredicto='ofical')
        ya = [{'work_id': 'w_1', 'campo': 'afiche', 'valor': {'archivo': '/a', 'veredicto': 'fotograma'}}]
        d = self._d(ya, 'afiche', '/a')                    # ratificar conserva el veredicto
        self.assertEqual((d['valor'], d['vistas'], 'a_mano' in d), ({'archivo': '/a', 'veredicto': 'fotograma'}, ['/b'], False))

    def test_cambia_la_vigente_no_la_reemplazada(self):
        decs = [{'work_id': 'w_1', 'campo': 'generos', 'valor': ['A']}, {'work_id': 'w_1', 'campo': 'generos', 'valor': ['B'], 'reemplaza': 0}]
        self._d(decs, 'generos', 'Drama')
        self.assertEqual(ou.elegidos(decs)['w_1']['genre'], 'Drama')

    def test_vacio_no_entra(self):
        with self.assertRaises(SystemExit):
            self._d([], 'generos', ' ')

    def test_no_pisa_una_sintesis_verificada_ni_acepta_lo_que_no_existe(self):
        for decs, campo, valor in (([{'work_id': 'w_1', 'campo': 'sinopsis.es', 'original': 'o', 'valor': 's'}], 'sinopsis.es', 'x'),
                                   ([], 'anio', '2025'), ([], 'inventado', 'x')):
            with self.assertRaises(SystemExit):
                self._d(decs, campo, valor)



class PrimerIngles(unittest.TestCase):
    """26 nov 2026: decidir negaba el inglés de una obra que solo publicaba español; cuatro obras
    lo recibieron con un script suelto. Ahora la decisión entra y ficha_unica lo lleva."""
    O = {'type': 'film', 'title': 'La tinaja', 'work_id': 'w_T1', 'director': 'Ana Pérez', 'synopsis': 'Una mujer vuelve a su pueblo.'}

    def _fs(self):
        return {'a': {'films': [dict(self.O)]}, 'b': {'films': [{'type': 'program', 'title': 'P', 'film_list': [dict(self.O)]}]}}

    def test_entra_y_llega_a_cada_festival(self):
        import ficha_unica
        fs, decs = self._fs(), []
        d = ou.decidir(decs, ou.publicado(fs)[0], 'w_T1', 'sinopsis.en', 'A woman returns to her town.', 'síntesis', 'Juan', '2026-11-26')
        self.assertEqual((d['valor'], d['antes']), ('A woman returns to her town.', {}))
        for f in fs.values():
            ficha_unica.aplicar(f, decs)
        self.assertEqual(sorted(ou.publicado(fs)[0]['w_T1']['synopsis_en'].items()), [('A woman returns to her town.', ['a', 'b'])])
        self.assertEqual([x for x in ou.divergencias(fs, decs, {}) if x[0] == 'w_T1'], [])

    def test_sin_espanol_no_hay_de_donde(self):
        fs = {'a': {'films': [dict(self.O, synopsis='')]}}
        with self.assertRaises(SystemExit):
            ou.decidir([], ou.publicado(fs)[0], 'w_T1', 'sinopsis.en', 'A woman returns.', 'm', 'Juan', '2026-11-26')

    def test_otros_campos_siguen_pidiendo_que_se_publique(self):
        with self.assertRaises(SystemExit):
            ou.decidir([], ou.publicado(self._fs())[0], 'w_T1', 'generos', 'Drama', 'm', 'Juan', '2026-11-26')


if __name__ == '__main__':
    unittest.main()
