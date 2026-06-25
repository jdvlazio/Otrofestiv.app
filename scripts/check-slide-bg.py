#!/usr/bin/env python3
"""check-slide-bg.py — guard de color de fondo de los slides de marketing.

Contexto: la serie de slides IG/X de Otrofestiv usa fondo CANÓNICO #0A0A0A
(negro casi puro). En jun 2026 un generador armado "desde la sesión" usó por
error #141414 (gris carbón, +claro) en los posts 10–27; saltaba a la vista en
el grid de IG al lado de los 1–9. Las tintas (blanco #F0EDE8, ámbar #F59E0B) sí
coincidían — el único defecto era el fondo. Este guard mide el color dominante
(el fondo ocupa ~80% del slide) y falla si NO es #0A0A0A.

Uso:
    python3 scripts/check-slide-bg.py <dir-o-archivo> [<dir-o-archivo> ...]
    python3 scripts/check-slide-bg.py m/                 # las copias hosteadas del repo
    python3 scripts/check-slide-bg.py "~/.../09_Marketing/Post_19"  # un master antes de programar

Correr SIEMPRE sobre un post (master o /m/) ANTES de programarlo en Buffer.
Exit 0 = todos OK · Exit 1 = al menos uno con fondo distinto (o error de lectura).
Requiere Pillow (PIL). Ver memoria [[marketing-slide-template]].
"""
import sys
import glob
import os

CANON = (10, 10, 10)  # #0A0A0A
CANON_HEX = "#0A0A0A"


def dominant(path):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    cols = im.getcolors(maxcolors=im.size[0] * im.size[1])
    cols.sort(reverse=True)
    return cols[0][1]  # (r,g,b) más frecuente = fondo


def iter_pngs(arg):
    p = os.path.expanduser(arg)
    if os.path.isdir(p):
        yield from sorted(glob.glob(os.path.join(p, "**", "*slide-*.png"), recursive=True))
    elif p.lower().endswith(".png"):
        yield p


def main(argv):
    args = argv[1:]
    if not args:
        print(__doc__)
        return 2
    targets = [f for a in args for f in iter_pngs(a)]
    if not targets:
        print(f"[check-slide-bg] sin slides PNG en: {', '.join(args)} (nada que validar)")
        return 0
    bad = []
    for f in targets:
        try:
            r, g, b = dominant(f)
        except Exception as e:  # noqa: BLE001
            print(f"[check-slide-bg] ERROR leyendo {f}: {e}")
            bad.append(f)
            continue
        if (r, g, b) != CANON:
            bad.append(f)
            print(f"[check-slide-bg] MAL  #{r:02X}{g:02X}{b:02X}  {f}")
    n = len(targets)
    if bad:
        print(f"\n[check-slide-bg] {len(bad)}/{n} slides con fondo != {CANON_HEX}. "
              f"Recolorear antes de programar.")
        return 1
    print(f"[check-slide-bg] OK — {n}/{n} slides con fondo {CANON_HEX}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
