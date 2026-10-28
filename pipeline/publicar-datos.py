#!/usr/bin/env python3
"""publicar-datos.py — publica el JSON de UN festival aparte de la app (18 oct 2026).

Uso:
  python3 pipeline/publicar-datos.py <festival>            # p. ej. bhff-2026
  python3 pipeline/publicar-datos.py <festival> --probar   # valida y muestra; no sube nada
  (--desde-main: solo lo usa el job «Datos al almacén» de GitHub, tras un merge a main)

Qué hace, en orden (si un paso falla, no sigue). Los GUARDIANES son los mismos
que protegen hoy un PR de datos — publicar aparte no se salta ninguno (Juan, 18 oct):
  0. el catálogo de obras al día con los festivales (catalogo_construir.py --comprobar)
  1. guardianes (los tests de navegador leen el archivo LOCAL: en el servidor de
     pruebas la app no usa el almacén — datos-fuente.js, 19 oct 2026):
     a. scripts/validate-festivals.js <festival>   (forma del festival, segundos)
     b. validate.py completo                        (172 chequeos, ~40 s)
     c. si el festival tiene pipeline: el archivo tiene que ser EXACTAMENTE lo que
        genera pipeline/publicar.py desde su build (re-generado en una copia
        aparte). Una edición a mano frena: saltearía los guardianes del pipeline
        y se perdería en el próximo armado;
     d. tests de navegador de ESE festival (festivals.spec + recorrido): la app
        lo abre, se arma un plan y Mi Plan lo muestra;
     e. planificador, Mi Plan y avisos: lo mismo que el CI de un PR de datos;
  2. lo sube a la rama `datos` del repo SIN tocar el checkout (plumbing de git:
     blob → árbol → commit sobre la punta de `datos` → push). Si el archivo es
     igual al de la punta, no hay commit nuevo;
  3. llama a la edge function `publicar-datos` con {festival, sha}: la función
     solo acepta la PUNTA de `datos`, guarda la versión (inmutable) en el almacén
     `datos` de Supabase y apunta indice.json a ella;
  4. baja lo publicado por la URL pública y compara la huella byte a byte.

Etapa 2·B1 (19 oct 2026): en el mismo commit viaja la FICHA del festival
(fichas/<id>.json, extraída de FESTIVAL_CONFIG con scripts/ficha-de.mjs) y su
afiche de portada; la función los pone en el índice. Un afiche o una fecha nueva
llegan a la portada en minutos, sin publicar la app.

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
    # 0. con qué correr los tests de navegador: sin esto el guardián d fallaba con
    #    un MODULE_NOT_FOUND enterrado en el stack (worktree nuevo, 19 oct 2026).
    if not os.path.exists(os.path.join(REPO, 'node_modules', '@playwright', 'test')):
        sys.exit('✗ faltan los módulos de las pruebas (node_modules) en esta carpeta.\n'
                 '  Corré: npm ci   — y en un worktree nuevo también: sh scripts/install-hooks.sh')
    # 0·b. fuentes vivas: un festival VIGENTE no se publica armado con fuentes
    #      vencidas (FICCALI, 20 oct: verificaba contra la página del 6 oct)
    sys.path.insert(0, os.path.join(REPO, 'pipeline'))
    import fuentes_vivas
    _v = fuentes_vivas.frenar_si_vencidas(fest, f'python3 pipeline/correr.py {fest} --bajar')
    if _v:
        sys.exit(_v)
    # 0·c. el catálogo al día: es DERIVADO de todos los festivales. Si un cambio no
    #      lo re-arma, el próximo --escribir arrastra 30 archivos ajenos (FICCALI
    #      #1218/#1219, 21 oct 2026). Con la caché de TMDB no usa la red (~60 s)
    r = _correr('catálogo al día', ['python3', 'pipeline/catalogo_construir.py', '--comprobar'], tiempo=300)
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
            # El código del pipeline que NO está commiteado no viaja a la copia (arma
            # desde HEAD a propósito: se publica con código que quedó registrado).
            # Pero hay que decirlo: si no, una diferencia se lee como «editado a mano».
            sucio = subprocess.run(['git', '-C', REPO, 'status', '--porcelain', '--', 'pipeline/*.py', 'pipeline/**/*.py'],
                                   capture_output=True, text=True, timeout=TIEMPO).stdout.split('\n')
            sucio = [l[3:] for l in sucio if l.strip()]
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
            elif sucio:
                sys.exit(f'✗ el pipeline tiene código SIN COMMITEAR ({", ".join(sucio[:4])}): la copia arma\n'
                         f'  desde el último commit y no lo ve. Commiteá ese cambio y volvé a correr.')
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
                if regen is None:   # el porqué, que antes se tragaba
                    print('    publicar.py dijo: ' + ((r.stderr or r.stdout or '').strip().splitlines() or ['(nada)'])[-1][:200])
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
    # e. lo mismo que corre el CI para un PR de datos (playwright.yml, job «datos»):
    # planificador y Mi Plan, más los avisos, que desde el 19 oct viajan EN el dato.
    # Publicar aparte no puede probar MENOS que el PR que reemplaza (hallazgo del
    # 19 oct: estos tres no corrían acá). Cada uno usa festivales FIJOS y ninguno
    # recorre todos: un archivo que no nombra a este festival no carga su JSON y su
    # dato no lo puede romper. Se corren los que lo nombran (los tres: 566 s → ~0–3 min).
    extra = [sp for sp in ['tests/planner.spec.js', 'tests/miplan.spec.js', 'tests/avisos.spec.js']
             if re.search(r"['\"/]" + '(' + re.escape(cfg) + '|' + re.escape(fest) + r')[\'\"./]',
                          open(os.path.join(REPO, sp), encoding='utf-8').read())]
    if extra:
        _correr(f'planificador / Mi Plan / avisos con {cfg} ({len(extra)} archivo(s))',
                ['npx', 'playwright', 'test', *extra, '--workers=1', '--reporter=line'], tiempo=900)
    else:
        print(f'  · planificador / Mi Plan / avisos: ninguno carga {cfg}')


WEB = 'https://otrofestiv.app'


def _afiches_en_la_web(fest, d, esperar=0):
    """Todo /assets/… que nombra el JSON tiene que existir en el repo Y estar ya
    servido por la web (19 oct 2026, hallazgo de Onboarding): los afiches de obras
    siguen en GitHub Pages, así que publicar los datos ANTES de que el PR del
    afiche se despliegue dejaba obras sin afiche. Compara el tamaño con el local:
    el mismo nombre con otro contenido sería un afiche viejo en caché.
    `esperar`: segundos que se espera al deploy (el job de main corre mientras
    Pages publica el mismo merge)."""
    rutas = sorted({x for x in re.findall(r'"(/assets/[^"?#]+)"', json.dumps(d, ensure_ascii=False))})
    if not rutas:
        return
    faltan_repo = [x for x in rutas if not os.path.isfile(os.path.join(REPO, x.lstrip('/')))]
    if faltan_repo:
        sys.exit(f'✗ el JSON nombra {len(faltan_repo)} afiche(s) que no están en el repo: ' + ', '.join(faltan_repo[:5]))
    from concurrent.futures import ThreadPoolExecutor
    from urllib.parse import quote
    def _mal(x):
        try:
            req = urllib.request.Request(WEB + quote(x), method='HEAD')
            with urllib.request.urlopen(req, timeout=20) as res:
                n = int(res.headers.get('Content-Length') or -1)
            loc = os.path.getsize(os.path.join(REPO, x.lstrip('/')))
            return None if n in (-1, loc) else f'{x} (en la web pesa {n}, local {loc})'
        except urllib.error.HTTPError as e:
            return f'{x} ({e.code})'
        except Exception as e:
            return f'{x} ({type(e).__name__})'
    fin = time.time() + esperar
    while True:
        with ThreadPoolExecutor(16) as ex:
            malos = [m for m in ex.map(_mal, rutas) if m]
        if not malos or time.time() >= fin:
            break
        print(f'  · {len(malos)} afiche(s) todavía no están en la web; espero el deploy…'); time.sleep(30)
    if malos:
        sys.exit(f'✗ {len(malos)} de {len(rutas)} afiche(s) que nombra el JSON NO están en la web todavía:\n    '
                 + '\n    '.join(malos[:6]) + '\n  Mergeá el PR de los afiches, esperá que la web se publique y volvé a correr.')
    print(f'  ✓ afiches en la web ({len(rutas)})')


class Choque(Exception):
    """Otra publicación movió la punta de `datos` entre nuestro commit y la
    función (409) o durante el push. Se rehace el commit sobre la punta nueva."""


REINTENTOS = 4


def _publicar(archivos, mensaje, cuerpo):
    """Commit a `datos` + llamada a la función, rehecho sobre la punta nueva si
    otra corrida (el job de main o un publicar a mano) se cruzó. Cada intento
    vuelve a bajar la punta, así que nunca pisa lo que publicó la otra."""
    for intento in range(1, REINTENTOS + 1):
        try:
            sha = _commit_en_datos(archivos, mensaje)
            return sha, _llamar({**cuerpo, 'sha': sha})
        except Choque as e:
            if intento == REINTENTOS:
                sys.exit(f'✗ {e}: {REINTENTOS} intentos, todos cruzados con otra publicación')
            espera = 5 * intento
            print(f'· {e}; reintento {intento + 1}/{REINTENTOS} en {espera} s')
            time.sleep(espera)


def _commit_en_datos(archivos, mensaje):
    """Pone cada {ruta: bytes} sobre la punta de la rama `datos` (sin tocar el
    checkout) y la empuja. Devuelve el sha de la punta (el mismo si nada cambió)."""
    git('fetch', '-q', 'origin', '+refs/heads/main:refs/remotes/origin/main')
    hay = subprocess.run(['git', '-C', REPO, 'ls-remote', '--exit-code', '--heads', 'origin', RAMA],
                         capture_output=True, timeout=TIEMPO).returncode == 0
    if hay:
        git('fetch', '-q', 'origin', f'+refs/heads/{RAMA}:refs/remotes/origin/{RAMA}')  # explícito: un clon que nunca bajó la rama no crea origin/datos
    base = git('rev-parse', f'origin/{RAMA}' if hay else 'origin/main')
    blobs = {ruta: git('hash-object', '-w', '--stdin', entrada=c) for ruta, c in archivos.items()}
    def _igual(ruta, blob):
        act = subprocess.run(['git', '-C', REPO, 'rev-parse', f'{base}:{ruta}'], capture_output=True, timeout=TIEMPO)
        return act.returncode == 0 and act.stdout.decode().strip() == blob
    if hay and all(_igual(r, b) for r, b in blobs.items()):
        print(f'· {", ".join(blobs)} ya {"es igual" if len(blobs) == 1 else "son iguales"} en la punta de {RAMA} ({base[:7]})')
        return base
    # índice propio, fuera del repo: el checkout y su índice no se tocan
    idx = os.path.join(tempfile.gettempdir(), f'publicar-datos-{os.getpid()}.idx')
    env = {**os.environ, 'GIT_INDEX_FILE': idx}
    try:
        cmds = [['read-tree', base]] + [['update-index', '--add', '--cacheinfo', f'100644,{b},{r}'] for r, b in blobs.items()]
        for cmd in cmds:
            r = subprocess.run(['git', '-C', REPO, *cmd], env=env, capture_output=True, timeout=TIEMPO)
            if r.returncode != 0:
                sys.exit(f'✗ git {cmd[0]}: {r.stderr.decode()[:300]}')
        arbol = subprocess.run(['git', '-C', REPO, 'write-tree'], env=env, capture_output=True,
                               timeout=TIEMPO).stdout.decode().strip()
    finally:
        if os.path.exists(idx):
            os.remove(idx)
    sha = git('commit-tree', arbol, '-p', base, '-m', mensaje)
    r = subprocess.run(['git', '-C', REPO, 'push', '-q', 'origin', f'{sha}:refs/heads/{RAMA}'],
                       capture_output=True, timeout=TIEMPO)
    if r.returncode != 0:
        err = r.stderr.decode(errors='replace')
        if re.search(r'non-fast-forward|fetch first|rejected', err):
            raise Choque(f'la punta de {RAMA} se movió mientras empujaba')
        sys.exit(f'✗ git push: {err.strip()[:300]}')
    print(f'✓ rama {RAMA} → {sha[:7]}')
    return sha


def _ficha(fest):
    """La FICHA del festival (Etapa 2·B1): los campos de portada de FESTIVAL_CONFIG,
    extraídos con el MISMO módulo que usa la app (scripts/ficha-de.mjs). Devuelve
    {ruta: bytes} para sumar al commit: la ficha y, si el afiche de portada es del
    repo, la imagen (la función la sube al almacén con su huella en el nombre)."""
    cfg = re.sub(r'-(\d+)$', r'\1', fest)
    r = subprocess.run(['node', 'scripts/ficha-de.mjs', cfg], cwd=REPO, capture_output=True, text=True, timeout=TIEMPO)
    if r.returncode == 3:
        print(f'  · {cfg} no está en FESTIVAL_CONFIG: sin ficha'); return {}
    if r.returncode != 0:
        sys.exit(f'✗ no se pudo leer la ficha de {cfg}: {r.stderr.strip()[:300]}')
    ficha = json.loads(r.stdout)
    out = {f'fichas/{fest}.json': r.stdout.encode()}
    art = ficha.get('keyArt') or ''
    if art.startswith('/assets/keyart/'):
        ap = os.path.join(REPO, art.lstrip('/'))
        if not os.path.exists(ap):
            sys.exit(f'✗ el afiche de portada {art} no existe en el repo')
        out[art.lstrip('/')] = open(ap, 'rb').read()
    print(f'  · ficha: {ficha.get("name")} · {ficha.get("dates")} · afiche {os.path.basename(art) or "—"}')
    return out


def _tiene_ficha(fest):
    try:
        with urllib.request.urlopen(PUBLICO + 'indice.json?m=' + str(int(time.time() // 60)), timeout=TIEMPO) as r:
            return bool(((json.loads(r.read()).get('festivales') or {}).get(fest) or {}).get('ficha'))
    except Exception:
        return False


def _llamar(cuerpo):
    req = urllib.request.Request(FUNCION, data=json.dumps(cuerpo).encode(),
                                 headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=TIEMPO) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        cuerpo_err = e.read().decode(errors='replace')[:300]
        if e.code == 409:
            raise Choque(f'la función respondió 409 ({cuerpo_err})')
        sys.exit(f'✗ publicar-datos {e.code}: {cuerpo_err}')


def interruptor(apagado):
    sha, res = _publicar({'datos-control.json': json.dumps({'apagado': apagado}).encode()},
                         f'datos: {"apagar" if apagado else "encender"} el almacén', {'festival': '_control'})
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
    # e. los afiches que nombra el JSON ya están en la web (en los dos modos: desde
    #    main se espera hasta 10 min al deploy de Pages del mismo merge)
    _afiches_en_la_web(fest, d, esperar=600 if '--desde-main' in sys.argv else 0)
    huella = hashlib.sha256(contenido).hexdigest()
    print(f'✓ guardianes OK · {len(d["films"])} obras · {len(contenido):,} bytes · {huella[:12]}')
    if '--probar' in sys.argv:
        print('· --probar: no se sube nada'); return

    # 2. a la rama `datos`, sin tocar el checkout: el JSON y la ficha (B1)
    # Desde main (el job), la ficha solo viaja si ese festival YA tiene una en el
    # almacén: una ficha entra de a una y a propósito, con este comando a mano.
    ficha = _ficha(fest)
    if '--desde-main' in sys.argv and ficha and not _tiene_ficha(fest):
        print('  · sin ficha en el almacén: entra a propósito con publicar-datos.py, no desde main'); ficha = {}
    # 3. publicar (commit + función; si otra corrida se cruza, se rehace sobre la punta nueva)
    sha, res = _publicar({ruta: contenido, **ficha}, f'datos({fest}): publicar {huella[:12]}',
                         {'festival': fest, 'por': os.environ.get('OTF_POR') or git('config', 'user.name') or 'comando'})
    if not res.get('ok'):
        sys.exit(f'✗ publicar-datos: {res}')

    # 4. verificar lo publicado byte a byte
    with urllib.request.urlopen(PUBLICO + res['archivo'], timeout=TIEMPO) as r:
        publicado = r.read()
    if hashlib.sha256(publicado).hexdigest() != huella:
        sys.exit('✗ lo publicado NO coincide con el archivo local')
    print(f'✓ publicado {fest} → {res["archivo"]}' + (' (sin cambios)' if res.get('igual') else ''))
    # 5. la ficha: el afiche de portada que quedó en el almacén es el del repo
    f = res.get('ficha') or {}
    art = f.get('keyArt') or ''
    if art.startswith(PUBLICO + 'keyart/'):
        local = json.loads(_ficha_local := subprocess.run(['node', 'scripts/ficha-de.mjs', re.sub(r'-(\d+)$', r'\1', fest)],
                           cwd=REPO, capture_output=True, text=True, timeout=TIEMPO).stdout).get('keyArt', '')
        with urllib.request.urlopen(art, timeout=TIEMPO) as r:
            subido = r.read()
        if hashlib.sha256(subido).hexdigest() != hashlib.sha256(open(os.path.join(REPO, local.lstrip('/')), 'rb').read()).hexdigest():
            sys.exit('✗ el afiche de portada publicado NO coincide con el del repo')
        print(f'✓ ficha publicada · afiche → {art.rsplit("/", 1)[-1]}')
    elif f:
        print('✓ ficha publicada')


if __name__ == '__main__':
    main()
