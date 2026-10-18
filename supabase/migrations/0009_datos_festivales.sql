-- 0009 — los datos de los festivales se publican aparte de la app (18 oct 2026, Juan).
-- Hasta acá cada festivals/<id>.json viajaba con el código: corregir un horario
-- era PR + CI de la app + deploy (mediana 44 min, más la espera del vigía). Ahora
-- el JSON de un festival se publica solo, por pipeline/publicar-datos.py, en el
-- almacén `datos`, y la app lo lee de ahí (paso 2). El código sigue su camino.
--
-- Estructura del almacén (público para leer, solo el servidor escribe):
--   festivales/<id>/<sha12>.json   una versión, INMUTABLE (nunca se pisa)
--   indice.json                    qué versión está vigente de cada festival
-- Volver atrás = apuntar el índice a la versión anterior, que sigue ahí.

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('datos', 'datos', true, 5242880, array['application/json'])
on conflict (id) do nothing;

-- Sin políticas de INSERT/UPDATE/DELETE para anon ni authenticated: solo la
-- clave de servidor (que se salta RLS) escribe. La lectura es pública por el
-- bucket público (URL /storage/v1/object/public/datos/...).

-- Registro de cada publicación: quién, cuándo, qué versión, y si fue reversión.
create table if not exists public.publicaciones_datos (
  id           bigint generated always as identity primary key,
  festival_id  text not null check (festival_id ~ '^[a-z0-9_-]{3,40}$'),
  archivo      text not null,
  sha256       text not null check (sha256 ~ '^[0-9a-f]{64}$'),
  bytes        integer not null check (bytes > 0),
  accion       text not null check (accion in ('publicar','revertir')),
  por          text not null,
  nota         text,
  creado_en    timestamptz not null default now()
);
create index if not exists publicaciones_datos_fest on public.publicaciones_datos (festival_id, creado_en desc);
alter table public.publicaciones_datos enable row level security;
revoke all on public.publicaciones_datos from anon, authenticated;
grant select, insert on public.publicaciones_datos to service_role;
grant usage on sequence public.publicaciones_datos_id_seq to service_role;
