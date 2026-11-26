"""La búsqueda de la sinopsis también busca cuando la obra no tiene ningún texto (26 nov 2026).

Onboarding corrió buscar_sinopsis.py sobre 20 obras sin sinopsis: las ocho clases salieron en
«no aplica: la obra no publica sinopsis» y el registro quedó COMPLETO sin haber buscado nada."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import buscar_sinopsis as b

O = {'type': 'film', 'title': 'La tinaja rota', 'work_id': 'w_PRUEBA1', 'director': 'Ana María Pérez', 'year': 2025}
FEST = {'zz-prueba': {'films': [O]}}
SINOPSIS = 'Una mujer vuelve a su pueblo y encuentra el hotel de su infancia abandonado entre la niebla.'


def red(buscar=(), textos=None, web=''):
    return {'web': lambda u: web, 'tmdb': lambda i, r: {}, 'buscar': lambda t: list(buscar),
            'textos': lambda i: (textos or {}).get(i, [])}


class SinTexto(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._reg, b.REGISTROS = b.REGISTROS, self.tmp.name

    def tearDown(self):
        b.REGISTROS = self._reg
        self.tmp.cleanup()

    def test_autoprueba(self):
        self.assertEqual(b.autoprueba(), [])

    def test_sin_texto_busca_y_no_queda_completo(self):
        r = b.buscar('w_PRUEBA1', festivales=FEST, red=red())
        self.assertEqual(r['modo'], 'sin texto')
        self.assertFalse(any('no aplica' in r['clases'][c] for c in ('fuentes', 'instagram', 'tmdb', 'web')))
        self.assertTrue(b.incompleto(r), 'sin responder las consultas web no puede estar completo')
        self.assertIn('"La tinaja rota" Pérez', [q['consulta'] for q in r['clases']['web']['consultas']])

    def test_no_aplica_en_todo_no_es_buscar(self):
        self.assertTrue(b.incompleto({'clases': {c: {'no aplica': 'la obra no publica sinopsis'} for c in b.CLASES}}))

    def test_tmdb_por_titulo_y_direccion(self):
        cands = [{'id': 7, 'titulo': 'La tinaja rota', 'directores': ['Luc Besson']},
                 {'id': 9, 'titulo': 'La tinaja rota', 'directores': ['Ana María Pérez']}]
        r = b.buscar('w_PRUEBA1', festivales=FEST, red=red(cands, {9: [('es', SINOPSIS)]}))
        q = r['clases']['tmdb']['consultas']
        self.assertEqual([x['donde'] for x in q], ['https://www.themoviedb.org/movie/9'], 'solo la ficha con SU dirección')
        self.assertEqual(r['hallazgo']['texto'], SINOPSIS)
        self.assertTrue(r['hallazgo']['a_mano'], 'sin número de TMDB en la obra lo confirma una persona')

    def test_tmdb_homonimo_de_otra_direccion_no_vale(self):
        r = b.buscar('w_PRUEBA1', festivales=FEST, red=red([{'id': 7, 'titulo': 'La tinaja rota', 'directores': ['Luc Besson']}], {7: [('es', SINOPSIS)]}))
        self.assertIsNone(r['hallazgo'])
        self.assertEqual(r['clases']['tmdb']['consultas'][0]['resultado'], 'sin resultado')

    def test_anotar_el_texto_lo_comprueba_la_maquina(self):
        b.buscar('w_PRUEBA1', festivales=FEST, red=red())
        c = '"La tinaja rota" Pérez'
        visto = []

        def comprobar(o, obra=None):
            visto.append((o['texto'], o['fuente'], obra['titulos']))
            return 'literal', 'en la página, junto al título'
        b.anotar([{'work_id': 'w_PRUEBA1', 'consulta': c, 'resultado': 'literal', 'url': 'https://festival.co/tinaja', 'texto': SINOPSIS}],
                 comprobar=comprobar, festivales=FEST)
        self.assertEqual(visto, [(SINOPSIS, 'https://festival.co/tinaja', ['La tinaja rota'])])
        self.assertEqual(b.registro('w_PRUEBA1')['hallazgo']['texto'], SINOPSIS)

    def test_anotar_literal_de_palabra_no_pasa(self):
        b.buscar('w_PRUEBA1', festivales=FEST, red=red())
        with self.assertRaises(SystemExit):     # dice que lo halló y no trae el texto
            b.anotar([{'work_id': 'w_PRUEBA1', 'consulta': '"La tinaja rota" Pérez', 'resultado': 'literal', 'url': 'https://x.co'}], festivales=FEST)
        b.anotar([{'work_id': 'w_PRUEBA1', 'consulta': '"La tinaja rota" Pérez', 'resultado': 'literal', 'url': 'https://x.co', 'texto': SINOPSIS}],
                 comprobar=lambda o, obra=None: ('no está', 'la página no lo trae'), festivales=FEST)
        self.assertIsNone(b.registro('w_PRUEBA1')['hallazgo'], 'manda la máquina, no lo que dijo quien anotó')

    def test_sin_fuente_solo_con_todo_respondido(self):
        b.buscar('w_PRUEBA1', festivales=FEST, red=red())
        sf, b.SIN_FUENTE = b.SIN_FUENTE, os.path.join(self.tmp.name, 'sf.json')
        try:
            with self.assertRaises(SystemExit):
                b.declarar_sin_fuente([{'work_id': 'w_PRUEBA1', 'motivo': 'no aparece'}])
            b.anotar([{'work_id': 'w_PRUEBA1', **p, 'resultado': 'sin resultado', 'nota': 'nada de la obra'} for p in
                      [{k: v for k, v in x.items() if k in ('consulta', 'donde')} for x in b.pendiente(['w_PRUEBA1'])]], festivales=FEST)
            self.assertEqual(b.declarar_sin_fuente([{'work_id': 'w_PRUEBA1', 'motivo': 'no aparece'}]), 1)
        finally:
            b.SIN_FUENTE = sf

    def test_obra_que_nadie_publica(self):
        with self.assertRaises(SystemExit):
            b.buscar('w_NOEXISTE', festivales=FEST, red=red())


if __name__ == '__main__':
    unittest.main()
