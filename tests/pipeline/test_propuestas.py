"""La cola de propuestas (docs/FUNCION.md §5): lo que traen el vigía y la
agenda de las salas entra como PROPUESTA; Juan acepta o rechaza; lo aceptado
pasa a ser afirmación. Nada entra sin su sí, nada se pierde, nada se repite.
Los casos marcados «A<n>» vienen de la auditoría independiente del 16 oct."""
import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import funcion, propuestas

HOY = '2026-10-16'


def af(valor='Sala 1', casilla='sala', fecha='2026-10-15', **kw):
    return {'ancla': {'sede': 'Cinemateca de Bogotá - Bogotá', 'dia': '2026-10-23', 'hora': '19:00'},
            'casilla': casilla, 'valor': valor,
            'fuente': {'tipo': 'sala', 'url': 'https://cinemateca.example/3620', 'fecha': fecha},
            'evidencia': 'Octubre 23 7:00 PM / ' + str(valor), **kw}


class Base(unittest.TestCase):
    def setUp(self):
        self.raiz = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.raiz, 'festivals', 'staging'))
        self.modelo('f')
        self.armados = []
        self.armado_ok = [True, True]          # antes, después

    def armar(self, fid):
        ok = self.armado_ok[len(self.armados)]
        self.armados.append(fid)
        return ok, '' if ok else '✗ conflicto'

    def modelo(self, fid, afs=()):
        json.dump({'_provenance': {'capturado': HOY}, 'afirmaciones': list(afs)},
                  open(self._p(fid, 'afirmaciones'), 'w'))

    def _p(self, fid, k):
        return os.path.join(self.raiz, 'festivals', 'staging', f'{fid}-{k}.json')

    def afs(self, fid='f'):
        return json.load(open(self._p(fid, 'afirmaciones')))['afirmaciones']

    def cola(self, fid='f'):
        return propuestas.leer(fid, self.raiz)['propuestas']

    def prop(self, a=None, fid='f'):
        return propuestas.proponer(fid, a or af(), 'salas-agenda', raiz=self.raiz, fecha_hoy=HOY)

    def decidir(self, ids, accion, fid='f', frase='Sí, dale'):
        return propuestas.decidir(fid, ids, accion, frase, raiz=self.raiz, fecha_hoy=HOY, armar=self.armar)


class Proponer(Base):
    def test_nueva_queda_pendiente(self):
        estado, pid = self.prop()
        self.assertEqual(estado, 'nueva')
        p = self.cola()[0]
        self.assertEqual((p['id'], p['estado'], p['por']), (pid, 'pendiente', 'salas-agenda'))
        self.assertEqual(self.afs(), [], 'proponer NO escribe afirmaciones')

    def test_invalida_no_entra(self):
        malo = af()
        malo['fuente'].pop('url')
        with self.assertRaises(funcion.AfirmacionInvalida):
            self.prop(malo)
        self.assertEqual(self.cola(), [])

    def test_repetida_no_se_duplica(self):
        _, a = self.prop()
        self.assertEqual(self.prop(), ('ya-pendiente', a))
        self.assertEqual(len(self.cola()), 1)

    def test_lo_ya_afirmado_por_la_misma_fuente_no_se_propone(self):
        self.modelo('f', [af()])
        self.assertEqual(self.prop()[0], 'ya-afirmada')

    def test_A2_mismo_valor_de_una_fuente_mas_nueva_si_entra(self):
        self.modelo('f', [af('Sala 1'), af('Sala 2', fecha='2026-10-15')])
        self.assertEqual(self.prop(af('Sala 1', fecha='2026-10-16'))[0], 'nueva',
                         'la fuente más nueva puede devolverle el triunfo a Sala 1')

    def test_lo_rechazado_no_vuelve_de_la_misma_fuente(self):
        _, a = self.prop()
        self.decidir([a], 'rechazar')
        self.assertEqual(self.prop(), ('ya-rechazada', a))

    def test_A1_rechazado_vuelve_si_la_fuente_es_mas_nueva_y_lo_dice(self):
        _, a = self.prop()
        self.decidir([a], 'rechazar', frase='No, eso es de otra función')
        estado, b = self.prop(af(fecha='2026-10-16'))
        self.assertEqual(estado, 'nueva')
        p = next(x for x in self.cola() if x['id'] == b)
        self.assertEqual(p['rechazada_antes'], [{'id': a, 'frase': 'No, eso es de otra función'}])

    def test_otro_valor_es_otra_propuesta(self):
        _, a = self.prop()
        _, b = self.prop(af('Sala 2'))
        self.assertNotEqual(a, b)

    def test_id_estable(self):
        self.assertEqual(self.prop()[1], propuestas.id_de(af()))

    def test_A5_nadie_propone_en_nombre_de_juan(self):
        j = af()
        j['fuente'] = {'tipo': 'juan', 'frase': 'x', 'fecha': '2026-10-15'}
        j['contra'] = 'Sala 2'
        with self.assertRaisesRegex(funcion.AfirmacionInvalida, 'Juan'):
            self.prop(j)

    def test_A6_festival_fuera_del_modelo_no_tiene_cola(self):
        os.remove(self._p('f', 'afirmaciones'))
        with self.assertRaisesRegex(funcion.AfirmacionInvalida, 'modelo'):
            self.prop()
        self.assertFalse(os.path.exists(self._p('f', 'propuestas')))


