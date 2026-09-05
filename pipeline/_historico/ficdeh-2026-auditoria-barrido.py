# -*- coding: utf-8 -*-
"""Auditoría del barrido de FICDEH: descarga y CONSERVA el HTML de las 91 fichas,
compara el nº de funciones del HTML crudo contra lo extraído, e inventaría TODAS
las etiquetas que la fuente emite dentro de los bloques de función."""
import json, re, html, time, subprocess, os, collections

REPO='/Users/Juanda/Documents/Otrofestiv-dev'
S='/private/tmp/claude-501/-Users-Juanda-Documents-Otrofestiv-dev/76d8e69e-96d8-4c9a-bd3e-6c690afe74f5/scratchpad'
CACHE=f'{S}/ficdeh-html'; os.makedirs(CACHE, exist_ok=True)
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36'

def get(url, slug):
    p=f'{CACHE}/{slug}.html'
    if os.path.exists(p) and os.path.getsize(p)>20000:
        return open(p,encoding='utf-8',errors='ignore').read()
    for _ in range(3):
        r=subprocess.run(['curl','-s','--compressed','--max-time','45','-A',UA,url],capture_output=True)
        if r.returncode==0 and len(r.stdout)>20000:
            open(p,'wb').write(r.stdout)
            return r.stdout.decode('utf-8','ignore')
        time.sleep(1.5)
    return ''

def texto(h):
    h=re.sub(r'<script[^>]*>.*?</script>|<style[^>]*>.*?</style>','',h,flags=re.S)
    t=html.unescape(re.sub(r'<[^>]+>','\n',h))
    return re.sub(r'\n\s*\n+','\n',t)

def bloques(t):
    """Cada trozo tras 'Ubicación:' hasta el siguiente (o hasta el fin del bloque)."""
    out=[]
    for tr in t.split('Ubicación:')[1:]:
        corte=re.split(r'\n\s*(?:cantidad|Inscribirme|PELÍCULAS)\b', tr)[0]
        out.append(corte[:900])
    return out

def etiquetas(tr):
    return [l.strip().rstrip(':').strip() for l in tr.split('\n')
            if re.match(r'^\s*[A-ZÁÉÍÓÚÑa-z][\w áéíóúñÁÉÍÓÚÑ]{2,25}:\s*$', l)]

staging=json.load(open(f'{REPO}/festivals/staging/ficdeh-2026.json'))
films=staging.get('films') or []
barrido=json.load(open(f'{REPO}/festivals/staging/ficdeh-2026-funciones-barrido.json'))['obras']

etq=collections.Counter(); anomalias=[]; sinHora=[]; sinSede=[]; totalHTML=0
for i,f in enumerate(films,1):
    url=(f.get('_src') or {}).get('url') or ''
    slug=url.rstrip('/').split('/')[-1]
    h=get(url, slug)
    if not h:
        anomalias.append((f['title'],'NO DESCARGÓ')); continue
    t=texto(h)
    bs=bloques(t)
    n_html=len(bs); totalHTML+=n_html
    for tr in bs:
        for e in etiquetas(tr): etq[e]+=1
    n_parse=len((barrido.get(f['title']) or {}).get('funciones') or [])
    if n_html!=n_parse:
        anomalias.append((f['title'], f'HTML={n_html} parse={n_parse}'))
    for fx in (barrido.get(f['title']) or {}).get('funciones') or []:
        if not fx['hora']: sinHora.append(f['title'])
        if not fx['sede']: sinSede.append(f['title'])
    time.sleep(0.15)

print(f'\nFUNCIONES EN HTML: {totalHTML} · en el sidecar: {sum(len(v["funciones"]) for v in barrido.values())}')
print(f'\nETIQUETAS QUE USA LA FUENTE dentro de los bloques de función:')
for e,c in etq.most_common(): print(f'   {c:4}  {e}')
print(f'\nDESAJUSTES ({len(anomalias)}):')
for t,d in anomalias: print(f'   ⚠️ {t[:45]:46} {d}')
print(f'\nfunciones sin hora: {len(sinHora)} · sin sede: {len(sinSede)}')
