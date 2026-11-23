#!/usr/bin/env python3
"""correo.py — el ÚNICO camino para escribirle a un festival por correo.

POR QUÉ (16 nov 2026). El correo a Cine para la Paz salió con TODO el texto
dentro de una cita (morado en Mail, «>» en cada línea en texto plano). Causa:
Mail, cuando el mensaje se arma por AppleScript (`make new outgoing message`,
con `content` o con `html content`), lo envuelve en
`<blockquote type="cite">` de su función «compartir enlace». Probado: pasa
también con texto plano. Juan: «Que nunca más vuelva a ocurrir».

LA REGLA, que este script hace cumplir:
  · NUNCA se envía por AppleScript. El mensaje es un .eml (X-Unsent) que se
    abre en Mail como borrador y lo envía una persona con un clic.
  · Antes de abrirlo, el .eml pasa el candado (`revisar`): sin cita, sin «>»
    al inicio de línea, con From/To/Subject, HTML bien cerrado, la
    presentación de Otrofestiv en un primer contacto.
  · Después de enviado, `--verificar-enviado` lee la FUENTE del mensaje en
    Enviados y frena si Mail le metió una cita.

    python3 scripts/correo.py --revisar <archivo.eml>
    python3 scripts/correo.py --abrir <archivo.eml>          # revisa y, si pasa, lo abre en Mail
    python3 scripts/correo.py --verificar-enviado "<asunto>"  # la fuente de lo que salió
"""
import email, email.policy, os, re, subprocess, sys

CITA = [
    (re.compile(r'<blockquote[^>]*type\s*=\s*["\']?cite', re.I), 'bloque citado (<blockquote type="cite">)'),
    (re.compile(r'Apple-Mail-URLShare', re.I), 'envoltura de Mail para compartir enlaces (Apple-Mail-URLShare*)'),
    (re.compile(r'^>', re.M), 'líneas que empiezan con «>» (texto citado)'),
]
PRESENTACION = 'Somos Otrofestiv, una app gratuita para que el público arme su plan en los festivales de cine'


def _texto(msg):
    """Todas las partes de texto del mensaje, decodificadas."""
    partes = []
    for p in (msg.walk() if msg.is_multipart() else [msg]):
        if p.get_content_maintype() == 'text':
            try:
                partes.append((p.get_content_subtype(), p.get_content()))
            except Exception:
                partes.append((p.get_content_subtype(), p.get_payload(decode=True).decode('utf-8', 'replace')))
    return partes


def _msg(fuente):
    # por bytes: con message_from_string, un cuerpo en UTF-8 de 8 bits se lee
    # como latin-1 y «público» deja de casar
    return email.message_from_bytes(fuente.encode('utf-8'), policy=email.policy.default)


def problemas_de_cita(fuente):
    """[descripción] de toda forma de cita en la fuente de un mensaje."""
    msg = _msg(fuente)
    out = []
    for sub, txt in _texto(msg):
        for rx, que in CITA:
            if rx.search(txt):
                out.append(f'{que} en la parte {sub}')
    return sorted(set(out))


def revisar(path, primer_contacto=True):
    """→ [problemas]. Vacío = se puede abrir para enviar."""
    fuente = open(path, encoding='utf-8').read()
    msg = _msg(fuente)
    out = problemas_de_cita(fuente)
    for h in ('From', 'To', 'Subject'):
        if not msg.get(h):
            out.append(f'falta la cabecera {h}')
    if msg.get('X-Unsent') != '1':
        out.append('falta «X-Unsent: 1» (sin ella Mail no lo abre como borrador)')
    cuerpo = ' '.join(t for _, t in _texto(msg))
    plano = re.sub(r'<[^>]+>', '', cuerpo)
    if primer_contacto and PRESENTACION not in re.sub(r'\s+', ' ', plano):
        out.append('el primer contacto no abre con la presentación de Otrofestiv')
    for sub, t in _texto(msg):
        if sub == 'html':
            for tag in ('p', 'ol', 'ul', 'li', 'a'):
                if len(re.findall(rf'<{tag}[\s>]', t, re.I)) != len(re.findall(rf'</{tag}>', t, re.I)):
                    out.append(f'HTML mal cerrado: <{tag}>')
    if re.search(r'[“”«»]', plano):
        out.append('comillas tipográficas en el texto: van rectas "..."')
    return out


def fuente_enviado(asunto):
    r = subprocess.run(['osascript', '-e',
                        f'tell application "Mail" to get source of (first message of sent mailbox whose subject is "{asunto}")'],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit(f'✗ no encontré «{asunto}» en Enviados: {r.stderr.strip()}')
    return r.stdout


def main():
    a = sys.argv
    if '--revisar' in a or '--abrir' in a:
        p = a[a.index('--revisar' if '--revisar' in a else '--abrir') + 1]
        malos = revisar(p, primer_contacto='--no-primer-contacto' not in a)
        if malos:
            sys.exit('✗ NO se abre para enviar:\n  · ' + '\n  · '.join(malos))
        print(f'✓ {os.path.basename(p)} pasa el candado')
        if '--abrir' in a:
            subprocess.run(['open', '-a', 'Mail', p], check=True)
            print('  abierto en Mail como borrador: lo envía una persona (nunca por AppleScript)')
    elif '--verificar-enviado' in a:
        malos = problemas_de_cita(fuente_enviado(a[a.index('--verificar-enviado') + 1]))
        if malos:
            sys.exit('✗ EL CORREO SALIÓ CON CITA:\n  · ' + '\n  · '.join(malos))
        print('✓ lo enviado no trae citas')
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
