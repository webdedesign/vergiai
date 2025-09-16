// functions/api/ingest.ts
// VergiAI • Ingest API (TypeScript) — Qdrant single/named vectors otomatik algılama

export const onRequest = async ({ request, env }: any) => {
  if (request.method !== "POST") return json({ error: "method not allowed" }, 405, request);

  // Admin token
  const provided = (request.headers.get("x-admin-token") || "").trim();
  const expected = (env.ADMIN_TOKEN || "").trim();
  if (expected && provided !== expected) return json({ error: "unauthorized" }, 401, request);

  // Body
  let payload: any;
  try { payload = await request.json(); } catch { return json({ error: "invalid json" }, 400, request); }
  const title = (payload?.title || "Belge").toString();
  const text: string = (payload?.text || "").toString();
  const url = typeof payload?.url === "string" && payload.url.trim() ? payload.url.trim() : undefined;
  const tags: string[] = Array.isArray(payload?.tags) ? payload.tags.map((t: any) => String(t)).slice(0, 20) : [];
  if (!text.trim()) return json({ error: "text required" }, 400, request);

  // Qdrant ENV
  const base = (env.QDRANT_URL || "").replace(/\/+$/, "");
  const collection = (env.QDRANT_COLLECTION || "vergiai").toString();
  const apiKey = env.QDRANT_API_KEY;
  if (!/^https?:\/\//i.test(base)) return json({ error: "invalid_qdrant_url" }, 500, request);
  if (!apiKey) return json({ error: "missing_qdrant_api_key" }, 500, request);

  // Metni parçalara böl
  const chunks = splitText(text, 800, 120);
  if (!chunks.length) return json({ error: "empty_chunks_after_split" }, 400, request);

  // Embeddings
  let vectors: number[][];
  try {
    vectors = [];
    for (const chunk of chunks) {
      const embOut: any = await env.AI.run("@cf/baai/bge-base-en-v1.5", { text: chunk });
      const v =
        Array.isArray(embOut?.data?.[0]?.embedding) ? embOut.data[0].embedding :
        Array.isArray(embOut?.data) ? embOut.data :
        embOut;
      if (!Array.isArray(v) || !v.length) throw new Error("empty_embedding_vector");
      vectors.push(v);
    }
  } catch (e: any) {
    return json({ error: "embedding_failed", detail: String(e?.message || e) }, 502, request);
  }

  // Koleksiyon konfigürasyonunu oku → single mı named mı?
  let mode: "single" | "named" = "single";
  let vectorName: string | undefined;
  try {
    const r = await fetch(`${base}/collections/${collection}`, { headers: { "api-key": apiKey } });
    const info = await r.json().catch(() => ({}));
    // Qdrant cevapları farklı sürümlerde şöyle gelir:
    // info.result.config.params.vectors  (veya)  info.result.params.vectors
    const params = info?.result?.config?.params || info?.result?.params || {};
    const vec = params?.vectors;

    if (vec && typeof vec === "object") {
      if (typeof vec.size === "number") {
        mode = "single"; // { size, distance }
      } else {
        // Named vectors (ör. { text: {size:768,...}, title: {size:384,...} })
        const keys = Object.keys(vec);
        if (keys.length === 0) throw new Error("no_vectors_defined");
        mode = "named";
        vectorName = keys[0]; // ilk vektör adını kullan (istersen ENV ile sabitleyebiliriz)
      }
    } else {
      // Eski/beklenmeyen şema → single varsay
      mode = "single";
    }
  } catch (e: any) {
    // Koleksiyon okunamadıysa, yine de single dene; yazma aşamasında 400/404 yakalanır
    mode = "single";
  }

  // Qdrant'a yaz (upsert)
  try {
    const points = vectors.map((v, i) => {
      const payloadObj = {
        title, url, tags,
        text: chunks[i],
        createdAt: new Date().toISOString()
      };
      const basePoint: any = { id: crypto.randomUUID(), payload: payloadObj };
      if (mode === "single") {
        basePoint.vector = v;
      } else {
        basePoint.vectors = { [vectorName as string]: v };
      }
      return basePoint;
    });

    const up = await fetch(`${base}/collections/${collection}/points?wait=true`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", "api-key": apiKey },
      body: JSON.stringify({ points })
    });

    if (!up.ok) {
      const t = await up.text().catch(() => "");
      return json({ error: "qdrant_write_failed", status: up.status, body: t }, 502, request);
    }
    return json({ ok: true, inserted: points.length, mode, vectorName }, 200, request);
  } catch (e: any) {
    return json({ error: "qdrant_request_failed", detail: String(e?.message || e) }, 502, request);
  }
};

// Helpers
function splitText(s: string, size = 800, overlap = 120) {
  const out: string[] = [];
  for (let i = 0; i < s.length; ) {
    const end = Math.min(s.length, i + size);
    out.push(s.slice(i, end));
    if (end === s.length) break;
    i = Math.max(0, end - overlap);
  }
  return out;
}

/** JSON helper — ?debug=1 iken 5xx'leri 200 döndürüp __status ekler */
function json(obj: any, status = 200, request?: Request) {
  const url = request ? new URL(request.url) : null;
  const debug = url?.searchParams.get("debug") === "1";
  const is5xx = status >= 500;
  const body = debug && is5xx ? { ...obj, __status: status } : obj;
  const code = debug && is5xx ? 200 : status;
  return new Response(JSON.stringify(body), {
    status: code,
    headers: { "Content-Type": "application/json" }
  });
}
