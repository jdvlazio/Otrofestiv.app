#!/usr/bin/env python3
"""compose-keyart.py — lleva el afiche de un festival al 2:3 que pide el splash.

LA REGLA (Juan, 6 ago 2026 — permanente)
    Se ESTIRA en un eje hasta 400×600. No se recorta, no se rellena con bandas,
    no se difumina.

POR QUÉ
La card del riel del splash es 2:3 exacto con `object-fit:cover`, así que
recorta todo afiche que no lo sea — y los afiches de festival casi nunca son 2:3
(suelen ser 3:4 o serie A). Medido en ago 2026: 7 de 10 keyArt se recortaban,
hasta +19,5% (Tercer Tiempo perdía casi un quinto del afiche).

Se evaluaron tres caminos con afiches reales, comparados a tamaño de card:
  · banda de color plano en los márgenes → deja una línea dura visible;
  · blur del propio afiche detrás (como `.ed-blur` de las fichas) → mejor, pero
    sigue siendo un marco alrededor de un afiche que quedó chico;
  · ESTIRAR en un eje → el afiche llena la card, se lee entero, y la deformación
    no se percibe. Aprobado: "estirar no se nota, se lee todo".

La compresión real de los casos existentes fue 5,7% / 5,9% / 7,4% / 16,3%. Aun
en el peor (Tercer Tiempo, el afiche más ancho) Juan lo dio por bueno a tamaño
de card. No hay umbral: se estira siempre, sin excepciones — una regla simple
que cualquier onboarding futuro aplica sin decidir nada.

WRITE-ONCE (regla de src/config.js)
El Service Worker cachea /assets/ cache-first para siempre. Sobreescribir un
keyArt in-place deja a los usuarios recurrentes viendo el afiche viejo
indefinidamente. Por eso este script escribe SIEMPRE a un nombre nuevo (sufijo
-v2, -v3…) y te dice qué línea cambiar en src/config.js.

USO
    python3 scripts/compose-keyart.py assets/keyart/<fest>.jpg
    python3 scripts/compose-keyart.py --all          # todos los que lo necesitan
    python3 scripts/compose-keyart.py --check        # solo diagnóstico, no escribe
"""
import argparse
import glob
import os
import re
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Falta Pillow:  pip3 install Pillow")

W, H = 400, 600           # lienzo 2:3 canónico del riel
TOL = 0.005               # 0,5% — por debajo de esto el recorte ya es invisible
KEYART_DIR = "assets/keyart"


def desvio(path):
    """(ancho, alto, desvío relativo de ancho sobre 2:3). Positivo = más ancho."""
    with Image.open(path) as im:
        w, h = im.size
    ideal = h * 2 / 3
    return w, h, (w - ideal) / ideal


def siguiente_version(path):
    """assets/keyart/x.jpg → x-v2.jpg ; x-v2.jpg → x-v3.jpg (write-once)."""
    base, ext = os.path.splitext(path)
    m = re.search(r"-v(\d+)$", base)
    if m:
        return f"{base[:m.start()]}-v{int(m.group(1)) + 1}{ext}"
    return f"{base}-v2{ext}"


def componer(path, dry=False):
    w, h, ex = desvio(path)
    nombre = os.path.basename(path)
    if abs(ex) <= TOL:
        print(f"  ✓ {nombre:26} {w}×{h}  ya es 2:3 ({ex:+.1%})")
        return None

    # Cuánto se comprime/estira cada eje al llevarlo a 2:3 — informativo, no decide.
    comp = (w - h * 2 / 3) / w * 100 if ex > 0 else (h - w * 3 / 2) / h * 100
    eje = "ancho" if ex > 0 else "alto"
    destino = siguiente_version(path)
    print(f"  → {nombre:26} {w}×{h}  {ex:+.1%} → estira a {W}×{H} "
          f"(el {eje} se comprime {comp:.1f}%)  →  {os.path.basename(destino)}")
    if dry:
        return destino

    with Image.open(path) as im:
        # LA REGLA: resize directo a 400×600. Los ejes se escalan independientes
        # (equivale a object-fit:fill). Nada de crop, bandas ni blur.
        im.convert("RGB").resize((W, H), Image.LANCZOS).save(
            destino, "JPEG", quality=92, optimize=True)

    print(f"     escrito · actualizá src/config.js:  keyArt:'/{destino}'")
    return destino


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("archivos", nargs="*", help="keyArt a llevar a 2:3")
    ap.add_argument("--all", action="store_true", help="todos los de assets/keyart/")
    ap.add_argument("--check", action="store_true", help="solo diagnóstico")
    args = ap.parse_args()

    objetivos = args.archivos or (
        sorted(glob.glob(f"{KEYART_DIR}/*.jpg")) if (args.all or args.check) else [])
    if not objetivos:
        ap.print_help()
        return 1

    print(f"Objetivo: {W}×{H} (2:3) por estirado en un eje · tolerancia {TOL:.1%}\n")
    hechos = [componer(p, dry=args.check) for p in objetivos]
    n = len([x for x in hechos if x])
    print(f"\n{n} necesita(n) estirado." if args.check else f"\n{n} estirado(s).")
    if n and not args.check:
        print("RECORDÁ: keyArt es write-once — el path viejo queda en el caché de los\n"
              "usuarios recurrentes hasta que config apunte al nuevo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
