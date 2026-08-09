# -*- coding: utf-8 -*-
"""sedes-html.py <fest-id> --centro LAT,LNG — la página para ubicar sedes a mano.

Lo que el geocodificador no resuelve lo resuelve Juan en Google Maps, y esta
página hace ese trabajo barato: un renglón por sede pendiente, con su búsqueda
en Maps preparada y un campo que entiende TRES formas de pegar la ubicación
—par decimal, enlace de Maps, Plus Code— mostrando dónde quedó para confirmar.
«Generar JSON» copia el resultado al portapapeles; ese JSON se pega al chat y
se ingiere con _prec:"manual", que es intocable para el geocodificador.

Lee  festivals/staging/<id>-venues-geo.json  (las _prec:"sin verificar")
Esc  fuentes/<id>/sedes.html                 (material de trabajo, fuera de git)
"""
import html, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OLC_JS = r"""
const A='23456789CFGHJMPQRVWX';
function decodeFull(code){code=code.replace('+','').replace(/0+$/,'').toUpperCase();
 let lat=-90,lng=-180,latRes=400,lngRes=400;
 for(let i=0;i<Math.min(code.length,10);i+=2){latRes/=20;lngRes/=20;
  lat+=latRes*A.indexOf(code[i]);lng+=lngRes*A.indexOf(code[i+1]);}
 for(let i=10;i<code.length;i++){latRes/=5;lngRes/=4;const d=A.indexOf(code[i]);
  lat+=latRes*Math.floor(d/4);lng+=lngRes*(d%4);}
 return [lat+latRes/2,lng+lngRes/2];}
function encode(lat,lng){let c='',l=lat+90,g=lng+180,rl=400,rg=400;
 for(let i=0;i<5;i++){rl/=20;rg/=20;const a=Math.floor(l/rl),b=Math.floor(g/rg);
  c+=A[a]+A[b];l-=a*rl;g-=b*rg;if(i===3)c+='+';}return c;}
function decode(code,refLat,refLng){code=code.trim().toUpperCase().split(/\s+/)[0];
 const sep=code.indexOf('+');if(sep===8)return decodeFull(code);
 const faltan=8-sep,refCode=encode(refLat,refLng).replace('+','');
 let [lat,lng]=decodeFull(refCode.slice(0,faltan)+code);
 const paso=Math.pow(20,2-faltan/2);
 if(lat-refLat>paso/2)lat-=paso;else if(refLat-lat>paso/2)lat+=paso;
 if(lng-refLng>paso/2)lng-=paso;else if(refLng-lng>paso/2)lng+=paso;
 return [lat,lng];}
"""


