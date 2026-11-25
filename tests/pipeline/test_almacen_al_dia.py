"""El almacén se pone al día sin cortar la tanda ni pisar lo publicado después (24 nov 2026)."""
import io, importlib.util, os, subprocess, sys, tempfile, unittest, urllib.error
AQUI = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(AQUI, 'pipeline'))
import almacen_al_dia as al


def _publicar_datos():
    spec = importlib.util.spec_from_file_location('publicar_datos', os.path.join(AQUI, 'pipeline', 'publicar-datos.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class Decidir(unittest.TestCase):
    def test_main_mas_nuevo_publica_aunque_el_push_no_lo_traiga(self):
        self.assertEqual(al.decidir(True, 200, False, 0, 100), 'publicar')

    def test_lo_publicado_despues_de_main_no_se_pisa(self):      # rama adelantada o vuelta atrás
        self.assertEqual(al.decidir(True, 100, False, 0, 200), 'adelante')
        self.assertEqual(al.decidir(True, 100, True, 300, 200), 'adelante')   # ni por su ficha

    def test_solo_la_ficha(self):
        self.assertEqual(al.decidir(False, 0, True, 300, 200), 'publicar')
        self.assertEqual(al.decidir(False, 0, True, 100, 200), 'adelante')
        self.assertEqual(al.decidir(False, 0, False, 0, 0), 'igual')


class Alta(unittest.TestCase):
    C = {'n-2026': ('', '2026-12-08T23:00'), 'oculto-2026': ('test', '2026-12-08'), 'viejo-2026': ('', '2026-11-24'),
         'ya-2026': ('', '2026-12-08'), 'sinjson-2026': ('', '2026-12-08'), 'sinfin-2026': ('', '')}

    def test_entra_solo_el_visible_vigente_con_json_y_fuera_del_almacen(self):
        self.assertEqual(al.altas(self.C, {'ya-2026': {}}, lambda f: f != 'sinjson-2026', '2026-11-25'), ['n-2026'])
        self.assertEqual(al.altas({'n-2026': ('', '2026-11-25T23:00')}, {}, lambda f: True, '2026-11-25'), ['n-2026'])   # el último día todavía

    def test_la_config_real_se_lee_y_nombra_archivos(self):
        c = al.config()
        self.assertIn('bogoshorts-2026', c)
        self.assertEqual(c['cinemancia-2025'][0], 'test')

    def correr(self, nuevos, ix=None, en_medio=None):
        viejo = {k: getattr(al, k) for k in ('traer_datos', 'indice', 'altas', 'config', 'publicar_todos', 'estado')}
        cola, vistos = [ix or {'a-2026': {}}], []
        ini = al.estado
        al.traer_datos, al.config, al.altas = (lambda: None), (lambda: {}), (lambda *a: list(nuevos))
        al.indice = lambda: cola[0]
        al.estado = lambda f, e: 'igual' if f == 'a-2026' else ini(f, e)
        viejo_run, al.subprocess.run = al.subprocess.run, lambda c, **k: vistos.append(' '.join([c[2], *c[4:]])) or type('R', (), {'returncode': 0})()
        def todos(lista, pub):
            if en_medio:
                cola[0] = en_medio
            return [f for f in lista if not pub(f, 1)]
        al.publicar_todos = todos
        try:
            try:
                al.main()
                return vistos, None
            except SystemExit as e:
                return vistos, str(e)
        finally:
            al.subprocess.run = viejo_run
            for k, v in viejo.items():
                setattr(al, k, v)

    def test_uno_se_publica(self):
        self.assertEqual(self.correr(['n-2026']), (['n-2026 --alta'], None))
        self.assertEqual(self.correr(['n-2026', 'm-2026'])[0], ['n-2026 --alta', 'm-2026 --alta'])

    def test_muchos_a_la_vez_no_entra_ninguno_y_queda_en_rojo(self):
        vistos, err = self.correr(['x-1', 'y-1', 'z-1'])
        self.assertEqual(vistos, [])
        self.assertIn('x-1', err)

    def test_el_alta_no_quita_las_republicaciones(self):
        self.assertEqual(self.correr(['n-2026'], ix={'a-2026': {}, 'r-2026': None})[0], ['r-2026', 'n-2026 --alta'])

    def test_un_publicado_que_desaparece_del_indice_no_se_republica(self):
        vistos, err = self.correr([], ix={'a-2026': {}, 'r-2026': None}, en_medio={'a-2026': {}})
        self.assertEqual((vistos, 'r-2026' in err), ([], True))

    def test_si_no_se_lee_la_config_queda_en_rojo(self):
        vistos, err = self.correr(None)
        self.assertIn('altas', err)

    def test_el_dia_es_el_de_colombia(self):
        ahora = al.datetime(2026, 11, 26, 2, 0, tzinfo=al.timezone.utc).timestamp()     # 21:00 del 25 en Colombia
        viejo, al.time.time = al.time.time, lambda: ahora
        try:
            self.assertEqual(al.hoy_colombia(), '2026-11-25')
        finally:
            al.time.time = viejo

    def test_si_alguien_lo_publico_mientras_tanto_se_vuelve_a_decidir(self):
        viejo, al.os.path.exists = al.os.path.exists, lambda p: False     # main ya no lo tiene: no se pisa
        try:
            self.assertEqual(self.correr(['n-2026'], en_medio={'a-2026': {}, 'n-2026': {}}), ([], None))
        finally:
            al.os.path.exists = viejo


class AltaConFicha(unittest.TestCase):
    """Con --alta viaja la ficha, y sin ficha no entra; sin --alta, un festival sin ficha en el almacén no la recibe."""
    def correr(self, *args, ficha=True):
        m, subido = _publicar_datos(), []
        m._control_funciones = lambda *a: None
        m._afiches_en_la_web = lambda *a, **k: None
        m._no_entra = lambda *a: subido.append('no_entra')
        m._ficha = lambda f: {'fichas/x.json': b'{}'} if ficha else {}
        m._tiene_ficha = lambda f: False
        def pub(archivos, *a):
            subido.append(sorted(archivos))
            raise SystemExit('hasta aquí')
        m._publicar = pub
        viejo, env = sys.argv, dict(os.environ)
        sys.argv = ['x', 'bogoshorts-2026', '--desde-main', *args]
        os.environ.update(GITHUB_ACTIONS='true', GITHUB_REF='refs/heads/main')
        try:
            with self.assertRaises(SystemExit):
                m.main()
        finally:
            sys.argv = viejo
            os.environ.clear()
            os.environ.update(env)
        return subido
    J = 'festivals/bogoshorts-2026.json'

    def test_alta(self):
        self.assertEqual(self.correr('--alta'), ['no_entra', ['festivals/bogoshorts-2026.json', 'fichas/x.json']])

    def test_alta_sin_ficha_no_entra(self):
        self.assertEqual(self.correr('--alta', ficha=False), ['no_entra'])

    def test_sin_alta_la_ficha_no_viaja(self):
        self.assertEqual(self.correr(), [[self.J]])


class Ficha(unittest.TestCase):
    I = {'name': 'X', 'keyArt': 'https://s/datos/keyart/aaaaaaaaaaaa.jpg'}

    def test_compara_campos_y_huella_del_keyart(self):
        self.assertFalse(al.ficha_difiere({'name': 'X', 'keyArt': '/assets/keyart/x.jpg'}, self.I, 'a' * 12))
        self.assertTrue(al.ficha_difiere({'name': 'Y', 'keyArt': '/assets/keyart/x.jpg'}, self.I, 'a' * 12))
        self.assertTrue(al.ficha_difiere({'name': 'X', 'keyArt': '/assets/keyart/x.jpg'}, self.I, 'b' * 12))

    def test_sin_ficha_en_el_almacen_no_entra_sola(self):
        self.assertFalse(al.ficha_difiere({'name': 'X'}, None, ''))


class Tanda(unittest.TestCase):
    def test_un_fallo_no_detiene_a_los_demas_y_se_reintenta(self):
        vistos, caidas = [], {'b': 1}
        def pub(f, vuelta):
            vistos.append((f, vuelta))
            if caidas.get(f):
                caidas[f] -= 1
                return False
            return True
        self.assertEqual(al.publicar_todos(['a', 'b', 'c'], pub, dormir=lambda s: None), [])
        self.assertEqual(vistos, [('a', 1), ('b', 1), ('c', 1), ('b', 2)])

    def test_lo_que_sigue_mal_se_dice(self):
        self.assertEqual(al.publicar_todos(['a', 'b'], lambda f, v: f == 'a', dormir=lambda s: None), ['b'])


class Tocado(unittest.TestCase):
    def test_la_fecha_del_ultimo_cambio_de_esa_ruta(self):
        t = tempfile.mkdtemp()
        def g(*a, fecha='1000'):
            subprocess.run(['git', '-C', t, '-c', 'user.email=t@t', '-c', 'user.name=t', *a], check=True, capture_output=True,
                           env={**os.environ, 'GIT_COMMITTER_DATE': fecha + ' +0000', 'GIT_AUTHOR_DATE': fecha + ' +0000'})
        g('init', '-q', '-b', 'main')
        for nombre, fecha in (('x.json', '1000000000'), ('y.json', '1000009999')):
            open(os.path.join(t, nombre), 'w').write(nombre)
            g('add', nombre); g('commit', '-qm', nombre, fecha=fecha)
        antes, al.REPO = al.REPO, t
        try:
            self.assertEqual((al.tocado('x.json'), al.tocado('y.json'), al.tocado('z')), (1000000000, 1000009999, 0))
        finally:
            al.REPO = antes


class QuienPublico(unittest.TestCase):
    """v1 puesta por un job lento DESPUÉS del merge de v2: main manda; puesta por una persona: no."""
    def test_autor_de_lo_publicado(self):
        t = tempfile.mkdtemp()
        g = lambda quien, *a: subprocess.run(['git', '-C', t, '-c', 'user.email=t@t', '-c', f'user.name={quien}', *a], check=True, capture_output=True, text=True).stdout.strip()
        g('x', 'init', '-q', '-b', 'datos')
        antes, al.REPO = al.REPO, t
        try:
            for quien, n in (('github-actions', 'a.json'), ('jdvlazio', 'b.json')):
                open(os.path.join(t, n), 'w').write(n)
                g(quien, 'add', n); g(quien, 'commit', '-qm', n)
            c = g('x', 'rev-parse', 'HEAD')
            self.assertEqual((al.lo_puso_el_job(c, 'a.json'), al.lo_puso_el_job(c, 'b.json')), (True, False))
        finally:
            al.REPO = antes

    def test_estado_cede_ante_main_solo_si_lo_puso_el_job(self):
        t = tempfile.mkdtemp()
        os.mkdir(os.path.join(t, 'festivals'))
        open(os.path.join(t, 'festivals', 'f.json'), 'w').write('v2')
        e = {'sha256': 'v1', 'publicado': '2026-11-24T10:08:00Z', 'commit': 'c'}
        viejo = al.REPO, al.tocado, al.lo_puso_el_job
        al.REPO, al.tocado = t, lambda *r: 1        # main la tocó mucho antes
        try:
            for job, esperado in ((True, 'publicar'), (False, 'adelante')):
                al.lo_puso_el_job = lambda *a: job
                self.assertEqual(al.estado('f', e), esperado)
        finally:
            al.REPO, al.tocado, al.lo_puso_el_job = viejo


class Pasajeros(unittest.TestCase):
    def test_502_y_cortes_de_red_se_reintentan(self):
        m = _publicar_datos()
        for e in (urllib.error.HTTPError('u', 502, 'x', {}, io.BytesIO(b'GitHub 403')), urllib.error.URLError('red'), ConnectionResetError()):
            def abrir(*a, _e=e, **k):
                raise _e
            m.urllib.request.urlopen, real = abrir, m.urllib.request.urlopen
            try:
                with self.assertRaises(m.Choque):
                    m._llamar({'festival': 'x', 'sha': 'y'})
            finally:
                m.urllib.request.urlopen = real


if __name__ == '__main__':
    unittest.main()
