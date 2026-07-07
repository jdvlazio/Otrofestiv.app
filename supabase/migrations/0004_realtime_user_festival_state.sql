-- 0004 — Sync del plan EN VIVO (F0.5): habilitar Realtime en user_festival_state.
--
-- Contexto: el plan ya sincroniza (upsert), pero el otro dispositivo solo bajaba al
-- reabrir la app (boot-load) → no sirve para festival en tiempo real ni Apple Watch.
-- Con Realtime, un cambio en un dispositivo se refleja en vivo en los demás.
--
-- Seguridad: la RLS own_select (auth.uid() = user_id) ya existe → cada usuario solo
-- recibe SUS propias filas por Realtime (postgres_changes respeta la policy de SELECT).
-- Mismo mecanismo ya probado con screening_reports (0001).
--
-- REPLICA IDENTITY FULL: garantiza que el registro completo viaje en los eventos
-- UPDATE/DELETE (no solo la PK), para que el filtro por user_id y el updated_at del
-- echo-guard estén siempre presentes. Costo despreciable (tabla de bajísima escritura).

alter table public.user_festival_state replica identity full;

alter publication supabase_realtime add table public.user_festival_state;
