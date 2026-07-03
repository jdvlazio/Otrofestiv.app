-- 0002 — Hardening del sistema de retraso colaborativo
-- Origen: auditoría con los advisors oficiales de Supabase (security + performance),
-- jul 2026, tras conectar el MCP de Supabase. SIN cambios de comportamiento para la
-- app: mismas reglas RLS, más seguras y más rápidas.
--
-- Aplicar en: Supabase Studio → SQL Editor (o vía MCP con aprobación de Juan).

-- 1) LOCKDOWN RPC (advisors 0028/0029):
--    rls_auto_enable es un event-trigger interno (SECURITY DEFINER) — jamás debe ser
--    invocable vía /rest/v1/rpc. delete_user solo tiene sentido para usuarios
--    logueados (borra su propio auth.uid()); anon no debe poder invocarla.
revoke execute on function public.rls_auto_enable() from anon, authenticated, public;
revoke execute on function public.delete_user() from anon, public;

-- 2) PIN search_path (advisor 0011): evita hijacking por search_path mutable.
--    (Los cuerpos ya usan referencias schema-qualified; con '' siguen resolviendo.)
alter function public.delete_user() set search_path = '';
alter function public.tg_screening_reports_touch() set search_path = '';
alter function public.tg_screening_reports_ratelimit() set search_path = '';

-- 3) PERF RLS (advisor 0003): auth.uid() se re-evaluaba POR FILA en 8 policies;
--    (select auth.uid()) lo convierte en initplan (1 vez por query). Misma semántica.
alter policy sr_insert on public.screening_reports with check (reporter_id = (select auth.uid()));
alter policy sr_update on public.screening_reports using (reporter_id = (select auth.uid())) with check (reporter_id = (select auth.uid()));
alter policy sr_delete on public.screening_reports using (reporter_id = (select auth.uid()));
alter policy own_select on public.user_festival_state using ((select auth.uid()) = user_id);
alter policy own_insert on public.user_festival_state with check ((select auth.uid()) = user_id);
alter policy own_update on public.user_festival_state using ((select auth.uid()) = user_id);
alter policy own_delete on public.user_festival_state using ((select auth.uid()) = user_id);

-- NO tocado a propósito:
--  · sr_select using(true) — por diseño ("solo informa": todos leen el consenso).
--  · Policies con acceso anon — por diseño (Anonymous Auth es la identidad del feature).
--  · idx_sr_created "sin uso" — lo usará la limpieza TTL futura; se conserva.
