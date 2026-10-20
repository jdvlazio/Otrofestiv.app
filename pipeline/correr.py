# -*- coding: utf-8 -*-
"""correr.py <fest-id> — el pipeline de un festival, en orden y a la vista.

El orden de los scripts de un festival vivía en la cabeza de quien lo montó:
extraer → enriquecer → geocodificar → ensamblar → publicar, con la fontanería
entre pasos invisible. Así se desincronizó FICDEH (el barrido escribía un
sidecar que el ensamblador no leía) sin que nadie lo notara durante días.

Este runner hace tres cosas y ninguna más:

  1. Corre los pasos DECLARADOS en pipeline/<fest-id>.plan.json, en orden,
     abortando al primer fallo. El plan es datos, no código: declara qué se
     corre; el cómo vive en cada script.
  2. Muestra el INVENTARIO de sidecars del festival antes y después, con la
     edad de cada `capturado`. Un sidecar viejo junto a uno recién escrito es
     exactamente la señal que faltó el 8 ago.

Formato del plan:
    { "pasos": [ { "cmd": "python3 pipeline/<id>-parse.py", "que": "…" } ] }

Uso:
    python3 pipeline/correr.py <fest-id>            # todo el plan
    python3 pipeline/correr.py <fest-id> --lista    # ver pasos e inventario
    python3 pipeline/correr.py <fest-id> --paso 3   # solo el paso 3
    python3 pipeline/correr.py <fest-id> --bajar    # baja las fuentes vivas y corre el plan

Fuentes vivas (20 oct 2026, pipeline/fuentes_vivas.py): si el plan declara
`fuentes_vivas` y el festival está vigente, una fuente sin bajar en 24 h FRENA
antes del primer paso. `--bajar` las refresca; `--fuentes-viejas` sigue igual,
dicho en voz alta.
"""
import datetime, glob, json, os, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def inventario(fid):
    hoy = datetime.date.today()
    filas = []
    for f in sorted(glob.glob(f'{REPO}/festivals/staging/{fid}*.json')):
        try:
            d = json.load(open(f, encoding='utf-8'))
            pr = d.get('_provenance') if isinstance(d, dict) else None
            cap = (pr or {}).get('capturado') or (pr or {}).get('recibido') or ''
        except Exception:
            cap = '¡JSON inválido!'
        edad = ''
        if cap and cap[:1].isdigit():
            dias = (hoy - datetime.date.fromisoformat(cap[:10])).days
            edad = f'hace {dias} día(s)' + ('  ⚠' if dias > 2 else '')
        filas.append(f'  {os.path.basename(f):52} {cap:12} {edad}')
    return filas


def main():
    if len(sys.argv) < 2:
        sys.exit('uso: python3 pipeline/correr.py <fest-id> [--lista | --paso N]')
    fid = sys.argv[1]
    plan_p = f'{REPO}/pipeline/{fid}.plan.json'
    if not os.path.exists(plan_p):
        sys.exit(f'no hay plan: {plan_p}\n(formato en el docstring de este script)')
    # El contrato del plan, ANTES del primer paso: lo que falte sale aquí,
    # junto y con remedio, no tras diez minutos de OCR y una vuelta entera.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import lib
    try:
        plan = lib.cargar_plan(fid)
    except AssertionError as e:
        sys.exit(f'✗ {e}')
    if plan['_clase'] == 'vacio':
        sys.exit(f'✗ {plan_p}: ni `pasos` ni `festival` — no hay pipeline declarado')
    pasos = plan['pasos']

    print(f'═══ {fid} · {len(pasos)} pasos · sidecars antes:')
    print('\n'.join(inventario(fid)) or '  (ninguno)')
    print()
    for i, p in enumerate(pasos, 1):
        print(f'  {i}. {p["cmd"]:52} {p.get("que", "")}')
    if '--lista' in sys.argv:
        return
    import fuentes_vivas
    if '--bajar' in sys.argv:
        print('\n─── fuentes vivas: bajando')
        try:
            fuentes_vivas.bajar(fid)
        except fuentes_vivas.FuenteMala as e:
            sys.exit(f'✗ {e}')
    _v = fuentes_vivas.frenar_si_vencidas(fid, f'python3 pipeline/correr.py {fid} --bajar')
    if _v and '--fuentes-viejas' not in sys.argv:
        sys.exit(_v + f'\n  (o --fuentes-viejas, a mano, si de verdad querés armar con lo que hay)')
    if _v:
        print('⚠ --fuentes-viejas: se arma con fuentes vencidas\n' + _v)

    solo = int(sys.argv[sys.argv.index('--paso') + 1]) if '--paso' in sys.argv else None
    for i, p in enumerate(pasos, 1):
        if solo and i != solo:
            continue
        print(f'\n─── paso {i}/{len(pasos)}: {p["cmd"]}')
        _b = f'{REPO}/festivals/staging/{fid}-build.json'
        _antes = os.path.getmtime(_b) if os.path.exists(_b) else 0
        r = subprocess.run(p['cmd'], shell=True, cwd=REPO)
        if r.returncode != 0:
            lib.marcar_fallo(fid, i, p['cmd'])
            sys.exit(f'\n✗ el paso {i} falló (exit {r.returncode}) — se aborta aquí; '
                     f'reanudar con --paso {i} tras corregir (el build queda marcado: publicar.py no lo acepta)')
        lib.limpiar_fallo(fid, i, cmd=p['cmd'])
        # si este paso reescribió el build, lleva el sello del runner y del plan
        if os.path.exists(_b) and os.path.getmtime(_b) > _antes:
            _c = lib.sellar_build(fid, i, p['cmd'])
            print(f'    sello: {_c["por"]} · plan {_c["plan_sha"]} · {_c["fecha"]}')

    print(f'\n═══ sidecars después:')
    print('\n'.join(inventario(fid)))
    print('\n→ ahora: python3 validate.py && node scripts/validate-festivals.js')


if __name__ == '__main__':
    main()
