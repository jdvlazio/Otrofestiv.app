"""El id estable de la función (docs/FUNCION.md §11). Juan (18 oct): cuando un
cambio DOBLE termina en id nuevo, el aviso tiene que ser VISIBLE al publicar,
con la función vieja y la nueva — quien la tenía en su plan la pierde."""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import funcion


def f(title='Parapeto', dia='2026-10-22', hora='19:00', sede='Cine - Bogotá', sala=''):
    return {'title': title, 'day': dia, 'time': hora, 'venue': sede, 'sala': sala, '_ancla': (sede, dia, hora)}


class Doble(unittest.TestCase):
    def test_cambio_doble_avisa_con_vieja_y_nueva(self):
        _, reg, _ = funcion.asignar_ids([f()], {})
        out, _, avisos = funcion.asignar_ids([f(title='Parapeto 2', hora='20:00')], reg)
        dobles = [a for a in avisos if a.startswith('⚠ id nuevo')]
        self.assertEqual(len(dobles), 1)
        self.assertIn('Parapeto 2', dobles[0])
        self.assertIn('parapeto', dobles[0].lower())
        self.assertIn('19:00', dobles[0])
        self.assertIn('20:00', dobles[0])

    def test_movida_no_es_doble(self):
        _, reg, _ = funcion.asignar_ids([f()], {})
        _, _, avisos = funcion.asignar_ids([f(hora='20:00')], reg)
        self.assertFalse([a for a in avisos if a.startswith('⚠ id nuevo')])

    def test_solo_avisa_por_la_que_nace(self):
        # A se queda, B sale, C nace (cambio doble de B): el aviso es por C, no por A
        _, reg, _ = funcion.asignar_ids([f(), f(title='B', hora='21:00')], {})
        _, _, avisos = funcion.asignar_ids([f(), f(title='C', hora='22:00')], reg)
        dobles = [a for a in avisos if a.startswith('⚠ id nuevo')]
        self.assertTrue(dobles)
        self.assertTrue(all('«C»' in a for a in dobles))

    def test_funcion_nueva_sin_salida_no_es_doble(self):
        _, reg, _ = funcion.asignar_ids([f()], {})
        _, _, avisos = funcion.asignar_ids([f(), f(title='Otra', hora='21:00')], reg)
        self.assertFalse([a for a in avisos if a.startswith('⚠ id nuevo')])


def pub(*fs):
    return {'films': [dict(id=i, title=t, day=d, time=h, venue='V') for i, t, d, h in fs]}


class Estable(unittest.TestCase):
    """[id-funcion-estable]: contra main, un id publicado no desaparece ni cambia
    de función; uno nuevo es una función nueva."""
    R = {'funciones': {}}

    def p(self, a, b, reg=None):
        return funcion.ids_estables(a, b, reg or self.R)

    def test_igual_sano(self):
        self.assertEqual(self.p(pub(('f_1', 'A', 'd1', '19:00')), pub(('f_1', 'A', 'd1', '19:00'))), [])

    def test_movida_o_renombrada_sana(self):
        self.assertEqual(self.p(pub(('f_1', 'A', 'd1', '19:00')), pub(('f_1', 'A', 'd1', '20:00'))), [])
        self.assertEqual(self.p(pub(('f_1', 'A', 'd1', '19:00')), pub(('f_1', 'B', 'd1', '19:00'))), [])

    def test_id_que_desaparece_frena(self):
        self.assertTrue(self.p(pub(('f_1', 'A', 'd1', '19:00')), pub(('f_2', 'A', 'd1', '19:00'))))

    def test_desaparece_pero_registrado_ausente_sano(self):
        reg = {'funciones': {'f_1': {'ausente': True}}}
        self.assertEqual(self.p(pub(('f_1', 'A', 'd1', '19:00')), pub(), reg), [])

    def test_mismo_id_otra_funcion_frena(self):
        r = self.p(pub(('f_1', 'A', 'd1', '19:00')), pub(('f_1', 'B', 'd2', '21:00')))
        self.assertTrue(r and 'cambió de función' in r[0])

    def test_id_repetido_frena(self):
        self.assertTrue(self.p(pub(), pub(('f_1', 'A', 'd1', '19:00'), ('f_1', 'B', 'd1', '20:00'))))

    def test_sin_ids_en_main_no_mide(self):
        self.assertEqual(self.p({'films': [{'title': 'A'}]}, pub(('f_1', 'A', 'd1', '19:00'))), [])


D = {'por_que': 'el festival lo confirmó', 'quien': 'juan', 'fecha': '2026-10-18'}


def clave(**k):
    c = funcion._clave(f(**k))
    return {**c, 'titulo': k.get('title', 'Parapeto')}


