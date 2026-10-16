"""La cola de propuestas — docs/FUNCION.md §5.

Lo que traen las fuentes secundarias (el vigía, la agenda de las salas,
ig-programa) NO se escribe en <fid>-afirmaciones.json: entra como PROPUESTA en
festivals/staging/<fid>-propuestas.json. Juan acepta o rechaza; lo aceptado
pasa a ser afirmación (con su fuente original, que es la que da el rango), lo
rechazado queda anotado.

Como Google Maps con «Sugerir una edición», a escala de una persona: la
máquina valida y descarta lo repetido; el que aprueba es Juan.

Reglas (auditoría del 16 oct):
- Una propuesta es un DATO DE UNA FUENTE: su id incluye la fuente y su fecha.
  La misma fuente con la misma fecha no se repite; una fuente MÁS NUEVA con el
  mismo valor sí entra (puede cambiar quién gana), y si ese valor se rechazó
  antes lo dice, con la frase de Juan.
- Nadie propone en nombre de Juan (tipo `juan` no entra por la cola).
- Solo un festival del modelo (con -afirmaciones.json) tiene cola.
- Al aceptar, el ARMADO REAL decide: se corre `ensamblar.py <fid> --ver` antes
  y después; si aparece un fallo que antes no estaba, se deshace todo. No se
  reimplementa la regla del modelo (memoria «verificador: mismo camino»).
- Escrituras atómicas (temporal + os.replace); primero la cola y después las
  afirmaciones, para que un corte deje un estado que el guardián ve.

  python3 pipeline/propuestas.py                                  # pendientes
  python3 pipeline/propuestas.py proponer <fid> <a.json> --por <quién>
  python3 pipeline/propuestas.py aceptar  <fid> <id…|todas> --frase "…"
  python3 pipeline/propuestas.py rechazar <fid> <id…|todas> --frase "…"
"""
import argparse, glob, hashlib, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import funcion

REPO = funcion.REPO
ESTADOS = ('pendiente', 'aceptada', 'rechazada')
ACCIONES = {'aceptar': 'aceptada', 'rechazar': 'rechazada'}


class ArmadoRoto(RuntimeError):
    """El armado real del festival no acepta lo aceptado (se deshizo)."""


def _p(fid, k, raiz):
    return os.path.join(raiz, 'festivals', 'staging', f'{fid}-{k}.json')


def _que(a):
    """Qué dice (no quién): dónde, qué casilla, qué valor."""
    an = a.get('ancla') or {}
    donde = a.get('funcion') or [an.get('sede'), an.get('dia'), an.get('hora')]
    return json.dumps([donde, a.get('casilla'), a.get('valor')], ensure_ascii=False, sort_keys=True)


def _firma(a):
    """Qué dice + QUIÉN y CUÁNDO: una propuesta es el dato de una fuente."""
    fu = a.get('fuente') or {}
    return json.dumps([_que(a), fu.get('tipo'), funcion._orden(fu) if fu.get('fecha') else None,
                       fu.get('url') or fu.get('frase')], ensure_ascii=False)


def id_de(a):
    return 'p' + hashlib.sha1(_firma(a).encode('utf-8')).hexdigest()[:8]


def leer(fid, raiz=REPO):
    p = _p(fid, 'propuestas', raiz)
    if not os.path.exists(p):
        return {'_provenance': {'metodo': 'cola de propuestas (docs/FUNCION.md §5)'}, 'propuestas': []}
    with open(p, encoding='utf-8') as fh:
        return json.load(fh)


