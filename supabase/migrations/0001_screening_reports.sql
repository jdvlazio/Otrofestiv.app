-- ─────────────────────────────────────────────────────────────────────────────
-- 0001_screening_reports.sql — Retraso colaborativo · Fase A (tuberías)
-- RFC: docs/RFC-retraso-colaborativo.md
--
-- Aplicar en: Supabase Dashboard → SQL Editor (no hay tooling de migraciones).
-- Prerrequisito aparte: habilitar "Anonymous sign-ins" en
--   Authentication → Sign In / Providers → Anonymous.
--
-- Identidad: cada dispositivo abre sesión anónima → auth.uid() confiable.
-- El "confirmado" NO se almacena: se deriva en el cliente de las filas vigentes.
-- ─────────────────────────────────────────────────────────────────────────────

create table if not exists public.screening_reports (
  id            uuid        primary key default gen_random_uuid(),
  festival_id   text        not null,
  -- screening_key = título|día|hora|sede  (la sede desambigua funciones repetidas)
  screening_key text        not null,
  reporter_id   uuid        not null default auth.uid(),
  delay_min     int         not null check (delay_min >= 0 and delay_min <= 240),
  -- Confianza derivada del token, NO del cliente: un usuario con email (no anónimo)
  -- pesa más. is_anonymous viene en el JWT de Supabase.
  is_authed     boolean     not null default (coalesce((auth.jwt() ->> 'is_anonymous')::boolean, true) = false),
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  -- 1 reporte vigente por persona+función → el quórum cuenta identidades distintas.
  unique (festival_id, screening_key, reporter_id)
);

create index if not exists idx_sr_festival_key on public.screening_reports (festival_id, screening_key);
create index if not exists idx_sr_created on public.screening_reports (created_at);

-- ── updated_at automático ────────────────────────────────────────────────────
create or replace function public.tg_screening_reports_touch()
returns trigger language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end $$;

drop trigger if exists trg_sr_touch on public.screening_reports;
create trigger trg_sr_touch before update on public.screening_reports
  for each row execute function public.tg_screening_reports_touch();

-- ── Rate-limit anti-abuso: máx 30 escrituras/hora por identidad ───────────────
create or replace function public.tg_screening_reports_ratelimit()
returns trigger language plpgsql as $$
declare recent int;
begin
  select count(*) into recent
  from public.screening_reports
  where reporter_id = auth.uid()
    and updated_at > now() - interval '1 hour';
  if recent >= 30 then
    raise exception 'rate_limit: demasiados reportes en la última hora';
  end if;
  return new;
end $$;

drop trigger if exists trg_sr_ratelimit on public.screening_reports;
create trigger trg_sr_ratelimit before insert or update on public.screening_reports
  for each row execute function public.tg_screening_reports_ratelimit();

-- ── GRANTs ───────────────────────────────────────────────────────────────────
-- Las policies RLS filtran DENTRO de los privilegios; sin GRANT, el rol
-- `authenticated` (que incluye a los usuarios anónimos) recibe "permission denied
-- for table". Supabase no siempre auto-aplica los default privileges → explícito.
grant select, insert, update, delete on public.screening_reports to authenticated;

-- ── RLS ──────────────────────────────────────────────────────────────────────
alter table public.screening_reports enable row level security;

-- Lectura: cualquier sesión (anónima o con email) puede leer todos los reportes.
-- Necesario para que cada cliente compute el estado derivado.
drop policy if exists sr_select on public.screening_reports;
create policy sr_select on public.screening_reports
  for select to authenticated using (true);

-- Escritura: solo tu propio reporte (reporter_id = auth.uid()).
drop policy if exists sr_insert on public.screening_reports;
create policy sr_insert on public.screening_reports
  for insert to authenticated with check (reporter_id = auth.uid());

drop policy if exists sr_update on public.screening_reports;
create policy sr_update on public.screening_reports
  for update to authenticated using (reporter_id = auth.uid()) with check (reporter_id = auth.uid());

drop policy if exists sr_delete on public.screening_reports;
create policy sr_delete on public.screening_reports
  for delete to authenticated using (reporter_id = auth.uid());

-- ── Realtime ─────────────────────────────────────────────────────────────────
-- Publicar la tabla para postgres_changes (fan-out a los clientes suscritos).
alter publication supabase_realtime add table public.screening_reports;