def ids(out):
    return [x['_fid'] for x in out]


class Trasladada(unittest.TestCase):
    """§11.3.3: mismo título, día y hora en OTRA sede → la misma función."""

    def test_cambio_de_sede_conserva_id(self):
        out0, reg, _ = funcion.asignar_ids([f()], {})
        out1, _, av = funcion.asignar_ids([f(sede='Otra - Bogotá')], reg)
        self.assertEqual(ids(out0), ids(out1))
        self.assertTrue(any('trasladada' in a for a in av))
        self.assertFalse([a for a in av if a.startswith('⚠')])

    def test_dos_candidatas_es_ambigua(self):
        # la misma obra a la misma hora en dos sedes y sale una de ellas
        _, reg, _ = funcion.asignar_ids([f(sede='A - X'), f(sede='B - X')], {})
        out, _, av = funcion.asignar_ids([f(sede='C - X')], reg)
        self.assertTrue(any('ambigua' in a for a in av))
        self.assertNotIn(ids(out)[0], reg['funciones'])

    def test_sede_y_hora_no_es_trasladada(self):
        out0, reg, _ = funcion.asignar_ids([f()], {})
        out1, _, _ = funcion.asignar_ids([f(sede='Otra - X', hora='21:00')], reg)
        self.assertNotEqual(ids(out0), ids(out1))


class Decision(unittest.TestCase):
    """§11.3.4: el cambio doble no se adivina; lo resuelve una decisión registrada."""

    def setUp(self):
        self.out0, self.reg, _ = funcion.asignar_ids([f()], {})
        self.viejo = ids(self.out0)[0]
        self.nueva = f(title='Parapeto 2', hora='20:00')

    def test_misma_conserva_id_y_no_avisa(self):
        dec = [{'viejo': self.viejo, 'nuevo': clave(title='Parapeto 2', hora='20:00'), **D}]
        out, reg, av = funcion.asignar_ids([self.nueva], self.reg, dec)
        self.assertEqual(ids(out), [self.viejo])
        self.assertFalse([a for a in av if a.startswith('⚠')])
        self.assertTrue(reg['funciones'][self.viejo].get('decidida'))

    def test_es_otra_calla_el_aviso_y_da_id_nuevo(self):
        dec = [{'viejo': self.viejo, 'nuevo': 'es_otra', **D}]
        out, _, av = funcion.asignar_ids([self.nueva], self.reg, dec)
        self.assertNotEqual(ids(out), [self.viejo])
        self.assertFalse([a for a in av if a.startswith('⚠')])

    def test_sin_por_que_es_invalida(self):
        for falta in ('por_que', 'quien', 'fecha'):
            d = {'viejo': self.viejo, 'nuevo': 'es_otra', **D}
            d.pop(falta)
            with self.assertRaises(funcion.AfirmacionInvalida):
                funcion.asignar_ids([self.nueva], self.reg, [d])

    def test_viejo_desconocido_es_invalida(self):
        with self.assertRaises(funcion.AfirmacionInvalida):
            funcion.asignar_ids([self.nueva], self.reg, [{'viejo': 'f_0000000000', 'nuevo': 'es_otra', **D}])

    def test_decision_que_no_encuentra_su_funcion_avisa(self):
        dec = [{'viejo': self.viejo, 'nuevo': clave(title='Nada', hora='23:00'), **D}]
        _, _, av = funcion.asignar_ids([self.nueva], self.reg, dec)
        self.assertTrue(any(a.startswith('⚠ decisión') for a in av))

    def test_la_decision_le_gana_a_la_heuristica(self):
        # sin decisión, «Parapeto» a las 20:00 se casaría como movida; la decisión dice que es otra
        dec = [{'viejo': self.viejo, 'nuevo': 'es_otra', **D}]
        out, _, _ = funcion.asignar_ids([f(hora='20:00')], self.reg, dec)
        self.assertNotEqual(ids(out), [self.viejo])

    def test_guardian_acepta_el_cambio_decidido(self):
        dec = [{'viejo': self.viejo, 'nuevo': clave(title='Parapeto 2', hora='20:00'), **D}]
        _, reg, _ = funcion.asignar_ids([self.nueva], self.reg, dec)
        a = pub((self.viejo, 'Parapeto', 'd1', '19:00'))
        b = pub((self.viejo, 'Parapeto 2', 'd1', '20:00'))
        self.assertEqual(funcion.ids_estables(a, b, reg), [])
        self.assertTrue(funcion.ids_estables(a, b, self.reg))   # sin decisión, frena


