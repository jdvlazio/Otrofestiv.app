// ── live-end — cierra la Live Activity a la hora de fin (14 oct 2026) ─────────
// Migración 0008. Dos llamadas:
//  · registrar  {token, end_at (ms), env, state}: la manda el iPhone al crear o
//    actualizar la tarjeta (un retraso corre end_at). Upsert por token.
//  · barrer     {barrer:true}: la manda pg_cron cada minuto. Para cada tarjeta
//    vencida (end_at <= ahora, sin cerrar) le pide a APNs el evento «end» con
//    dismissal-date = ahora: iOS la saca de la pantalla bloqueada.
// Sin JWT (como `reportar`): el iPhone no tiene por qué tener sesión, y barrer es
// idempotente (solo cierra lo vencido). Defensas: formato estricto del token,
// end_at dentro de las próximas 12 h (lo que dura una Live Activity) y estado
// chico.
// Secreto: APNS_P8 (el contenido del .p8 — lo carga Juan en el panel). El Key ID
// y el Team ID no son secretos.

import { createClient } from "npm:@supabase/supabase-js@2";

const KEY_ID = "QWN2V25AYY";
const TEAM_ID = "SA6AP6G8L7";
const TOPIC = "app.otrofestiv.mobile.push-type.liveactivity";
const HOST = { production: "https://api.push.apple.com", sandbox: "https://api.sandbox.push.apple.com" };

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { ...CORS, "Content-Type": "application/json" } });

const RE_TOKEN = /^[0-9a-f]{32,400}$/;

// JWT de proveedor APNs (ES256). Apple pide renovarlo entre 20 y 60 min: se
// cachea 40 min en la instancia.
let _jwt: { v: string; at: number } | null = null;
const b64u = (b: ArrayBuffer | Uint8Array | string) => {
  const bytes = typeof b === "string" ? new TextEncoder().encode(b) : new Uint8Array(b);
  let s = ""; bytes.forEach((x) => (s += String.fromCharCode(x)));
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
};
async function apnsJwt(): Promise<string> {
  const now = Math.floor(Date.now() / 1000);
  if (_jwt && now - _jwt.at < 40 * 60) return _jwt.v;
  const pem = Deno.env.get("APNS_P8") ?? "";
  const der = Uint8Array.from(atob(pem.replace(/-----[^-]+-----/g, "").replace(/\s+/g, "")), (c) => c.charCodeAt(0));
  const key = await crypto.subtle.importKey("pkcs8", der, { name: "ECDSA", namedCurve: "P-256" }, false, ["sign"]);
  const head = b64u(JSON.stringify({ alg: "ES256", kid: KEY_ID }));
  const body = b64u(JSON.stringify({ iss: TEAM_ID, iat: now }));
  const sig = await crypto.subtle.sign({ name: "ECDSA", hash: "SHA-256" }, key, new TextEncoder().encode(`${head}.${body}`));
  _jwt = { v: `${head}.${body}.${b64u(sig)}`, at: now };
  return _jwt.v;
}

async function cerrar(row: { push_token: string; env: string; state: unknown }): Promise<{ st: number; why: string }> {
  const now = Math.floor(Date.now() / 1000);
  const r = await fetch(`${HOST[row.env as "production" | "sandbox"] ?? HOST.production}/3/device/${row.push_token}`, {
    method: "POST",
    headers: {
      authorization: `bearer ${await apnsJwt()}`,
      "apns-push-type": "liveactivity",
      "apns-topic": TOPIC,
      "apns-priority": "10",
      "content-type": "application/json",
    },
    body: JSON.stringify({ aps: { timestamp: now, event: "end", "dismissal-date": now, "content-state": row.state } }),
  });
  // El motivo de Apple (BadDeviceToken, InvalidProviderToken…) va al log: sin él
  // un 400 de token vencido y uno de clave mal cargada se ven iguales.
  if (r.status === 200) { await r.body?.cancel(); return { st: 200, why: "" }; }
  const why = String((await r.json().catch(() => ({})))?.reason ?? "");
  console.warn("live-end APNs:", r.status, why);
  return { st: r.status, why };
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return json(405, { error: "method not allowed" });
  let b: Record<string, unknown>;
  try { b = await req.json(); } catch { return json(400, { error: "json inválido" }); }
  const sb = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, {
    auth: { persistSession: false },
  });

  if (b.barrer === true) {
    const { data, error } = await sb.from("live_activities")
      .select("push_token, env, state").is("ended_at", null)
      .lte("end_at", new Date().toISOString()).limit(200);
    if (error) { console.error("live-end barrer:", error.code, error.message); return json(500, { error: "no se pudo leer" }); }
    if (!data?.length) return json(200, { cerradas: 0 });
    if (!Deno.env.get("APNS_P8")) return json(503, { error: "falta APNS_P8" });
    let ok = 0;
    for (const row of data) {
      let st = 0, why = "";
      try { ({ st, why } = await cerrar(row)); } catch { st = 0; }
      // 200 = cerrada; 410 o BadDeviceToken = la tarjeta ya no existe: las dos se
      // marcan para no reintentar. Cualquier otro error (clave, tema) se reintenta
      // en 1 min y queda en el log con el motivo de Apple.
      if (st === 200 || st === 410 || why === "BadDeviceToken") {
        await sb.from("live_activities").update({ ended_at: new Date().toISOString() }).eq("push_token", row.push_token);
        if (st === 200) ok++;
      }
    }
    return json(200, { cerradas: ok, vencidas: data.length });
  }

  const token = String(b.token ?? "").toLowerCase();
  const end = Number(b.end_at);
  const env = b.env === "sandbox" ? "sandbox" : "production";
  if (!RE_TOKEN.test(token)) return json(400, { error: "token" });
  if (!Number.isFinite(end) || end < Date.now() - 3600_000 || end > Date.now() + 12 * 3600_000) {
    return json(400, { error: "end_at" });
  }
  const state = b.state;
  if (!state || typeof state !== "object" || JSON.stringify(state).length > 4000) return json(400, { error: "state" });
  const { error } = await sb.from("live_activities").upsert({
    push_token: token, env, end_at: new Date(end).toISOString(), state,
    ended_at: null, updated_at: new Date().toISOString(),
  }, { onConflict: "push_token" });
  if (error) console.error("live-end registrar:", error.code, error.message);
  return error ? json(500, { error: "no se pudo guardar" }) : json(200, { ok: true });
});
