"""Guardián de sinopsis (19 nov 2026, pedido de Juan tras CUAFF): toda OBRA
publicada lleva sinopsis en español o su porqué en `sin_sinopsis` con fuentes.
Dueño único: pipeline/sinopsis.py."""
import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import sinopsis

ES = 'Una mujer vuelve al pueblo donde creció.'
EN = 'A woman returns to the town where she grew up.'


def _raiz(sin_sinopsis=None):
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, 'festivals', 'staging'))
    if sin_sinopsis is not None:
        json.dump({'sin_sinopsis': sin_sinopsis},
                  open(os.path.join(d, 'festivals', 'staging', 'x-2026-correcciones.json'), 'w'))
    return d


class Pendientes(unittest.TestCase):
    def test_con_sinopsis_en_espanol_no_queda_pendiente(self):
        self.assertEqual(sinopsis.pendientes('x-2026', [{'title': 'A', 'synopsis': ES}], _raiz()), [])

    def test_solo_en_ingles_se_marca_para_traducir(self):
        p = sinopsis.pendientes('x-2026', [{'title': 'A', 'synopsis_en': EN}], _raiz())
        self.assertEqual([(x['titulo'], x['accion']) for x in p], [('A', 'traducir')])

    def test_sin_ninguna_se_marca_para_buscar(self):
        p = sinopsis.pendientes('x-2026', [{'title': 'A'}], _raiz())
        self.assertEqual(p[0]['accion'], 'buscar')

    def test_las_actividades_no_cuentan(self):
        films = [{'title': 'Taller', 'event_kind': 'taller'}, {'title': 'Charla', 'type': 'event'}]
        self.assertEqual(sinopsis.pendientes('x-2026', films, _raiz()), [])

    def test_en_un_programa_cuentan_sus_obras_no_el_programa(self):
        films = [{'title': 'Programa 1', 'film_list': [{'title': 'Corto A', 'synopsis': ES},
                                                        {'title': 'Corto B'}]}]
        p = sinopsis.pendientes('x-2026', films, _raiz())
        self.assertEqual([(x['titulo'], x['programa']) for x in p], [('Corto B', 'Programa 1')])

    def test_una_obra_repetida_cuenta_una_vez(self):
        p = sinopsis.pendientes('x-2026', [{'title': 'A'}, {'title': 'A'}], _raiz())
        self.assertEqual(len(p), 1)


class Declaracion(unittest.TestCase):
    def test_con_porque_y_fuentes_la_cubre(self):
        r = _raiz({'A': {'_por_que': 'no la publica nadie', 'fuentes': ['ficha de la sala', 'TMDB']}})
        self.assertEqual(sinopsis.pendientes('x-2026', [{'title': 'A'}], r), [])

    def test_por_el_titulo_del_programa_cubre_sus_obras(self):
        r = _raiz({'Programa 1': {'_por_que': 'x', 'fuentes': ['web del festival']}})
        films = [{'title': 'Programa 1', 'film_list': [{'title': 'Corto B'}]}]
        self.assertEqual(sinopsis.pendientes('x-2026', films, r), [])

    def test_sin_fuentes_no_cuenta(self):
        r = _raiz({'A': {'_por_que': 'no la encontré'}})
        self.assertEqual(len(sinopsis.pendientes('x-2026', [{'title': 'A'}], r)), 1)

    def test_sin_porque_no_cuenta(self):
        r = _raiz({'A': {'fuentes': ['TMDB']}})
        self.assertEqual(len(sinopsis.pendientes('x-2026', [{'title': 'A'}], r)), 1)


class Deuda(unittest.TestCase):
    def test_un_festival_sin_deuda_parte_de_cero(self):
        self.assertIsNotNone(sinopsis.excede('nuevo-2099', [{'title': 'A'}], _raiz()))

    def test_publicar_usa_el_dueno_unico(self):
        src = open(os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline', 'publicar.py'),
                   encoding='utf-8').read()
        self.assertIn('sinopsis.excede', src)


class Calidad(unittest.TestCase):
    """23 nov 2026: un texto que no es sinopsis cuenta como si no estuviera."""
    LISTA = 'Alejandra Castaño Arias, Wildier Tascón Tascón, Roxana Panchí Gutierrez, Alexa Yagarí Panchí, Laura Giraldo Mira'

    def test_la_lista_de_actores_queda_pendiente(self):
        p = sinopsis.pendientes('x-2026', [{'title': 'A', 'synopsis': self.LISTA}], _raiz())
        self.assertEqual((p[0]['accion'], p[0]['defectos']), ('corregir', ['parece una lista de nombres']))
        self.assertIn('corregir', sinopsis.linea(p[0]))

    def test_sin_sinopsis_no_excusa_publicar_un_texto_malo(self):
        r = _raiz({'A': {'_por_que': 'x', 'fuentes': ['y']}})
        self.assertEqual(len(sinopsis.pendientes('x-2026', [{'title': 'A', 'synopsis': self.LISTA}], r)), 1)

    def test_falso_positivo_declarado_con_porque(self):
        r = _raiz()
        for pq, n in (('la leyó Juan', 0), ('', 1)):
            json.dump({'sinopsis_revisada': {'A': {'_por_que': pq}}}, open(os.path.join(r, 'festivals', 'staging', 'x-2026-correcciones.json'), 'w'))
            self.assertEqual(len(sinopsis.pendientes('x-2026', [{'title': 'A', 'synopsis': self.LISTA}], r)), n)


class Herencia(unittest.TestCase):
    def test_una_defectuosa_no_viaja_a_otro_festival(self):
        import herencia
        w = lambda s: {'sinopsis': {'es': s}, 'presentaciones': ['otro-2026']}
        self.assertIsNone(herencia.valor(w(ES + ' Enlace para comprar entrada para la función'), 'synopsis_es', 'x-2026', 'A'))
        self.assertEqual(herencia.valor(w(ES), 'synopsis_es', 'x-2026', 'A'), ES)


if __name__ == '__main__':
    unittest.main()
