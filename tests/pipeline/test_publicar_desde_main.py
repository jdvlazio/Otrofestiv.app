"""publicar-datos.py solo publica lo que está en main, salvo urgencia declarada (25 nov 2026).
Se prueba sin red ni publicación: la función que decide queda aislada con git de mentira."""
import importlib.util, os, sys, unittest
AQUI = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
spec = importlib.util.spec_from_file_location('publicar_datos', os.path.join(AQUI, 'pipeline', 'publicar-datos.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class DesdeMain(unittest.TestCase):
    def correr(self, en_main, sucio, *args):
        llamadas = []
        viejo = (m.git, m.subprocess.run, sys.argv, m.guardianes)
        m.git = lambda *a, **k: ''
        def run(cmd, *a, **k):
            if 'show' in cmd:
                with open(os.path.join(AQUI, 'festivals', 'funza-2026.json'), 'rb') as fh:
                    b = fh.read()
                return type('R', (), {'stdout': b if en_main else b + b' '})()
            if 'status' in cmd:
                return type('R', (), {'stdout': ' M x' if sucio else ''})()
            return viejo[1](cmd, *a, **k)
        m.subprocess.run = run
        def para(*a, **k):
            llamadas.append('guardianes')
            raise SystemExit('alcanzó los guardianes')
        m.guardianes = para
        sys.argv = ['x', 'funza-2026', *args]
        try:
            with self.assertRaises(SystemExit) as e:
                m.main()
            return str(e.exception), llamadas
        finally:
            m.git, m.subprocess.run, sys.argv, m.guardianes = viejo

    def test_fuera_de_main_no_publica(self):
        msg, ll = self.correr(False, False)
        self.assertIn('no es lo que hay en main', msg)
        self.assertEqual(ll, [])

    def test_sin_commitear_no_publica(self):
        msg, ll = self.correr(False, True)
        self.assertIn('sin commitear', msg)

    def test_en_main_sigue(self):
        self.assertEqual(self.correr(True, False)[1], ['guardianes'])

    def test_urgencia_declarada_sigue(self):
        self.assertEqual(self.correr(False, False, '--urgente', 'el festival movió la sala hoy')[1], ['guardianes'])


if __name__ == '__main__':
    unittest.main()
