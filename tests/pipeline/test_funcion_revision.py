#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La revisión previa al merge (16 oct 2026): cada hallazgo, su reproducción
como test. Escritos antes de corregir."""
import datetime
import json
import os
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, 'pipeline'))
import funcion  # noqa: E402
import lib  # noqa: E402

CTX = {'fuente_principal': {'tipo': 'festival-web', 'fecha': '2026-10-07', 'url': 'https://festival.example/p'}}


def f(title='X', sala='A', dia='2026-10-22', hora='18:00', **kw):
    d = {'title': title, 'type': 'film', 'day': dia, 'time': hora, 'venue': 'Cine - Bogotá', 'sala': sala,
         'duration': '90 min', '_ancla': ('Cine - Bogotá', dia, hora)}
    d.update(kw)
    return d


class H1EstimadaNoSeConserva(unittest.TestCase):
    def test_un_festival_en_el_modelo_no_repone_la_duracion_publicada(self):
        import ensamblar
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, 'festivals', 'staging'))
        json.dump({'films': [{'title': 'X', 'duration': '75 min'}]}, open(os.path.join(d, 'festivals', 'zzz-2026.json'), 'w'))
        viejo, ensamblar.REPO = ensamblar.REPO, d
        try:
            fs = [{'title': 'X', 'duration': None}]
            ensamblar._conservar_publicado('zzz-2026', fs, sin=('duration',))
            self.assertFalse(fs[0].get('duration'))
            fs = [{'title': 'X', 'duration': None}]
            ensamblar._conservar_publicado('zzz-2026', fs)
            self.assertEqual(fs[0].get('duration'), '75 min')   # sin el modelo, como siempre
        finally:
            ensamblar.REPO = viejo


class M3IdAusenteNoSeRevive(unittest.TestCase):
    def test_una_ausente_no_presta_su_id_a_otra_funcion(self):
        a, reg, _ = funcion.asignar_ids([f()], {})
        _, reg, avisos = funcion.asignar_ids([f(title='Otra', hora='20:00')], reg)
        b, _, avisos = funcion.asignar_ids([f(sala='B', dia='2026-10-30', hora='15:00'), f(title='Otra', hora='20:00')], reg)
        self.assertNotEqual(a[0]['_fid'], b[0]['_fid'])

    def test_la_que_vuelve_igual_recupera_su_id_y_avisa(self):
        a, reg, _ = funcion.asignar_ids([f()], {})
        _, reg, _ = funcion.asignar_ids([f(title='Otra', hora='20:00')], reg)
        b, _, avisos = funcion.asignar_ids([f(), f(title='Otra', hora='20:00')], reg)
        self.assertEqual(a[0]['_fid'], b[0]['_fid'])
        self.assertTrue(any('volvió' in x for x in avisos))


class M4HoraMala(unittest.TestCase):
    def test_hora_fuera_de_rango_no_tiene_formato(self):
        self.assertFalse(funcion.FORMATO['time']('99:99'))
        self.assertFalse(funcion.FORMATO['time']('24:00'))
        self.assertTrue(funcion.FORMATO['time']('23:59'))

    def test_una_hora_mala_en_la_base_es_un_conflicto_no_una_caida(self):
        r = funcion.resolver([f(hora='7pm', duration=None, _ancla=('Cine - Bogotá', '2026-10-22', '7pm'))], [], CTX)
        self.assertTrue(any(c.get('tipo') == 'formato-base' for c in r.conflictos))

    def test_estimar_salta_las_horas_malas(self):
        out = funcion.estimar_duraciones([f(hora='7pm', duration=None), f(title='Y', hora='20:00', duration=None)])
        self.assertFalse(out[0].get('duration'))
        self.assertEqual(out[1]['duration'], '60 min')


class M5Detector(unittest.TestCase):
    def _d(self, t):
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, 'pipeline'))
        open(os.path.join(d, 'pipeline', 'zzz-2026-crudo.py'), 'w').write(t)
        return funcion.excepciones_en_scripts(d)

    def test_anotada_y_dict_llamada(self):
        self.assertEqual(len(self._d("HORA_X: dict = {'a': 1}\nSALA_Y = dict(a=1)\n")), 2)

    def test_dentro_de_if_y_de_main(self):
        t = "if True:\n    HORA = {'a': 1}\ndef main():\n    DURACION = {'b': 2}\n"
        self.assertEqual(len(self._d(t)), 2)

    def test_nombres_que_faltaban(self):
        self.assertEqual(len(self._d("SEDE_ERRADA = {}\nTITULOS = {}\nQUITAR = []\nCORRECCION = {}\n")), 4)

    def test_la_tabla_de_sedes_de_la_fuente_no_es_excepcion(self):
        self.assertEqual(self._d("SEDES = {'Sala 1': ('Cine', 'Sala 1')}\n"), [])

    def test_nombres_de_entrada_y_parches(self):
        self.assertEqual(len(self._d("ENTRADAS = {'a': 1}\nGRATIS = ['a']\nPRECIOS = {}\nOVERRIDES = {}\nPARCHES = {}\n")), 5)


class L7RegistroSinRuido(unittest.TestCase):
    def test_mismo_registro_no_cambia(self):
        _, reg, _ = funcion.asignar_ids([f()], {})
        _, reg2, _ = funcion.asignar_ids([f()], reg)
        self.assertEqual(reg, reg2)

    def test_con_ausentes_tampoco_cambia_entre_corridas(self):
        _, reg, _ = funcion.asignar_ids([f(), f(title='Otra', hora='20:00')], {})
        _, reg2, _ = funcion.asignar_ids([f()], reg)        # «Otra» sale
        _, reg3, _ = funcion.asignar_ids([f()], reg2)       # y sigue afuera
        self.assertEqual(reg2, reg3)


class L8Idempotencia(unittest.TestCase):
    def test_borrar_una_decision_no_hace_caer_la_segunda_pasada(self):
        dec = {'ancla': {'sede': 'Cine - Bogotá', 'dia': '2026-10-22', 'hora': '18:00'}, 'casilla': 'sala', 'valor': 'B',
               'contra': 'A', 'fuente': {'tipo': 'juan', 'fecha': '2026-10-15', 'frase': '«la B»'}}
        r1 = funcion.resolver([f()], [dec], CTX)
        funcion.resolver(r1.funciones, [], CTX)    # no StopIteration


class L9FalloPorComando(unittest.TestCase):
    def test_otro_comando_con_el_mismo_numero_no_limpia(self):
        r = tempfile.mkdtemp()
        os.makedirs(os.path.join(r, 'festivals', 'staging'))
        os.makedirs(os.path.join(r, 'pipeline'))
        json.dump({'pasos': [{'cmd': 'a'}]}, open(os.path.join(r, 'pipeline', 'zzz-2026.plan.json'), 'w'))
        json.dump({'films': []}, open(os.path.join(r, 'festivals', 'staging', 'zzz-2026-build.json'), 'w'))
        lib.sellar_build('zzz-2026', 1, 'a', repo=r)
        lib.marcar_fallo('zzz-2026', 2, 'verificar', repo=r)
        lib.limpiar_fallo('zzz-2026', 2, repo=r, cmd='otro')
        b = json.load(open(os.path.join(r, 'festivals', 'staging', 'zzz-2026-build.json')))
        self.assertFalse(lib.sello_valido('zzz-2026', b, repo=r)[0])


class L10HoyEnColombia(unittest.TestCase):
    def test_hoy_es_el_de_colombia(self):
        # a las 03:00 UTC del 16 todavía es el 15 en Colombia
        self.assertEqual(funcion.hoy(datetime.datetime(2026, 10, 16, 3, 0)), '2026-10-15')
        self.assertEqual(funcion.hoy(datetime.datetime(2026, 10, 16, 6, 0)), '2026-10-16')


if __name__ == '__main__':
    unittest.main()
