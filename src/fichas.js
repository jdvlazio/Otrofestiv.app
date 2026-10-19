// fichas.js — la FICHA de cada festival viaja aparte de la app (Etapa 2·B1, 19 oct 2026).
//
// La ficha es lo que la portada necesita ANTES de bajar ningún festival: nombre,
// lema, ciudad, fechas, zona, afiche de portada, estado. Se sigue ESCRIBIENDO en
// FESTIVAL_CONFIG (src/config.js) —ahí la vigilan sus guardianes—, pero se PUBLICA
// con pipeline/publicar-datos.py al índice del almacén, y la app la aplica encima
// de la copia que trae adentro. Un afiche o una fecha nueva llegan en minutos, sin
// publicar la app. Un festival nuevo aparece en la portada igual.
//
// Solo importa el adaptador de almacenamiento (que no importa nada): lo carga
// config.js en el arranque, antes que todo, y lo usan el comando y los tests.
import { storage } from './storage/storage.js';

// Lo único que una ficha puede tocar. `storageKey` NO: es la llave de lo guardado
// por cada usuario (lista, plan, diario) — cambiarla le borraría todo. Los días y
// las funciones tampoco: son del JSON del festival.
export const CAMPOS_FICHA=['name','fullName','shortName','displayName','tagline','city','country',
  'metroArea','dates','dates_en','year','timezoneOffset','festivalStartStr','festivalEndStr',
  'keyArt','keyArtPos','group','status','priority','instagram'];

// Con estos, un festival que la app no conoce puede aparecer en la portada.
const MINIMOS=['name','city','dates','festivalStartStr','festivalEndStr'];

// id de la app ↔ nombre del archivo: bhff2026 ↔ bhff-2026 (igual que festivalJsonUrl).
export const idDeArchivo=a=>String(a).replace(/-(\d+)$/,'$1');

// fichasDelIndice(indice) → { id: ficha } con las que trae el índice del almacén.
export function fichasDelIndice(ix){
  const out={};
  if(!ix||ix.apagado||!ix.festivales||typeof ix.festivales!=='object') return out;
  for(const [archivo,e] of Object.entries(ix.festivales)){
    if(e&&e.ficha&&typeof e.ficha==='object') out[idDeArchivo(archivo)]=e.ficha;
  }
  return out;
}

// aplicarFichas(config, fichas) — pisa SOLO los campos de ficha; crea el festival
// si la app no lo conoce y la ficha trae lo mínimo. Devuelve los ids que cambiaron.
// Un campo ausente en la ficha se deja como está (la copia de la app manda).
export function aplicarFichas(config, fichas){
  const cambiados=[];
  for(const [id,f] of Object.entries(fichas||{})){
    if(!/^[a-z0-9]{3,40}$/.test(id)||!f||typeof f!=='object') continue;
    let c=config[id];
    if(!c){
      if(!MINIMOS.every(k=>f[k])) continue;
      c=config[id]={storageKey:id+'_',films:null,posters:null,lbSlugs:{}};
    }
    let cambio=false;
    for(const k of CAMPOS_FICHA){
      if(!(k in f)) continue;
      if(JSON.stringify(c[k])!==JSON.stringify(f[k])){ c[k]=f[k]; cambio=true; }
    }
    if(cambio) cambiados.push(id);
  }
  return cambiados;
}

// La última copia vista, para que la portada salga AL INSTANTE (y sin conexión)
// con lo más nuevo que conoce el teléfono. Nunca rompe el arranque.
export function fichasGuardadas(){ return typeof localStorage==='undefined'?{}:storage.getFichas(); }
export function guardarFichas(fichas){ if(typeof localStorage!=='undefined') storage.setFichas(fichas); }
