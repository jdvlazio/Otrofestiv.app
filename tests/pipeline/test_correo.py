"""scripts/correo.py — el candado de los correos a festivales (16 nov 2026)."""
import os, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))
import correo as C

BIEN = '''X-Unsent: 1
From: hola@otrofestiv.app
To: info@festival.com
Subject: Festival en Otrofestiv
MIME-Version: 1.0
Content-Type: text/html; charset=utf-8

<p>Hola:</p>
<p>Somos <a href="https://otrofestiv.app">Otrofestiv</a>, una app gratuita para que el público arme su plan en los festivales de cine.</p>
<ol><li>¿A qué hora termina "Premiación"?</li></ol>
'''


def eml(txt):
    p = tempfile.mktemp(suffix='.eml')
    open(p, 'w', encoding='utf-8').write(txt)
    return p


class Candado(unittest.TestCase):
    def test_bien_pasa(self):
        self.assertEqual(C.revisar(eml(BIEN)), [])

    def test_lo_que_salio_mal_el_16_nov(self):
        malo = BIEN.replace('<p>Hola:</p>', '<blockquote type="cite"><p>Hola:</p>') + '</blockquote>'
        self.assertTrue(any('citado' in x for x in C.revisar(eml(malo))))
        plano = BIEN.replace('Content-Type: text/html', 'Content-Type: text/plain').replace('<p>Hola:</p>', '> Hola:')
        self.assertTrue(any('«>»' in x for x in C.revisar(eml(plano))))
        self.assertTrue(C.problemas_de_cita(BIEN.replace('<p>Hola', '<div class="Apple-Mail-URLShareWrapperClass"><p>Hola')))

    def test_sin_presentacion_ni_cabeceras_ni_borrador(self):
        x = C.revisar(eml(BIEN.replace('X-Unsent: 1\n', '').replace('To: info@festival.com\n', '')
                          .replace('Somos <a href="https://otrofestiv.app">Otrofestiv</a>', 'Somos nosotros')))
        self.assertTrue(any('X-Unsent' in y for y in x))
        self.assertTrue(any('To' in y for y in x))
        self.assertTrue(any('presentación' in y for y in x))

    def test_comillas_tipograficas_y_html_mal_cerrado(self):
        x = C.revisar(eml(BIEN.replace('"Premiación"', '«Premiación»').replace('</ol>', '')))
        self.assertTrue(any('comillas' in y for y in x))
        self.assertTrue(any('<ol>' in y for y in x))


if __name__ == '__main__':
    unittest.main()
