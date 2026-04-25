#!/usr/bin/env node
// api_client_demo.js — call the local USO API from a script.
// Demonstrates JS runtime, fetch, and local network interaction.
//
// Env vars:
//   BASE_URL — USO API root (default: http://localhost:8000)

const BASE_URL = (process.env.BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

async function probe() {
  console.log(`[api-client] Probing USO at ${BASE_URL}`);

  // 1. Health check
  const healthRes = await fetch(`${BASE_URL}/health`);
  if (!healthRes.ok) throw new Error(`/health returned HTTP ${healthRes.status}`);
  const health = await healthRes.json();
  console.log('[api-client] Health:', JSON.stringify(health));

  // 2. List registered scripts
  const scriptsRes = await fetch(`${BASE_URL}/api/scripts`);
  if (!scriptsRes.ok) throw new Error(`/api/scripts returned HTTP ${scriptsRes.status}`);
  const body = await scriptsRes.json();
  const scripts = Array.isArray(body) ? body : (body.items ?? []);
  console.log(`[api-client] Scripts registered: ${scripts.length}`);
  scripts.slice(0, 8).forEach((s, i) => {
    console.log(`  ${String(i + 1).padStart(2)}. ${s.name} (${s.runtime})`);
  });

  // 3. Show a summary
  const runtimes = scripts.reduce((acc, s) => {
    acc[s.runtime] = (acc[s.runtime] || 0) + 1;
    return acc;
  }, {});
  console.log('[api-client] Runtime breakdown:', JSON.stringify(runtimes));
  console.log('[api-client] Done.');
}

probe().catch(err => {
  console.error('[api-client] Error:', err.message);
  process.exit(1);
});
