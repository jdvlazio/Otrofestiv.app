#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests del modelo de la función (docs/FUNCION.md). Se escribieron ANTES que
pipeline/funcion.py: cada regla de la §4 tiene su caso. Corre con
`python3 -m unittest discover -s tests/pipeline` y lo llama validate.py
[funcion-tests]."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'pipeline'))
import funcion  # noqa: E402

CINE = 'Cinemateca de Bogotá'
SALA_URL = 'https://cinematecadebogota.gov.co/node/peliculas/3620'
IG = 'https://www.instagram.com/p/XXX/'


def base(**kw):
    f = {'title': 'Hiperrealidad', 'type': 'film', 'day': '2026-10-23', 'time': '19:00',
         'venue': f'{CINE} - Bogotá', 'sala': 'Sala 3', 'duration': '90 min',
         '_ancla': (CINE, '2026-10-23', '19:00')}
    f.update(kw)
    return f


def af(casilla, valor, tipo='sala', fecha='2026-10-15', url=SALA_URL, ancla=(CINE, '2026-10-23', '19:00'), **kw):
    a = {'ancla': {'sede': ancla[0], 'dia': ancla[1], 'hora': ancla[2]}, 'casilla': casilla, 'valor': valor,
         'fuente': {'tipo': tipo, 'fecha': fecha, **({'url': url} if tipo != 'juan' else {'frase': url})}}
    a.update(kw)
    return a


CTX = {'fuente_principal': {'tipo': 'festival-web', 'fecha': '2026-10-07', 'url': 'https://festival.example/programa'}}


def resolver(funciones, afirmaciones, **ctx):
    return funcion.resolver(funciones, afirmaciones, {**CTX, **ctx})


class Rango(unittest.TestCase):
    def test_sala_gana_la_sede_sobre_el_festival(self):
        r = resolver([base()], [af('sala', 'Sala 2')])
        self.assertEqual(r.funciones[0]['sala'], 'Sala 2')
        self.assertEqual(r.funciones[0]['_procedencia']['sala']['tipo'], 'sala')
        self.assertEqual(r.conflictos, [])

    def test_hora_gana_el_festival_sobre_la_sala(self):
        r = resolver([base()], [af('time', '19:30')])
        self.assertEqual(r.funciones[0]['time'], '19:00')

    def test_juan_gana_siempre(self):
        r = resolver([base()], [af('sala', 'Sala 2'), af('sala', 'Sala Capital', tipo='juan', url='«ponela en la Capital»')])
        self.assertEqual(r.funciones[0]['sala'], 'Sala Capital')
        self.assertEqual(r.funciones[0]['_procedencia']['sala']['tipo'], 'juan')


class MasReciente(unittest.TestCase):
    def test_dentro_del_rango_gana_lo_mas_reciente(self):
        # IG del festival del 14 oct contra la web del 7 oct: mismo rango, gana IG
        r = resolver([base()], [af('time', '19:30', tipo='festival-ig', fecha='2026-10-14', url=IG)])
        self.assertEqual(r.funciones[0]['time'], '19:30')

    def test_la_fecha_de_la_fuente_principal_es_la_de_la_funcion(self):
        # el crudo se regenera hoy, pero la web se leyó el 26 sep: el IG del 14 oct
        # es más nuevo y gana la hora
        f = base(_src={'url': 'https://festival.example/p', 'date': '2026-09-26'})
        r = resolver([f], [af('time', '19:30', tipo='festival-ig', fecha='2026-10-14', url=IG)],
                     fuente_principal={'tipo': 'festival-web', 'fecha': '2026-10-16', 'url': 'https://festival.example/p'})
        self.assertEqual(r.funciones[0]['time'], '19:30')

    def test_lo_viejo_no_pisa_lo_nuevo(self):
        r = resolver([base()], [af('time', '18:00', tipo='festival-ig', fecha='2026-10-01', url=IG)])
        self.assertEqual(r.funciones[0]['time'], '19:00')


class Conflicto(unittest.TestCase):
    def test_mismo_rango_misma_fecha_distinto_valor_es_conflicto(self):
        r = resolver([base()], [af('sala', 'Sala 2'), af('sala', 'Sala 1', url=SALA_URL + '?b')])
        self.assertEqual(len(r.conflictos), 1)
        self.assertEqual(r.conflictos[0]['casilla'], 'sala')
        # ninguna gana: queda lo de la fuente principal
        self.assertEqual(r.funciones[0]['sala'], 'Sala 3')

    def test_mismo_valor_no_es_conflicto(self):
        r = resolver([base()], [af('sala', 'Sala 2'), af('sala', 'Sala 2', url=SALA_URL + '?b')])
        self.assertEqual(r.conflictos, [])

    def test_una_decision_cierra_el_conflicto(self):
        r = resolver([base()], [af('sala', 'Sala 2'), af('sala', 'Sala 1', url=SALA_URL + '?b'),
                                af('sala', 'Sala 2', tipo='juan', url='«la 2»')])
        self.assertEqual(r.conflictos, [])
        self.assertEqual(r.funciones[0]['sala'], 'Sala 2')


