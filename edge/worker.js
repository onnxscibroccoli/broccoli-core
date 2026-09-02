// Broccoli Edge Worker — free-tier schema emulator + vector store.
// Deploy: cd edge && npx wrangler deploy
// Secrets (wrangler secret put): CF_API_TOKEN is NOT needed here; this worker
// is the dumb mailbox. It stores encrypted payloads and runs the emulator.
// Bindings (wrangler.toml): KV_NS, D1_DB, VECTORIZE, AI.

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type,Authorization",
};

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...CORS },
  });
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") return new Response(null, { headers: CORS });
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, "") || "/";

    try {
      if (path === "/health" && request.method === "GET") {
        return json({ ok: true, service: "broccoli-edge", ts: Date.now() });
      }

      // POST /ingest  { records: [...] }  -> store encrypted-ish JSON in KV
      if (path === "/ingest" && request.method === "POST") {
        const body = await request.json();
        const records = Array.isArray(body.records) ? body.records : [body];
        let stored = 0;
        for (const rec of records) {
          const key = `rec:${Date.now()}:${Math.random().toString(36).slice(2, 8)}`;
          await env.KV_NS.put(key, JSON.stringify(rec), { expirationTtl: 60 * 60 * 24 * 30 });
          stored++;
        }
        return json({ ok: true, stored });
      }

      // POST /search  { query, k }  -> naive substring search over KV (free tier)
      if (path === "/search" && request.method === "POST") {
        const { query = "", k = 5 } = await request.json();
        const q = String(query).toLowerCase();
        const list = await env.KV_NS.list({ limit: 1000 });
        const hits = [];
        for (const key of list.keys) {
          const val = await env.KV_NS.get(key.name);
          if (val && val.toLowerCase().includes(q)) {
            hits.push(JSON.parse(val));
            if (hits.length >= k) break;
          }
        }
        return json({ ok: true, hits });
      }

      // POST /emulator/trial  { schema }  -> dry-run a schema, return pass/fail
      if (path === "/emulator/trial" && request.method === "POST") {
        const schema = await request.json();
        const steps = Array.isArray(schema.steps) ? schema.steps : [];
        const known = new Set([
          "bluetooth.on","bluetooth.toggle","wifi.toggle","notification",
          "calendar.create","shell","app.launch","wait",
        ]);
        let ok = true;
        const results = [];
        for (const s of steps) {
          const pass = known.has(s.action);
          results.push({ action: s.action, ok: pass });
          if (!pass) ok = false;
        }
        // persist the trial outcome
        const key = `trial:${Date.now()}`;
        await env.KV_NS.put(key, JSON.stringify({ schema, ok, results, ts: Date.now() }),
          { expirationTtl: 60 * 60 * 24 * 7 });
        return json({ ok, results, promoted: ok });
      }

      // POST /ai/embed  { text }  -> Workers AI embedding (BGE), free 10k neurons/day
      if (path === "/ai/embed" && request.method === "POST") {
        const { text } = await request.json();
        const resp = await env.AI.run("@cf/baai/bge-small-en-v1.5", { text: [String(text)] });
        const vec = resp?.data?.[0] || resp?.result?.data?.[0] || [];
        return json({ ok: true, dimensions: vec.length, vector: vec });
      }

      // POST /ai/classify  { text }  -> tiny classifier via Workers AI
      if (path === "/ai/classify" && request.method === "POST") {
        const { text } = await request.json();
        const resp = await env.AI.run("@cf/qwen/qwen1.5-0.5b-chat", {
          messages: [
            { role: "system", content: "Classify the user intent into one of: toggle_bluetooth, set_reminder, open_calendar, search_memory, report_status, unknown. Reply with ONLY the label." },
            { role: "user", content: String(text) },
          ],
        });
        const label = (resp?.response || resp?.result?.response || "unknown").trim().toLowerCase();
        return json({ ok: true, intent: label });
      }

      // GET /stats
      if (path === "/stats" && request.method === "GET") {
        const list = await env.KV_NS.list({ limit: 1000 });
        return json({ ok: true, kv_keys: list.keys.length });
      }

      return json({ ok: false, error: "not found", path }, 404);
    } catch (err) {
      return json({ ok: false, error: String(err) }, 500);
    }
  },
};
