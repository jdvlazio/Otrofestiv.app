"""La función publicada la releyó otro y su acceso tiene fuente (24 nov 2026, BOGOSHORTS)."""
import contextlib, importlib.util, io, json, os, sys, tempfile, unittest
from unittest import mock
RAIZ = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, os.path.join(RAIZ, 'pipeline'))
import sello_funcion as s

HOY, FID = '2026-11-24', 'prueba-2026'
F = {'id': 'f_1', 'title': 'X', 'day': '2026-12-01', 'time': '19:00', 'venue': 'Sala - Bogotá', 'is_free': True, 'has_qa': False}
PAGO = {'alcance': 'sede', 'nombre': 'Sala - Bogotá', 'nivel': 'declarado', 'acceso': 'pago', 'cita': 'Boleta $10.000', 'url': 'https://x/a.pdf'}
LIBRE = {'alcance': 'festival', 'nombre': FID, 'nivel': 'sin-aviso', 'acceso': 'gratis', 'documentos_revisados': ['https://x/acreditaciones.pdf']}
CERRADO = {'_provenance': {'capturado': '2026-11-24T08:00'}, 'raices': {'web': 'https://x', 'bio': 'https://y'}, 'items': {'https://x/a.pdf': {'estado': 'usada'}}}


def fest(*a, **k):
    return {'films': list(a) or [dict(F, **k)], 'venues': {'Sala - Bogotá': {'short': 'Sala'}}}


def indice(*ids, roto=False):
    def abrir(url, timeout=None):
        if roto:
            raise OSError('sin red')
        return io.BytesIO(json.dumps({'festivales': {i: {'archivo': 'x'} for i in ids or ('otro',)}}).encode())
    return abrir


