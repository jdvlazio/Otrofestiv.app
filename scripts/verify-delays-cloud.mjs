#!/usr/bin/env node
// ─────────────────────────────────────────────────────────────────────────────
// verify-delays-cloud.mjs — Auditor repetible de la tubería de retraso colaborativo.
// RFC: docs/RFC-retraso-colaborativo.md · tabla: supabase/migrations/0001_*.sql
//
// Prueba END-TO-END contra el backend real (no mocks):
//   1. sign-in anónimo                         → identidad de dispositivo
//   2. INSERT propio (reporter_id = auth.uid)  → GRANT + default + RLS insert
//   3. SELECT                                  → RLS select
//   4. INSERT con reporter ajeno               → RLS DEBE rechazar (anti-abuso)
//   5. delay_min fuera de rango                → CHECK constraint
//   6. DELETE propio + limpieza                → RLS delete
//
// Uso:  node scripts/verify-delays-cloud.mjs
// La publishable key es pública (ya está en el bundle); el row _selftest se borra.
// Exit 0 = todo verde; exit 1 = algún gate falló.
// ─────────────────────────────────────────────────────────────────────────────

const URL = process.env.SB_URL || 'https://eytxrvbnwzxuedbmnnqr.supabase.co';
const KEY = process.env.SB_KEY || 'sb_publishable_-edEGNPRmpsRy7ThJMWtdw_bs6IVZSC';
const FEST = '_selftest';

let pass = 0, fail = 0;
const ok  = (m) => { pass++; console.log(`  ✓ ${m}`); };
const bad = (m) => { fail++; console.log(`  ✗ ${m}`); };

const h = (token) => ({
  apikey: KEY,
  Authorization: `Bearer ${token || KEY}`,
  'Content-Type': 'application/json',
});

async function main() {
  // 1 — sesión anónima
  const sres = await fetch(`${URL}/auth/v1/signup`, {
    method: 'POST', headers: h(),
    body: JSON.stringify({ data: {}, gotrue_meta_security: {} }),
  });
  const sjson = await sres.json();
  const token = sjson.access_token;
  const uid = sjson.user?.id;
  if (!token || !uid) { bad(`sign-in anónimo (${sjson.msg || sres.status})`); return done(); }
  ok(`sign-in anónimo (role=${sjson.user?.role}, is_anonymous=${sjson.user?.is_anonymous})`);

  // 2 — INSERT propio
  const ires = await fetch(`${URL}/rest/v1/screening_reports`, {
    method: 'POST', headers: { ...h(token), Prefer: 'return=representation' },
    body: JSON.stringify({ festival_id: FEST, screening_key: 'selftest|DIA|HORA|SEDE', delay_min: 15 }),
  });
  const irows = await ires.json();
  const row = Array.isArray(irows) ? irows[0] : null;
  if (row && row.delay_min === 15 && row.reporter_id === uid && row.is_authed === false) {
    ok('INSERT propio (reporter_id=auth.uid, is_authed=false derivado del token)');
  } else {
    bad(`INSERT propio (${ires.status}: ${irows.message || JSON.stringify(row)})`);
  }

  // 3 — SELECT
  const qres = await fetch(`${URL}/rest/v1/screening_reports?festival_id=eq.${FEST}&select=festival_id,delay_min`, { headers: h(token) });
  const qrows = await qres.json();
  Array.isArray(qrows) && qrows.length >= 1 ? ok(`SELECT (${qrows.length} fila/s)`) : bad(`SELECT (${qres.status}: ${qrows.message || JSON.stringify(qrows)})`);

  // 4 — RLS: reporter ajeno debe fallar
  const nres = await fetch(`${URL}/rest/v1/screening_reports`, {
    method: 'POST', headers: h(token),
    body: JSON.stringify({ festival_id: FEST, screening_key: 'hack|x|x|x', delay_min: 5, reporter_id: '00000000-0000-0000-0000-000000000000' }),
  });
  nres.status === 403 ? ok('RLS bloquea reporter ajeno (403)') : bad(`RLS NO bloqueó reporter ajeno (HTTP ${nres.status})`);

  // 5 — CHECK de rango
  const rres = await fetch(`${URL}/rest/v1/screening_reports`, {
    method: 'POST', headers: h(token),
    body: JSON.stringify({ festival_id: FEST, screening_key: 'x|y|z|w', delay_min: 9999 }),
  });
  [400, 409].includes(rres.status) ? ok(`CHECK rechaza delay fuera de rango (${rres.status})`) : bad(`CHECK NO rechazó delay 9999 (HTTP ${rres.status})`);

  // 6 — limpieza
  await fetch(`${URL}/rest/v1/screening_reports?festival_id=eq.${FEST}`, { method: 'DELETE', headers: h(token) });
  const lres = await fetch(`${URL}/rest/v1/screening_reports?festival_id=eq.${FEST}&select=festival_id`, { headers: h(token) });
  const left = await lres.json();
  Array.isArray(left) && left.length === 0 ? ok('DELETE propio + limpieza (0 residuales)') : bad(`limpieza dejó ${Array.isArray(left) ? left.length : '?'} filas`);

  done();
}

function done() {
  console.log(`\n  ${fail === 0 ? '✅' : '❌'}  ${pass} OK · ${fail} fallo(s)`);
  process.exit(fail === 0 ? 0 : 1);
}

console.log('Auditando tubería de retraso colaborativo (Fase A)…');
main().catch((e) => { console.error('error:', e.message); process.exit(1); });