class Decidir(Base):
    def test_aceptar_la_vuelve_afirmacion_con_su_fuente(self):
        _, a = self.prop()
        self.assertEqual(self.decidir([a], 'aceptar'), 1)
        x = self.afs()[0]
        self.assertEqual((x['valor'], x['fuente']['tipo'], x['propuesta']), ('Sala 1', 'sala', a))
        p = self.cola()[0]
        self.assertEqual(p['estado'], 'aceptada')
        self.assertEqual(p['decision'], {'fecha': HOY, 'frase': 'Sí, dale'})
        self.assertEqual(self.armados, ['f', 'f'], 'el armado real corre antes y después')

    def test_rechazar_no_toca_afirmaciones_ni_arma(self):
        _, a = self.prop()
        self.decidir([a], 'rechazar')
        self.assertEqual(self.afs(), [])
        self.assertEqual(self.cola()[0]['estado'], 'rechazada')
        self.assertEqual(self.armados, [])

    def test_A3_si_el_armado_frena_se_deshace_todo(self):
        _, a = self.prop()
        self.armado_ok = [True, False]
        with self.assertRaises(propuestas.ArmadoRoto):
            self.decidir([a], 'aceptar')
        self.assertEqual(self.afs(), [])
        self.assertEqual(self.cola()[0]['estado'], 'pendiente')
        self.assertNotIn('decision', self.cola()[0])

    def test_A3_armado_que_ya_fallaba_no_se_toca(self):
        _, a = self.prop()
        self.armado_ok = [False]
        with self.assertRaisesRegex(propuestas.ArmadoRoto, 'ANTES'):
            self.decidir([a], 'aceptar')
        self.assertEqual(self.afs(), [])
        self.assertEqual(self.cola()[0]['estado'], 'pendiente')

    def test_todas_es_solo_las_pendientes(self):
        _, a = self.prop()
        self.prop(af('Sala 2'))
        self.decidir([a], 'rechazar')
        self.assertEqual(self.decidir('todas', 'aceptar'), 1)
        self.assertEqual([x['valor'] for x in self.afs()], ['Sala 2'])

    def test_todas_sin_pendientes_es_cero_y_no_arma(self):
        self.assertEqual(self.decidir('todas', 'aceptar'), 0)
        self.assertEqual(self.armados, [])

    def test_A7_sin_ids_no_es_cero_callado(self):
        with self.assertRaises(ValueError):
            self.decidir([], 'aceptar')

    def test_sin_frase_no_hay_decision(self):
        _, a = self.prop()
        with self.assertRaises(ValueError):
            self.decidir([a], 'aceptar', frase='')

    def test_id_desconocido_no_decide_nada(self):
        _, a = self.prop()
        with self.assertRaisesRegex(KeyError, 'desconocida.*pzzzzzzzz'):
            self.decidir([a, 'pzzzzzzzz'], 'aceptar')
        self.assertEqual(self.afs(), [], 'todo o nada')
        self.assertEqual(self.cola()[0]['estado'], 'pendiente')

    def test_ya_decidida_no_se_redecide(self):
        _, a = self.prop()
        self.decidir([a], 'aceptar')
        with self.assertRaises(ValueError):
            self.decidir([a], 'rechazar')

    def test_festival_que_salio_del_modelo_no_acepta(self):
        _, a = self.prop()
        os.remove(self._p('f', 'afirmaciones'))
        with self.assertRaises(funcion.AfirmacionInvalida):
            self.decidir([a], 'aceptar')
        self.assertFalse(os.path.exists(self._p('f', 'afirmaciones')), 'no se crea el modelo por la puerta de atrás')

    def test_accion_desconocida(self):
        _, a = self.prop()
        with self.assertRaises(ValueError):
            self.decidir([a], 'borrar')

    def test_A4_escritura_atomica_no_deja_temporales(self):
        _, a = self.prop()
        self.decidir([a], 'aceptar')
        self.assertEqual([x for x in os.listdir(os.path.join(self.raiz, 'festivals', 'staging')) if x.endswith('.tmp')], [])


