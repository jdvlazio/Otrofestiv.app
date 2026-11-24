"""Duraciones (20 nov 2026, Funza: «Basta Mamá» publicada con 125 min, la franja
con su conversatorio; dura 77). Dueños: pipeline/duraciones.py y la franja en
pipeline/ensamblar.py (_enriquece)."""
import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import duraciones
import ensamblar


def _raiz(runtimes, decl=None):
    d = tempfile.mkdtemp()
    st = os.path.join(d, 'festivals', 'staging')
    os.makedirs(st)
    json.dump({'verificadas': {t: {'tmdb_id': i + 1, 'duracion_tmdb': r} for i, (t, r) in enumerate(runtimes.items())}},
              open(os.path.join(st, 'x-2026-enriquecido.json'), 'w'))
    if decl is not None:
        json.dump({'duracion_distinta': decl}, open(os.path.join(st, 'x-2026-correcciones.json'), 'w'))
    return d


class Margen(unittest.TestCase):
    def test_la_franja_de_funza_esta_fuera(self):
        self.assertTrue(duraciones.fuera_de_margen(125, 77))

    def test_un_corte_de_pocos_minutos_no(self):
        self.assertFalse(duraciones.fuera_de_margen(80, 77))     # 3 min
        self.assertFalse(duraciones.fuera_de_margen(130, 120))   # 10 min: más de 5, pero menos del 10 % de 120 (12)
        self.assertTrue(duraciones.fuera_de_margen(135, 120))


class Distintas(unittest.TestCase):
    def test_funza(self):
        r = _raiz({'Basta Mamá': 77})
        xs = duraciones.distintas('x-2026', [{'title': 'Basta Mamá', 'duration': '125 min'}], r)
        self.assertEqual([(x['titulo'], x['dur'], x['tmdb']) for x in xs], [('Basta Mamá', 125, 77)])

    def test_dentro_de_un_programa(self):
        r = _raiz({'Corto': 29})
        films = [{'title': 'Programa', 'film_list': [{'title': 'Corto', 'duration': '23 min'}]}]
        xs = duraciones.distintas('x-2026', films, r)
        self.assertEqual(xs[0]['programa'], 'Programa')

    def test_declarada_con_porque_no_cuenta(self):
        r = _raiz({'Bright Future': 115}, {'Bright Future': {'_por_que': 'corte internacional de 92 min'}})
        self.assertEqual(duraciones.distintas('x-2026', [{'title': 'Bright Future', 'duration': '92 min'}], r), [])

    def test_declarada_sin_porque_no_sirve(self):
        r = _raiz({'Bright Future': 115}, {'Bright Future': {'_por_que': ''}})
        self.assertEqual(len(duraciones.distintas('x-2026', [{'title': 'Bright Future', 'duration': '92 min'}], r)), 1)
        self.assertEqual(len(duraciones.declaradas('x-2026', r)[1]), 1)

    def test_las_actividades_no_se_miden(self):
        r = _raiz({'Taller': 30})
        self.assertEqual(duraciones.distintas('x-2026', [{'title': 'Taller', 'duration': '120 min', 'type': 'event'}], r), [])

    def test_sin_enriquecido_no_hay_con_que_medir(self):
        d = tempfile.mkdtemp()
        self.assertEqual(duraciones.distintas('x-2026', [{'title': 'A', 'duration': '125 min'}], d), [])


class Franja(unittest.TestCase):
    def setUp(self):
        ensamblar.AVISOS_FRANJA.clear()
        ensamblar.AVISOS_DURACION.clear()

    def test_la_obra_se_queda_con_su_runtime_y_el_sobrante_es_conversatorio(self):
        dst = {'title': 'Basta Mamá', 'duration': '125 min', '_franja_min': 125}
        ensamblar._enriquece(dst, {'duracion_tmdb': 77})
        self.assertEqual(dst['duration'], '77 min')
        self.assertTrue(dst['has_qa'])
        self.assertNotIn('_franja_min', dst)
        self.assertEqual(ensamblar.AVISOS_DURACION, [])          # ya no es una contradicción

    def test_si_el_crudo_trae_la_duracion_de_la_obra_manda_esa(self):
        dst = {'title': 'A', 'duration': '80 min', '_franja_min': 120}
        ensamblar._enriquece(dst, {'duracion_tmdb': 77})
        self.assertEqual(dst['duration'], '80 min')
        self.assertTrue(dst['has_qa'])

    def test_poco_sobrante_no_es_conversatorio(self):
        dst = {'title': 'A', 'duration': '85 min', '_franja_min': 85}
        ensamblar._enriquece(dst, {'duracion_tmdb': 77})
        self.assertEqual(dst['duration'], '77 min')
        self.assertFalse(dst.get('has_qa'))

    def test_sin_franja_la_duracion_del_festival_manda_y_avisa(self):
        dst = {'title': 'A', 'duration': '125 min'}
        ensamblar._enriquece(dst, {'duracion_tmdb': 77})
        self.assertEqual(dst['duration'], '125 min')
        self.assertEqual(len(ensamblar.AVISOS_DURACION), 1)


class Publicar(unittest.TestCase):
    def test_publicar_usa_el_dueno_unico(self):
        src = open(os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline', 'publicar.py'), encoding='utf-8').read()
        self.assertIn('duraciones.distintas', src)


if __name__ == '__main__':
    unittest.main()
