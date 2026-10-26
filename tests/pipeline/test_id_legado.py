"""El id estable para TODO festival (docs/FUNCION.md §11.6 paso 4): los de
legado reciben el id desde lo publicado, sin rearmar (rearmar traería cambios
del pipeline que nadie revisó: 15 de 22 builds difieren hoy de lo publicado), y
el ensamblador se los conserva cuando el festival se rearma."""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import funcion


def pub(title='Parapeto', day='2026-10-22', time='19:00', venue='Cine - Bogotá', **kw):
    return {'title': title, 'day': day, 'time': time, 'venue': venue, **kw}


def montaje(p):
    """La misma función como la ve el ensamblador: _ancla = (sede, día, hora)."""
    return {**p, '_ancla': (p['venue'], p['day'], p['time'])}


class Legado(unittest.TestCase):
    def test_solo_agrega_id(self):
        fs = [pub(), pub(title='Otra', time='21:00', sala='2')]
        out, _ = funcion.ids_para_publicado(fs, {})
        for a, b in zip(fs, out):
            self.assertEqual({k: v for k, v in b.items() if k != 'id'}, a)
            self.assertRegex(b['id'], r'^f_[0-9a-f]{10}$')
        self.assertEqual(len({x['id'] for x in out}), 2)

    def test_no_toca_lo_que_recibe(self):
        fs = [pub()]
        funcion.ids_para_publicado(fs, {})
        self.assertNotIn('id', fs[0])

    def test_entrada_sin_horario_no_es_funcion(self):
        out, reg = funcion.ids_para_publicado([pub(), {'title': 'Cortometraje Ficción'}], {})
        self.assertIn('id', out[0])
        self.assertNotIn('id', out[1])
        self.assertEqual(len(reg['funciones']), 1)

    def test_idempotente(self):
        out1, reg1 = funcion.ids_para_publicado([pub(), pub(title='B', time='20:00')], {})
        out2, reg2 = funcion.ids_para_publicado(out1, reg1)
        self.assertEqual((out1, reg1), (out2, reg2))

    def test_el_ensamblador_conserva_el_id_del_legado(self):
        # la garantía de compatibilidad: rearmar después no cambia ningún id
        fs = [pub(), pub(title='B', time='20:00', sala='Sala 2')]
        out, reg = funcion.ids_para_publicado(fs, {})
        arm, _, av = funcion.asignar_ids([montaje(p) for p in fs], reg)
        self.assertEqual([x['id'] for x in out], [x['_fid'] for x in arm])
        # por CLAVE EXACTA, no rescatada por la heurística (movida / renombrada)
        self.assertEqual(av, [])

    def test_el_ensamblador_conserva_el_id_aunque_cambie_la_caja(self):
        # rearmar un festival viejo cambia la caja de títulos (Caja de Título, 15 oct)
        out, reg = funcion.ids_para_publicado([pub(title='EL PARAPETO')], {})
        arm, _, av = funcion.asignar_ids([montaje(pub(title='El Parapeto'))], reg)
        self.assertEqual(out[0]['id'], arm[0]['_fid'])
        self.assertEqual(av, [])

    def test_un_id_ya_publicado_se_respeta(self):
        # BHFF/Fantasmagoría/Ficcali ya tienen id: la pasada no los recalcula
        out, _ = funcion.ids_para_publicado([pub(id='f_0123456789')], {})
        self.assertEqual(out[0]['id'], 'f_0123456789')


class Montaje(unittest.TestCase):
    """El ensamblador da id a todo festival, tenga o no afirmaciones."""

    def test_sin_afirmaciones_tambien_publica_id(self):
        fs = [montaje(pub()), montaje(pub(title='B', time='20:00'))]
        out, reg, _ = funcion.ids_del_montaje(fs, {}, [])
        self.assertTrue(all(x.get('id') == x.get('_fid') and x['id'] for x in out))
        self.assertEqual(len(reg['funciones']), 2)

    def test_sin_ancla_no_inventa(self):
        # un build viejo sin _ancla no se toca (no hay con qué casar): sale igual
        fs = [pub()]
        out, reg, av = funcion.ids_del_montaje(fs, {'funciones': {}}, [])
        self.assertEqual(out, fs)
        self.assertTrue(av and 'sin _ancla' in av[0])

    def test_publica_ids_anteriores(self):
        f0 = montaje(pub(title='A'))
        _, reg, _ = funcion.ids_del_montaje([f0, montaje(pub(title='B', time='21:00'))], {}, [])
        a, b = list(reg['funciones'])
        D = {'por_que': 'p', 'quien': 'q', 'fecha': '2026-10-18'}
        nuevo = funcion._clave(montaje(pub(title='A y B')))
        out, _, _ = funcion.ids_del_montaje([montaje(pub(title='A y B'))], reg,
                                            [{'viejo': a, 'nuevo': nuevo, 'absorbe': [b], **D}])
        self.assertEqual(out[0]['ids_anteriores'], [b])


if __name__ == '__main__':
    unittest.main()


class Formato(unittest.TestCase):
    """La pasada de legado reescribe el JSON publicado: el único cambio debe ser `id`."""

    def test_todos_los_publicados_se_reescriben_byte_a_byte(self):
        import glob
        raiz = os.path.join(os.path.dirname(__file__), '..', '..', 'festivals')
        for p in sorted(glob.glob(os.path.join(raiz, '*.json'))):
            raw = open(p, encoding='utf-8').read()
            self.assertEqual(funcion.volcar_como(raw, __import__('json').loads(raw)), raw, p)

    def test_formato_desconocido_frena(self):
        with self.assertRaises(funcion.AfirmacionInvalida):
            funcion.volcar_como('{ "a" :1}', {'a': 1})
