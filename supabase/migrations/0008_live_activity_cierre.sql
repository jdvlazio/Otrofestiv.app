-- 0008 — cierre de la Live Activity a la hora de fin (14 oct 2026, Juan).
-- Sin servidor, iOS no deja programar el fin de una Live Activity: la tarjeta
-- quedaba en la pantalla bloqueada hasta que se abría la app. Ahora el iPhone
-- registra el token push de cada tarjeta con su hora de fin real (con retraso),
-- y un cron por minuto llama a la edge function `live-end`, que le manda a APNs
-- el evento «end» de las vencidas.
--
-- La tabla no guarda quién es la persona: solo el token de la tarjeta (sirve
-- únicamente para esa Live Activity y muere con ella), la hora de fin y el
-- estado a mostrar al cerrar. Sin políticas: solo la lee y escribe la función
-- con service_role.

create extension if not exists pg_cron;
create extension if not exists pg_net;

create table if not exists public.live_activities (
  push_token  text primary key check (push_token ~ '^[0-9a-f]+$' and length(push_token) between 32 and 400),
  env         text not null default 'production' check (env in ('production','sandbox')),
  end_at      timestamptz not null,
  state       jsonb not null,
  ended_at    timestamptz,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index if not exists live_activities_pendientes on public.live_activities (end_at) where ended_at is null;
alter table public.live_activities enable row level security;
revoke all on public.live_activities from anon, authenticated;
grant select, insert, update, delete on public.live_activities to service_role;

-- Cada minuto: cerrar las vencidas. Barrer es idempotente (solo toca end_at <= now()
-- y sin ended_at), así que la llamada no necesita secreto.
select cron.schedule('live-end-barrido', '* * * * *', $$
  select net.http_post(
    url := 'https://eytxrvbnwzxuedbmnnqr.supabase.co/functions/v1/live-end',
    body := '{"barrer":true}'::jsonb,
    headers := '{"Content-Type":"application/json"}'::jsonb
  );
$$);

-- Limpieza diaria: lo cerrado hace más de 2 días ya no sirve.
select cron.schedule('live-end-limpieza', '17 4 * * *', $$
  delete from public.live_activities where coalesce(ended_at, end_at) < now() - interval '2 days';
$$);
