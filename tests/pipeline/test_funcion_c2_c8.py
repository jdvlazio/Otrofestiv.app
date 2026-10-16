#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C2–C8 de la auditoría del 16 oct (docs/FUNCION.md §9). Escritos antes que
las correcciones; varios son los casos que el senior dev confirmó con código."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'pipeline'))
import funcion  # noqa: E402

CINE = 'Cinemateca de Bogotá'
URL = 'https://sala.example/f'
CTX = {'fuente_principal': {'tipo': 'festival-web', 'fecha': '2026-10-07', 'url': 'https://festival.example/p'}}


def base(**kw):
    f = {'title': 'H', 'type': 'film', 'day': '2026-10-23', 'time': '19:00', 'venue': f'{CINE} - Bogotá',
         'sala': 'Sala 3', 'duration': '90 min', '_ancla': (CINE, '2026-10-23', '19:00')}
    f.update(kw)
    return f


def af(casilla, valor, tipo='sala', fecha='2026-10-15', url=URL, ancla=(CINE, '2026-10-23', '19:00'), **kw):
    fu = {'tipo': tipo, 'fecha': fecha}
    fu.update({'url': url} if tipo != 'juan' else {'frase': url})
    if 'publicado' in kw:
        fu['publicado'] = kw.pop('publicado')
    a = {'ancla': {'sede': ancla[0], 'dia': ancla[1], 'hora': ancla[2]}, 'casilla': casilla, 'valor': valor, 'fuente': fu}
    a.update(kw)
    return a


def R(fs, afs, **ctx):
    return funcion.resolver(fs, afs, {**CTX, **ctx})


class C2Duracion(unittest.TestCase):
    """La estimación sale del resolver: es el último paso, aparte."""

    def test_resolver_no_estima(self):
        r = R([base(duration=None)], [])
        self.assertFalse(r.funciones[0].get('duration'))

    def test_estimar_solo_lo_vacio(self):
        fs = [base(duration=None), base(title='Otra', time='20:00', duration='45 min', _ancla=(CINE, '2026-10-23', '20:00'))]
        out = funcion.estimar_duraciones([dict(x, _procedencia={}) for x in fs])
        self.assertEqual([x['duration'] for x in out], ['60 min', '45 min'])
        self.assertEqual(out[0]['_procedencia']['duration']['marca'], 'estimado')

    def test_horas_como_horas_no_como_texto(self):
        # con el formato estricto (HH:MM) «9:00» no es una hora: no se estima
        # (es un conflicto de formato en el resolver); con horas válidas el hueco
        # se mide en minutos
        fs = [base(time='9:00', duration=None), base(title='Otra', time='10:00', _ancla=(CINE, '2026-10-23', '10:00'))]
        out = funcion.estimar_duraciones([dict(x, _procedencia={}) for x in fs])
        self.assertFalse(out[0].get('duration'))
        fs = [base(time='09:00', duration=None), base(title='Otra', time='10:30', _ancla=(CINE, '2026-10-23', '10:30'))]
        out = funcion.estimar_duraciones([dict(x, _procedencia={}) for x in fs])
        self.assertEqual(out[0]['duration'], '90 min')

    def test_otra_sede_no_cuenta(self):
        fs = [base(duration=None), base(title='Otra', time='19:30', venue='Otra sede - Bogotá', _ancla=('Otra sede', '2026-10-23', '19:30'))]
        out = funcion.estimar_duraciones([dict(x, _procedencia={}) for x in fs])
        self.assertEqual(out[0]['duration'], '60 min')


class C3Robustez(unittest.TestCase):
    def test_fuente_sin_rango_para_la_casilla_se_rechaza(self):
        with self.assertRaises(funcion.AfirmacionInvalida):
            R([base(sala=None)], [af('sala', 'Sala 2', tipo='prensa', url='https://prensa.example/x')])

    def test_idempotente(self):
        r1 = R([base()], [af('sala', 'Sala 2')])
        r2 = R(r1.funciones, [af('sala', 'Sala 2')])
        limpio = lambda fs: [{k: v for k, v in f.items() if k != '_procedencia'} for f in fs]
        self.assertEqual(limpio(r1.funciones), limpio(r2.funciones))

    def test_libre_quita_el_link_de_compra_de_la_base(self):
        r = R([base(ticket_url='https://tix.example/1', is_free=False)], [af('entrada', 'libre')])
        self.assertIs(r.funciones[0]['is_free'], True)
        self.assertNotIn('ticket_url', r.funciones[0])

    def test_conflicto_entre_funciones_nuevas_no_se_pierde(self):
        nueva = lambda t: af('existe', {'title': t, 'type': 'event', 'venue': f'{CINE} - Bogotá', 'day': '2026-10-24',
                                        'time': '15:00'}, tipo='festival-ig', url='https://ig.example/' + t,
                             ancla=(CINE, '2026-10-24', '15:00'))
        r = R([base()], [nueva('A'), nueva('B')])
        self.assertTrue(r.conflictos)

    def test_sin_ancla_error_claro(self):
        f = base()
        f.pop('_ancla')
        with self.assertRaises(funcion.AfirmacionInvalida):
            R([f], [])

    def test_existe_con_datos_sobre_funcion_existente_se_rechaza(self):
        with self.assertRaises(funcion.AfirmacionInvalida):
            R([base()], [af('existe', {'title': 'X', 'type': 'film', 'venue': 'V - X', 'day': '2026-10-23', 'time': '19:00'},
                            tipo='festival-ig', url='https://ig.example/x')])


