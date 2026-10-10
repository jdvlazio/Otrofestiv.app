// ── reportar — retraso de una función SIN sesión de email (10 oct 2026) ───────
// Migración 0006. El cliente sin cuenta manda {festival_id, screening_key,
// delay_min, token}; `token` es un identificador al azar que la app guarda en el
// dispositivo. Acá se guarda su HUELLA (sha-256 → uuid), nunca el token: quien
// lea la tabla no puede volver al dispositivo.
//
// Por qué una función y no la auth anónima: pedir sesión anónima pisaba la de
// email y disparaba el límite por IP de las altas (PR #270). Esto no crea
// usuarios ni toca la sesión.
//
// Defensas (además de las de la tabla: un reporte vigente por persona y función,
// 0–240 min, 30/hora por persona — trigger, ahora por reporter_id):
//  · ventana: la fecha de la función tiene que estar a ±1 día de hoy;
//  · formato estricto de cada campo; nada de texto libre más allá de la clave.
// Límite honesto: borrar los datos de la app da un token nuevo. Lo compensan la
// ventana, la mediana y el quórum de 2 del consenso.

import { createClient } from "npm:@supabase/supabase-js@2";

const CORS = {
  "Access-Control-Allow-Origin": "*", // sin credenciales: el origen de WKWebView es capacitor://
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { ...CORS, "Content-Type": "application/json" } });

const RE_FEST = /^[a-z0-9_-]{3,40}$/;
const RE_TOKEN = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
// clave = título|YYYY-MM-DD|HH:MM|sede (domain/delays.js, cloudScreeningKey)
const RE_KEY = /^[^|]{1,200}\|(\d{4}-\d{2}-\d{2})\|\d{2}:\d{2}\|[^|]{0,120}$/;

// La huella del token, con forma de uuid (la columna reporter_id es uuid).
async function huella(token: string): Promise<string> {
  const d = new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode("otf-dispositivo:" + token)));
  const h = [...d.slice(0, 16)].map((b) => b.toString(16).padStart(2, "0")).join("");
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20, 32)}`;
}

// ±1 día: la función es de hoy, de ayer o de mañana (sin saber la zona del
// festival, el día de margen cubre de UTC-12 a UTC+14).
function enVentana(dia: string, ahora = Date.now()): boolean {
  const t = Date.parse(dia + "T12:00:00Z");
  return Number.isFinite(t) && Math.abs(t - ahora) <= 36 * 3600 * 1000;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return json(405, { error: "method not allowed" });
  let b: Record<string, unknown>;
  try { b = await req.json(); } catch { return json(400, { error: "json inválido" }); }
  const festival_id = String(b.festival_id ?? ""), screening_key = String(b.screening_key ?? "");
  const token = String(b.token ?? ""), delay_min = Number(b.delay_min);
  if (!RE_FEST.test(festival_id)) return json(400, { error: "festival_id" });
  if (!RE_TOKEN.test(token)) return json(400, { error: "token" });
  const m = RE_KEY.exec(screening_key);
  if (!m) return json(400, { error: "screening_key" });
  if (!Number.isInteger(delay_min) || delay_min < 0 || delay_min > 240) return json(400, { error: "delay_min" });
  if (!enVentana(m[1])) return json(422, { error: "fuera de la ventana" });

  const sb = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, {
    auth: { persistSession: false },
  });
  const reporter_id = await huella(token);

  // 0 = retraso limpiado: se borra el reporte propio (como cloudClearDelay).
  if (delay_min === 0) {
    const { error } = await sb.from("screening_reports").delete()
      .eq("festival_id", festival_id).eq("screening_key", screening_key).eq("reporter_id", reporter_id);
    return error ? json(500, { error: "no se pudo borrar" }) : json(200, { ok: true, borrado: true });
  }
  const { error } = await sb.from("screening_reports").upsert(
    { festival_id, screening_key, delay_min, reporter_id, is_authed: false },
    { onConflict: "festival_id,screening_key,reporter_id" },
  );
  if (error) {
    if (/rate_limit/.test(error.message)) return json(429, { error: "demasiados reportes" });
    return json(500, { error: "no se pudo guardar" });
  }
  return json(200, { ok: true });
});
