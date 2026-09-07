"""Extracción del PDF oficial del programa QAFF 2026 (Bogotá).

limpia  → páginas del PDF sin el ruido del lomo vertical
fichas  → las 65 fichas de obra (país, año, duración, tipo, idioma, sinopsis)
parrilla→ los créditos impresos junto a cada obra + las marcas de invitado
programa→ la programación transcrita, página por página
verifica→ cada dato transcrito contra la página que declara ser su fuente
"""
import os

STAGING = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       '..', '..', 'festivals', 'staging')


def _ruta(nombre):
    return os.path.join(STAGING, nombre)
