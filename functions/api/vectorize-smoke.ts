export const onRequest = async ({ env }: any) => {
  try {
    if (!env.VECTORIZE_INDEX || typeof env.VECTORIZE_INDEX.upsert !== "function") {
      return json({ error: "missing_vectorize_binding" }, 500);
    }
    // 768 boyutlu sıfır vektör
    const values = new Array(768).fill(0);
    const res = await env.VECTORIZE_INDEX.upsert([{
      id: crypto.randomUUID(),
      values,
      metadata: { title: "smoke", text: "smoke", createdAtTs: Date.now() }
    }]);
    return json({ ok: true, upsert: res });
  } catch (e:any) {
    return json({ error: "vectorize_smoke_failed", detail: String(e?.message || e) }, 502);
  }
};
const json = (o:any,s=200)=>new Response(JSON.stringify(o),{status:s,headers:{'Content-Type':'application/json'}});

