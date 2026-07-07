-- 0003 — FIX crítico: user_festival_state nunca recibió GRANT de CRUD al rol
-- `authenticated`, por lo que TODA escritura del plan fallaba con "permission
-- denied for table" antes de evaluar RLS. Resultado: la tabla estuvo VACÍA (0
-- filas) pese a usuarios firmados con email → el sync de plan (y el prereq del
-- Apple Watch) nunca funcionó. Cazado 7 jul 2026 vía logs de Postgres + revisión
-- de information_schema.role_table_grants.
--
-- Nota Supabase: los usuarios ANÓNIMOS (signInAnonymously) operan como rol
-- `authenticated` (con is_anonymous=true), NO como `anon`. `anon` es solo para
-- requests sin sesión. Por eso el grant va a `authenticated`.
--
-- Seguridad: las políticas RLS (own_select/insert/update/delete, ya existentes)
-- restringen cada operación a las filas propias (auth.uid() = user_id). El grant
-- solo habilita la operación a nivel de tabla; RLS sigue acotando a lo propio.
-- El código cliente (_cloudSave) además solo sincroniza para usuarios no-anónimos.

grant select, insert, update, delete on public.user_festival_state to authenticated;

-- No se concede a `anon` a propósito: el sync de plan es solo para usuarios con
-- email (el cliente lo gatea; anon = solo identidad de reportes de retraso).
