-- 0005 — «Tu festival» (#1055): en QUÉ función vio el usuario cada obra que marcó
-- fuera del Plan ({title: {day, time, venue}}). Con esto el recorrido puede
-- afirmar «N días · M sedes»; sin el dato la obra cuenta como vista pero no suma
-- día ni sede (regla: ningún número que no se pueda afirmar).
--
-- Aditiva y compatible: default '{}' → las filas y los clientes viejos siguen
-- igual. El cliente mergea por clave (gana lo más reciente), como `ratings`.
-- ORDEN DE DESPLIEGUE: esta migración va ANTES que la app que escribe la columna;
-- un upsert con una columna inexistente falla entero y se perdería el plan.

alter table public.user_festival_state
  add column if not exists watched_meta jsonb not null default '{}'::jsonb;
