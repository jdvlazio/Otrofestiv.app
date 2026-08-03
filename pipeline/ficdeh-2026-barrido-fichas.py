# -*- coding: utf-8 -*-
"""Barrido metódico de las fichas de FICDEH: por obra, todas sus funciones
(ubicación + hora + tipo de ingreso) y las etiquetas de fecha.
Hipótesis a validar: nº de funciones == nº de etiquetas de fecha, y el orden
se corresponde. Se valida contra la grilla real de la Cinemateca (30 funciones
con día confirmado)."""
import json, re, html, time, subprocess, unicodedata, os

REPO='/Users/Juanda/Documents/Otrofestiv-dev'
UA={'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36'}

def get(url):
    for _ in range(3):
        r=subprocess.run(['curl','-sL','--compressed','--max-time','45','-A',UA['User-Agent'],url],capture_output=True)
        if r.returncode==0 and len(r.stdout)>2000:
            return r.stdout.decode('utf-8','ignore')
        time.sleep(1.5)
    return ''

def texto(h):
    h=re.sub(r'<script[^>]*>.*?</script>|<style[^>]*>.*?</style>','',h,flags=re.S)
    t=html.unescape(re.sub(r'<[^>]+>','\n',h))
    return re.sub(r'\n\s*\n+','\n',t)

CIUDADES={'bogot':'Bogotá','medell':'Medellín','cali':'Cali','barranquilla':'Barranquilla',
 'cartagena':'Cartagena','armenia':'Armenia','ibagu':'Ibagué','quibd':'Quibdó',
 'pereira':'Pereira','manizales':'Manizales','tunja':'Tunja'}

def parse(t):
    """→ (funciones[], fechas[]). OJO: entre 'Ubicación' y 'Hora' puede haber
    'Sala:' (y potencialmente otros campos). Se trocea por 'Ubicación:' y se
    leen las etiquetas dentro de cada trozo — nunca asumir orden fijo."""
    funcs=[]
    trozos=t.split('Ubicación:')[1:]
    for tr in trozos:
        tr=tr.split('Ubicación:')[0][:800]
        lineas=[x.strip() for x in tr.split('\n')]
        lineas=[x for x in lineas if x]
        sede=lineas[0] if lineas else ''
        def campo(nombre):
            for i,l in enumerate(lineas):
                if l.rstrip(':').strip().lower()==nombre:
                    return lineas[i+1] if i+1<len(lineas) else ''
            return ''
        funcs.append({'sede':sede,'sala':campo('sala'),'fecha':campo('fecha'),
                      'hora':campo('hora'),'ingreso':campo('tipo de ingreso')})
    fechas=re.findall(r'\n(\d{1,2}\s+AGO)\n', t)
    return funcs, fechas

staging=json.load(open(f'{REPO}/festivals/staging/ficdeh-2026.json'))
films=staging.get('films') or []
out={}
for i,f in enumerate(films,1):
    url=(f.get('_src') or {}).get('url') or ''
    if not url: continue
    t=texto(get(url))
    funcs,fechas=parse(t)
    out[f['title']]={'url':url,'funciones':funcs,'fechas':fechas,
                     'n_func':len(funcs),'n_fechas':len(fechas),
                     'cuadra':len(funcs)==len(fechas)}
    print(f"[{i:3}/{len(films)}] {f['title'][:40]:41} func={len(funcs)} fechas={len(fechas)} {'OK' if len(funcs)==len(fechas) else '⚠️'}")
    time.sleep(0.25)

json.dump(out, open('/private/tmp/claude-501/-Users-Juanda-Documents-Otrofestiv-dev/76d8e69e-96d8-4c9a-bd3e-6c690afe74f5/scratchpad/ficdeh-fichas.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
cuadran=sum(1 for v in out.values() if v['cuadra'])
print(f"\nRESUMEN: {len(out)} obras · cuadran nº funciones=nº fechas: {cuadran} · no cuadran: {len(out)-cuadran}")
