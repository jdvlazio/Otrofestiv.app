// ── publicar-datos — publica el JSON de UN festival aparte de la app (18 oct 2026)
// Migración 0009. Los datos ya no esperan el CI ni el deploy de la app: el
// comando pipeline/publicar-datos.py sube festivals/<id>.json a la rama `datos`
// del repo y llama a esta función con {festival, sha}. La función:
//   1. exige que `sha` sea la PUNTA ACTUAL de la rama `datos` (GitHub API).
//      Esa es la autorización: solo quien puede pushear al repo publica, y nadie
//      puede re-publicar una versión vieja llamando con un sha antiguo;
//   2. baja festivals/<id>.json de ese commit, verifica que sea JSON con la forma
//      mínima de un festival (films[] con al menos una función);
//   3. lo guarda en datos/festivales/<id>/<sha12>.json (inmutable: si ya existe,
//      no se toca) y apunta indice.json a esa versión, guardando la anterior;
//   4. anota la publicación en publicaciones_datos.
// Volver atrás = revertir el commit en la rama `datos` y publicar de nuevo: un
// solo camino, siempre con historia en git.

import { createClient } from "npm:@supabase/supabase-js@2";

const REPO = "jdvlazio/Otrofestiv.app";
const RAMA = "datos";
const RE_FEST = /^[a-z0-9_-]{3,40}$/;
const RE_SHA = /^[0-9a-f]{40}$/;

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

async function sha256(b: Uint8Array): Promise<string> {
  const d = new Uint8Array(await crypto.subtle.digest("SHA-256", b));
  return [...d].map((x) => x.toString(16).padStart(2, "0")).join("");
}

Deno.serve(async (req) => {
  if (req.method !== "POST") return json(405, { error: "method not allowed" });
  let b: Record<string, unknown>;
  try { b = await req.json(); } catch { return json(400, { error: "json inválido" }); }
  const fest = String(b.festival ?? ""), sha = String(b.sha ?? "").toLowerCase();
  const por = String(b.por ?? "comando").slice(0, 60);
  if (!RE_FEST.test(fest)) return json(400, { error: "festival" });
  if (!RE_SHA.test(sha)) return json(400, { error: "sha" });

  // 1. Autorización: el sha tiene que ser la punta de la rama `datos`.
  const gh = await fetch(`https://api.github.com/repos/${REPO}/branches/${RAMA}`, {
    headers: { "User-Agent": "otrofestiv-publicar-datos", Accept: "application/vnd.github+json" },
  });
  if (!gh.ok) return json(502, { error: `GitHub ${gh.status}` });
  const punta = (await gh.json())?.commit?.sha;
  if (punta !== sha) return json(409, { error: "el sha no es la punta de la rama datos", punta });

  // 2. El archivo de ESE commit.
  const raw = await fetch(`https://raw.githubusercontent.com/${REPO}/${sha}/festivals/${fest}.json`);
  if (!raw.ok) return json(404, { error: `no existe festivals/${fest}.json en ${sha.slice(0, 7)}` });
  const bytes = new Uint8Array(await raw.arrayBuffer());
  let data: Record<string, unknown>;
  try { data = JSON.parse(new TextDecoder().decode(bytes)); } catch { return json(422, { error: "no es JSON" }); }
  const films = Array.isArray(data.films) ? data.films : null;
  if (!films || !films.length) return json(422, { error: "sin films: no se publica un festival vacío" });

  const huella = await sha256(bytes);
  const archivo = `festivales/${fest}/${huella.slice(0, 12)}.json`;
  const sb = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, {
    auth: { persistSession: false },
  });
  const st = sb.storage.from("datos");

  // 3. La versión (inmutable) y el índice.
  const up = await st.upload(archivo, bytes, { contentType: "application/json", cacheControl: "31536000", upsert: false });
  if (up.error && !/exists|Duplicate/i.test(up.error.message)) { console.error("publicar-datos versión:", up.error.message); return json(500, { error: "no se pudo guardar la versión" }); }

  let indice: { version: number; festivales: Record<string, Record<string, unknown>> } = { version: 1, festivales: {} };
  const prev = await st.download("indice.json");
  if (prev.data) { try { indice = JSON.parse(await prev.data.text()); } catch { /* índice ilegible: se rehace */ } }
  const antes = indice.festivales[fest];
  const ahora = new Date().toISOString();
  indice.festivales[fest] = {
    archivo, sha256: huella, bytes: bytes.length, commit: sha, publicado: ahora,
    anterior: antes && antes.archivo !== archivo ? antes.archivo : (antes?.anterior ?? null),
  };
  indice.version = (indice.version || 1);
  const idx = await st.upload("indice.json", new TextEncoder().encode(JSON.stringify(indice)), {
    contentType: "application/json", cacheControl: "30", upsert: true,
  });
  if (idx.error) { console.error("publicar-datos índice:", idx.error.message); return json(500, { error: "no se pudo actualizar el índice" }); }

  // 4. Registro.
  const reg = await sb.from("publicaciones_datos").insert({
    festival_id: fest, archivo, sha256: huella, bytes: bytes.length,
    accion: antes && b.revertir === true ? "revertir" : "publicar", por, nota: sha,
  });
  if (reg.error) console.error("publicar-datos registro:", reg.error.message);
  return json(200, { ok: true, festival: fest, archivo, sha256: huella, bytes: bytes.length, igual: antes?.archivo === archivo });
});
