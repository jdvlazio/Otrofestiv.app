# -*- coding: utf-8 -*-
"""play-subir.py — sube el .aab firmado de Otrofestiv a una pista de prueba de Play.

    python3 scripts/play-subir.py --probar            # solo prueba el acceso (abre y descarta un edit)
    python3 scripts/play-subir.py <ruta.aab> [--pista alpha] [--notas "texto"]

Por qué existe (28 sep 2026): App Store ya se sube desde la terminal con la
sesión de Xcode; Play no tenía equivalente y cada APK dependía de Juan frente a
Android Studio y Play Console. Ahora:
  · la FIRMA la hace Gradle con el keystore de Otrofestiv y las contraseñas del
    Llavero de macOS (android/app/build.gradle en ~/Otrofestiv.app, nunca en un
    archivo);
  · la SUBIDA la hace este script con la cuenta de servicio
    otrofestiv-subidas@otrofestiv-play (clave en ~/.otrofestiv/, permiso SOLO de
    «lanzar en pistas de prueba»).

Nunca toca producción: la pista por defecto es «alpha» (prueba cerrada) y se
rechaza «production». Sin dependencias raras: requests + cryptography.
"""
import argparse, base64, json, os, sys, time
import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

PAQUETE = 'app.otrofestiv.mobile'
CLAVE = os.path.expanduser('~/.otrofestiv/play-service-account.json')
API = 'https://androidpublisher.googleapis.com/androidpublisher/v3/applications/' + PAQUETE
SUBIDA = 'https://androidpublisher.googleapis.com/upload/androidpublisher/v3/applications/' + PAQUETE


def _b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b'=').decode()


def token():
    sa = json.load(open(CLAVE))
    ahora = int(time.time())
    cab = _b64(json.dumps({'alg': 'RS256', 'typ': 'JWT'}).encode())
    cuerpo = _b64(json.dumps({
        'iss': sa['client_email'], 'scope': 'https://www.googleapis.com/auth/androidpublisher',
        'aud': sa['token_uri'], 'iat': ahora, 'exp': ahora + 3600}).encode())
    llave = serialization.load_pem_private_key(sa['private_key'].encode(), password=None)
    firma = llave.sign(f'{cab}.{cuerpo}'.encode(), padding.PKCS1v15(), hashes.SHA256())
    r = requests.post(sa['token_uri'], data={
        'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
        'assertion': f'{cab}.{cuerpo}.{_b64(firma)}'}, timeout=30)
    r.raise_for_status()
    return r.json()['access_token']


def _ok(r, que):
    if r.status_code >= 300:
        sys.exit(f'✗ {que}: HTTP {r.status_code} — {r.text[:500]}')
    return r.json() if r.text else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('aab', nargs='?')
    ap.add_argument('--probar', action='store_true')
    ap.add_argument('--pista', default='alpha')
    ap.add_argument('--notas', default='')
    a = ap.parse_args()
    if a.pista == 'production':
        sys.exit('✗ este script no publica en producción: eso se decide a mano en Play Console')
    h = {'Authorization': 'Bearer ' + token()}
    edit = _ok(requests.post(f'{API}/edits', headers=h, timeout=60), 'abrir edit')['id']

    if a.probar:
        pistas = _ok(requests.get(f'{API}/edits/{edit}/tracks', headers=h, timeout=60), 'leer pistas')
        requests.delete(f'{API}/edits/{edit}', headers=h, timeout=60)
        for t in pistas.get('tracks', []):
            vs = [c for rel in t.get('releases', []) for c in rel.get('versionCodes', [])]
            print(f"  {t['track']:12} versionCodes {vs}")
        print('✓ acceso a Play OK (edit descartado, nada cambió)')
        return

    if not a.aab or not os.path.exists(a.aab):
        sys.exit('✗ falta la ruta del .aab')
    with open(a.aab, 'rb') as f:
        r = requests.post(f'{SUBIDA}/edits/{edit}/bundles?uploadType=media',
                          headers={**h, 'Content-Type': 'application/octet-stream'}, data=f, timeout=900)
    vc = _ok(r, 'subir bundle')['versionCode']
    print(f'  bundle subido: versionCode {vc}')
    rel = {'versionCodes': [str(vc)], 'status': 'completed'}
    if a.notas:
        rel['releaseNotes'] = [{'language': 'es-419', 'text': a.notas}]
    _ok(requests.put(f'{API}/edits/{edit}/tracks/{a.pista}', headers=h,
                     json={'track': a.pista, 'releases': [rel]}, timeout=60), 'asignar pista')
    _ok(requests.post(f'{API}/edits/{edit}:commit', headers=h, timeout=120), 'confirmar edit')
    print(f'✓ versionCode {vc} publicado en la pista «{a.pista}»')


if __name__ == '__main__':
    main()
