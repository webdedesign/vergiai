// functions/api/ingest.ts
// VergiAI • Ingest API (TypeScript + robust error handling + debug mode)

/**
 * ENV (Production):
 * - ADMIN_TOKEN         : string (güçlü ASCII/hex dize)
 * - QDRANT_URL          : https://<cluster>.<region>.<provider>.cloud.qdrant.io  (sonunda / yok)
 * - QDRANT_API_KEY      : string
 * - QDRANT_COLLECTION   : string (örn. "vergi")
 *
 * Functions → Bindings:
 * - AI (Cloudflare Workers AI)   // Variable name tam olarak "AI" olmalı
 */

export const onRequest = async ({ request, env }: any) => {
  if (request.method !== "POST") {
    return json({ error: "method not allowed" }, 405, request);
  }

  // --- Admin token kontrolü (opsiyonel ama önerilir) ---
  const provided = (request.headers.get("x-admin-token") || "").trim();
  const expected = (env.ADMIN_TOKEN || "").trim();
  if (expected && provided !== expected) {
    return json({ error: "unauthorized" }, 401, request);
  }

  // --- İstek gövdesi ---
  let payload: any;
  try {
    payload = await request.json();
  } catch {
    return json({ error: "invalid json" }, 400, request);
  }

  const title = (payload?.title || "Belge").toString();
  const text: string = (payload?.text || "").toString();
  const url =
    typeof payload?.url === "string" && payload.url.trim().length
      ? payload.url.trim()
      : undefined;
  const tags: string[] = Array.isArray(payload?.tags)
    ? payload.tags.map((t: any) => String(t)).slice(0, 20)
    : [];

  if (!text || !text.trim()) {
    return json({ error: "text required" }, 400, request);
  }

  // --- Qdrant ayarları ---
  const qurl = (env.QDRANT_URL || "").replace(/\/+$/, "");
  const collection = (env.QDRANT_COLLECTION || "vergi").toString();

  if (!qurl || !/^https?:\/\//i.test(qurl)) {
    return json({ error: "invalid_qdrant_url" }, 500, request);
  }
  if (!env.QDRANT_API_KEY) {
    return json({ error: "missing_qdrant_api_key" }, 500, request);
  }

  // --- Metni parçalara böl ---
  const chunks = splitText(text, 800, 120);
  if (!chunks.length) {
    return json({ error: "empty_chunks_after_split" }, 400, request);
  }

  // --- Her parça için embedding ---
  const points: any[] = [];
  try {
    for (const chunk of chunks) {
      const embOut: any = await env.AI.run("@cf/baai/bge-base-en-v1.5", { text: chunk });
      const vector =
        Array.isArray(embOut?.data?.[0]?.embedding) ? embOut.data[0].embedding :
        Array.isArray(embOut?.data) ? embOut.data :
        embOut;

      if (!Array.isArray(vector) || !vector.length) {
        throw new Error("empty_embedding_vector");
      }

      points.push({
        id: crypto.randomUUID(),
        vector,
        payload: {
          title,
          url,
          tags,
          text: chunk,
          createdAt: new Date().toISOString()
        }
      });
    }
  } catch (e: any) {
    return json(
      { error: "embedding_failed", detail: String(e?.message || e) },
      502,
      request
    );
  }

  // --- Qdrant'a yaz (upsert) ---
  try {
    const up = await fetch(`${qurl}/collections/${collection}/points?wait=true`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "api-key": env.QDRANT_API_KEY
      },
      body: JSON.stringify({ points })
    });

    if (!up.ok) {
      const bodyText = await up.text().catch(() => "");
      // Ör. 400: dimension uyumsuz, 401: key hatalı, 404: koleksiyon yok/yanlış ad
      return json(
        { error: "qdrant_write_failed", status: up.status, body: bodyText },
        502,
        request
      );
    }

    return json({ ok: true, inserted: points.length }, 200, request);
  } catch (e: any) {
    return json(
      { error: "qdrant_request_failed", detail: String(e?.message || e) },
      502,
      request
    );
  }
};

// --- Yardımcılar ---

function splitText(s: string, size = 800, overlap = 120) {
  const out: string[] = [];
  let i = 0;
  const n = s.length;
  while (i < n) {
    const end = Math.min(n, i + size);
    out.push(s.slice(i, end));
    if (end === n) break;
    i = Math.max(0, end - overlap);
  }
  return out;
}

/**
 * JSON helper
 * - Normalde verilen status ile döner.
 * - URL'de ?debug=1 varsa ve status >= 500 ise, CF'nin 5xx HTML hata sayfasını
 *   devreye sokmamak için 200 döndürür ve __status alanına gerçek kodu koyar.
 */
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
