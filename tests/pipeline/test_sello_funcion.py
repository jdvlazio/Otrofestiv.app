"""La función publicada la releyó otro y su acceso tiene fuente (24 nov 2026, BOGOSHORTS)."""
import contextlib, importlib.util, io, json, os, subprocess, sys, tempfile, unittest
from unittest import mock
RAIZ = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, os.path.join(RAIZ, 'pipeline'))
import sello_funcion as s

HOY, FID = '2026-11-24', 'prueba-2026'
F = {'id': 'f_1', 'title': 'X', 'day': '2026-12-01', 'time': '19:00', 'venue': 'Sala - Bogotá', 'is_free': True, 'has_qa': False}
PAGO = {'alcance': 'sede', 'nombre': 'Sala - Bogotá', 'nivel': 'declarado', 'acceso': 'pago', 'cita': 'Boleta $10.000', 'url': 'https://x/a.pdf'}
LIBRE = {'alcance': 'festival', 'nombre': FID, 'nivel': 'sin-aviso', 'acceso': 'gratis', 'documentos_revisados': ['https://x/a.pdf']}
CERRADO = {'_provenance': {'capturado': '2026-11-24T08:00'}, 'raices': {'web': 'https://x', 'bio': 'https://y'}, 'items': {'https://x/a.pdf': {'estado': 'usada'}}}


def fest(*a, **k):
    return {'ticketing_model': 'mixed', 'films': list(a) or [dict(F, **k)], 'venues': {'Sala - Bogotá': {'short': 'Sala'}}}