class Verificar(Base):
    def problemas(self):
        return propuestas.verificar(self.raiz)

    def editar(self, fn, k='propuestas'):
        p = self._p('f', k)
        d = json.load(open(p))
        fn(d)
        json.dump(d, open(p, 'w'))

    def test_cola_sana(self):
        _, a = self.prop()
        self.decidir([a], 'aceptar')
        self.prop(af('Sala 2'))
        self.assertEqual(self.problemas(), [])

    def test_aceptada_que_no_llego(self):
        _, a = self.prop()
        self.decidir([a], 'aceptar')
        self.modelo('f', [])
        self.assertTrue(any('no está en' in x for x in self.problemas()))

    def test_A4_afirmacion_de_propuesta_que_la_cola_no_acepto(self):
        _, a = self.prop()
        self.modelo('f', [{**af(), 'propuesta': a}])
        self.assertTrue(any('no la tiene aceptada' in x for x in self.problemas()))

    def test_A6_rechazada_que_esta_en_afirmaciones(self):
        _, a = self.prop()
        self.decidir([a], 'rechazar')
        self.modelo('f', [af()])
        self.assertTrue(any('rechazada pero está' in x for x in self.problemas()))

    def test_A6_cola_de_festival_fuera_del_modelo(self):
        self.prop()
        os.remove(self._p('f', 'afirmaciones'))
        self.assertTrue(any('no está en el modelo' in x for x in self.problemas()))

    def test_A6_pendiente_editada_a_mano_queda_invalida(self):
        self.prop()
        self.editar(lambda d: d['propuestas'][0]['afirmacion']['fuente'].pop('url'))
        self.assertTrue(any('inválida' in x for x in self.problemas()))

    def test_estado_raro(self):
        self.prop()
        self.editar(lambda d: d['propuestas'][0].__setitem__('estado', 'quizas'))
        self.assertTrue(any('quizas' in x and 'desconocido' in x for x in self.problemas()))

    def test_decidida_sin_frase(self):
        _, a = self.prop()
        self.decidir([a], 'rechazar')
        self.editar(lambda d: d['propuestas'][0].__setitem__('decision', {'fecha': HOY}))
        self.assertTrue(any('sin frase' in x for x in self.problemas()))

    def test_id_que_no_corresponde(self):
        self.prop()
        self.editar(lambda d: d['propuestas'][0]['afirmacion'].__setitem__('valor', 'Sala 9'))
        self.assertTrue(any('no corresponde' in x for x in self.problemas()))

    def test_pendientes_de_todos(self):
        self.prop()
        self.modelo('g')
        self.prop(fid='g')
        self.assertEqual(sorted(propuestas.pendientes(self.raiz)), ['f', 'g'])


class Cli(Base):
    def test_A7_todas_va_sola(self):
        with self.assertRaises(SystemExit):
            propuestas.main(['aceptar', 'f', 'todas', 'p123', '--frase', 'x'])

    def test_A7_sin_ids_es_error(self):
        with self.assertRaises(SystemExit):
            propuestas.main(['aceptar', 'f', '--frase', 'x'])


if __name__ == '__main__':
    unittest.main()
