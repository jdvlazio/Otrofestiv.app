"""El almacén se pone al día por huella, sin cortar la tanda ni pisar lo que va adelante (24 nov 2026)."""
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
    def test_atrasado_se_publica_adelantado_no(self):
        self.assertEqual(al.decidir(False, False, True), 'igual')
        self.assertEqual(al.decidir(True, True, False), 'publicar')
        self.assertEqual(al.decidir(True, False, False), 'adelante')
        self.assertEqual(al.decidir(True, False, True), 'publicar')


class Tanda(unittest.TestCase):
    def test_un_fallo_no_detiene_a_los_demas_y_se_reintenta(self):
        vistos, caidas = [], {'b': 1}
        def pub(f):
            vistos.append(f)
            if caidas.get(f):
                caidas[f] -= 1
                return False
            return True
        self.assertEqual(al.publicar_todos(['a', 'b', 'c'], pub, dormir=lambda s: None), [])
        self.assertEqual(vistos, ['a', 'b', 'c', 'b'])

    def test_lo_que_sigue_mal_se_dice(self):
        self.assertEqual(al.publicar_todos(['a', 'b'], lambda f: f == 'a', dormir=lambda s: None), ['b'])


class Historia(unittest.TestCase):
    def test_reconoce_versiones_de_main(self):
        t = tempfile.mkdtemp()
        g = lambda *a: subprocess.run(['git', '-C', t, '-c', 'user.email=t@t', '-c', 'user.name=t', *a], check=True, capture_output=True)
        g('init', '-q', '-b', 'main')
        for v in ('uno', 'dos'):
            open(os.path.join(t, 'x.json'), 'w').write(v)
            g('add', 'x.json'); g('commit', '-qm', v)
        antes, al.REPO = al.REPO, t
        try:
            b = al.blobs_de_main('x.json')
        finally:
            al.REPO = antes
        self.assertIn(al.blob(b'uno'), b)
        self.assertIn(al.blob(b'dos'), b)
        self.assertNotIn(al.blob(b'desde una rama'), b)


class Pasajeros(unittest.TestCase):
    def test_502_y_corte_de_red_se_reintentan(self):
        m = _publicar_datos()
        for e in (urllib.error.HTTPError('u', 502, 'x', {}, io.BytesIO(b'GitHub 403')), urllib.error.URLError('red')):
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