def _guardar(p, d):
    tmp = p + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(d, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def _afirmaciones(fid, raiz):
    p = _p(fid, 'afirmaciones', raiz)
    if not os.path.exists(p):
        return None
    with open(p, encoding='utf-8') as fh:
        return json.load(fh)


def _en_modelo(fid, raiz):
    if _afirmaciones(fid, raiz) is None:
        raise funcion.AfirmacionInvalida(f'{fid} no está en el modelo de la función (sin -afirmaciones.json): '
                                         'migrarlo primero; la cola no lo crea')


def proponer(fid, afirmacion, por, raiz=REPO, fecha_hoy=None):
    """→ (estado, id). estado: 'nueva' | 'ya-pendiente' | 'ya-aceptada' |
    'ya-rechazada' | 'ya-afirmada'. Lo inválido lanza y no entra."""
    _en_modelo(fid, raiz)
    if (afirmacion.get('fuente') or {}).get('tipo') == 'juan':
        raise funcion.AfirmacionInvalida(f'{fid}: una decisión de Juan no entra por la cola (la toma él, en el chat)')
    funcion.validar(afirmacion, fecha_hoy)
    pid, firma = id_de(afirmacion), _firma(afirmacion)
    if any(_firma(a) == firma for a in _afirmaciones(fid, raiz).get('afirmaciones') or []):
        return 'ya-afirmada', pid
    d = leer(fid, raiz)
    for x in d['propuestas']:
        if x['id'] == pid:
            return 'ya-' + x['estado'], pid
    nueva = {'id': pid, 'estado': 'pendiente', 'por': por, 'fecha': fecha_hoy or funcion.hoy(),
             'afirmacion': afirmacion}
    antes = [x for x in d['propuestas'] if x['estado'] == 'rechazada' and _que(x['afirmacion']) == _que(afirmacion)]
    if antes:   # el mismo valor ya se rechazó, de otra fuente o fecha: Juan lo ve
        nueva['rechazada_antes'] = [{'id': x['id'], 'frase': x['decision']['frase']} for x in antes]
    d['propuestas'].append(nueva)
    _guardar(_p(fid, 'propuestas', raiz), d)
    return 'nueva', pid


def _armar(fid):
    """El armado real, sin escribir nada: (ok, salida)."""
    r = subprocess.run([sys.executable, os.path.join(REPO, 'pipeline', 'ensamblar.py'), fid, '--ver'],
                       capture_output=True, text=True, cwd=REPO)
    return r.returncode == 0, (r.stdout + r.stderr)[-1500:]


def decidir(fid, ids, accion, frase, raiz=REPO, fecha_hoy=None, armar=None):
    """Acepta o rechaza, TODO O NADA. ids = lista o 'todas' (las pendientes).
    `armar(fid) → (ok, salida)` es el armado real (inyectable en tests)."""
    if accion not in ACCIONES:
        raise ValueError(f'acción desconocida «{accion}» (aceptar | rechazar)')
    if not (frase or '').strip():
        raise ValueError('una decisión lleva la frase de Juan')
    d = leer(fid, raiz)
    por_id = {x['id']: x for x in d['propuestas']}
    if ids == 'todas':
        ids = [x['id'] for x in d['propuestas'] if x['estado'] == 'pendiente']
    elif not ids:
        raise ValueError('sin ids: ¿cuáles? (o «todas»)')
    faltan = [i for i in ids if i not in por_id]
    if faltan:
        raise KeyError(f'{fid}: propuesta(s) desconocida(s): {", ".join(faltan)}')
    ya = [i for i in ids if por_id[i]['estado'] != 'pendiente']
    if ya:
        raise ValueError(f'{fid}: ya decidida(s): {", ".join(ya)}')
    if not ids:
        return 0
    p_pr, p_af = _p(fid, 'propuestas', raiz), _p(fid, 'afirmaciones', raiz)
    d_af = None
    if accion == 'aceptar':
        _en_modelo(fid, raiz)
        for i in ids:
            funcion.validar(por_id[i]['afirmacion'], fecha_hoy)
        armar = armar or _armar
        ok_antes, sal = armar(fid)
        if not ok_antes:
            raise ArmadoRoto(f'{fid}: el armado ya falla ANTES de aceptar; arreglar eso primero:\n{sal}')
        d_af = _afirmaciones(fid, raiz)
        original_af, original_pr = json.loads(json.dumps(d_af)), json.loads(json.dumps(d))
        d_af['afirmaciones'] = (d_af.get('afirmaciones') or []) + [
            {**por_id[i]['afirmacion'], 'propuesta': i} for i in ids]
    dec = {'fecha': fecha_hoy or funcion.hoy(), 'frase': frase.strip()}
    for i in ids:
        por_id[i]['estado'], por_id[i]['decision'] = ACCIONES[accion], dec
    _guardar(p_pr, d)                      # primero la cola: un corte acá lo ve el guardián
    if d_af is not None:
        _guardar(p_af, d_af)
        ok, sal = armar(fid)
        if not ok:
            _guardar(p_af, original_af)
            _guardar(p_pr, original_pr)
            raise ArmadoRoto(f'{fid}: con lo aceptado el armado frena (conflicto u otra cosa); se deshizo. '
                             f'Salida de ensamblar --ver:\n{sal}')
    return len(ids)


def pendientes(raiz=REPO):
    out = {}
    for p in sorted(glob.glob(os.path.join(raiz, 'festivals', 'staging', '*-propuestas.json'))):
        fid = os.path.basename(p)[:-len('-propuestas.json')]
        xs = [x for x in leer(fid, raiz)['propuestas'] if x.get('estado') == 'pendiente']
        if xs:
            out[fid] = xs
    return out


def verificar(raiz=REPO):
    """Problemas de la cola (guardián [propuestas-validas])."""
    mal = []
    fids = {os.path.basename(p)[:-len('-propuestas.json')]
            for p in glob.glob(os.path.join(raiz, 'festivals', 'staging', '*-propuestas.json'))}
    fids |= {os.path.basename(p)[:-len('-afirmaciones.json')]
             for p in glob.glob(os.path.join(raiz, 'festivals', 'staging', '*-afirmaciones.json'))}
    for fid in sorted(fids):
        try:
            xs = leer(fid, raiz)['propuestas']
        except Exception as e:
            mal.append(f'{fid}: la cola no se puede leer ({e})')
            continue
        d_af = _afirmaciones(fid, raiz)
        if xs and d_af is None:
            mal.append(f'{fid}: tiene cola pero no está en el modelo (nada se podría aceptar)')
        afs = (d_af or {}).get('afirmaciones') or []
        firmas = {_firma(a) for a in afs}
        estado = {x.get('id'): x.get('estado') for x in xs}
        for a in afs:
            if a.get('propuesta') and estado.get(a['propuesta']) != 'aceptada':
                mal.append(f'{fid} {a["propuesta"]}: es afirmación pero la cola no la tiene aceptada')
        vistos = set()
        for x in xs:
            q = f'{fid} {x.get("id")}'
            if x.get('id') in vistos:
                mal.append(f'{q}: id repetido')
            vistos.add(x.get('id'))
            if x.get('estado') not in ESTADOS:
                mal.append(f'{q}: estado «{x.get("estado")}» desconocido')
                continue
            a = x.get('afirmacion') or {}
            if x.get('id') != id_de(a):
                mal.append(f'{q}: el id no corresponde a la afirmación (¿la editaron a mano?)')
            if x['estado'] == 'pendiente':
                try:
                    funcion.validar(a)
                except funcion.AfirmacionInvalida as e:
                    mal.append(f'{q}: pendiente inválida ({e})')
            elif not ((x.get('decision') or {}).get('frase') and (x.get('decision') or {}).get('fecha')):
                mal.append(f'{q}: decidida sin frase o sin fecha')
            if x['estado'] == 'aceptada' and _firma(a) not in firmas:
                mal.append(f'{q}: aceptada pero no está en {fid}-afirmaciones.json')
            if x['estado'] == 'rechazada' and _firma(a) in firmas:
                mal.append(f'{q}: rechazada pero está en {fid}-afirmaciones.json')
    return mal


def _texto(a):
    an = a.get('ancla') or {}
    donde = a.get('funcion') or f"{an.get('sede')} {an.get('dia')} {an.get('hora')}"
    fu = a['fuente']
    return f"{donde} · {a.get('casilla')} → {a.get('valor')!r}  [{fu['tipo']} {funcion._orden(fu)}]"


def main(argv=None):
    ap = argparse.ArgumentParser(description='cola de propuestas (docs/FUNCION.md §5)')
    sub = ap.add_subparsers(dest='cmd')
    pp = sub.add_parser('proponer')
    pp.add_argument('fid')
    pp.add_argument('archivo')
    pp.add_argument('--por', required=True)
    for c in ACCIONES:
        pc = sub.add_parser(c)
        pc.add_argument('fid')
        pc.add_argument('ids', nargs='+')
        pc.add_argument('--frase', required=True)
    a = ap.parse_args(argv)
    if a.cmd is None:
        pend = pendientes()
        if not pend:
            print('✓ sin propuestas pendientes')
        for fid, xs in pend.items():
            print(f'{fid} — {len(xs)} pendiente(s)')
            for x in xs:
                print(f"  {x['id']}  {_texto(x['afirmacion'])}  (por {x['por']}, {x['fecha']})")
                for r in x.get('rechazada_antes') or []:
                    print(f"      ⚠ este valor ya se rechazó ({r['id']}): «{r['frase']}»")
    elif a.cmd == 'proponer':
        with open(a.archivo, encoding='utf-8') as fh:
            print(*proponer(a.fid, json.load(fh), a.por))
    else:
        if 'todas' in a.ids and len(a.ids) > 1:
            ap.error('«todas» va sola')
        n = decidir(a.fid, 'todas' if a.ids == ['todas'] else a.ids, a.cmd, a.frase)
        print(f'✓ {a.fid}: {n} propuesta(s) {ACCIONES[a.cmd]}(s)')


if __name__ == '__main__':
    main()
