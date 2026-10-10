-- 0006 — reportar y ver retrasos SIN sesión de email (10 oct 2026, aprobado por Juan)
-- Plan: el retraso colaborativo solo existía para las cuentas con email (7 activas):
-- sin sesión no se escribía NI SE LEÍA. Ahora:
--   · escribir: la edge function `reportar` (service role) con un identificador
--     por dispositivo — no se crean usuarios ni se toca la sesión (el bug que
--     obligó a quitar la auth anónima, PR #270);
--   · leer: consenso_festival(), sin reporter_id (nunca se expone quién reportó).

-- 1 · El límite de 30/hora contaba por auth.uid(). Desde la edge function
--     (service role) auth.uid() es null → contaba 0 y no limitaba nada. Se cuenta
--     por la fila: el reporter_id de la persona (cuenta o dispositivo).
create or replace function public.tg_screening_reports_ratelimit()
returns trigger language plpgsql set search_path to '' as $$
declare recent int;
begin
  select count(*) into recent from public.screening_reports
   where reporter_id = new.reporter_id and updated_at > now() - interval '1 hour';
  if recent >= 30 then raise exception 'rate_limit: demasiados reportes en la última hora'; end if;
  return new;
end $$;

-- 2 · Lectura pública del consenso: lo mínimo para el aviso. `id` identifica a
--     la persona dentro de la función (hay una fila por persona y función:
--     unique festival_id+screening_key+reporter_id), sin decir quién es.
--     Solo lo vigente: el consenso ignora lo de más de 120 min.
create or replace function public.consenso_festival(p_festival text)
returns table(id uuid, screening_key text, delay_min int, is_authed boolean, created_at timestamptz)
language sql stable security definer set search_path to '' as $$
  select r.id, r.screening_key, r.delay_min, r.is_authed, r.created_at
    from public.screening_reports r
   where r.festival_id = p_festival
     and r.updated_at > now() - interval '3 hours';
$$;
revoke all on function public.consenso_festival(text) from public;
grant execute on function public.consenso_festival(text) to anon, authenticated;

-- 3 · La edge function `reportar` escribe con service_role, que en este proyecto
--     NO tenía permisos de escritura sobre la tabla (medido: 500 en la primera
--     prueba contra producción). Aplicado aparte como 0006b; queda acá para que
--     el archivo diga todo lo que se hizo.
grant select, insert, update, delete on table public.screening_reports to service_role;