class Base(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        p = mock.patch.object(s, 'STAGING', t.name); p.start(); self.addCleanup(p.stop)
        self.pon('fuentes', CERRADO); self.pon('acceso', [LIBRE]); self.sella(fest())

    def pon(self, que, d):
        with open(s._ruta(FID, que), 'w', encoding='utf-8') as fh:
            json.dump(d, fh)

    def lote(self, d, **k):
        lt = s.lote(FID, d)
        for e in lt['funciones']:
            e.update(dict(monta='a', verifica='b', contra='https://x/prog.pdf p. 3', veredicto='fiel'), **k)
        return lt

    def sella(self, d, **k):
        return s.sellar(self.lote(d, **k), d)

    def control(self, d, *ids, **k):
        return s.control(FID, d, indice(*ids, **k), HOY, modelo=False)

    def frena(self, d, texto):
        f, _ = self.control(d)
        self.assertTrue(any(texto in x for x in f), f)


class Primera(Base):
    def test_todo_en_orden_pasa(self):
        self.assertEqual(self.control(fest()), ([], []))
        self.assertEqual(s.autoprueba(), [])

    def test_hora_cambiada(self):
        self.frena(fest(time='20:00'), 'cambió después del sello')

    def test_funcion_nueva(self):
        self.frena(fest(F, dict(F, id='f_2')), 'f_2: sin sello')

    def test_cada_campo_de_la_huella(self):
        for c in s.CAMPOS:
            with self.subTest(c):
                self.assertTrue(s.faltan(fest(**{c: 'otro'}), *s.sidecars(FID)))
        # y la lista misma: quitar un campo de CAMPOS tiene que romper el test
        self.assertEqual(set(s.CAMPOS), {'title', 'day', 'date', 'time', 'hasta', 'film_start', 'venue', 'sala', 'info', 'unscheduled',
            'has_qa', 'qa_type', 'is_free', 'requires_registration', 'registration_url', 'ticket_url', 'by_invitation', 'online',
            'stream_url', 'stream_platform', 'audience'})

    def test_lo_heredado_entra_en_la_huella(self):
        for c in s.ACCESO:
            d = fest(); d['venues']['Sala - Bogotá'][c] = 'x'
            with self.subTest('sede ' + c):
                self.assertTrue(s.faltan(d, *s.sidecars(FID)))
        for c in ('ticket_url', 'ticketing_model', 'acceso_por_defecto'):
            with self.subTest('festival ' + c):
                self.assertTrue(s.faltan(dict(fest(), **{c: 'x'}), *s.sidecars(FID)))
        for c in ('nivel', 'acceso', 'cita', 'url', 'documentos_revisados'):
            with self.subTest('entrada ' + c):
                self.assertTrue(s.faltan(fest(), s.sidecars(FID)[0], [dict(LIBRE, **{c: 'x'})]))

    def test_funcion_dentro_de_screenings(self):
        d = fest({'title': 'O', 'is_free': True, 'screenings': [dict(F, title='O'), dict(F, title='O', id='f_2')]})
        self.assertEqual(set(s.funciones(d)), {'f_1', 'f_2'})
        self.sella(d)
        d['films'][0]['screenings'][1]['time'] = '21:00'
        self.assertEqual([k for k, _, _ in s.faltan(d, *s.sidecars(FID))], ['f_2'])

    def test_claves_repetidas_no_se_pisan(self):
        self.assertEqual(len(s.funciones(fest(F, F))), 2)

    def test_sin_acceso(self):
        self.pon('acceso', [])
        self.frena(fest(), 'sin acceso con fuente')

    def test_gratis_sin_documentos(self):
        self.pon('acceso', [dict(LIBRE, documentos_revisados=[])])
        self.frena(fest(), 'sin documentos')

    def test_sin_aviso_no_puede_ser_pago(self):
        self.assertTrue(s.invalidas([dict(LIBRE, acceso='pago')]))

    def test_declarado_exige_cita_y_url(self):
        for k in ('cita', 'url'):
            self.assertTrue(s.invalidas([dict(PAGO, **{k: ''})]))

    def test_pago_declarado_publicado_gratis(self):
        self.pon('acceso', [LIBRE, PAGO])       # la sede manda sobre el festival
        self.frena(fest(), 'publica gratis y su sede dice pago')

    def test_gratis_por_omision_contra_pago_declarado(self):
        f = {k: v for k, v in F.items() if k != 'is_free'}
        self.assertTrue(s.contradicciones(fest(f), [PAGO], HOY))

    def test_pago_o_invitacion_publicados_contra_gratis(self):
        for k in ({'is_free': False}, {'by_invitation': True}):
            self.assertTrue(s.contradicciones(fest(**k), [LIBRE], HOY))
        d = fest({k: v for k, v in F.items() if k != 'is_free'}); d['venues']['Sala - Bogotá']['ticket_url'] = 'https://b'
        self.assertTrue(s.contradicciones(d, [LIBRE], HOY))     # boleta heredada de la sede

    def test_inscripcion_declarada_sin_publicar(self):
        e = dict(PAGO, acceso=['gratis', 'inscripción'])
        self.assertTrue(s.contradicciones(fest(), [e], HOY))
        self.assertFalse(s.contradicciones(fest(requires_registration=True), [e], HOY))

    def test_la_funcion_manda_sobre_la_sede(self):
        self.assertFalse(s.contradicciones(fest(), [PAGO, dict(PAGO, alcance='función', nombre='f_1', acceso='gratis')], HOY))

    def test_nombre_que_no_existe(self):
        self.pon('acceso', [LIBRE, dict(PAGO, nombre='Salla')])
        self.frena(fest(), 'no existe en el programa')
        self.assertEqual(s.sin_cubrir(fest(), [PAGO, dict(PAGO, alcance='función', nombre='f_1')], HOY), [])

    def test_funcion_pasada_no_pide_acceso(self):
        self.assertEqual(s.sin_cubrir(fest(day='2026-11-01'), [], HOY), [])
        self.assertTrue(s.sin_cubrir(fest(day=HOY), [], HOY))

    def test_inventario(self):
        self.pon('fuentes', dict(CERRADO, items={'https://x/b.pdf': {'estado': 'sin-revisar'}}))
        self.frena(fest(), 'sin revisar')
        self.frena(fest(), '«sin-aviso» con el inventario abierto')
        os.remove(s._ruta(FID, 'fuentes'))
        self.frena(fest(), 'sin inventario')

    def test_indice_ilegible_frena(self):
        for abrir in (indice(roto=True), lambda u, timeout=None: io.BytesIO(b'{}'), lambda u, timeout=None: io.BytesIO(b'{"festivales": {}}')):
            f, _ = s.control(FID, fest(), abrir, HOY, modelo=False)
            self.assertTrue('índice' in f[0])


class Publicado(Base):
    def test_solo_avisa(self):
        self.pon('acceso', [LIBRE, PAGO]); os.remove(s._ruta(FID, 'fuentes'))
        f, av = self.control(fest(time='20:00'), FID)
        self.assertEqual(f, [])
        self.assertTrue(len(av) >= 3)


class Sellar(Base):
    def test_rechaza(self):
        d = fest(time='20:00')
        for k in ({'verifica': ' A '}, {'contra': ''}, {'contra': 'el programa'}, {'monta': ''}, {'huella': 'x'}):
            with self.subTest(k), self.assertRaises(SystemExit):
                self.sella(d, **k)
        self.assertTrue(s.faltan(d, *s.sidecars(FID)))

    def test_lo_no_fiel_no_se_sella(self):
        self.assertEqual(self.sella(fest(time='20:00'), veredicto='mal'), (0, ['f_1']))

    def test_sello_a_mano_con_el_mismo_lector(self):
        k = s.sidecars(FID)[0]['f_1']
        self.pon('sellos-funcion', {'f_1': dict(k, verifica='a')})
        self.assertTrue(s.revisar(FID, fest(), HOY, modelo=False)[0])


class PublicarDatos(Base):
    def test_primera_frena_y_ya_publicado_no(self):
        spec = importlib.util.spec_from_file_location('pd', os.path.join(RAIZ, 'pipeline', 'publicar-datos.py'))
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        for frenos, avisos in ((['x'], []), ([], ['x'])):
            with mock.patch.object(s, 'control', return_value=(frenos, avisos)), contextlib.redirect_stdout(io.StringIO()):
                if frenos:
                    with self.assertRaises(SystemExit):
                        m._control_funciones(FID, '{}')
                    m._ENS = []
                    m._control_funciones(FID, '{}'); self.assertEqual(len(m._ENS), 1)
                    m._ENS = None
                else:
                    m._control_funciones(FID, '{}')

    def test_la_compuerta_esta_puesta(self):
        with open(os.path.join(RAIZ, 'pipeline', 'publicar-datos.py'), encoding='utf-8') as fh:
            src = fh.read()
        self.assertEqual(src.count('    _control_funciones(fest, contenido)\n'), 2)


if __name__ == '__main__':
    unittest.main()
