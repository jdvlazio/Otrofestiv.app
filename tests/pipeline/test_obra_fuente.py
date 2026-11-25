"""La obra es la fuente; el festival pone función y lugar (paso 7). Y deshacer (paso 8)."""
import copy, json, os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import catalogo, deshacer, obra_fuente as of, obra_unica as ou

O = {'type': 'film', 'title': 'X', 'work_id': 'w_1', 'director': 'Ana Díaz, Luz Paz', 'year': 2025, 'country': 'Colombia, Francia', 'flags': '🇨🇴🇫🇷', 'genre': 'Drama',
     'synopsis': 'Una.', 'synopsis_lang': 'es', 'synopsis_en': 'A.', 'poster': 'https://image.tmdb.org/t/p/w500/a.jpg', 'posterSource': 'tmdb', 'tmdb_id': 7, 'lbSlug': 'x',
     'day': 'VIE 1', 'time': '10:00', 'venue': 'v', 'duration': '9 min', 'title_en': 'X'}


class Fuente(unittest.TestCase):
    def test_autoprueba(self):
        self.assertEqual(of.autoprueba(), [])

    def test_ida_y_vuelta_exacta(self):
        d, decs = {'films': [copy.deepcopy(O), {'type': 'film', 'title': 'P', 'film_list': [dict(copy.deepcopy(O), work_id='w_2')]}]}, []
        of.sembrar('f', d, decs, 'x')
        sin = of.desnudar(d)
        self.assertEqual(set(sin['films'][0]), {'type', 'title', 'work_id', 'day', 'time', 'venue', 'duration', 'title_en'})
        of.componer(sin, decs)
        self.assertEqual(sin, d)

    def test_sembrar_no_pisa_lo_decidido(self):
        decs = [{'work_id': 'w_1', 'campo': 'anio', 'valor': 2020}]
        d = {'films': [copy.deepcopy(O)]}
        of.sembrar('f', d, decs, 'x')
        self.assertEqual([x['valor'] for x in decs if x['campo'] == 'anio'], [2020])
        self.assertEqual([x[1] for x in of.problemas('f', d, decs)], ['year'])

    def test_sembrar_no_decide_contra_otro_festival(self):
        decs = []
        with self.assertRaises(SystemExit):
            of.sembrar('f', {'films': [copy.deepcopy(O)]}, decs, 'x', festivales={'g': {'films': [dict(O, year=1999)]}})
        self.assertEqual(decs, [])

    def test_fotograma_remoto_y_pais_historico_tienen_dueno(self):
        d, decs = {'films': [dict(O, posterSource='editorial', country='Armenia, URSS', flags='🇦🇲')]}, []
        of.sembrar('f', d, decs, 'x')
        sin = of.desnudar(d)
        of.componer(sin, decs)
        self.assertEqual((sin['films'][0]['poster'], sin['films'][0]['posterSource'], sin['films'][0]['country']), (O['poster'], 'editorial', 'Armenia, URSS'))

    def test_un_fotograma_descartado_no_se_publica(self):
        desc = {'work_id': 'w_1', 'campo': 'afiche', 'valor': {'archivo': 'https://image.tmdb.org/t/p/w500/hoja.jpg', 'veredicto': 'fotograma'}}
        for o in (dict(O, poster='/assets/real.jpg', posterSource='oficial'), {k: v for k, v in O.items() if not k.startswith('poster')}):
            d = {'films': [copy.deepcopy(o)]}
            of.componer(d, [desc])
            self.assertEqual(d['films'][0].get('poster'), o.get('poster'))
        with self.assertRaises(SystemExit):
            of.sembrar('f', {'films': [copy.deepcopy(O)]}, [desc], 'x')

    def test_pais_solo_historico_no_deja_bandera_vieja(self):
        d = {'films': [dict(O)]}
        of.componer(d, [{'work_id': 'w_1', 'campo': 'paises', 'valor': ['SU']}])
        self.assertEqual((d['films'][0]['country'], 'flags' in d['films'][0]), ('URSS', False))

    def test_sinopsis_vacia_decidida_quita_todo(self):
        d = {'films': [copy.deepcopy(O)]}
        decs = []
        of.sembrar('f', d, decs, 'x')
        next(x for x in decs if x['campo'] == 'sinopsis.es')['valor'] = ''
        of.componer(d, decs)
        self.assertNotIn('synopsis_lang', d['films'][0])
        self.assertEqual(of.problemas('f', d, decs), [])

    def test_al_legado_no_entra_nadie(self):
        self.assertEqual(of.legado() - of.LEGADO_MAX, set())

    def test_decidir_otra_cosa_se_ve_en_el_festival(self):
        d, decs = {'films': [copy.deepcopy(O)]}, []
        of.sembrar('f', d, decs, 'x')
        next(x for x in decs if x['campo'] == 'anio')['valor'] = 2024
        self.assertEqual([x[1] for x in of.problemas('f', d, decs)], ['year'])
        of.componer(d, decs)
        self.assertEqual((d['films'][0]['year'], of.problemas('f', d, decs)), (2024, []))

    def test_eventos_y_obras_sin_id_no_se_tocan(self):
        d = {'films': [dict(O, type='event'), {k: v for k, v in O.items() if k != 'work_id'}]}
        self.assertEqual(of.desnudar(d), d)

    def test_todo_festival_publicado_esta_enrolado_o_en_el_legado_y_cumple(self):
        fs = ou._festivales()
        self.assertEqual([x for f, d in fs.items() if of.enrolado(f) for x in of.problemas(f, d)], [])


