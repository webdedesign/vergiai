export const onRequest = async ({ request, env }: any) => {
  if (request.method !== "POST") return json({ error: "method not allowed" }, 405);

  // Admin koruması
  const provided = (request.headers.get("x-admin-token") || "").trim();
  const expected = (env.ADMIN_TOKEN || "").trim(); // Production ENV'de tanımlı olmalı
  if (expected && provided !== expected) return json({ error: "unauthorized" }, 401);

  // Gövdeyi al
  let payload: any;
  try { payload = await request.json(); } catch { return json({ error: "invalid json" }, 400); }
  const { title = "Belge", text = "", url, tags = [] } = payload || {};
  if (!text || !text.trim()) return json({ error: "text required" }, 400);

  // Ayarlar
  const qurl = (env.QDRANT_URL || "").replace(/\/+$/, "");
  const collection = env.QDRANT_COLLECTION || "vergi";

  // Parçala
  const chunks = splitText(text, 800, 120);
  const points: any[] = [];

  // Embedding
  try {
    for (const chunk of chunks) {
      const embOut: any = await env.AI.run("@cf/baai/bge-base-en-v1.5", { text: chunk });
      const vector =
        Array.isArray(embOut?.data?.[0]?.embedding) ? embOut.data[0].embedding :
        Array.isArray(embOut?.data) ? embOut.data :
        embOut;

      points.push({
        id: crypto.randomUUID(),
        vector,
        payload: { title, url, tags, text: chunk, createdAt: new Date().toISOString() }
      });
    }
  } catch (e: any) {
    return json({ error: "embedding_failed", detail: String(e?.message || e) }, 502);
  }

  // Qdrant'a yaz
  try {
    const up = await fetch(`${qurl}/collections/${collection}/points?wait=true`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", "api-key": env.QDRANT_API_KEY },
      body: JSON.stringify({ points })
    });
    if (!up.ok) {
      const t = await up.text().catch(() => "");
      return json({ error: "qdrant_write_failed", status: up.status, body: t }, 502);
    }
    return json({ ok: true, inserted: points.length });
  } catch (e: any) {
    return json({ error: "qdrant_request_failed", detail: String(e?.message || e) }, 502);
  }
};

function splitText(s: string, size = 800, overlap = 120) {
  const out: string[] = [];
  let i = 0;
  while (i < s.length) {
    const end = Math.min(s.length, i + size);
    out.push(s.slice(i, end));
    i = end - overlap;
    if (i < 0) i = 0;
    if (end === s.length) break;
  }
  return out;
}
function json(obj: any, status = 200) {
  return new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json" } });
}
