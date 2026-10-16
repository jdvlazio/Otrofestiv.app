"""Bisturí de UNA pasada: aplica funcion.marcar_paga_supuesta (la misma regla
que ensamblar) sobre el JSON PUBLICADO de un festival mixed que no se puede
re-armar sin arrastrar otros cambios (Narrar el Futuro: géneros que derivaron;
Itagüí: obras sin afiche revisado que frenan publicar). Solo escribe
`is_free: false`; la marca `_procedencia` no se publica (publicar la quita), y
la próxima corrida de ensamblar la pone igual. Idempotente.

  python3 pipeline/entrada-paga-supuesta.py <fid>
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import funcion

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    fid = sys.argv[1]
    p = os.path.join(REPO, 'festivals', f'{fid}.json')
    d = json.load(open(p, encoding='utf-8'))
    fs = d.get('films') or []
    n = funcion.marcar_paga_supuesta(fs, funcion.ticketing_model_de(fid))
    for f in fs:
        f.pop('_procedencia', None)
    if n:   # mismo formato que publicar.py
        json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f'{fid}: {n} función(es) paga(s) por supuesto')
