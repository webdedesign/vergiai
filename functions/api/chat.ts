export const onRequest = async ({ request, env }: any) => {
  if (request.method !== "POST") return json({ error: "method not allowed" }, 405);

  // Gövde
  let payload: any;
  try { payload = await request.json(); } catch { return json({ error: "invalid json" }, 400); }
  const message: string = (payload?.message || "").trim();
  if (!message) return json({ error: "message required" }, 400);

  // 1) Embed
  let vector: number[];
  try {
    const embOut: any = await env.AI.run("@cf/baai/bge-base-en-v1.5", { text: message });
    vector =
      Array.isArray(embOut?.data?.[0]?.embedding) ? embOut.data[0].embedding :
      Array.isArray(embOut?.data) ? embOut.data :
      embOut;
  } catch (e: any) {
    return json({ error: "embed_failed", detail: String(e?.message || e) }, 502);
  }

  // 2) Qdrant arama
  const qurl = (env.QDRANT_URL || "").replace(/\/+$/, "");
  const collection = env.QDRANT_COLLECTION || "vergi";
  let contexts: string[] = [];
  let sources: any[] = [];
  try {
    const qres = await fetch(`${qurl}/collections/${collection}/points/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "api-key": env.QDRANT_API_KEY },
      body: JSON.stringify({ vector, limit: 5, with_payload: true, score_threshold: 0.2 })
    });
    const data = await qres.json().catch(() => ({}));
    const result: any[] = data?.result || [];
    contexts = result.map((p: any) => p?.payload?.text || "").filter(Boolean);
    sources = result.map((p: any) => ({
      id: p?.id, score: p?.score, title: p?.payload?.title || "", url: p?.payload?.url || ""
    }));
  } catch (e: any) {
    return json({ error: "qdrant_search_failed", detail: String(e?.message || e) }, 502);
  }

  const contextText = contexts.length ? contexts.join("\n---\n") : "(bağlam bulunamadı)";

  // 3) LLM yanıtı
  const prompt = `Sen Türkiye mevzuatına odaklı bir vergi danışmanı asistansın.
Aşağıdaki bağlamdan yararlanarak kısa ve net cevap ver. Bağlam yetersizse "Bu konuda elimde yeterli bilgi yok" de.
BAĞLAM:
${contextText}

SORU: ${message}

YANIT:`;

  try {
    const completion: any = await env.AI.run("@cf/meta/llama-3.1-8b-instruct", { prompt });
    const answer: string = completion?.response ?? completion?.result ?? "Yanıt bulunamadı.";
    return json({ answer, sources });
  } catch (e: any) {
    return json({ error: "llm_failed", detail: String(e?.message || e) }, 502);
  }
};

function json(obj: any, status = 200) {
  return new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json" } });
}
