"""Un programa de 2+ obras no hereda la ficha de UNA (20 oct 2026, BHFF): «El
Susurro + Esquirlas de Caracol» recibía el lbSlug, el año, el género y la
descripción de El Susurro. Dos capas: enriquecer.py no busca el título del
programa en TMDB, y ensamblar.py no le pega una ficha de TMDB aunque exista."""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import enriquecer, ensamblar

DOS = [{'titulo': 'El Susurro'}, {'titulo': 'Esquirlas de Caracol'}]


class EnriquecerNoBuscaElPrograma(unittest.TestCase):
    def test_dos_obras_es_programa(self):
        self.assertTrue(enriquecer.es_programa({'titulo': 'El Susurro + Esquirlas de Caracol', 'obras': DOS}))
        self.assertTrue(enriquecer.es_programa({'film_list': [{'title': 'A'}, {'title': 'B'}]}))

    def test_el_titulo_del_programa_no_se_busca_y_sus_obras_si(self):
        fs = [{'titulo': 'El Susurro + Esquirlas de Caracol', 'obras': DOS},
              {'titulo': 'Critters'},
              {'titulo': 'Programa de uno', 'obras': [{'titulo': 'Solo'}]}]
        t = set(enriquecer.obras_a_buscar(fs, {}))
        self.assertEqual(t, {'El Susurro', 'Esquirlas de Caracol', 'Critters', 'Programa de uno', 'Solo'})

    def test_una_obra_o_ninguna_no_es_programa(self):
        self.assertFalse(enriquecer.es_programa({'obras': DOS[:1]}))
        self.assertFalse(enriquecer.es_programa({'titulo': 'Critters'}))


class EnsamblarNoPegaLaFicha(unittest.TestCase):
    PROG = {'title': 'El Susurro + Esquirlas de Caracol', 'film_list': [{'title': 'El Susurro'}, {'title': 'Esquirlas de Caracol'}]}

    def test_ficha_de_tmdb_no_va_al_programa(self):
        it = {'titulo': 'El Susurro + Esquirlas de Caracol', 'lbSlug': 'the-whisper-2025', 'tmdb_id': 1534530, 'anio': 2025}
        self.assertIsNone(ensamblar.ficha_de_la_funcion(self.PROG, it))

    def test_lo_declarado_para_el_programa_si_pasa(self):
        it = {'titulo': 'El Susurro + Esquirlas de Caracol', 'sinopsis': 'Dos obras de terror colombiano.'}
        self.assertEqual(ensamblar.ficha_de_la_funcion(self.PROG, it), it)

    def test_una_obra_sigue_tomando_su_ficha(self):
        it = {'lbSlug': 'critters', 'tmdb_id': 1}
        self.assertEqual(ensamblar.ficha_de_la_funcion({'title': 'Critters'}, it), it)
        self.assertEqual(ensamblar.ficha_de_la_funcion({'film_list': [{'title': 'Critters'}]}, it), it)

    def test_aplicado_no_deja_campos_de_una_obra(self):
        e = dict(self.PROG)
        it = ensamblar.ficha_de_la_funcion(e, {'lbSlug': 'the-whisper-2025', 'tmdb_id': 1534530, 'genero': 'Terror', 'anio': 2025})
        if it:
            ensamblar._enriquece(e, it)
        for k in ('lbSlug', 'tmdb_id', 'genre', 'year'):
            self.assertNotIn(k, e)


if __name__ == '__main__':
    unittest.main()
