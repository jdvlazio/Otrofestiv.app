-- 0010 — el almacén `datos` también guarda los afiches de PORTADA (Etapa 2·B1, 19 oct 2026).
-- La función publicar-datos sube la imagen del keyArt de cada ficha a
-- datos/keyart/<sha12>.<ext>: inmutable (el nombre es su huella), así que una
-- versión nueva del afiche es un archivo nuevo y ningún teléfono se queda con el
-- viejo. Solo imágenes de afiche; el resto del bucket sigue siendo JSON.
update storage.buckets
   set allowed_mime_types = array['application/json','image/jpeg','image/png','image/webp']
 where id = 'datos';
