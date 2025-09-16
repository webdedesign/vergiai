// functions/api/chat.ts
// VergiAI • Chat API (single vector, 768, cosine)
// Girdi: { message: string, tags?: string[], sinceDays?: number }
// Çıktı: { answer: string, sources: Array<{title,url,score}> }

export const onRequest = async ({ request, env }: any) => {
  if (request.method !== "POST") return json({ error: "method not allowed" }, 405, request);

  // Body
  let payload: any;
  try { payload = await request.json(); } catch { return json({ error: "invalid json" }, 400, request); }
  const message = (payload?.message || "").toString().trim();
  const tags: string[] = Array.isArray(payload?.tags) ? payload.tags.map((t:any)=>String(t).trim()).filter(Boolean) : [];
  const sinceDays = Number.isFinite(payload?.sinceDays) ? Number(payload.sinceDays) : undefined;
  if (!message) return json({ error: "message required" }, 400, request);

  // ENV
  const base = (env.QDRANT_URL || "").replace(/\/+$/, "");
  const collection = (env.QDRANT_COLLECTION || "vergiai").toString();
  const apiKey = env.QDRANT_API_KEY;
  if (!/^https?:\/\//i.test(base)) return json({ error: "invalid_qdrant_url" }, 500, request);
  if (!apiKey) return json({ error: "missing_qdrant_api_key" }, 500, request);

  // 1) Embed soru
  let queryVec: number[];
  try {
    const emb: any = await env.AI.run("@cf/baai/bge-base-en-v1.5", { text: message });
    queryVec =
      Array.isArray(emb?.data?.[0]?.embedding) ? emb.data[0].embedding :
      Array.isArray(emb?.data) ? emb.data :
      emb;
    if (!Array.isArray(queryVec) || !queryVec.length) throw new Error("empty_embedding");
  } catch (e:any) {
    return json({ error: "embed_failed", detail: String(e?.message || e) }, 502, request);
  }

  // 2) Qdrant arama (single vector)
  const searchBody: any = { vector: queryVec, limit: 5, with_payload: true, score_threshold: 0.2 };
  const must: any[] = [];
  if (tags.length) must.push({ key: "tags", match: { any: tags } });
  if (sinceDays && sinceDays > 0) {
    const gte = Date.now() - sinceDays * 24 * 60 * 60 * 1000;
    must.push({ key: "createdAtTs", range: { gte } });
  }
  if (must.length) searchBody.filter = { must };

  let contexts: string[] = [];
  let sources: any[] = [];
  try {
    const q = await fetch(`${base}/collections/${collection}/points/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "api-key": apiKey },
      body: JSON.stringify(searchBody)
    });
    const data = await q.json().catch(()=> ({}));
    const result: any[] = data?.result || [];
    contexts = result.map(p => p?.payload?.text || "").filter(Boolean);
    sources = result.map(p => ({
      title: p?.payload?.title || "",
      url: p?.payload?.url || "",
      score: p?.score
    }));
  } catch (e:any) {
    return json({ error: "qdrant_search_failed", detail: String(e?.message || e) }, 502, request);
  }

  // 3) Cevap üretimi (LLM)
  const contextText = contexts.length ? contexts.join("\n---\n").slice(0, 6000) : "(bağlam bulunamadı)";
  const prompt = `Sen Türkiye mevzuatına odaklı bir vergi danışmanı asistansın.
Bağlamdan yararlanarak kısa, net ve doğru cevap ver. Bağlam yetersizse "Bu konuda elimde yeterli bilgi yok" de.
BAĞLAM:
${contextText}

SORU: ${message}

YANIT:`;

  try {
    const out: any = await env.AI.run("@cf/meta/llama-3.1-8b-instruct", { prompt });
    const answer: string = out?.response ?? out?.result ?? "Yanıt bulunamadı.";
    return json({ answer, sources }, 200, request);
  } catch (e:any) {
    return json({ error: "llm_failed", detail: String(e?.message || e) }, 502, request);
  }
};

function json(obj:any, status=200, request?: Request) {
  const url = request ? new URL(request.url) : null;
  const debug = url?.searchParams.get("debug") === "1";
  const is5xx = status >= 500;
  const body = debug && is5xx ? { ...obj, __status: status } : obj;
  const code = debug && is5xx ? 200 : status;
  return new Response(JSON.stringify(body), { status: code, headers: { "Content-Type": "application/json" } });
}
