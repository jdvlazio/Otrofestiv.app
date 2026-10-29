#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C1 de la auditoría (docs/FUNCION.md §9): un id estable por función. Escritos
antes que el código."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'pipeline'))
import funcion  # noqa: E402


def f(title='Hiperrealidad', sede='Cinemateca de Bogotá', dia='2026-10-23', hora='19:00', sala='Sala 3'):
    return {'title': title, 'type': 'film', 'day': dia, 'time': hora, 'venue': f'{sede} - Bogotá', 'sala': sala,
            '_ancla': (sede, dia, hora)}


class Ids(unittest.TestCase):
    def test_dos_salas_a_la_misma_hora_son_dos_funciones(self):
        fs, reg, avisos = funcion.asignar_ids([f(sala='Sala 1', title='A'), f(sala='Sala 2', title='B')], {})
        self.assertEqual(len({x['_fid'] for x in fs}), 2)

    def test_misma_sede_en_dos_ciudades_son_dos_funciones(self):
        # FICDEH: «Cinema Local» en Bogotá y en Cali, mismo día y hora, misma obra.
        # El ancla es el venue PUBLICADO, con su ciudad
        a = dict(f(title='Feito Pipa', sala=''), venue='Cinema Local - Bogotá', _ancla=('Cinema Local - Bogotá', '2026-08-13', '18:30'))
        b = dict(f(title='Feito Pipa', sala=''), venue='Cinema Local - Cali', _ancla=('Cinema Local - Cali', '2026-08-13', '18:30'))
        fs, _, _ = funcion.asignar_ids([a, b], {})
        self.assertEqual(len({x['_fid'] for x in fs}), 2)

    def test_el_id_es_estable_entre_montajes(self):
        fs1, reg, _ = funcion.asignar_ids([f()], {})
        fs2, reg2, avisos = funcion.asignar_ids([f()], reg)
        self.assertEqual(fs1[0]['_fid'], fs2[0]['_fid'])
        self.assertEqual(avisos, [])

    def test_una_funcion_movida_conserva_su_id_y_avisa(self):
        fs1, reg, _ = funcion.asignar_ids([f()], {})
        fs2, reg2, avisos = funcion.asignar_ids([f(hora='19:30')], reg)
        self.assertEqual(fs1[0]['_fid'], fs2[0]['_fid'])
        self.assertTrue(any('movida' in a for a in avisos))

    def test_una_funcion_renombrada_conserva_su_id(self):
        fs1, reg, _ = funcion.asignar_ids([f()], {})
        fs2, _, avisos = funcion.asignar_ids([f(title='Hiperrealidad (versión restaurada)')], reg)
        self.assertEqual(fs1[0]['_fid'], fs2[0]['_fid'])
        self.assertTrue(any('renombrada' in a for a in avisos))

    def test_ambigua_no_se_elige_en_silencio(self):
        # dos funciones viejas candidatas para una nueva: id nuevo y aviso
        fs1, reg, _ = funcion.asignar_ids([f(title='X', sala='Sala 1', hora='18:00'), f(title='X', sala='Sala 1', hora='20:00')], {})
        fs2, _, avisos = funcion.asignar_ids([f(title='X', sala='Sala 1', hora='19:00')], reg)
        self.assertNotIn(fs2[0]['_fid'], {x['_fid'] for x in fs1})
        self.assertTrue(any('ambigua' in a for a in avisos))

    def test_duplicado_exacto_en_la_fuente_es_error(self):
        with self.assertRaises(funcion.AfirmacionInvalida):
            funcion.asignar_ids([f(), f()], {})

    def test_el_registro_no_olvida_las_que_salen(self):
        _, reg, _ = funcion.asignar_ids([f(), f(title='Otra', hora='21:00')], {})
        _, reg2, avisos = funcion.asignar_ids([f()], reg)
        self.assertEqual(len(reg2['funciones']), 2)
        self.assertTrue(any('ya no está' in a for a in avisos))


class ResolverPorId(unittest.TestCase):
    CTX = {'fuente_principal': {'tipo': 'festival-web', 'fecha': '2026-10-07', 'url': 'https://festival.example/p'}}

    def test_dos_salas_misma_hora_no_se_pierden(self):
        fs, _, _ = funcion.asignar_ids([f(sala='Sala 1', title='A'), f(sala='Sala 2', title='B')], {})
        r = funcion.resolver(fs, [], self.CTX)
        self.assertEqual(sorted(x['title'] for x in r.funciones), ['A', 'B'])

    def test_la_afirmacion_apunta_al_id(self):
        fs, _, _ = funcion.asignar_ids([f(sala='Sala 1', title='A'), f(sala='Sala 2', title='B')], {})
        b = next(x for x in fs if x['title'] == 'B')
        a = {'funcion': b['_fid'], 'casilla': 'sala', 'valor': 'Sala Capital',
             'fuente': {'tipo': 'sala', 'fecha': '2026-10-15', 'url': 'https://sala.example/b'}}
        r = funcion.resolver(fs, [a], self.CTX)
        self.assertEqual({x['title']: x['sala'] for x in r.funciones}, {'A': 'Sala 1', 'B': 'Sala Capital'})

    def test_id_desconocido_es_error(self):
        fs, _, _ = funcion.asignar_ids([f()], {})
        a = {'funcion': 'f_noexiste00', 'casilla': 'sala', 'valor': 'Sala 2',
             'fuente': {'tipo': 'sala', 'fecha': '2026-10-15', 'url': 'https://sala.example/b'}}
        with self.assertRaises(funcion.AnclaPerdida):
            funcion.resolver(fs, [a], self.CTX)


if __name__ == '__main__':
    unittest.main()
