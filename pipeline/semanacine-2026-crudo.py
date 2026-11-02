#!/usr/bin/env python3
"""semanacine-2026-crudo.py — la lámina «Programación 2026» de la 5.ª Semana
del Cine Colombiano (Cali, 3–9 nov) → crudo.

LA FUENTE es UNA lámina de Instagram de @semanadelcinecolombiano
(https://www.instagram.com/p/DfKgpBVpyUt/, 31 oct 2026, 1440×1920, copia en
fuentes/semanacine-2026/programacion-DfKgpBVpyUt.jpg). El festival no tiene
web. Transcrita a ojo y cruzada con pipeline/ocr.py sobre la misma imagen
(2 nov 2026): coinciden las 13 casillas de hora, título y sede.
El post del 1 nov (p/DfMs0KoJgLT) repite El Titán con la misma hora y sede.

DECISIONES (Juan, 2 nov 2026):
  · sección = la palabra del festival en la lámina («Película»,
    «Conversatorio», «Cine Bajo las Estrellas», «Proyección de cortos locales»);
  · el sábado 7 («Cine Bajo las Estrellas, película y encuentro musical»,
    Brisas de Mayo) no trae hora ni película: no se publica hasta que la anuncien;
  · acceso: ninguna pieza anuncia pago (El Titán: «ingreso hasta agotar aforo")
    → entrada libre (regla de Juan, 13 oct).
DURACIÓN: la lámina no la da. Las películas la toman de TMDB (enriquecer);
los conversatorios no se declaran (sin dato no se inventa).
"""
import io, json, os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

OUT = f'{REPO}/festivals/staging/semanacine-2026-crudo.json'
SRC = {'url': 'https://www.instagram.com/p/DfKgpBVpyUt/', 'date': '2026-10-31', 'tipo': 'festival-ig'}
USC = 'Universidad Santiago de Cali'
ACCESO = 'Entrada libre (no se anuncia pago)'

# (día, hora, título, sección, sede, sala, extra)
FILAS = [
    ('2026-11-03', '08:30', 'Conversatorio «Cine Colombiano: nuevo Café de Colombia»', 'Conversatorio', 'Acajel', '',
     {'sinopsis': 'Con Arturo Murgas (Semana del Cine Colombiano).'}),
    ('2026-11-03', '12:00', 'Lejos, aquí', 'Película', USC, 'Auditorio T-Usaca',
     {'director': 'Ana Sofía Osorio Ruiz', 'has_qa': True, '_nota': 'Presentación con Ana María Osorio (Directora)'}),
    ('2026-11-03', '18:00', 'Perro come perro', 'Cine Bajo las Estrellas', USC, 'Plazoleta de Los Sabios',
     {'director': 'Carlos Moreno', '_nota': 'Homenaje 20 años de la película Perro, Come Perro.'}),
    ('2026-11-04', '09:00', 'Conversatorio «Experiencias y Vivencias en el Cine»', 'Conversatorio', USC, 'Auditorio 1101',
     {'sinopsis': 'Con Jhonny Hendrix (director).'}),
    ('2026-11-04', '18:30', 'El Titán', 'Película', 'Teatrino Proyecto Oriente', '',
     {'director': 'Alexander Giraldo', 'has_qa': True,
      '_nota': 'Presentación con Alex Giraldo (Director). Homenaje a Elkin Ramírez (post p/DfMs0KoJgLT).'}),
    ('2026-11-05', '12:00', 'Chocó', 'Película', USC, 'Auditorio T-Usaca', {'director': 'Jhonny Hendrix'}),
    ('2026-11-05', '18:00', 'Anina', 'Película', USC, 'Auditorio T-Usaca', {'director': 'Alfredo Soderguit'}),
    ('2026-11-06', '14:00', 'Conversatorio «El Metafilme Georgina»', 'Conversatorio', USC, 'Auditorio 1101',
     {'sinopsis': 'Con Sebastián Ospina (actor y director).'}),
    # HORA: la lámina general dice 5 pm; la pieza propia (p/DfBHkY-pbPy) «4:00 PM». Contradicción
    # sin respuesta aún (correo a ajmurgas, 2 nov): va la más temprana (regla de Juan)
    ('2026-11-06', '16:00', 'Conversatorio «Experiencias en la Dirección de 100 años de Soledad»', 'Conversatorio',
     'Casa Occio', '', {'sinopsis': 'Con Carlos Moreno (director).'}),
    ('2026-11-09', '12:00', 'Conversatorio «Del Barrio a la Embajada»', 'Conversatorio', USC, 'Auditorio T-Usaca',
     {'sinopsis': 'Con Héctor Aguirre (fotógrafo y realizador).'}),
    ('2026-11-09', '13:00', 'Proyección de cortos locales', 'Proyección de cortos locales', USC, 'Auditorio T-Usaca',
     {'sinopsis': 'Presentación del video «Barrio Brother», realizado entre Cali y Nueva York.'}),
]
NO_SE_PUBLICA = [{'dia': '2026-11-07', 'hora': '', 'actividad': 'Cine Bajo las Estrellas, película y encuentro musical (Centro Cultural Brisas de Mayo)',
                  'por_que': 'la lámina no da hora ni película (decisión de Juan, 2 nov)'}]
EVENTOS = {'Conversatorio', 'Proyección de cortos locales'}


def main():
    funciones = []
    for dia, hora, tit, sec, sede, sala, extra in FILAS:
        r = {'dia': dia, 'hora': hora, 'titulo': tit, 'sede': sede, 'sala': sala, 'ciudad': 'Cali',
             'seccion': sec, 'acceso': ACCESO, '_src': dict(SRC, fila=f'{dia} {hora} · {tit}')}
        if sec in EVENTOS:
            r.update(tipo='evento', event_kind='conversatorio' if sec == 'Conversatorio' else 'proyección')
        r.update(extra)
        funciones.append(r)
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance('Lámina «Programación 2026» de @semanadelcinecolombiano (IG p/DfKgpBVpyUt, 31 oct 2026)',
                                  metodo='transcripción a ojo cruzada con pipeline/ocr.py',
                                  que_aporta='la programación entera: día, hora, actividad, sede, sala'),
        '_acceso': {'estado': 'Entrada libre', 'revisado': '2026-11-02',
                    'fuentes': ['lámina de programación', 'post de El Titán (1 nov)', 'El País, 29 oct'],
                    '_por_que': 'Ninguna fuente anuncia boletería; El País: «eventos gratuitos». Regla de Juan: sin aviso de pago es gratis.'},
        '_no_se_publica': NO_SE_PUBLICA,
        'funciones': funciones}, ensure_ascii=False, indent=1) + '\n')
    print(f'✓ {len(funciones)} funciones → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
