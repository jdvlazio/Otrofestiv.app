#!/usr/bin/env python3
"""servidor-pruebas.py <puerto> — el servidor que levanta Playwright para los tests.

POR QUÉ EXISTE (19 oct 2026): el test que más fallaba «de a ratos» (la app nunca
llegaba a data-app-ready) no era la app: era este servidor CORTANDO conexiones
(net::ERR_CONNECTION_RESET sobre /src/*.js). socketserver acepta por defecto solo
5 conexiones en espera (request_queue_size = 128); la app pide más de 30 módulos ES
de golpe, en macOS las que sobran se rechazan, y un módulo que no llega deja el
arranque a medias. Empeoraba a medida que la app ganaba módulos: medido 7 de 10
corridas de datos-fuente.spec con algún test caído.

Hilos (ThreadingHTTPServer, ya estaba) + cola de 128 + hilos que no traban el cierre.
"""
import sys
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler


class Servidor(ThreadingHTTPServer):
    request_queue_size = 128
    daemon_threads = True


if __name__ == '__main__':
    Servidor(('', int(sys.argv[1])), SimpleHTTPRequestHandler).serve_forever()
