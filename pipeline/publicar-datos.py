#!/usr/bin/env python3
"""publicar-datos.py — publica el JSON de UN festival aparte de la app (18 oct 2026).

Uso:
  python3 pipeline/publicar-datos.py <festival>            # p. ej. bhff-2026
  python3 pipeline/publicar-datos.py <festival> --probar   # valida y muestra; no sube nada
  (--desde-main: solo lo usa el job «Datos al almacén» de GitHub, tras un merge a main)

Qué hace, en orden (si un paso falla, no sigue). Los GUARDIANES son los mismos
que protegen hoy un PR de datos — publicar aparte no se salta ninguno (Juan, 18 oct):
  1. guardianes:
     a. scripts/validate-festivals.js <festival>   (forma del festival, segundos)
     b. validate.py completo                        (172 chequeos, ~40 s)
     c. si el festival tiene pipeline: el archivo tiene que ser EXACTAMENTE lo que
        genera pipeline/publicar.py desde su build (re-generado en una copia
        aparte). Una edición a mano frena: saltearía los guardianes del pipeline
        y se perdería en el próximo armado;
     d. tests de navegador de ESE festival (festivals.spec + recorrido): la app
        lo abre, se arma un plan y Mi Plan lo muestra;
  2. lo sube a la rama `datos` del repo SIN tocar el checkout (plumbing de git:
     blob → árbol → commit sobre la punta de `datos` → push). Si el archivo es
     igual al de la punta, no hay commit nuevo;
  3. llama a la edge function `publicar-datos` con {festival, sha}: la función
     solo acepta la PUNTA de `datos`, guarda la versión (inmutable) en el almacén
     `datos` de Supabase y apunta indice.json a ella;
  4. baja lo publicado por la URL pública y compara la huella byte a byte.

Volver atrás: `git revert` del commit en la rama `datos` (o publicar la versión
anterior del archivo) y correr esto de nuevo. Un solo camino, con historia.

El código de la app NO pasa por acá: sigue PR + CI + deploy. Ver migración 0009.
"""
import hashlib, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAMA = 'datos'
FUNCION = 'https://eytxrvbnwzxuedbmnnqr.supabase.co/functions/v1/publicar-datos'
PUBLICO = 'https://eytxrvbnwzxuedbmnnqr.supabase.co/storage/v1/object/public/datos/'
TIEMPO = 120   # tope por comando de red: nada se queda colgado


def git(*a, entrada=None):
    r = subprocess.run(['git', '-C', REPO, *a], input=entrada, capture_output=True, timeout=TIEMPO)
    if r.returncode != 0:
        sys.exit(f'✗ git {" ".join(a[:2])}: {r.stderr.decode(errors="replace").strip()[:300]}')
    return r.stdout.decode().strip()


def _correr(nombre, cmd, tiempo=TIEMPO, cwd=None):
    t = time.time()
    try:
        r = subprocess.run(cmd, cwd=cwd or REPO, capture_output=True, text=True, timeout=tiempo)
    except subprocess.TimeoutExpired:
        sys.exit(f'✗ {nombre}: pasó el tope de {tiempo} s — no se publica')
    if r.returncode != 0:
        print((r.stdout or '')[-2500:], (r.stderr or '')[-1500:])
        sys.exit(f'✗ {nombre} falló — no se publica')
    print(f'  ✓ {nombre} ({time.time() - t:.0f} s)')
    return r