class Entrada(unittest.TestCase):
    def test_sin_senal_es_libre_por_supuesto(self):
        r = resolver([base()], [])
        f = r.funciones[0]
        self.assertIs(f['is_free'], True)
        self.assertEqual(f['_procedencia']['entrada']['marca'], 'supuesto')

    def test_sede_que_siempre_cobra_supone_boleta(self):
        r = resolver([base()], [], sedes_que_cobran={CINE})
        self.assertIs(r.funciones[0]['is_free'], False)
        self.assertEqual(r.funciones[0]['_procedencia']['entrada']['marca'], 'supuesto')

    def test_festival_pago_supone_boleta(self):
        r = resolver([base()], [], ticketing_model='paid')
        self.assertIs(r.funciones[0]['is_free'], False)

    def test_la_sala_dice_libre(self):
        r = resolver([base(is_free=False)], [af('entrada', 'libre')])
        self.assertIs(r.funciones[0]['is_free'], True)
        self.assertNotIn('marca', r.funciones[0]['_procedencia']['entrada'])

    def test_boleta_es_explicita_y_no_publica_precio(self):
        r = resolver([base()], [af('entrada', 'boleta', evidencia='Con boleta: $7.000')])
        f = r.funciones[0]
        self.assertIs(f['is_free'], False)
        self.assertNotIn('7.000', repr({k: v for k, v in f.items() if not k.startswith('_')}))

    def test_entrada_de_la_fuente_principal_se_respeta(self):
        r = resolver([base(requires_registration=True)], [])
        f = r.funciones[0]
        self.assertIs(f['requires_registration'], True)
        self.assertNotIn('marca', f['_procedencia']['entrada'])

    def test_link_de_compra_de_la_sala(self):
        r = resolver([base()], [af('ticket_url', 'https://cinemateca.checkout.tuboleta.com/x')])
        self.assertEqual(r.funciones[0]['ticket_url'], 'https://cinemateca.checkout.tuboleta.com/x')

    def test_entrada_desconocida_se_rechaza(self):
        with self.assertRaises(funcion.AfirmacionInvalida):
            resolver([base()], [af('entrada', 'gratis')])


class Duracion(unittest.TestCase):
    def test_sin_duracion_se_estima_hasta_la_siguiente(self):
        a = base(duration=None)
        b = base(title='Otra', time='20:00', _ancla=(CINE, '2026-10-23', '20:00'))
        r = resolver([a, b], [])
        f = r.funciones[0]
        self.assertEqual(f['duration'], '60 min')
        self.assertEqual(f['_procedencia']['duration']['marca'], 'estimado')

    def test_estimada_tope_90_y_60_si_es_la_ultima(self):
        a = base(duration=None)
        self.assertEqual(resolver([a], []).funciones[0]['duration'], '60 min')
        b = base(title='Otra', time='23:00', _ancla=(CINE, '2026-10-23', '23:00'))
        self.assertEqual(resolver([base(duration=None), b], []).funciones[0]['duration'], '90 min')

    def test_duracion_afirmada_no_se_estima(self):
        r = resolver([base(duration=None)], [af('duration', '75 min', tipo='festival-ig', url=IG)])
        self.assertEqual(r.funciones[0]['duration'], '75 min')
        self.assertNotIn('marca', r.funciones[0]['_procedencia']['duration'])


class ExisteYAncla(unittest.TestCase):
    def test_agregar_una_funcion(self):
        nueva = af('existe', {'title': 'Taller', 'type': 'event', 'event_kind': 'taller', 'venue': f'{CINE} - Bogotá',
                              'day': '2026-10-24', 'time': '15:00', 'duration': '180 min'},
                   tipo='festival-ig', url=IG, ancla=(CINE, '2026-10-24', '15:00'))
        r = resolver([base()], [nueva])
        self.assertEqual(len(r.funciones), 2)
        self.assertEqual(r.funciones[1]['_procedencia']['existe']['tipo'], 'festival-ig')

    def test_quitar_una_funcion_pide_por_que(self):
        with self.assertRaises(funcion.AfirmacionInvalida):
            resolver([base()], [af('existe', False, tipo='juan', url='«fuera»')])
        r = resolver([base()], [af('existe', False, tipo='juan', url='«fuera»', por_que='colegio, acceso restringido')])
        self.assertEqual(r.funciones, [])

    def test_ancla_que_no_existe_aborta(self):
        with self.assertRaises(funcion.AnclaPerdida):
            resolver([base()], [af('sala', 'Sala 2', ancla=(CINE, '2026-10-23', '21:00'))])

    def test_la_hora_movida_no_rompe_las_demas_afirmaciones(self):
        # el ancla es la de la fuente principal: después de mover la hora, la sala
        # se sigue afirmando contra 19:00
        r = resolver([base()], [af('time', '19:30', tipo='festival-ig', fecha='2026-10-14', url=IG),
                                af('sala', 'Sala 2')])
        self.assertEqual((r.funciones[0]['time'], r.funciones[0]['sala']), ('19:30', 'Sala 2'))


