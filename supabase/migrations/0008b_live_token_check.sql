-- 0008b — el check del token usaba {32,400}: Postgres no acepta repeticiones
-- de más de 255 («invalid repetition count») y TODO registro fallaba. Mismo
-- criterio con length().
alter table public.live_activities drop constraint if exists live_activities_push_token_check;
alter table public.live_activities add constraint live_activities_push_token_check
  check (push_token ~ '^[0-9a-f]+$' and length(push_token) between 32 and 400);
