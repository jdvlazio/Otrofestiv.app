-- 0007 — Boleta, nivel 1 (#1077): las funciones del Plan marcadas «Tengo boleta».
-- Claves «título|día|hora» (una función, no una obra). Se sincroniza como
-- watched: lista por festival en la fila del usuario.
-- OJO: aplicar ANTES de publicar la app — la app sube la fila entera y, sin la
-- columna, el guardado en la nube de quien tiene cuenta fallaría.
alter table public.user_festival_state
  add column if not exists ticketed jsonb not null default '[]'::jsonb;
