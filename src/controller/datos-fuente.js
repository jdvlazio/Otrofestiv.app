// controller/datos-fuente.js — de dónde salen los datos de un festival.
// DATOS APARTE (migración 0009, 18 oct 2026).
// Los festivales se publican sin pasar por el deploy de la app
// (pipeline/publicar-datos.py → almacén `datos` de Supabase). Dueño único de
// «de dónde salen los datos de un festival»: lo usan la carga y el refresco en
// caliente. Orden: si el índice del almacén tiene ese festival, se lee de ahí;
// si no está, o si el almacén falla, la copia de la web de siempre. Nunca peor
// que antes: cualquier error cae al camino viejo.
// `apagado:true` en el índice desactiva el almacén para todos (interruptor).
import { report } from '../telemetry.js';
import { _fetchFestivalJson, festivalJsonUrl } from './loader.js';
import { FESTIVAL_CONFIG } from '../config.js';
import { aplicarFichas, fichasDelIndice, guardarFichas } from '../fichas.js';

export const DATOS_URL='https://eytxrvbnwzxuedbmnnqr.supabase.co/storage/v1/object/public/datos/';
let _indice=null, _indiceAt=0;
export const origenDatos={};   // de dónde salió cada festival cargado (diagnóstico y tests)
async function _indiceDatos(){
  if(_indice && Date.now()-_indiceAt<60000) return _indice;   // un minuto de caché
  try{
    // ?m=<minuto>: el CDN de Supabase guarda el índice ~3 min aunque cambie
    // (medido el 18 oct con Fantasmagoría). Una URL por minuto lo esquiva: una
    // corrección llega en ≤1 min, y el CDN sigue sirviendo a todos el mismo minuto.
    const j=await _fetchFestivalJson(DATOS_URL+'indice.json?m='+Math.floor(Date.now()/60000),1,3000);
    if(j && j.festivales && typeof j.festivales==='object'){ _indice=j; _indiceAt=Date.now(); }
  }catch(e){ /* sin almacén: el camino de siempre */ }
  return _indice;
}
// SERVIDOR DE PRUEBAS (19 oct 2026, aprobado por Juan): en localhost CON puerto
// —el servidor de Playwright y el de desarrollo— se leen los archivos locales.
// Sin esto los tests bajaban lo YA publicado: publicar-datos.py y el CI de un PR
// de datos probaban la versión vieja, no la que iban a publicar. Producción no
// cambia: otrofestiv.app y el Android (https://localhost, sin puerto) siguen en el
// almacén. `?almacen=1` lo vuelve a encender (los tests del propio almacén).
const _servidorDePruebas=()=>{ try{
  const L=globalThis.location; if(!L) return false;
  return ['localhost','127.0.0.1'].includes(L.hostname) && !!L.port
    && !new URLSearchParams(L.search).has('almacen');
}catch(e){ return false; } };
export async function cargarDatosFestival(id, tries=3, timeoutMs=6000){
  if(_servidorDePruebas()){ origenDatos[id]='web'; return _fetchFestivalJson(festivalJsonUrl(id),tries,timeoutMs); }
  const archivo=festivalJsonUrl(id).replace(/^festivals\//,'').replace(/\.json$/,'');
  const ix=await _indiceDatos();
  const e=ix && !ix.apagado && ix.festivales[archivo];
  if(e && typeof e.archivo==='string' && /^festivales\/[a-z0-9_-]+\/[0-9a-f]{12}\.json$/.test(e.archivo)){
    try{
      const d=await _fetchFestivalJson(DATOS_URL+e.archivo,2,timeoutMs);
      // sin marcar el dato: la huella del refresco compara el JSON tal cual
      if(d && Array.isArray(d.films) && d.films.length){ origenDatos[id]='almacen'; return d; }
    }catch(err){ report(err,'datos-almacen:'+id); }
  }
  origenDatos[id]='web';
  return _fetchFestivalJson(festivalJsonUrl(id),tries,timeoutMs);
}

// refrescarFichas() — baja el índice y aplica las fichas que trae (Etapa 2·B1).
// Las guarda para el PRÓXIMO arranque, que ya sale con ellas desde config.js.
// Devuelve los ids que cambiaron en ESTA sesión (la portada se re-dibuja con eso).
// En el servidor de pruebas no baja nada: los tests ven la copia local, como con
// los datos. Si el almacén está apagado, se olvida lo guardado (vuelve a la copia
// de la app): el interruptor apaga TODO lo que viene del almacén.
export async function refrescarFichas(){
  if(_servidorDePruebas()) return [];
  const ix=await _indiceDatos();
  if(!ix) return [];
  const fichas=fichasDelIndice(ix);
  guardarFichas(fichas);
  return aplicarFichas(FESTIVAL_CONFIG, fichas);
}
