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

export const DATOS_URL='https://eytxrvbnwzxuedbmnnqr.supabase.co/storage/v1/object/public/datos/';
let _indice=null, _indiceAt=0;
export const origenDatos={};   // de dónde salió cada festival cargado (diagnóstico y tests)
async function _indiceDatos(){
  if(_indice && Date.now()-_indiceAt<60000) return _indice;   // un minuto de caché
  try{
    const j=await _fetchFestivalJson(DATOS_URL+'indice.json',1,3000);
    if(j && j.festivales && typeof j.festivales==='object'){ _indice=j; _indiceAt=Date.now(); }
  }catch(e){ /* sin almacén: el camino de siempre */ }
  return _indice;
}
export async function cargarDatosFestival(id, tries=3, timeoutMs=6000){
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
