"""pipeline/bandeja.py: ningún post leído por el vigía queda sin decidir ni aplicar."""
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import bandeja as bj  # noqa: E402

T0 = datetime(2026, 11, 16, 9, 0)
POST = {'shortCode': 'DfzcCpZm2Uq', 'timestamp': '2026-11-16T08:00:00.000Z',
        'childPosts': [{}, {}, {}]}


class Bandeja(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.ruta = os.path.join(self.dir.name, 'sub', 'bandeja.json')

    def tearDown(self):
        self.dir.cleanup()

    def guardian(self, ahora):
        return bj.main(['--bandeja', self.ruta, '--guardian', '--hoy', ahora.isoformat()])

    def cli(self, *args, ahora=T0):
        return bj.main(['--bandeja', self.ruta, '--hoy', ahora.isoformat(), *args])

    def test_ingreso_pendiente_e_idempotente(self):
        p = bj.ingresar(self.ruta, 'villadelcine2026', '2026-11-15', POST, T0)
        self.assertEqual((p['estado'], p['laminas'], p['festival']), ('pendiente', 3, 'villadelcine2026'))
        self.cli('--decidir', 'DfzcCpZm2Uq', 'sin_dato', '--evidencia', 'lámina 1: foto de gala', '--por-que', 'no hay premios')
        p = bj.ingresar(self.ruta, 'otro2026', '2026-11-15', POST, T0)
        self.assertEqual(p['estado'], 'sin_dato')          # no vuelve a pendiente
        self.assertEqual(p['festivales'], ['villadelcine2026', 'otro2026'])

    def test_pendiente_frena_despues_de_4h(self):
        bj.ingresar(self.ruta, 'vdc', '2026-11-15', POST, T0)
        self.assertEqual(self.guardian(T0 + timedelta(hours=3)), 0)
        self.assertEqual(self.guardian(T0 + timedelta(hours=5)), 1)

    def test_decidido_sin_aplicar_frena_y_aplicado_libera(self):
        bj.ingresar(self.ruta, 'vdc', '2026-11-15', POST, T0)
        self.assertEqual(self.cli('--decidir', 'DfzcCpZm2Uq', 'palmares', '--evidencia', 'lámina 2 dice Mejor corto: X'), 0)
        self.assertEqual(self.guardian(T0 + timedelta(hours=5)), 1)
        self.assertEqual(self.cli('--aplicado', 'DfzcCpZm2Uq', '--pr', '1520'), 0)
        self.assertEqual(self.guardian(T0 + timedelta(hours=5)), 0)

    def test_reglas_de_decision(self):
        bj.ingresar(self.ruta, 'vdc', '2026-11-15', POST, T0)
        self.assertEqual(self.cli('--decidir', 'DfzcCpZm2Uq', 'palmares'), 2)                       # sin evidencia
        self.assertEqual(self.cli('--decidir', 'DfzcCpZm2Uq', 'sin_dato', '--evidencia', 'x'), 2)   # sin por qué
        self.assertEqual(self.cli('--decidir', 'DfzcCpZm2Uq', 'otra', '--evidencia', 'x'), 2)
        self.assertEqual(self.cli('--aplicado', 'DfzcCpZm2Uq', '--pr', '1'), 2)                     # no decidido
        self.assertEqual(self.cli('--decidir', 'NOEXISTE', 'palmares', '--evidencia', 'x'), 2)

    def test_decision_sin_evidencia_en_archivo_frena(self):
        bj.ingresar(self.ruta, 'vdc', '2026-11-15', POST, T0)
        b = bj.cargar(self.ruta)
        b['posts']['DfzcCpZm2Uq'].update(estado='aplicado', decision='palmares', pr=1)
        bj.guardar(self.ruta, b)
        self.assertEqual(self.guardian(T0), 1)

    def test_cierre_obligatorio_al_salir_de_la_ventana(self):
        bj.ingresar(self.ruta, 'vdc', '2026-11-15', POST, T0)
        self.cli('--decidir', 'DfzcCpZm2Uq', 'sin_dato', '--evidencia', 'lámina 1: afiche', '--por-que', 'promo')
        self.assertEqual(self.guardian(datetime(2026, 11, 23, 12)), 0)   # día 8: aún en ventana
        self.assertEqual(self.guardian(datetime(2026, 11, 24, 12)), 1)   # salió sin cierre
        self.assertEqual(self.cli('--cierre', 'vdc', 'no_compite'), 2)    # sin evidencia
        self.assertEqual(self.cli('--cierre', 'vdc', 'no_compite', '--evidencia', 'sin jurado en 2025 ni 2026'), 0)
        self.assertEqual(self.guardian(datetime(2026, 11, 24, 12)), 0)


if __name__ == '__main__':
    unittest.main()
