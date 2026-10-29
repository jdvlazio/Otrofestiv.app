"""Afiches declarados en <fid>-afiches.json (MIDBO, 20 oct 2026, #1210):
`sobre_tmdb` reemplaza la imagen de TMDB rechazada, y `asset` da un nombre
propio que enriquecer.py escribe y encuadrar-posters.py respeta (un solo dueño)."""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import lib

TMDB = {'tmdb_id': 9, 'poster_path': '/x.jpg', 'poster': 'https://image.tmdb.org/t/p/w500/x.jpg', 'posterSource': 'tmdb', 'anio': 2025}


class SobreTmdb(unittest.TestCase):
    def test_con_la_marca_sale_la_imagen_de_tmdb_y_queda_la_ficha(self):
        e = lib.sin_tmdb_si_se_pide(TMDB, {'archivo': 'x', 'sobre_tmdb': True})
        for k in ('poster_path', 'poster', 'posterSource'):
            self.assertNotIn(k, e)
        self.assertEqual((e['tmdb_id'], e['anio']), (9, 2025))   # la ficha sigue

    def test_sin_la_marca_tmdb_manda(self):
        self.assertEqual(lib.sin_tmdb_si_se_pide(TMDB, {'archivo': 'x'}), TMDB)

    def test_no_toca_el_original(self):
        lib.sin_tmdb_si_se_pide(TMDB, {'sobre_tmdb': True})
        self.assertIn('poster', TMDB)


class Asset(unittest.TestCase):
    def test_nombre_propio_si_lo_trae(self):
        self.assertEqual(lib.asset_declarado('Trizas', {'asset': 'trizas-afiche.jpg'}), 'trizas-afiche.jpg')

    def test_si_no_el_slug_del_titulo(self):
        self.assertEqual(lib.asset_declarado('La taquigrafista', {}), 'la-taquigrafista.jpg')

    def test_enriquecer_y_encuadrar_usan_el_mismo_dueno(self):
        raiz = os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline')
        for f in ('enriquecer.py', 'encuadrar-posters.py'):
            src = open(os.path.join(raiz, f), encoding='utf-8').read()
            self.assertIn('asset_declarado', src, f'{f} calcula el nombre por su cuenta')
            self.assertNotIn("d.get('asset') or", src, f'{f} tiene una copia propia de la regla')


if __name__ == '__main__':
    unittest.main()