class C4Formato(unittest.TestCase):
    def malo(self, a):
        with self.assertRaises(funcion.AfirmacionInvalida):
            R([base()], [a])

    def test_hora_7pm(self):
        self.malo(af('time', '7pm', tipo='festival-ig', url='https://ig.example/x'))

    def test_duracion_numero(self):
        self.malo(af('duration', 75, tipo='festival-ig', url='https://ig.example/x'))

    def test_obligatoria_none(self):
        self.malo(af('venue', None, tipo='juan', url='«x»'))

    def test_ancla_hora_mala(self):
        self.malo(af('sala', 'Sala 2', ancla=(CINE, '2026-10-23', '7pm')))

    def test_url_sin_https(self):
        self.malo(af('sala', 'Sala 2', url='http://sala.example/f'))

    def test_fecha_imposible_o_futura(self):
        self.malo(af('sala', 'Sala 2', fecha='2026-99-99'))
        self.malo(af('sala', 'Sala 2', fecha='2099-01-01'))

    def test_has_qa_booleano(self):
        self.malo(af('has_qa', 'sí', tipo='festival-web', url='https://festival.example/x'))


class C5Decisiones(unittest.TestCase):
    def test_decision_sin_contra_se_rechaza(self):
        with self.assertRaises(funcion.AfirmacionInvalida):
            R([base()], [af('sala', 'Sala 1', tipo='juan', url='«la 1»')])

    def test_decision_vigente(self):
        r = R([base()], [af('sala', 'Sala 1', tipo='juan', url='«la 1»', contra='Sala 3')])
        self.assertEqual(r.funciones[0]['sala'], 'Sala 1')
        self.assertEqual(r.conflictos, [])

    def test_decision_vencida_vuelve_a_revision(self):
        # Juan decidió contra «Sala 3»; ahora la sala dice «Sala 2»: lo que pisó cambió
        r = R([base()], [af('sala', 'Sala 2'), af('sala', 'Sala 1', tipo='juan', url='«la 1»', contra='Sala 3')])
        self.assertTrue(any(c.get('tipo') == 'decision-a-revisar' for c in r.conflictos))


class C6Fechas(unittest.TestCase):
    def test_publicado_manda_sobre_captura(self):
        # el IG se capturó hoy pero se publicó el 1 sep; la web se leyó el 7 oct: gana la web
        r = R([base()], [af('time', '19:30', tipo='festival-ig', fecha='2026-10-15', url='https://ig.example/x',
                            publicado='2026-09-01')])
        self.assertEqual(r.funciones[0]['time'], '19:00')


class C8Inscripcion(unittest.TestCase):
    def test_inscripcion_ya_no_es_valor_de_entrada(self):
        with self.assertRaises(funcion.AfirmacionInvalida):
            R([base()], [af('entrada', 'inscripcion', tipo='festival-web', url='https://festival.example/x')])

    def test_boleta_con_inscripcion(self):
        r = R([base()], [af('entrada', 'boleta', tipo='festival-web', url='https://festival.example/x'),
                         af('requires_registration', True, tipo='festival-web', url='https://festival.example/x')])
        f = r.funciones[0]
        self.assertIs(f['is_free'], False)
        self.assertIs(f['requires_registration'], True)


class C10Nivel(unittest.TestCase):
    """Las casillas son de la FUNCIÓN; lo de la obra va por el catálogo."""

    def test_los_campos_de_la_obra_no_son_afirmaciones(self):
        for c in ('director', 'year', 'country', 'synopsis', 'poster', 'genre', 'tmdb_id', 'lbSlug'):
            with self.assertRaises(funcion.AfirmacionInvalida, msg=c):
                R([base()], [af(c, 'x', tipo='festival-web', url='https://festival.example/x')])

    def test_toda_casilla_declara_su_nivel_funcion(self):
        self.assertEqual(set(funcion.NIVEL), set(funcion.RANGO))
        self.assertEqual(set(funcion.NIVEL.values()), {'funcion'})


if __name__ == '__main__':
    unittest.main()
