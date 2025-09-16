export async function onRequestPost(context) {
  const { request, env } = context;

  // Basit admin koruması
  const token = request.headers.get('x-admin-token');
  if (!token || token !== env.ADMIN_TOKEN) {
    return new Response(JSON.stringify({ error: "unauthorized" }), { status: 401 });
  }

  // ... mevcut kodun devamı ...

export async function onRequestPost(context) {
  const { request, env } = context;
  const { title="Belge", text="", url, tags=[] } = await request.json().catch(() => ({}));
  if (!text.trim()) return new Response(JSON.stringify({ error:"text required" }),{status:400});

  const qurl = (env.QDRANT_URL || "").replace(/\/+$/, "");
  const collection = env.QDRANT_COLLECTION || "vergi";

  const chunks = splitText(text, 800, 120);
  const points = [];
  for (const chunk of chunks) {
    const embOut = await env.AI.run("@cf/baai/bge-base-en-v1.5", { text: chunk });
    const vector = Array.isArray(embOut?.data?.[0]?.embedding)
        ? embOut.data[0].embedding
        : Array.isArray(embOut?.data) ? embOut.data
        : embOut;
    points.push({
      id: crypto.randomUUID(),
      vector,
      payload: { title, url, tags, text: chunk, createdAt: new Date().toISOString() }
    });
  }

  const up = await fetch(`${qurl}/collections/${collection}/points?wait=true`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", "api-key": env.QDRANT_API_KEY },
    body: JSON.stringify({ points })
  });

  return new Response(JSON.stringify({ ok: up.ok, inserted: points.length }), {
    headers: { "Content-Type": "application/json" }, status: up.ok ? 200 : 500
  });
}

function splitText(s, size=800, overlap=120){
  const out=[]; let i=0;
  while(i<s.length){ const end=Math.min(s.length,i+size); out.push(s.slice(i,end)); i=end-overlap; if(i<0)i=0; if(end===s.length)break; }
  return out;
}
