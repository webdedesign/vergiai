// functions/api/chat.ts  (yalnızca arama bölümü gösterim)
async function searchQdrant(env: any, vector: number[]) {
  const base = (env.QDRANT_URL || "").replace(/\/+$/, "");
  const collection = (env.QDRANT_COLLECTION || "vergiai").toString();

  // Koleksiyon tipini öğren
  let mode: "single" | "named" = "single";
  let vectorName: string | undefined;
  try {
    const r = await fetch(`${base}/collections/${collection}`, { headers: { "api-key": env.QDRANT_API_KEY } });
    const info = await r.json().catch(() => ({}));
    const params = info?.result?.config?.params || info?.result?.params || {};
    const vec = params?.vectors;
    if (vec && typeof vec === "object") {
      if (typeof vec.size === "number") mode = "single";
      else { mode = "named"; vectorName = Object.keys(vec)[0]; }
    }
  } catch {}

  const body: any = { limit: 5, with_payload: true, score_threshold: 0.2 };
  if (mode === "single") body.vector = vector;
  else { body.vector = vector; body.using = vectorName; } // named’de Qdrant “using” bekler

  const qres = await fetch(`${base}/collections/${collection}/points/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "api-key": env.QDRANT_API_KEY },
    body: JSON.stringify(body)
  });
  const data = await qres.json().catch(() => ({}));
  return data?.result || [];
}
