// functions/api/ingest.ts
// VergiAI — Ingest (Vectorize sürümü; Qdrant yok)
// Gereken Bindings (Settings → Functions → Bindings):
//   - AI                (Workers AI)          → variable name: AI
//   - Vectorize index   (Vectorize)           → variable name: VECTORIZE_INDEX
// Gerekli ENV (Production):
//   - ADMIN_TOKEN  (Secret)  → admin.html'deki token ile aynı olmalı
//
// Özellikler:
//   - x-admin-token doğrulaması
//   - Metni parçalara bölme (chunking)
//   - @cf/baai/bge-base-en-v1.5 ile embedding (768-dim)
//   - env.VECTORIZE_INDEX.upsert(...) ile kaydetme
//   - ?debug=1 iken 5xx hataları 200 + __status ile JSON döner (502 HTML görmezsin)

export const onRequest = async (ctx: any) => {
  try {
    return await handler(ctx);
  } catch (e: any) {
    return J({ error: "unhandled", detail: String(e?.message || e) }, 500, ctx?.request);
  }
};

async function handler({ request, env }: any) {
  // (İstersen CORS preflight için OPTIONS’a 204 dönebilirsin)
  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204 });
  }
  if (request.method !== "POST") {
    return J({ error: "method not allowed" }, 405, request);
  }

  // --- Admin Token Kontrolü ---
  const expected = (env.ADMIN_TOKEN || "").trim();
  const provided = (request.headers.get("x-admin-token") || "").trim();
  if (expected && provided !== expected) {
    return J({ error: "unauthorized" }, 401, request);
  }

  // --- Body Oku ---
  let p: any;
  try {
    p = await request.json();
  } catch {
    return J({ error: "invalid json" }, 400, request);
  }

  const title = String(p?.title ?? "Belge");
  const text  = String(p?.text ?? "");
  const url   = typeof p?.url === "string" && p.url.trim() ? p.url.trim() : undefined;
  const tags: string[] = Array.isArray(p?.tags)
    ? p.tags.map((t: any) => String(t).trim()).filter(Boolean).slice(0, 20)
    : [];

  if (!text.trim()) {
    return J({ error: "text required" }, 400, request);
  }

  // --- Binding Kontrolleri ---
  if (!env.AI || typeof env.AI.run !== "function") {
    return J({ error: "missing_ai_binding" }, 500, request);
  }
  if (!env.VECTORIZE_INDEX || typeof env.VECTORIZE_INDEX.upsert !== "function") {
    return J({ error: "missing_vectorize_binding" }, 500, request);
  }

  // --- Metni Parçala ---
  const chunks = split(text, 800, 120);
  if (!chunks.length) {
    return J({ error: "empty_chunks" }, 400, request);
  }

  // --- Embedding + Vectorize Upsert ---
  const now = Date.now();
  const vectors: Array<{ id: string; values: number[]; metadata: any }> = [];

  try {
    for (const chunk of chunks) {
      const emb: any = await env.AI.run("@cf/baai/bge-base-en-v1.5", { text: chunk });

      // Çeşitli cevap biçimlerini normalize et
      const values =
        Array.isArray(emb?.data?.[0]?.embedding) ? emb.data[0].embedding :
        Array.isArray(emb?.data) ? emb.data :
        emb;

      if (!Array.isArray(values) || !values.length) {
        throw new Error("empty_embedding");
      }

      vectors.push({
        id: crypto.randomUUID(),
        values,
        metadata: {
          title,
          url,
          tags,
          text: chunk,
          createdAt: new Date(now).toISOString(),
          createdAtTs: now
        }
      });
    }
  } catch (e: any) {
    return J({ error: "embedding_failed", detail: String(e?.message || e) }, 502, request);
  }

  try {
    // Not: insert() de kullanılabilir; upsert tekrar yüklemelerde de çalışır.
    const result = await env.VECTORIZE_INDEX.upsert(vectors);
    return J({ ok: true, inserted: vectors.length, result }, 200, request);
  } catch (e: any) {
    return J({ error: "vectorize_upsert_failed", detail: String(e?.message || e) }, 502, request);
  }
}

// --- Yardımcılar ---

/** Metni boyut+overlap ile parçalara böl */
function split(s: string, size = 800, overlap = 120) {
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

/** JSON helper — ?debug=1 iken 5xx → 200 + __status */
function J(obj: any, status = 200, req?: Request) {
  const url = req ? new URL(req.url) : null;
  const debug = url?.searchParams.get("debug") === "1";
  const is5xx = status >= 500;
  const body = debug && is5xx ? { ...obj, __status: status } : obj;
  const code = debug && is5xx ? 200 : status;
  return new Response(JSON.stringify(body), {
    status: code,
    headers: { "Content-Type": "application/json" }
  });
}
