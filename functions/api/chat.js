export async function onRequestPost(context) {
  const { request, env } = context;
  const { message } = await request.json().catch(() => ({}));
  if (!message) return new Response(JSON.stringify({ error:"message required" }),{status:400});

  // 1) Embed
  const embOut = await env.AI.run("@cf/baai/bge-base-en-v1.5", { text: message });
  const vector = Array.isArray(embOut?.data?.[0]?.embedding)
      ? embOut.data[0].embedding
      : Array.isArray(embOut?.data) ? embOut.data
      : embOut;

  // 2) Qdrant search
  const url = (env.QDRANT_URL || "").replace(/\/+$/, "");
  const collection = env.QDRANT_COLLECTION || "vergi";
  const qres = await fetch(`${url}/collections/${collection}/points/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "api-key": env.QDRANT_API_KEY },
    body: JSON.stringify({ vector, limit: 5, with_payload: true, score_threshold: 0.2 })
  });
  const { result = [] } = await qres.json().catch(() => ({ result: [] }));
  const contextText = result.map(p => p.payload?.text || "").filter(Boolean).join("\n---\n");
  const sources = result.map(p => ({ id:p.id, score:p.score, title:p.payload?.title||"", url:p.payload?.url||"" }));

  // 3) LLM answer
  const prompt = `Sen Türkiye mevzuatına odaklı bir vergi danışmanı asistansın.
Aşağıdaki bağlamdan yararlanarak kısa ve net cevap ver. Bağlam yetersizse "Bu konuda elimde yeterli bilgi yok" de.
BAĞLAM:
${contextText || "(bağlam yok)"}

SORU: ${message}

YANIT:`;
  const completion = await env.AI.run("@cf/meta/llama-3.1-8b-instruct", { prompt });
  const answer = completion?.response ?? completion?.result ?? "Yanıt bulunamadı.";

  return new Response(JSON.stringify({ answer, sources }), { headers:{ "Content-Type":"application/json" }});
}