class PartirFusionar(unittest.TestCase):
    """§11.4: el id viejo queda marcado en el registro y viaja en ids_anteriores."""

    def test_partida(self):
        out0, reg, _ = funcion.asignar_ids([f(title='Programa')], {})
        v = ids(out0)[0]
        h1, h2 = f(title='Corto 1'), f(title='Corto 2', hora='20:00')
        dec = [{'viejo': v, 'partida': [clave(title='Corto 1'), clave(title='Corto 2', hora='20:00')], **D}]
        out, reg2, av = funcion.asignar_ids([h1, h2], reg, dec)
        self.assertNotIn(v, ids(out))
        self.assertEqual(reg2['funciones'][v]['partida_en'], ids(out))
        self.assertEqual(out[0].get('_ids_anteriores'), [v])
        self.assertFalse(out[1].get('_ids_anteriores'))
        self.assertFalse([a for a in av if a.startswith('⚠')])

    def test_fusion(self):
        out0, reg, _ = funcion.asignar_ids([f(title='A'), f(title='B', hora='21:00')], {})
        a, b = ids(out0)
        dec = [{'viejo': a, 'nuevo': clave(title='A y B'), 'absorbe': [b], **D}]
        out, reg2, av = funcion.asignar_ids([f(title='A y B')], reg, dec)
        self.assertEqual(ids(out), [a])
        self.assertEqual(out[0].get('_ids_anteriores'), [b])
        self.assertEqual(reg2['funciones'][b]['fusionada_en'], a)
        self.assertFalse([x for x in av if x.startswith('⚠')])

    def test_ids_anteriores_persisten_en_el_registro(self):
        out0, reg, _ = funcion.asignar_ids([f(title='A'), f(title='B', hora='21:00')], {})
        a, b = ids(out0)
        dec = [{'viejo': a, 'nuevo': clave(title='A y B'), 'absorbe': [b], **D}]
        _, reg2, _ = funcion.asignar_ids([f(title='A y B')], reg, dec)
        out, _, _ = funcion.asignar_ids([f(title='A y B')], reg2)    # siguiente montaje, sin re-decidir
        self.assertEqual(out[0].get('_ids_anteriores'), [b])

    def test_guardian_acepta_partida_y_fusion(self):
        out0, reg, _ = funcion.asignar_ids([f(title='A'), f(title='B', hora='21:00')], {})
        a, b = ids(out0)
        dec = [{'viejo': a, 'nuevo': clave(title='A y B'), 'absorbe': [b], **D}]
        _, reg2, _ = funcion.asignar_ids([f(title='A y B')], reg, dec)
        self.assertEqual(funcion.ids_estables(pub((a, 'A', 'd', '19:00'), (b, 'B', 'd', '21:00')),
                                              pub((a, 'A y B', 'd', '19:00')), reg2), [])

    def test_partida_no_se_ofrece_como_la_que_salio(self):
        out0, reg, _ = funcion.asignar_ids([f(title='Programa')], {})
        v = ids(out0)[0]
        dec = [{'viejo': v, 'partida': [clave(title='Corto 1')], **D}]
        _, _, av = funcion.asignar_ids([f(title='Corto 1'), f(title='Otra', hora='22:00')], reg, dec)
        self.assertFalse([a for a in av if a.startswith('⚠') and v in a])

    def test_hijas_no_avisan_aunque_salga_otra(self):
        out0, reg, _ = funcion.asignar_ids([f(title='Programa'), f(title='X', dia='2026-10-25', hora='10:00')], {})
        v = ids(out0)[0]
        dec = [{'viejo': v, 'partida': [clave(title='Corto 1'), clave(title='Corto 2', hora='20:00')], **D}]
        _, _, av = funcion.asignar_ids([f(title='Corto 1'), f(title='Corto 2', hora='20:00')], reg, dec)
        self.assertFalse([a for a in av if a.startswith('⚠ id nuevo')])