class Validez(unittest.TestCase):
    def test_sin_fuente_no_entra(self):
        a = af('sala', 'Sala 2')
        a['fuente'].pop('url')
        with self.assertRaises(funcion.AfirmacionInvalida):
            resolver([base()], [a])

    def test_sin_fecha_no_entra(self):
        a = af('sala', 'Sala 2')
        a['fuente'].pop('fecha')
        with self.assertRaises(funcion.AfirmacionInvalida):
            resolver([base()], [a])

    def test_tipo_de_fuente_desconocido(self):
        with self.assertRaises(funcion.AfirmacionInvalida):
            resolver([base()], [af('sala', 'Sala 2', tipo='rumor')])

    def test_casilla_desconocida(self):
        with self.assertRaises(funcion.AfirmacionInvalida):
            resolver([base()], [af('precio', '$7.000')])

    def test_casilla_obligatoria(self):
        self.assertEqual(funcion.faltan_obligatorias(base()), [])
        self.assertIn('time', funcion.faltan_obligatorias(base(time=None)))


class Carga(unittest.TestCase):
    """cargar() y contexto(): el archivo del festival y su contexto, validados."""

    def setUp(self):
        import tempfile
        self.d = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.d, 'festivals', 'staging'))

    def _escribir(self, nombre, data):
        import json
        with open(os.path.join(self.d, 'festivals', 'staging', nombre), 'w', encoding='utf-8') as f:
            json.dump(data, f)

    def test_sin_archivo_no_hay_afirmaciones(self):
        self.assertIsNone(funcion.cargar('zzz-2026', raiz=self.d))

    def test_archivo_sin_provenance_se_rechaza(self):
        self._escribir('zzz-2026-afirmaciones.json', {'afirmaciones': []})
        with self.assertRaises(funcion.AfirmacionInvalida):
            funcion.cargar('zzz-2026', raiz=self.d)

    def test_archivo_valida_cada_afirmacion(self):
        self._escribir('zzz-2026-afirmaciones.json', {'_provenance': {'capturado': '2026-10-16'},
                                                      'afirmaciones': [af('precio', '$7.000')]})
        with self.assertRaises(funcion.AfirmacionInvalida):
            funcion.cargar('zzz-2026', raiz=self.d)

    def test_contexto_de_la_fuente_principal(self):
        crudo = {'_provenance': {'url': 'https://festival.example/p', 'capturado': '2026-09-26'}}
        c = funcion.contexto(crudo, plan={'fuente_principal': 'festival-web'}, ticketing_model='mixed')
        self.assertEqual(c['fuente_principal'], {'tipo': 'festival-web', 'url': 'https://festival.example/p',
                                                 'fecha': '2026-09-26'})
        self.assertIn(CINE, c['sedes_que_cobran'])
        self.assertEqual(c['ticketing_model'], 'mixed')

    def test_contexto_sin_fecha_de_la_fuente_principal_falla(self):
        with self.assertRaises(funcion.AfirmacionInvalida):
            funcion.contexto({'_provenance': {'url': 'https://x'}}, plan={})

    def test_afirmaciones_de_una_ancla(self):
        xs = [af('sala', 'Sala 2'), af('sala', 'Sala 1', ancla=(CINE, '2026-10-24', '19:00'))]
        self.assertEqual(len(funcion.de_ancla(xs, (CINE, '2026-10-23', '19:00'))), 1)


class Boleteria(unittest.TestCase):
    def test_modelo_de_boleteria_desde_config(self):
        cfg = "  'zzz2026': {\n    name:'Z',\n    ticketing_model:'mixed',\n    films:null\n  },\n  'yyy2026': {\n    name:'Y',films:null\n  },"
        self.assertEqual(funcion.ticketing_model_de('zzz-2026', cfg), 'mixed')
        self.assertIsNone(funcion.ticketing_model_de('yyy-2026', cfg))
        self.assertIsNone(funcion.ticketing_model_de('xxx-2026', cfg))

    def test_bhff_es_mixto_en_el_repo(self):
        self.assertEqual(funcion.ticketing_model_de('bhff-2026'), 'mixed')


class SedesQueCobran(unittest.TestCase):
    def test_cada_sede_que_cobra_cita_su_fuente(self):
        for sede, fuente in funcion.SEDES_QUE_COBRAN.items():
            self.assertTrue(str(fuente).strip(), sede)


class Autoprueba(unittest.TestCase):
    def test_la_autoprueba_no_tiene_ciegos(self):
        self.assertEqual(funcion.autoprueba(), [])


if __name__ == '__main__':
    unittest.main()
