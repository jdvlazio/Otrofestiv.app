// ── src/lru.js ─────────────────────────────────────────────────────────────────
// Decisión PURA del LRU del cache de festivales en memoria (aplicada por loader.js).
// lruTouch(order, id, cap): mueve `id` a MRU (final) y devuelve el nuevo orden + los
// ids a evictar si se excede `cap`. `id` (el activo, recién tocado) NUNCA se evicta.
// Aislada acá para testearse sin la cadena de imports de loader.js (DOM).
export function lruTouch(order, id, cap){
  const next = order.filter(x => x !== id);
  next.push(id);
  const evict = [];
  while(next.length > cap) evict.push(next.shift());
  return { order: next, evict };
}
