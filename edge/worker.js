export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const cors = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type,Authorization",
    };
    if (request.method === "OPTIONS") return new Response(null, { headers: cors });

    try {
      if (url.pathname === "/health" || url.pathname === "/") {
        return json({ ok: true, service: "broccoli-edge", version: "0.1.0" }, cors);
      }
      if (url.pathname === "/embed" && request.method === "POST") {
        const body = await request.json();
        const text = String(body.text || "");
        const vec = hashEmbed(text, 64);
        return json({ ok: true, dims: vec.length, vector: vec }, cors);
      }
      if (url.pathname === "/infer" && request.method === "POST") {
        const body = await request.json();
        const text = String(body.text || "").toLowerCase();
        let intent = "unknown";
        if (/(bluetooth|bt)\b/.test(text)) intent = "toggle_bluetooth";
        else if (/(remind|reminder|alarm)\b/.test(text)) intent = "set_reminder";
        else if (/(calendar|schedule|event)\b/.test(text)) intent = "open_calendar";
        else if (/(search|find|remember)\b/.test(text)) intent = "search_memory";
        return json({ ok: true, intent, confidence: intent === "unknown" ? 0.1 : 0.8 }, cors);
      }
      if (url.pathname === "/sync" && request.method === "POST") {
        const body = await request.json();
        const key = String(body.key || "default");
        await env.BROCCOLI_KV.put("sync:" + key, JSON.stringify(body.payload || {}), { expirationTtl: 60 * 60 * 24 * 30 });
        return json({ ok: true, stored: true }, cors);
      }
      if (url.pathname.startsWith("/sync/") && request.method === "GET") {
        const key = decodeURIComponent(url.pathname.slice("/sync/".length));
        const val = await env.BROCCOLI_KV.get("sync:" + key, { type: "json" });
        return json({ ok: true, key, value: val }, cors);
      }
      return json({ ok: false, error: "not found", path: url.pathname }, cors, 404);
    } catch (err) {
      return json({ ok: false, error: String(err) }, cors, 500);
    }
  },
};

function json(obj, headers, status = 200) {
  return new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json", ...headers } });
}

// Deterministic 64-dim bag-of-words hash embedding. No model download, no Neurons spent.
function hashEmbed(text, dims) {
  const vec = new Array(dims).fill(0);
  const tokens = String(text || "").toLowerCase().match(/[a-z0-9']+/g) || [];
  for (const t of tokens) {
    let h = 2166136261;
    for (let i = 0; i < t.length; i++) {
      h ^= t.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    const idx = (h >>> 0) % dims;
    vec[idx] += 1;
  }
  let norm = 0;
  for (const v of vec) norm += v * v;
  norm = Math.sqrt(norm) || 1;
  return vec.map((v) => v / norm);
}