def guardianes(fest, ruta, contenido):
    # a. forma del festival
    _correr('validate-festivals', ['node', 'scripts/validate-festivals.js', fest])
    # b. validate.py completo: imprime «PUSH BLOQUEADO» y sale distinto de 0
    r = _correr('validate.py', ['python3', 'validate.py'], tiempo=300)
    if 'BLOQUEADO' in r.stdout:
        print(r.stdout[-2500:]); sys.exit('✗ validate.py bloquea — no se publica')
    # c. con pipeline: el archivo == lo que genera publicar.py (en una copia aparte)
    if os.path.exists(os.path.join(REPO, 'pipeline', f'{fest}.plan.json')):
        tmp = tempfile.mkdtemp(prefix='publicar-datos-')
        copia = os.path.join(tmp, 'repo')
        try:
            git('worktree', 'add', '-q', '--detach', copia, 'HEAD')
            # lo que todavía no está commiteado del festival (build, plan, staging) viaja a la copia
            for rel in ['pipeline', 'festivals/staging', 'festivals']:
                o = os.path.join(REPO, rel)
                for n in os.listdir(o):
                    if n.startswith(fest) and os.path.isfile(os.path.join(o, n)):
                        shutil.copy2(os.path.join(o, n), os.path.join(copia, rel, n))
            # publicar.py puede negarse (build sin sello, pérdida de datos): eso
            # también es «el pipeline no reproduce», no un error de este comando.
            r = subprocess.run(['python3', 'pipeline/publicar.py', fest], cwd=copia,
                               capture_output=True, text=True, timeout=300)
            regen = open(os.path.join(copia, ruta), 'rb').read() if r.returncode == 0 else None
            en_main = subprocess.run(['git', '-C', REPO, 'show', f'origin/main:{ruta}'],
                                     capture_output=True, timeout=TIEMPO).stdout
            if regen == contenido:
                print('  ✓ igual a lo que genera el pipeline')
            elif regen is not None and regen == en_main:
                # el pipeline SÍ reproduce lo publicado y lo tuyo es distinto: edición a mano
                sys.exit(f'✗ {ruta} NO es lo que genera el pipeline (¿editado a mano?).\n'
                         f'  Corregilo aguas arriba y re-armá: python3 pipeline/correr.py {fest}')
            else:
                # el pipeline YA no reproducía lo publicado en main antes de este cambio
                # (13 festivales al 18 oct, hallazgo de Onboarding): se trata como legado.
                print(f'  ⚠ LEGADO: el pipeline de {fest} ya no reproduce lo publicado en main\n'
                      f'    ({"publicar.py se niega" if regen is None else "genera otra cosa"}). Se publica\n'
                      f'    lo tuyo con los demás guardianes; conviene re-armarlo aguas arriba.')
        finally:
            subprocess.run(['git', '-C', REPO, 'worktree', 'remove', '--force', copia], capture_output=True, timeout=TIEMPO)
            shutil.rmtree(tmp, ignore_errors=True)
    else:
        print('  · sin pipeline: no hay build contra el cual comparar')
    # d. la app con ESTE festival (id de la app: bhff-2026 → bhff2026)
    # id de la app: el archivo con guion antes de los dígitos finales (bhff-2026 →
    # bhff2026, ficci-65 → ficci65; festivalJsonUrl hace la inversa).
    cfg = re.sub(r'-(\d+)$', r'\1', fest)
    specs = ['tests/festivals.spec.js', 'tests/recorrido-festival.spec.js']
    # ¿Oculto? Se decide por la CONFIG (group:'test'), nunca por «la lista de tests
    # vino vacía»: si Playwright falla al listar (no instalado, red, carga) eso se
    # leía como «sin tests» y el guardián se salteaba en silencio — Ficcali y
    # Guatapé publicaron así el 18 oct (hallazgo de Onboarding). Falla CERRADO.
    cfg_src = open(os.path.join(REPO, 'src', 'config.js'), encoding='utf-8').read()
    m = re.search(r"\n  '" + re.escape(cfg) + r"':\s*\{(.*?)\n  \}", cfg_src, re.S)
    if not m:
        # Festival NUEVO, todavía sin config: la app no lo muestra. Sus tests corren
        # en el PR que suma su config (CI completo), con este mismo JSON.
        print(f'  ⚠ {cfg} todavía no está en la app (sin FESTIVAL_CONFIG): sus tests corren en el PR de su config')
        return
    if re.search(r"group:\s*'test'", re.sub(r'//[^\n]*', '', m.group(1))):
        print(f'  ⚠ {cfg} es un festival oculto (group:\'test\'): sin tests de navegador, se omiten')
        return
    _correr(f'tests de navegador de {cfg}',
            ['npx', 'playwright', 'test', *specs, '-g', cfg, '--workers=1', '--reporter=line'], tiempo=600)