class Auditoria(unittest.TestCase):
    """Los hallazgos de la auditoría independiente del 18 oct, uno por test."""

    def base(self):
        out, reg, _ = funcion.asignar_ids([f(title='Uno', hora='10:00'), f(title='Dos', hora='12:00'),
                                           f(title='Tres', dia='2026-10-23', hora='10:00')], {})
        return ids(out), reg

    def test_dos_decisiones_a_la_misma_clave_frenan(self):
        (a, _, c), reg = self.base()
        dest = clave(title='Uno X', dia='2026-10-24', hora='10:00')
        with self.assertRaises(funcion.AfirmacionInvalida):
            funcion.asignar_ids([f(title='Uno X', dia='2026-10-24', hora='10:00')], reg,
                                [{'viejo': a, 'nuevo': dest, **D}, {'viejo': c, 'nuevo': dest, **D}])

    def test_el_mismo_viejo_dos_veces_frena(self):
        (a, _, _), reg = self.base()
        with self.assertRaises(funcion.AfirmacionInvalida):
            funcion.asignar_ids([f(title='Uno X')], reg, [{'viejo': a, 'nuevo': clave(title='Uno X'), **D},
                                                          {'viejo': a, 'nuevo': 'es_otra', **D}])

    def test_fusion_consigo_misma_frena(self):
        (a, _, _), reg = self.base()
        with self.assertRaises(funcion.AfirmacionInvalida):
            funcion.asignar_ids([f(title='Uno X')], reg, [{'viejo': a, 'nuevo': clave(title='Uno X'), 'absorbe': [a], **D}])

    def test_clave_exacta_no_reusa_un_id_ya_tomado(self):
        (a, b, c), reg = self.base()
        out, _, _ = funcion.asignar_ids([f(title='Tres X', dia='2026-10-24', hora='10:00'),
                                         f(title='Tres', dia='2026-10-23', hora='10:00')], reg,
                                        [{'viejo': c, 'nuevo': clave(title='Tres X', dia='2026-10-24', hora='10:00'), **D}])
        self.assertEqual(len(set(ids(out))), 2)

    def test_decidida_se_cae_cuando_la_funcion_vuelve_a_cambiar(self):
        out0, reg, _ = funcion.asignar_ids([f()], {})
        v = ids(out0)[0]
        _, reg, _ = funcion.asignar_ids([f(title='P2', hora='20:00')], reg,
                                        [{'viejo': v, 'nuevo': clave(title='P2', hora='20:00'), **D}])
        _, reg, _ = funcion.asignar_ids([f(title='P2', hora='21:00')], reg)       # se movió otra vez, sin decisión
        self.assertFalse(reg['funciones'][v].get('decidida'))

    def test_absorbida_presente_frena(self):
        (a, b, _), reg = self.base()
        with self.assertRaises(funcion.AfirmacionInvalida):
            funcion.asignar_ids([f(title='Uno y Dos', hora='10:00'), f(title='Dos', hora='12:00')], reg,
                                [{'viejo': a, 'nuevo': clave(title='Uno y Dos', hora='10:00'), 'absorbe': [b], **D}])

    def test_es_otra_sobre_presente_frena(self):
        (a, _, _), reg = self.base()
        with self.assertRaises(funcion.AfirmacionInvalida):
            funcion.asignar_ids([f(title='Uno', hora='10:00')], reg, [{'viejo': a, 'nuevo': 'es_otra', **D}])

    def test_madre_de_partida_presente_frena(self):
        (a, _, _), reg = self.base()
        with self.assertRaises(funcion.AfirmacionInvalida):
            funcion.asignar_ids([f(title='Uno', hora='10:00'), f(title='Corto')], reg,
                                [{'viejo': a, 'partida': [clave(title='Corto')], **D}])

    def test_rearmado_sin_avisos_espurios(self):
        (a, b, _), reg = self.base()
        fs = [f(title='Uno y Dos', hora='10:00')]
        dec = [{'viejo': a, 'nuevo': clave(title='Uno y Dos', hora='10:00'), 'absorbe': [b], **D}]
        out1, reg1, _ = funcion.asignar_ids(fs, reg, dec)
        out2, reg2, av = funcion.asignar_ids(fs, reg1, dec)
        self.assertEqual((ids(out1), reg1), (ids(out2), reg2))
        self.assertFalse([x for x in av if 'movida' in x])

    def test_guardian_frena_fusion_con_destino_no_publicado(self):
        reg = {'funciones': {'f_b': {'fusionada_en': 'f_a'}}}
        self.assertTrue(funcion.ids_estables(pub(('f_b', 'B', 'd', '1')), pub(('f_c', 'C', 'd', '2')), reg))
        reg = {'funciones': {'f_b': {'partida_en': ['f_x', 'f_y']}}}
        self.assertTrue(funcion.ids_estables(pub(('f_b', 'B', 'd', '1')), pub(('f_x', 'X', 'd', '2')), reg))
        self.assertEqual(funcion.ids_estables(pub(('f_b', 'B', 'd', '1')),
                                              pub(('f_x', 'X', 'd', '2'), ('f_y', 'Y', 'd', '3')), reg), [])

    def test_madre_que_reaparece_despues_no_recupera_su_id(self):
        out0, reg, _ = funcion.asignar_ids([f(title='Programa')], {})
        v = ids(out0)[0]
        _, reg, _ = funcion.asignar_ids([f(title='Corto 1', hora='20:00')], reg,
                                        [{'viejo': v, 'partida': [clave(title='Corto 1', hora='20:00')], **D}])
        out, _, _ = funcion.asignar_ids([f(title='Corto 1', hora='20:00'), f(title='Programa')], reg)
        self.assertNotIn(v, ids(out))


if __name__ == '__main__':
    unittest.main()
