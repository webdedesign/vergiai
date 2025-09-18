// VergiAI — Ingest API (Cloudflare Pages Functions, TypeScript)
// Özellikler:
// - ADMIN_TOKEN doğrulaması (header: x-admin-token)
// - Workers AI ile embedding (@cf/baai/bge-base-en-v1.5)
// - Qdrant'a upsert (single ya da named vectors şemasını OTOMATİK algılar)
// - Sağlam hata yakalama + ?debug=1 iken 5xx yerine 200 + __status döndürme
// - Payload: title, url, tags, text, createdAt (ISO), createdAtTs (epoch ms)
// Gerekli ENV (Production):
//   ADMIN_TOKEN (Secret) [opsiyonel ama önerilir]
//   QDRANT_URL (Text)            ör: https://...cloud.qdrant.io   (sonunda / yok)
//   QDRANT_API_KEY (Secret)
//   QDRANT_COLLECTION (Text)     ör: vergiai
// Opsiyonel ENV (şemayı zorlamak istersen):
//   QDRANT_VECTOR_MODE (Text)    "single" | "named"
//   QDRANT_VECTOR_NAME (Text)    named modda kullanılacak vektör adı (örn: "text")
// Bindings (Functions → Bindings):
//   AI  (Cloudflare Workers AI)  — variable name tam "AI" olmalı

export const onRequest = async (ctx: any) => {
  // Üst seviye beklenmeyen hatalarda bile JSON döndür (502 HTML'i engeller)
  try {
    return await handler(ctx);
  } catch (e: any) {
    return json(
      { error: "unhandled", detail: String(e?.message || e) },
      500,
      ctx?.request
    );
  }
};

async function handler({ request, env }: any) {
  if (request.method !== "POST") {
    return json({ error: "method not allowed" }, 405, request);
  }

  // --- Admin token kontrolü (opsiyonel, set ettiysen zorunlu tutar) ---
  const provided = (request.headers.get("x-admin-token") || "").trim();
  const expected = (env.ADMIN_TOKEN || "").trim();
  if (expected && provided !== expected) {
    return json({ error: "unauthorized" }, 401, request);
  }

  // --- Body ---
  let payload: any;
  try {
    payload = await request.json();
  } catch {
    return json({ error: "invalid json" }, 400, request);
  }

  const title = String(payload?.title ?? "Belge");
  const text  = String(payload?.text ?? "");
  const url   = typeof payload?.url === "string" && payload.url.trim() ? payload.url.trim() : undefined;
  const tags: string[] = Array.isArray(payload?.tags)
    ? payload.tags.map((t: any) => String(t).trim()).filter(Boolean).slice(0, 20)
    : [];

  if (!text.trim()) {
    return json({ error: "text required" }, 400, request);
  }

  // --- ENV / Bağlantılar ---
  const base = String(env.QDRANT_URL || "").replace(/\/+$/, "");
  const collection = String(env.QDRANT_COLLECTION || "vergiai");
  const apiKey = env.QDRANT_API_KEY;

  if (!/^https?:\/\//i.test(base)) {
    return json({ error: "invalid_qdrant_url" }, 500, request);
  }
  if (!apiKey) {
    return json({ error: "missing_qdrant_api_key" }, 500, request);
  }
  if (!env.AI || typeof env.AI.run !== "function") {
    return json({ error: "missing_ai_binding" }, 500, request);
  }

  // --- Metni parçalara böl (chunking) ---
  const chunks = splitText(text, 800, 120);
  if (!chunks.length) {
    return json({ error: "empty_chunks_after_split" }, 400, request);
  }

  // --- Embeddings ---
  const vectors: number[][] = [];
  try {
    for (const chunk of chunks) {
      const emb: any = await env.AI.run("@cf/baai/bge-base-en-v1.5", { text: chunk });
      const vec =
        Array.isArray(emb?.data?.[0]?.embedding) ? emb.data[0].embedding :
        Array.isArray(emb?.data) ? emb.data :
        emb;

      if (!Array.isArray(vec) || !vec.length) {
        throw new Error("empty_embedding_vector");
      }
      vectors.push(vec);
    }
  } catch (e: any) {
    return json(
      { error: "embedding_failed", detail: String(e?.message || e) },
      502,
      request
    );
  }

  // --- Qdrant: koleksiyon şemasını belirle (single vs named) ---
  const forcedMode = String(env.QDRANT_VECTOR_MODE || "").toLowerCase();
  const forcedName = env.QDRANT_VECTOR_NAME ? String(env.QDRANT_VECTOR_NAME) : undefined;

  let mode: "single" | "named" = forcedMode === "single" || forcedMode === "named" ? (forcedMode as any) : "single";
  let vectorName: string | undefined = forcedName;

  if (!forcedMode) {
    try {
      const r = await fetch(`${base}/collections/${collection}`, {
        headers: { "api-key": apiKey }
      });
      const info = await r.json().catch(() => ({}));
      const params = info?.result?.config?.params || info?.result?.params || {};
      const vconf = params?.vectors;

      if (vconf && typeof vconf === "object") {
        if (typeof vconf.size === "number") {
          mode = "single"; // { size, distance }
        } else {
          // named vectors: { text: {size:768,...}, ... }
          const keys = Object.keys(vconf);
          if (keys.length) {
            mode = "named";
            vectorName = vectorName || keys[0]; // ilk anahtarı kullan
          }
        }
      }
    } catch {
      // okunamadıysa varsayılan single kalsın; upsert aşamasında hata yakalarız
    }
  }
// `vectors.map` döngüsünden hemen önce
const mode = env.QDRANT_VECTOR_MODE;
console.log("QDRANT_VECTOR_MODE değeri:", mode);
console.log("QDRANT_VECTOR_MODE tipi:", typeof mode);

const points = vectors.map((v, i) => {
  // ... diğer kodunuz
  // --- Upsert body'yi hazırla ---
  const now = Date.now();
  const points = vectors.map((v, i) => {
    const pld = {
      title,
      url,
      tags,
      text: chunks[i],
      createdAt: new Date(now).toISOString(),
      createdAtTs: now
    };

    const basePoint: any = { id: crypto.randomUUID(), payload: pld };
    if (mode === "single") {
      basePoint.vector = v;
    } else {
      const name = vectorName || "text";
      basePoint.vectors = { [name]: v };
    }
    return basePoint;
  });

  // --- Qdrant upsert ---
  try {
    const up = await fetch(`${base}/collections/${collection}/points?wait=true`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "api-key": apiKey
      },
      body: JSON.stringify({ points })
    });

    if (!up.ok) {
      const body = await up.text().catch(() => "");
      return json(
        { error: "qdrant_write_failed", status: up.status, body },
        502,
        request
      );
    }

    return json({ ok: true, inserted: points.length, mode, vectorName }, 200, request);
  } catch (e: any) {
    return json(
      { error: "qdrant_request_failed", detail: String(e?.message || e) },
      502,
      request
    );
  }
}

/** Metni sabit boyutlu parçalara ayır (overlap'lı) */
function splitText(s: string, size = 800, overlap = 120) {
  const out: string[] = [];
  let i = 0;
  while (i < s.length) {
    const end = Math.min(s.length, i + size);
    out.push(s.slice(i, end));
    if (end === s.length) break;
    i = Math.max(0, end - overlap);
  }
  return out;
}

/** JSON helper — ?debug=1 iken 5xx'leri 200 döndürür ve __status ekler */
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