def _commit_en_datos(ruta, contenido, mensaje):
    """Pone `contenido` en `ruta` sobre la punta de la rama `datos` (sin tocar el
    checkout) y la empuja. Devuelve el sha de la punta (el mismo si no cambió)."""
    git('fetch', '-q', 'origin', '+refs/heads/main:refs/remotes/origin/main')
    hay = subprocess.run(['git', '-C', REPO, 'ls-remote', '--exit-code', '--heads', 'origin', RAMA],
                         capture_output=True, timeout=TIEMPO).returncode == 0
    if hay:
        git('fetch', '-q', 'origin', f'+refs/heads/{RAMA}:refs/remotes/origin/{RAMA}')  # explícito: un clon que nunca bajó la rama no crea origin/datos
    base = git('rev-parse', f'origin/{RAMA}' if hay else 'origin/main')
    blob = git('hash-object', '-w', '--stdin', entrada=contenido)
    act = subprocess.run(['git', '-C', REPO, 'rev-parse', f'{base}:{ruta}'], capture_output=True, timeout=TIEMPO)
    if hay and act.returncode == 0 and act.stdout.decode().strip() == blob:
        print(f'· {ruta} ya es igual en la punta de {RAMA} ({base[:7]})')
        return base
    idx = os.path.join(tempfile.gettempdir(), f'publicar-datos-{os.getpid()}.idx')
    env = {**os.environ, 'GIT_INDEX_FILE': idx}
    try:
        for cmd in (['read-tree', base], ['update-index', '--add', '--cacheinfo', f'100644,{blob},{ruta}']):
            r = subprocess.run(['git', '-C', REPO, *cmd], env=env, capture_output=True, timeout=TIEMPO)
            if r.returncode != 0:
                sys.exit(f'✗ git {cmd[0]}: {r.stderr.decode()[:300]}')
        arbol = subprocess.run(['git', '-C', REPO, 'write-tree'], env=env, capture_output=True,
                               timeout=TIEMPO).stdout.decode().strip()
    finally:
        if os.path.exists(idx):
            os.remove(idx)
    sha = git('commit-tree', arbol, '-p', base, '-m', mensaje)
    git('push', '-q', 'origin', f'{sha}:refs/heads/{RAMA}')
    print(f'✓ rama {RAMA} → {sha[:7]}')
    return sha


def _llamar(cuerpo):
    req = urllib.request.Request(FUNCION, data=json.dumps(cuerpo).encode(),
                                 headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=TIEMPO) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f'✗ publicar-datos {e.code}: {e.read().decode()[:300]}')


def interruptor(apagado):
    sha = _commit_en_datos('datos-control.json', json.dumps({'apagado': apagado}).encode(),
                           f'datos: {"apagar" if apagado else "encender"} el almacén')
    res = _llamar({'festival': '_control', 'sha': sha})
    if not res.get('ok'):
        sys.exit(f'✗ {res}')
    print(f'✓ almacén {"APAGADO: la app lee la web" if res["apagado"] else "encendido"}')


