#!/usr/bin/env python3
"""festicinerio-2026-catalogo.py — la Selección Oficial de FESTICINERIO V (Riosucio,
8–13 nov 2026), desde su carrusel de Instagram p/DfVZajiG5qG (4 nov, embed público).

Las láminas 01 a 11 son LISTAS de texto (sección, «título. Dir. …», país solo en
las internacionales); no traen afiches, horas ni salas. Dos lecturas: la tabla de
abajo, transcrita a ojo, y Vision (pipeline/ocr.py): toda palabra de 4+ letras de
título y dirección tiene que estar en SU lámina, y son 48 obras.
"""
import io
import json
import os
import re
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402
from ocr import leer  # noqa: E402

POST = 'DfVZajiG5qG'
IG = f'{REPO}/fuentes/ig/{POST}-x2'
DESTINO = f'{REPO}/festivals/staging/festicinerio-2026-catalogo.json'
PAIS = {'BRA': 'Brasil', 'ARG': 'Argentina', 'CR': 'Costa Rica', 'MEX': 'México', 'PER': 'Perú',
        'UK': 'Reino Unido', 'IND': 'India'}
# lámina, sección, [(título, dirección, país)]
LAMINAS = [
    ('01', 'Largometrajes', [
        ('Andariega', 'Raúl Soto R.', None),
        ('Simplicity of Chaos', 'Sebastián Montiel', None),
        ('Diòba', 'Adriana Marcela Rojas Espitia', None),
        ('Paristopia', 'Emanuel Rojas G.', None),
        ('En Bajo de 4 Puntas', 'Cristian Camilo Camargo C.', None)]),
    ('02', 'Ficción', [
        ('Post-Familia', 'Alexis Tafur', None),
        ('Independencia', 'Jhon Agudelo', None),
        ('HDLT', 'Artefactum Suba', None),
        ('No te Despiertes', 'Hernán Velasquez Vila', None),
        ('Baño de Damas', 'Natalya Carrillo', None),
        ('El Ocaso de los Dioses', 'Juan Pablo Rendón', None),
        ('Carlina', 'Ángela María Leyton', None)]),
    ('03', 'Documental', [
        ('Tentado de Difunto', 'Juan David Correa', None),
        ('Apotnojushi La Casa del viento', 'Marbel Ina Vanegas Jusayu', None),
        ('El Amor en los Tiempos de Cumbia', 'Violeta Barrios', None),
        ('Ornamento', 'Esteban López, Lucy Ortega', None)]),
    ('04', 'Experimental', [
        ('Chaika', 'Ingrid Bonilla', None),
        ('Sirena Mecánica', 'Violeta Vieytes Vivares, Damián Sato', None),
        ('Anoche a la Media Noche', 'Ricardo Muñoz Izquierdo', None),
        ('Todo lo que Pasará Mañana', 'Santiago Calle García', None),
        ('Necedades', 'Andrés Alvarez', None),
        ('Despojo', 'Daniel Rodriguez', None)]),
    ('05', 'Selección Riosucio', [
        ('La Barbacoa', 'Luis Román', None),
        ('Red de meliponicultura de Caldas: diversidad y conservación de las meliponinas', 'Sergio Gaviria', None)]),
    ('06', 'Historias de Carnaval Internacional', [
        ('Cathi e os Elefantes', 'Morena Dornelas, Caio Dornelas', 'BRA'),
        ('Debajo de esas Galeras', 'Rosario Morales Scheller', 'ARG'),
        ('Quarta-Feira', 'Barbara Santos, Joao Pedro Pardo', 'BRA'),
        ('La Dama de las Mil Máscaras', 'Wainer Méndez', 'CR')]),
    ('07', 'Panorama Regional', [
        ('Comadres', 'Ingryd Ríos T.', None),
        ('La Gallina Saraviada', 'Ingrid Bonilla', None),
        ('Que el Cielo Nos Perdone', 'Andrés Buitrago', None)]),
    ('08', 'Ficción Internacional', [
        ('Enquanto Meu Coração Bate Impetuoso', 'Luiz Villasboas Maudonnet, Iuri Salles', 'BRA'),
        ('Soñe Que Tocaba la Batería', 'Alexei Gudiño', 'MEX'),
        ('Perros Guardianes', 'Miguel Ángel Condor', 'PER')]),
    ('09', 'Animación', [
        ('Pipona', 'María Elizabeth López', None),
        ('Baile del Caos', 'Valeria Preciado', None),
        ('El Espejo de la Vida', 'Simón Sanchez Plazas', None),
        ('Boato', 'Alexandra Michel Julio', None),
        ('Romu', 'Andrés Julián Yepes', None),
        ('Big Bang Lio', 'Sarah Luna Valero', None),
        ('Suelo', 'Eduar Yosniel Pájaro', None)]),
    ('10', 'Videoclip', [
        ('Fliehende Stürme: Puppen', 'Sandra Rengifo', None),
        ('Mucho Gusto', 'Cintia Obando', None),
        ('Árbol en Pie', 'Red Comunitaria Trans, Mapa López, Rodrigo Torrijos', None),
        ('Tower of Silence by Headless Buddha', 'Isabel Echeverri', None)]),
    ('11', 'Animación Internacional', [
        ('Nibbling of the Night', 'Gabi Bania', 'UK'),
        ('The Magical Colors', 'Victor Vinicius', 'BRA'),
        ('The Mango Tree', 'Hema Seth, Alok Seth', 'IND')]),
]


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn')


def main():
    rutas = {n: f'{IG}/{n}.jpg' for n, _, _ in LAMINAS}
    lec = leer(list(rutas.values()))
    obras, fallos = [], []
    for n, seccion, lista in LAMINAS:
        txt = plano(' '.join(lec.get(rutas[n], [])))
        for titulo, director, pais in lista:
            for p in re.findall(r'\w{4,}', plano(f'{titulo} {director}')):
                if p not in txt:
                    fallos.append(f'{titulo}: «{p}» no se lee en la lámina {n}')
            o = {'titulo': titulo, 'director': director, 'categoria': seccion,
                 '_src': {'url': f'https://www.instagram.com/p/{POST}/', 'post': POST, 'lamina': f'{n}.jpg',
                          'date': '2026-11-04'}}
            if pais:
                o['pais'] = PAIS[pais]
            obras.append(o)
    if fallos:
        sys.exit('✗ la OCR no confirma:\n  ' + '\n  '.join(fallos))
    if len(obras) != 48:
        sys.exit(f'✗ {len(obras)} obras, se esperaban 48')
    with io.open(DESTINO, 'w', encoding='utf-8') as f:
        json.dump({'_provenance': provenance(
            fuente='IG @festicinerio, carrusel de la Selección Oficial (4 nov 2026)',
            url=f'https://www.instagram.com/p/{POST}/',
            metodo='lectura a ojo de las 11 láminas, confirmada por Vision'), 'obras': obras},
            f, ensure_ascii=False, indent=1)
    print(f'✓ {len(obras)} obras → {DESTINO}')


if __name__ == '__main__':
    main()
