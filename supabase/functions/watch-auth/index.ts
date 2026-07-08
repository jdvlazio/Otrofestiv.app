// ── watch-auth — handoff de identidad iPhone → Apple Watch (F1.0) ─────────────
// Plan: docs/PLAN-apple-watch-F1.md §2. El teléfono (ya autenticado) llama esta
// función con SU JWT; la función genera un pase de UN SOLO USO (magiclink
// hashed_token) para el email del PROPIO caller y lo devuelve. El reloj lo canjea
// con verifyOTP(tokenHash:) y obtiene SU PROPIA sesión (cadena de refresh propia
// — jamás se comparte la sesión del teléfono: la rotación de refresh tokens
// revocaría ambas; ver Supabase docs "User sessions").
//
// Seguridad:
//  · service-role key SOLO acá (server-side; el cliente jamás la ve).
//  · el email JAMÁS se acepta por parámetro — siempre el del JWT verificado.
//  · usuarios anónimos o sin email → 403.
//  · el token_hash es de un solo uso y expira según otp_expiry del proyecto.

import { createClient } from "npm:@supabase/supabase-js@2";

const CORS = {
  "Access-Control-Allow-Origin": "*", // la autorización real es el JWT, no el origin (WKWebView usa origin capacitor://)
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") {
    return new Response(JSON.stringify({ error: "method not allowed" }), {
      status: 405, headers: { ...CORS, "Content-Type": "application/json" },
    });
  }

  try {
    const authHeader = req.headers.get("Authorization") ?? "";
    if (!authHeader.startsWith("Bearer ")) {
      return new Response(JSON.stringify({ error: "missing bearer token" }), {
        status: 401, headers: { ...CORS, "Content-Type": "application/json" },
      });
    }

    // 1. Verificar el JWT del caller (cliente con anon key + su header).
    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const caller = createClient(supabaseUrl, Deno.env.get("SUPABASE_ANON_KEY")!, {
      global: { headers: { Authorization: authHeader } },
    });
    const { data: { user }, error: userErr } = await caller.auth.getUser();
    if (userErr || !user) {
      return new Response(JSON.stringify({ error: "invalid token" }), {
        status: 401, headers: { ...CORS, "Content-Type": "application/json" },
      });
    }
    // Solo usuarios permanentes con email (sin email no hay magiclink posible).
    if (user.is_anonymous || !user.email) {
      return new Response(JSON.stringify({ error: "email account required" }), {
        status: 403, headers: { ...CORS, "Content-Type": "application/json" },
      });
    }

    // 2. Generar el pase de un solo uso para el email del PROPIO caller.
    const admin = createClient(supabaseUrl, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, {
      auth: { autoRefreshToken: false, persistSession: false },
    });
    const { data, error } = await admin.auth.admin.generateLink({
      type: "magiclink",
      email: user.email,
    });
    if (error || !data?.properties?.hashed_token) {
      console.error("[watch-auth] generateLink:", error?.message);
      return new Response(JSON.stringify({ error: "could not generate link" }), {
        status: 500, headers: { ...CORS, "Content-Type": "application/json" },
      });
    }

    // 3. Devolver SOLO el hash (ni action_link ni email_otp — mínimo necesario).
    return new Response(JSON.stringify({ token_hash: data.properties.hashed_token }), {
      status: 200, headers: { ...CORS, "Content-Type": "application/json" },
    });
  } catch (e) {
    console.error("[watch-auth] unexpected:", e);
    return new Response(JSON.stringify({ error: "internal error" }), {
      status: 500, headers: { ...CORS, "Content-Type": "application/json" },
    });
  }
});