def indice(*ids, roto=False, pub=None, roto_festival=False):
    def abrir(url, timeout=None):
        if roto or (roto_festival and 'indice.json' not in url):
            raise OSError('sin red')
        x = {'festivales': {i: {'archivo': f'festivales/{i}/x.json'} for i in ids or ('otro',)}} if 'indice.json' in url else pub or {'films': [F]}
        return io.BytesIO(json.dumps(x).encode())
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
            'has_qa', 'qa_type', 'premium', 'is_free', 'requires_registration', 'registration_url', 'ticket_url', 'by_invitation', 'online',
            'stream_url', 'stream_platform', 'audience'})

    def test_lo_heredado_entra_en_la_huella(self):
        for c in ('short', 'address', 'city', 'lat', 'lng') + s.ACCESO:
            d = fest(); d['venues']['Sala - Bogotá'][c] = 'x'
            with self.subTest('sede ' + c):
                self.assertTrue(s.faltan(d, *s.sidecars(FID)))
        for c in ('ticket_url', 'ticketing_model', 'acceso_por_defecto'):
            with self.subTest('festival ' + c):
                self.assertTrue(s.faltan(dict(fest(), **{c: 'x'}), *s.sidecars(FID)))
        for c in ('nivel', 'acceso', 'cita', 'url'):
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
        self.assertTrue(s.contradicciones(dict(fest(f), ticketing_model=None), [PAGO], HOY))

    def test_pago_o_invitacion_publicados_contra_gratis(self):
        for k in ({'is_free': False}, {'by_invitation': True}):
            self.assertTrue(s.contradicciones(fest(**k), [LIBRE], HOY))
        for c, v in (('is_free', True), ('ticket_url', 'https://b')):     # la app NO hereda acceso de la sede
            d = fest({k: v for k, v in F.items() if k != 'is_free'}); d['venues']['Sala - Bogotá'][c] = v
            self.assertTrue(s.contradicciones(d, [LIBRE], HOY))

    def test_pago_que_la_app_no_muestra(self):
        for modelo in (None, 'free'):
            d = dict(fest(is_free=False), ticketing_model=modelo)
            for e in (PAGO, LIBRE, dict(PAGO, acceso='inscripción')):
                self.assertTrue(s.contradicciones(d, [e], HOY))
        for v in ('false', 1, 0):
            for e in (PAGO, LIBRE):
                self.assertTrue(s.contradicciones(fest(is_free=v), [e], HOY))
        self.assertTrue(s.contradicciones(fest(ticket_url='https://b'), [LIBRE], HOY))     # gratis con enlace de compra

    def test_avisos_dia_y_sesiones(self):
        for d in (dict(fest(), avisos=[{'type': 'rescheduled', 'title': 'X', 'newTime': '09:00'}]),
                  dict(fest(), avisos=[{'type': 'cancelled', 'cities': ['Bogotá']}]), dict(fest(), festivalDates={F['day']: '2026-12-02'})):
            self.assertTrue(s.faltan(d, *s.sidecars(FID)))
        self.assertEqual(s.faltan(dict(fest(), avisos=[{'title': 'Otra'}]), *s.sidecars(FID)), [])
        self.assertTrue(s.contradicciones(fest(sessions=[{'id': 'z', 'day': '2020-01-01'}]), [PAGO], HOY))

    def test_futura_no_se_esquiva(self):
        for k in ({'hasta': '2020-01-01'}, {'day': '0000-00-00'}, {'day': 'TBD'}, {'day': '2020-01-01', 'hasta': '2026-12-31', 'info': True}):
            self.assertTrue(s.futura(dict(F, **k), HOY), k)
        self.assertTrue(s.futura(s.explotar({'day': '2020-01-01', 'screenings': [{'date': '2026-12-01'}]})[0], HOY))

    def test_explotar_igual_que_la_app(self):
        base = dict(F, by_invitation=True, online=True, is_free=False, sala='9', ticket_url='https://b', registration_url='https://r', film_start='19:30', requires_registration=True, qa_type='team', hasta='2026-12-05', info=True)
        films = [dict(F), dict(base, sessions=[{'id': 'z'}])] + [dict(o, screenings=[x]) for o in (F, base) for x in (
            {'date': '2026-12-02', 'time': '1'}, {'day': '2026-12-02', 'is_free': None, 'by_invitation': False, 'online': False, 'title': 'no'},
            {'id': 'f_9', 'venue': 'V', 'sala': '2', 'is_free': True, 'by_invitation': True, 'online': True, 'stream_url': 'u', 'film_start': '2', 'registration_url': 'h', 'ticket_url': '', 'has_qa': False, 'requires_registration': False, 'qa_type': 'guests', 'hasta': 'x', 'audience': 'press'})]
        js = "const m=await import(process.argv[1]);process.stdout.write(JSON.stringify(m.explodeScreenings(JSON.parse(process.argv[2]))))"
        r = subprocess.run(['node', '--input-type=module', '-e', js, os.path.abspath(os.path.join(RAIZ, 'src', 'domain', 'film.js')), json.dumps(films)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        for a, b in zip([g for f in films for g in s.explotar(f)], json.loads(r.stdout), strict=True):
            for c in s.CAMPOS + ('id',):
                self.assertEqual(a.get(c), b.get(c), c)

    def test_inscripcion_declarada_sin_publicar(self):
        e = dict(PAGO, acceso=['gratis', 'inscripción'])
        self.assertTrue(s.contradicciones(fest(), [e], HOY))
        self.assertFalse(s.contradicciones(fest(requires_registration=True), [e], HOY))

    def test_la_funcion_manda_sobre_la_sede(self):
        self.assertFalse(s.contradicciones(fest(), [PAGO, dict(PAGO, alcance='función', nombre='f_1', acceso='gratis')], HOY))

    def test_pdf_de_acreditaciones_descartado_sin_leer(self):   # el caso real de BOGOSHORTS
        u = 'https://info.bogoshorts.com/24BSFF_acreditaciones2026.pdf'
        self.pon('fuentes', dict(CERRADO, items={**CERRADO['items'], u: {'tipo': 'pdf', 'estado': 'descartada', '_por_que': 'bases de acreditación, sin programación'}}))
        self.frena(fest(), '«sin-aviso» sin leer ' + u)
        self.pon('acceso', [dict(LIBRE, documentos_revisados=['https://x/a.pdf', u])])
        self.assertEqual(self.control(fest()), ([], []))

    def test_sala(self):
        sala = dict(PAGO, alcance='sala', sala='1')
        d = fest(dict(F, sala='1'), dict(F, id='f_2', sala='2'))
        c = s.contradicciones(d, [LIBRE, sala], HOY)
        self.assertEqual(len(c), 1); self.assertIn('f_1', c[0])
        self.assertEqual(s.sin_cubrir(d, [LIBRE, sala], HOY), [])
        self.assertTrue(s.sin_cubrir(d, [LIBRE, dict(sala, sala='9')], HOY))
        self.assertTrue(s.contradicciones(d, [dict(PAGO, acceso='gratis'), sala], HOY))     # la sala manda sobre la sede
        self.assertTrue(s.invalidas([dict(sala, sala='')]) and s.invalidas([dict(PAGO, sala='1')]))

    def test_contradiccion_no_es_archivo_invalido(self):    # en validate.py solo avisa
        self.pon('acceso', [LIBRE, PAGO])
        mal, pend = s.revisar(FID, fest(), HOY, modelo=False)
        self.assertEqual(mal, []); self.assertIn('publica gratis', pend[0])

    def test_pasadas_solo_en_la_primera(self):
        d = fest(F, dict(F, id='f_2', day='2026-11-01'))
        self.frena(d, 'f_2: sin sello')
        self.assertEqual(self.control(d, FID, pub=d), ([], []))

    def test_acceso_de_otro_festival(self):
        self.pon('acceso', [dict(LIBRE, nombre='otro-2025')])
        self.frena(fest(), 'no es ' + FID)

    def test_sin_aviso_con_inventario_vacio(self):
        self.pon('fuentes', dict(CERRADO, items={}))
        self.frena(fest(), 'inventario vacío')
        self.pon('fuentes', dict(CERRADO, raices={'_sin_web': '', '_sin_bio': ''}))
        self.frena(fest(), 'mal formado')

    def test_dato_mal_formado_frena_la_primera_y_avisa_al_publicado(self):
        for que, x in (('fuentes', []), ('fuentes', dict(CERRADO, items=[])), ('acceso', [{'alcance': []}]), ('acceso', {}), ('sellos-funcion', [])):
            with self.subTest(que=que, x=x):
                viejo = s._leer(s._ruta(FID, que), None)
                self.pon(que, x)
                self.assertTrue(self.control(fest())[0])
                f, av = self.control(fest(), FID)
                self.assertTrue(f == [] and av)
                self.pon(que, viejo)
        with open(s._ruta(FID, 'acceso'), 'w') as fh:
            fh.write('{')
        self.assertTrue('JSON' in self.control(fest())[0][0] and s.revisar(FID, None)[0])
        self.assertEqual(self.control(fest(), FID)[0], [])
        self.assertTrue(s.control(FID, {'films': [None]}, indice(), HOY, modelo=False)[0])

    def test_invitacion_no_lleva_precio(self):
        self.assertTrue(s.invalidas([dict(PAGO, acceso=['pago', 'invitación'])]))

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
            self.assertTrue('almacén' in f[0])


class Publicado(Base):
    def test_solo_avisa(self):
        self.pon('acceso', [LIBRE, PAGO]); os.remove(s._ruta(FID, 'fuentes'))
        f, av = self.control(fest(time='20:00'), FID)
        self.assertEqual(f, [])
        self.assertTrue(len(av) >= 3)


    def test_lo_publicado_ilegible_frena(self):
        self.assertIn('almacén', self.control(fest(), FID, roto_festival=True)[0][0])
        for pub in ([], {'films': 3}):
            f, _ = s.control(FID, fest(), lambda u, timeout=None: io.BytesIO(json.dumps({'festivales': {FID: {'archivo': 'x'}}} if 'indice' in u else pub).encode()), HOY, modelo=False)
            self.assertTrue(f)

    def test_catalogo_sin_fechas(self):
        cat = fest({'title': 'X', 'unscheduled': True}, {'title': 'Y', 'day': ''})
        self.pon('acceso', [])
        self.assertEqual(self.control(cat), ([], []))
        self.assertTrue(self.control(fest(), FID, pub=cat)[0])      # con el programa, es la primera
        os.remove(s._ruta(FID, 'fuentes'))
        self.frena(cat, 'sin inventario')

    def test_programa_grande_despues(self):
        otras = [dict(F, id=f'f_{n}') for n in range(2, 5)]
        self.assertTrue(self.control(fest(F, *otras), FID)[0])              # 3 nuevas de 4
        f, av = self.control(fest(F, *otras), FID, pub=fest(F, otras[0]))   # 2 de 4: justo la mitad, pasa
        self.assertTrue(f == [] and av)
        f, av = self.control(fest(F, *otras[:2]), FID)                      # 2 de última hora: avisa
        self.assertTrue(f == [] and av)
        pas = [dict(x, day='2026-11-01') for x in otras]                    # las pasadas no cuentan
        self.assertEqual(self.control(fest(F, *pas), FID)[0], [])
        self.assertEqual(self.control(fest(F, *pas), FID)[1], [])
        f, av = self.control(fest(dict(F, time='20:00'), *pas), FID)
        self.assertTrue(f == [] and av)


class CI(Base):
    def correr(self, d, *ids, config=None, **k):
        os.makedirs(os.path.join(s.STAGING, 'festivals'), exist_ok=True)
        with open(os.path.join(s.STAGING, 'festivals', FID + '.json'), 'w', encoding='utf-8') as fh:
            json.dump(d, fh)
        with mock.patch.object(s, 'REPO', s.STAGING):
            return s.ci({'prueba2026': '2026-12-31T23:59:00', 'sinarchivo2026': ''} if config is None else config, indice(*ids, **k), HOY, modelo=False)

    def test_festival_nuevo_sin_sello_rojo_y_sellado_verde(self):
        self.assertEqual(self.correr(fest()), {})
        self.pon('sellos-funcion', {})
        self.assertEqual(list(self.correr(fest())), [FID])
        self.assertEqual(list(self.correr(fest(), config={'prueba2026': '2026-01-01'})), [FID])    # fuera del índice, aunque diga que terminó
        self.assertEqual(self.correr(fest(), config={}), {})       # oculto: no está en la lista

    def test_cambio_de_hora_en_publicado_verde(self):
        self.assertEqual(self.correr(fest(time='20:00'), FID), {})

    def test_terminado_y_publicado_no_se_baja(self):
        self.assertEqual(self.correr(fest(), FID, config={'prueba2026': '2026-11-23'}, roto_festival=True), {})

    def test_sin_red_falla_claro(self):
        self.assertIn('no se pudo leer el índice', self.correr(fest(), roto=True)['almacén'][0])
        self.assertIn('no se pudo leer el almacén', self.correr(fest(), FID, roto_festival=True)[FID][0])

    def test_el_paso_esta_puesto_sin_secretos(self):
        with open(os.path.join(RAIZ, '.github', 'workflows', 'bump-and-validate.yml'), encoding='utf-8') as fh:
            yml = fh.read()
        paso = yml.split('- name: Sello de función')[1].split('- name:')[0]
        self.assertIn("if: github.event_name == 'pull_request'", paso)
        self.assertIn('sello_funcion.py --ci', paso)
        self.assertIn('fetch-depth: 2', yml)
        self.assertIn('cambios=$(git diff', paso)     # si el diff falla, el paso falla
        self.assertNotIn('${{', paso)
        self.assertNotIn('secrets.', yml)


class Sellar(Base):
    def test_llevan_provenance(self):
        # [staging-provenance] la exige en todo sidecar: no es un sello ni una entrada
        with open(s._ruta(FID, 'sellos-funcion'), encoding='utf-8') as fh:
            self.assertTrue(json.load(fh)['_provenance']['capturado'])
        self.assertEqual(list(s.sidecars(FID)[0]), ['f_1'])
        self.pon('acceso', {'_provenance': {'capturado': '2026-11-25'}, 'entradas': [LIBRE]})
        self.assertEqual(s.revisar(FID, fest(), HOY, modelo=False), ([], []))
        self.pon('acceso', {'_provenance': {}, 'entradas': {}})
        self.assertTrue(s.revisar(FID, fest(), HOY, modelo=False)[0])

    def test_rechaza(self):
        d = fest(time='20:00')
        for k in ({'verifica': ' A '}, {'contra': ''}, {'contra': 'el programa'}, {'contra': 'n/a'}, {'monta': ''}, {'huella': 'x'}):
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
