"""La cascada de lo ya publicado (enriquecer.reuso_publicada): una obra sin ficha
de TMDB que YA publicamos en otro festival reusa lo que mostramos entonces. Hasta
el 17 oct reusaba solo afiche y sinopsis; país, año, duración, género y sinopsis
en inglés se quedaban en el otro festival (Ficcali, Vanguardias: «La Tinaja» con
afiche y sin país — lo cazó [dato-que-no-viaja])."""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import enriquecer


class Reuso(unittest.TestCase):
    def test_trae_todo_lo_publicado(self):
        pub = [{'festival': 'popayan-2026', 'titulo': 'La Tinaja', 'sinopsis': 'Una tinaja…',
                'country': 'Colombia', 'year': 2025, 'duration': '14 min', 'genre': 'Documental',
                'synopsis_en': 'A jar…'}]
        e = enriquecer.reuso_publicada(pub)
        self.assertEqual((e['pais'], e['anio'], e['duracion_tmdb'], e['genero'], e['synopsis_en']),
                         ('Colombia', 2025, 14, 'Documental', 'A jar…'))

    def test_sin_nada_que_reusar_es_none(self):
        self.assertIsNone(enriquecer.reuso_publicada([{'festival': 'x', 'titulo': 't'}]))

    def test_solo_el_pais_alcanza(self):
        e = enriquecer.reuso_publicada([{'festival': 'x', 'titulo': 't', 'country': 'Colombia'}])
        self.assertEqual(e['pais'], 'Colombia')


if __name__ == '__main__':
    unittest.main()
