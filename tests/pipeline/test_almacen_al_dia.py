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
