#!/usr/bin/env python3
"""
translate-synopsis.py — Genera synopsis_es faltantes via Claude API
Fuente: synopsis (idioma de origen, ej. PT) con fallback a synopsis_en.
Destino: synopsis_es (español neutro latinoamericano).
Uso: python3 scripts/translate-synopsis.py festivals/olhar-2026.json
      python3 scripts/translate-synopsis.py festivals/aff-2026.json
Requiere: ANTHROPIC_API_KEY en entorno o argumento --key
"""
import json, sys, time, urllib.request, urllib.parse, argparse, os

ANTHROPIC_URL = 'https://api.anthropic.com/v1/messages'
MODEL         = 'claude-haiku-4-5-20251001'  # rápido y económico para traducción

SYSTEM = """You are a film synopsis translator specializing in Latin American and world cinema.
Translate the given film synopsis (source may be Portuguese or English) to natural, engaging neutral Latin American Spanish.
Rules:
- Preserve proper nouns, character names, and place names as-is
- Keep the same tone (dramatic, poetic, factual) as the original
- Do not add or remove information
- Output only the translated text, no preamble or explanation
- Keep it concise — same length as the original"""

def translate(source_text, api_key, festival_name=''):
    payload = {
        'model': MODEL,
        'max_tokens': 400,
        'system': SYSTEM,
        'messages': [{'role': 'user', 'content': f'Translate this film synopsis to Spanish:\n\n{source_text}'}]
    }
    req = urllib.request.Request(
        ANTHROPIC_URL,
        data=json.dumps(payload).encode(),
        headers={
            'Content-Type':       'application/json',
            'x-api-key':          api_key,
            'anthropic-version':  '2023-06-01',
        },
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    return data['content'][0]['text'].strip()

def run(fest_path, api_key, dry_run=False):
    data  = json.load(open(fest_path, encoding='utf-8'))
    films = data.get('films', [])

    # Fuente: synopsis (idioma de origen, ej. PT) con fallback a synopsis_en.
    # Destino: synopsis_es (campo nuevo). Solo films sin synopsis_es aún.
    to_translate = [
        f for f in films
        if (f.get('synopsis') or f.get('synopsis_en'))
        and not f.get('synopsis_es')
        and f.get('type') != 'event'
        and not f.get('is_cortos')
    ]

    print(f"Festival: {fest_path}")
    print(f"Films con fuente (synopsis/synopsis_en): {sum(1 for f in films if f.get('synopsis') or f.get('synopsis_en'))}")
    print(f"Sin synopsis_es:    {len(to_translate)}")
    print(f"Modo:               {'DRY RUN' if dry_run else 'LIVE'}\n")

    ok = 0; errors = []
    for f in to_translate:
        title = f.get('title', '?')
        try:
            if dry_run:
                print(f"  [DRY] {title[:50]}")
                continue
            source_text = f.get('synopsis') or f.get('synopsis_en')
            synopsis_es = translate(source_text, api_key)
            f['synopsis_es'] = synopsis_es
            ok += 1
            print(f"  ✓ {title[:45]:45} → {synopsis_es[:70]}…")
            time.sleep(0.3)
        except Exception as e:
            errors.append(title)
            print(f"  ✗ {title[:50]} — {e}")

    if not dry_run and ok > 0:
        with open(fest_path, 'w', encoding='utf-8') as out:
            json.dump(data, out, ensure_ascii=False, indent=2)
        print(f"\n✓ {ok} sinopsis traducidas | {len(errors)} errores")
        print(f"Guardado: {fest_path}")
    elif dry_run:
        print(f"\n[DRY RUN] Habría traducido {len(to_translate)} sinopsis")

    return ok

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('festival', help='Ruta al JSON del festival')
    parser.add_argument('--key',     help='Anthropic API key (o usa env ANTHROPIC_API_KEY)')
    parser.add_argument('--dry-run', action='store_true', help='Solo lista sin traducir')
    args = parser.parse_args()

    api_key = args.key or os.environ.get('ANTHROPIC_API_KEY')
    if not api_key and not args.dry_run:
        print("ERROR: Falta API key. Usa --key o ANTHROPIC_API_KEY env var"); sys.exit(1)

    run(args.festival, api_key, dry_run=args.dry_run)

# ─── FLUJO RECOMENDADO PARA FUTURAS CORRIDAS ────────────────────────
#
# 1. Ensamblar el JSON del festival con synopsis (origen) + synopsis_en si existe.
#
# 2. Claude API (genera synopsis_es desde synopsis/synopsis_en):
#    ANTHROPIC_API_KEY=sk-... python3 scripts/translate-synopsis.py festivals/olhar-2026.json
#    → Traduce a español neutro vía Claude Haiku (rápido y económico)
#
# 3. Manual (para casos especiales o corrección de calidad):
#    Editar directamente el JSON del festival
#
# NOTA ENGINE: para festivales no-español (synopsis_lang != 'es'), el display
#    en ES debe preferir synopsis_es. La de-binarización del engine
#    (_lang==='en' ? synopsis_en : synopsis  →  3 vías es/pt/en) es deuda
#    pendiente: hasta resolverla, synopsis_es no se muestra solo. No asumir
#    que el fallback actual cubre el caso PT→ES.