class Deshacer(unittest.TestCase):
    def test_vuelve_al_valor_anterior(self):
        vals = {'w_1': {'year': {'2024': ['a']}}}
        decs = [{'work_id': 'w_1', 'campo': 'anio', 'valor': 2024, 'motivo': 'm', 'fecha': 'f', 'quien': 'q'}]
        antes = copy.deepcopy(decs)
        ou.decidir(decs, vals, 'w_1', 'anio', '2025', 'otro', 'yo', 'hoy')
        ou.decidir(decs, vals, 'w_1', 'anio', '2026', 'otro', 'yo', 'hoy')
        deshacer.deshacer(decs, {}, 'w_1', 'anio')
        self.assertEqual(decs[0]['valor'], 2025)
        deshacer.deshacer(decs, {}, 'w_1', 'anio')
        decs[0].pop('antes')
        self.assertEqual(decs, antes)

    def test_la_primera_decision_devuelve_lo_de_cada_festival(self):
        fs = {'ficci-65': {'films': [{'title': 'X', 'type': 'film', 'work_id': 'w_1', 'year': 2025}]}, 'tiff-2026': {'films': [{'title': 'X', 'type': 'film', 'work_id': 'w_1', 'year': 2025}]}}
        decs = [{'work_id': 'w_1', 'campo': 'anio', 'valor': 2025, 'antes': {'ficci-65': '2023', 'tiff-2026': 2024}}]
        deshacer.deshacer(decs, fs, 'w_1', 'anio')
        self.assertEqual((decs, fs['ficci-65']['films'][0]['year'], fs['tiff-2026']['films'][0]['year']), ([], 2023, 2024))

    def test_no_corre_los_reemplazos_ni_deshace_lo_que_no_puede(self):
        a = {'work_id': 'w_1', 'campo': 'anio', 'valor': 1, 'antes': {'ficci-65': 2}}
        decs = [a, {'work_id': 'w_2', 'campo': 'anio', 'valor': 1}, {'work_id': 'w_2', 'campo': 'anio', 'valor': 2, 'reemplaza': 1}]
        deshacer.deshacer(decs, {}, 'w_1', 'anio')
        self.assertEqual(decs[1]['reemplaza'], 0)
        for x in (dict(a, sembrada=True), dict(a, campo='afiche', valor={'archivo': 'x', 'veredicto': 'oficial'}), dict(a, antes={'ficci-65': [1, 2]}), dict(a, antes={'nuevo-2027': 1})):
            with self.assertRaises(SystemExit):
                deshacer.deshacer([x], {}, 'w_1', x['campo'])

    def test_sin_memoria_no_inventa(self):
        with self.assertRaises(SystemExit):
            deshacer.deshacer([{'work_id': 'w_1', 'campo': 'anio', 'valor': 1}], {}, 'w_1', 'anio')


if __name__ == '__main__':
    unittest.main()