def main():
    if '--apagar' in sys.argv or '--encender' in sys.argv:
        return interruptor('--apagar' in sys.argv)
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) != 1:
        sys.exit(__doc__)
    fest = args[0]
    ruta = f'festivals/{fest}.json'
    p = os.path.join(REPO, ruta)
    if not os.path.exists(p):
        sys.exit(f'✗ no existe {ruta}')
    contenido = open(p, 'rb').read()
    try:
        d = json.loads(contenido)
    except ValueError as e:
        sys.exit(f'✗ {ruta} no es JSON: {e}')
    if not d.get('films'):
        sys.exit(f'✗ {ruta} no tiene films: no se publica un festival vacío')

    # 1. GUARDIANES — los mismos de un PR de datos; si uno falla, no se publica.
    # --desde-main: solo el job «Datos al almacén» de GitHub, sobre lo que ya entró
    # a main con su CI requerido (los guardianes ya corrieron en el PR).
    if '--desde-main' in sys.argv:
        if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('GITHUB_REF') != 'refs/heads/main':
            sys.exit('✗ --desde-main es solo para el job de GitHub sobre main')
        print('  · desde main: los guardianes ya corrieron en el PR')
    else:
        guardianes(fest, ruta, contenido)
    huella = hashlib.sha256(contenido).hexdigest()
    print(f'✓ guardianes OK · {len(d["films"])} obras · {len(contenido):,} bytes · {huella[:12]}')
    if '--probar' in sys.argv:
        print('· --probar: no se sube nada'); return

    # 2. a la rama `datos`, sin tocar el checkout
    git('fetch', '-q', 'origin', '+refs/heads/main:refs/remotes/origin/main')
    hay_rama = subprocess.run(['git', '-C', REPO, 'ls-remote', '--exit-code', '--heads', 'origin', RAMA],
                              capture_output=True, timeout=TIEMPO).returncode == 0
    if hay_rama:
        git('fetch', '-q', 'origin', f'+refs/heads/{RAMA}:refs/remotes/origin/{RAMA}')  # explícito: un clon que nunca bajó la rama no crea origin/datos
    base = git('rev-parse', f'origin/{RAMA}' if hay_rama else 'origin/main')
    blob = git('hash-object', '-w', '--stdin', entrada=contenido)
    actual = subprocess.run(['git', '-C', REPO, 'rev-parse', f'{base}:{ruta}'], capture_output=True, timeout=TIEMPO)
    if hay_rama and actual.returncode == 0 and actual.stdout.decode().strip() == blob:
        sha = base
        print(f'· {ruta} ya es igual en la punta de {RAMA} ({sha[:7]})')
    else:
        # índice propio, fuera del repo: el checkout y su índice no se tocan
        idx = os.path.join(tempfile.gettempdir(), f'publicar-datos-{os.getpid()}.idx')
        env = {**os.environ, 'GIT_INDEX_FILE': idx}
        try:
            for cmd in (['read-tree', base], ['update-index', '--add', '--cacheinfo', f'100644,{blob},{ruta}']):
                r = subprocess.run(['git', '-C', REPO, *cmd], env=env, capture_output=True, timeout=TIEMPO)
                if r.returncode != 0:
                    sys.exit(f'✗ git {cmd[0]}: {r.stderr.decode()[:300]}')
            arbol = subprocess.run(['git', '-C', REPO, 'write-tree'], env=env, capture_output=True,
                                   timeout=TIEMPO).stdout.decode().strip()
        finally:
            if os.path.exists(idx):
                os.remove(idx)
        sha = git('commit-tree', arbol, '-p', base, '-m', f'datos({fest}): publicar {huella[:12]}')
        git('push', '-q', 'origin', f'{sha}:refs/heads/{RAMA}')
        print(f'✓ rama {RAMA} → {sha[:7]}')

    # 3. publicar
    req = urllib.request.Request(FUNCION, data=json.dumps({'festival': fest, 'sha': sha,
                                 'por': os.environ.get('OTF_POR') or git('config', 'user.name') or 'comando'}).encode(),
                                 headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=TIEMPO) as r:
            res = json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f'✗ publicar-datos {e.code}: {e.read().decode()[:300]}')
    if not res.get('ok'):
        sys.exit(f'✗ publicar-datos: {res}')

    # 4. verificar lo publicado byte a byte
    with urllib.request.urlopen(PUBLICO + res['archivo'], timeout=TIEMPO) as r:
        publicado = r.read()
    if hashlib.sha256(publicado).hexdigest() != huella:
        sys.exit('✗ lo publicado NO coincide con el archivo local')
    print(f'✓ publicado {fest} → {res["archivo"]}' + (' (sin cambios)' if res.get('igual') else ''))


if __name__ == '__main__':
    main()