def main():
    if len(sys.argv) < 2 or '--centro' not in sys.argv:
        sys.exit('uso: python3 pipeline/sedes-html.py <fest-id> --centro LAT,LNG [--ciudad "Manizales, Caldas"]')
    fid = sys.argv[1]
    lat0, lng0 = map(float, sys.argv[sys.argv.index('--centro') + 1].split(','))
    ciudad = (sys.argv[sys.argv.index('--ciudad') + 1]
              if '--ciudad' in sys.argv else '')

    geo = json.load(open(f'{REPO}/festivals/staging/{fid}-venues-geo.json', encoding='utf-8'))
    pend = sorted([(k, v) for k, v in geo.items()
                   if isinstance(v, dict) and not v.get('lat') and not k.startswith('_')],
                  key=lambda x: -x[1].get('n', 0))
    if not pend:
        print('0 sedes pendientes — nada que generar'); return

    filas = []
    for k, v in pend:
        q = html.escape(f'{k}, {ciudad}'.replace('"', '')).replace(' ', '+')
        filas.append(f'''<tr data-sede="{html.escape(k)}">
 <td class="n">{v.get('n', '')}</td><td><b>{html.escape(k)}</b></td>
 <td><a target="_blank" rel="noopener" href="https://www.google.com/maps/search/{q}">abrir en Maps ↗</a></td>
 <td><input placeholder="coordenadas, enlace o Plus Code" spellcheck="false"></td>
 <td class="ok"></td></tr>''')

    out = f'''<!doctype html><meta charset="utf-8"><title>{fid} · sedes por ubicar</title>
<style>
 body{{font:15px/1.5 -apple-system,system-ui,sans-serif;margin:0;padding:24px;background:#111;color:#eee}}
 h1{{font-size:19px;margin:0 0 4px}} p{{color:#999;margin:0 0 18px;max-width:64ch}}
 code{{background:#222;padding:1px 5px;border-radius:4px;font-size:12.5px;color:#e0a33e}}
 table{{border-collapse:collapse;width:100%;max-width:1040px}}
 td,th{{padding:9px 10px;border-bottom:1px solid #2a2a2a;vertical-align:top;text-align:left}}
 th{{color:#888;font-size:12px;letter-spacing:.06em;text-transform:uppercase}}
 .n{{color:#e0a33e;text-align:right;width:40px}} a{{color:#7fb2ff}}
 input{{width:270px;padding:6px 8px;border:1px solid #3a3a3a;border-radius:6px;
        background:#1a1a1a;color:#eee;font:13px ui-monospace,monospace}}
 input.bad{{border-color:#c25}} .ok{{color:#4c9;width:120px;font:12px ui-monospace,monospace}}
 button{{margin-top:20px;padding:10px 18px;border:0;border-radius:999px;background:#e0a33e;
         color:#111;font-weight:600;font-size:14px;cursor:pointer}}
 #salida{{width:100%;max-width:1040px;height:170px;margin-top:14px;display:none;background:#1a1a1a;
          color:#ddd;border:1px solid #3a3a3a;border-radius:8px;padding:10px;font:12px ui-monospace,monospace}}
</style>
<h1>{fid} · {len(pend)} sedes por ubicar</h1>
<p>Pegá lo que tengas: <code>5.0689, -75.5174</code> (clic derecho en Maps, primer
 renglón del menú), el <b>enlace</b> de Maps, o un <b>Plus Code</b>. La columna de
 la derecha confirma dónde quedó. Al terminar, «Generar JSON» lo copia al
 portapapeles: pegalo en el chat.</p>
<table><tr><th>func.</th><th>sede</th><th>buscar</th><th>coordenadas</th><th>queda en</th></tr>
{''.join(filas)}</table>
<button onclick="gen()">Generar JSON</button>
<textarea id="salida" spellcheck="false"></textarea>
<script>{OLC_JS}
const REF=[{lat0},{lng0}];
function leer(v){{v=v.trim();if(!v)return null;
 let m=/[@!]3?d?(-?\\d+\\.\\d+)[,!]\\s*4?d?(-?\\d+\\.\\d+)/.exec(v)||/(-?\\d+[.,]\\d+)\\s*,\\s*(-?\\d+[.,]\\d+)/.exec(v);
 if(m)return [+m[1].replace(',','.'),+m[2].replace(',','.')];
 if(/^[23456789CFGHJMPQRVWX]{{2,8}}\\+[23456789CFGHJMPQRVWX]{{2,3}}/i.test(v))
  try{{return decode(v,REF[0],REF[1])}}catch(e){{return null}}
 return null;}}
const dentro=c=>c&&Math.abs(c[0]-REF[0])<0.3&&Math.abs(c[1]-REF[1])<0.3;
document.querySelectorAll('input').forEach(i=>i.addEventListener('input',()=>{{
 const c=leer(i.value),ok=dentro(c),tr=i.closest('tr');
 i.classList.toggle('bad',!!i.value.trim()&&!ok);
 tr.querySelector('.ok').textContent=ok?c[0].toFixed(5)+', '+c[1].toFixed(5):'';
 tr.dataset.coord=ok?JSON.stringify(c):'';}}));
function gen(){{const out={{}};
 document.querySelectorAll('tr[data-sede]').forEach(tr=>{{if(tr.dataset.coord){{
  const c=JSON.parse(tr.dataset.coord);
  out[tr.dataset.sede]={{lat:+c[0].toFixed(7),lng:+c[1].toFixed(7),_prec:'manual'}};}}}});
 const t=document.getElementById('salida');t.style.display='block';
 t.value=JSON.stringify(out,null,1);t.select();document.execCommand('copy');}}
</script>'''

    dest_dir = f'{REPO}/fuentes/{fid}'
    os.makedirs(dest_dir, exist_ok=True)
    dest = f'{dest_dir}/sedes.html'
    open(dest, 'w', encoding='utf-8').write(out)
    print(f'{dest} · {len(pend)} sedes')


if __name__ == '__main__':
    main()
