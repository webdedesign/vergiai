// functions/api/ingest.ts
export const onRequestPost = async (ctx: any) => {
  const { request, env } = ctx;
  try {
    // 1) Yöntem ve token kontrolü
    if (request.method !== "POST") {
      return json({ error: "method_not_allowed" }, 405);
    }
    const adminHeader = request.headers.get("x-admin-token") || "";
    if (!env.ADMIN_TOKEN || adminHeader !== env.ADMIN_TOKEN) {
      return json({ error: "unauthorized" }, 401);
    }

    // 2) Body al
    const body = await request.json().catch(() => null);
    if (!body || (!body.text && !body.chunks)) {
      return json({ error: "bad_request", detail: "Provide `text` or `chunks`[]" }, 400);
    }

    const now = new Date();
    const title = (body.title ?? "").toString();
    const url = (body.url ?? "").toString();
    const ns = (body.namespace ?? "default").toString();
    const tagsInput = Array.isArray(body.tags) ? body.tags : [];
    const tags = tagsInput.filter(Boolean).map(x => String(x)).join(",");

    // 3) Metni chunkla (kendi verirsen chunks kullanılır)
    const chunks: string[] = Array.isArray(body.chunks) && body.chunks.length
      ? body.chunks.map((x: any) => String(x))
      : splitText(String(body.text), body.chunkSize ?? 800, body.chunkOverlap ?? 120);

    if (!chunks.length) return json({ error: "empty_text" }, 400);

    // 4) Embedding → number[] (768)
    const makeVector = async (text: string) => {
      const out: any = await env.AI.run("@cf/baai/bge-base-en-v1.5", { text }); // 768-dim
      let vec: any =
        Array.isArray(out?.data?.[0]?.embedding) ? out.data[0].embedding :
        Array.isArray(out?.data) ? out.data :
        out?.embedding ?? out;

      // Float32Array -> number[], vs.
      if (ArrayBuffer.isView(vec)) vec = Array.from(vec as Float32Array);
      if (!Array.isArray(vec)) throw new Error("embed_not_array");
      // sayıları normalize et
      vec = vec.map((n: any) => {
        const v = Number(n);
        return Number.isFinite(v) ? v : 0;
      });
      if (vec.length !== 768) throw new Error(`bad_dim_${vec.length}`);
      return vec as number[];
    };

    // 5) Metadata’yı sadeleştir
    const safeMeta = (extra: Record<string, any>) => {
      const meta: Record<string, any> = {};
      for (const [k, v] of Object.entries(extra)) {
        if (v === undefined || v === null) continue;
        if (Array.isArray(v)) { meta[k] = v.filter(Boolean).map(x => String(x)).join(","); continue; }
        if (typeof v === "object") { meta[k] = JSON.stringify(v).slice(0, 9000); continue; }
        if (["string","number","boolean"].includes(typeof v)) meta[k] = v;
      }
      return meta;
    };

    // 6) Vektörleri hazırla
    const baseId = body.id ? String(body.id) : cryptoRandomId();
    const vectors = [];
    for (let i = 0; i < chunks.length; i++) {
      const text = chunks[i];
      const values = await makeVector(text);
      const id = `${baseId}#${i.toString().padStart(4,"0")}`;

      vectors.push({
        id,
        values,
        namespace: ns,
        metadata: safeMeta({
          title,
          url,
          tags,
          text,                  // istersen burayı da kısalt: text.slice(0, 4000)
          createdAt: now.toISOString(),
          createdAtTs: Math.floor(now.getTime()/1000),
        }),
      });
    }

    // 7) Vectorize’a gönder (upsert | insert)
    const mode = new URL(request.url).searchParams.get("mode") || "upsert";
    let result;
    if (mode === "insert") {
      result = await env.VECTORIZE_INDEX.insert(vectors); // alternatif
    } else {
      result = await env.VECTORIZE_INDEX.upsert(vectors); // varsayılan
    }

    return json({ ok: true, count: vectors.length, mode, mutationId: result?.mutationId ?? null });

  } catch (e: any) {
    // Bilgi amaçlı hata dönüşü (502 HTML yerine JSON)
    return json({ error: detect(e), detail: String(e?.message || e) }, 200);
  }
};

// —— yardımcılar ——
const json = (o: any, status = 200) =>
  new Response(JSON.stringify(o), { status, headers: { "Content-Type": "application/json" } });

const detect = (e: any) => {
  const s = String(e?.message || e);
  if (s.includes("embed")) return "embedding_failed";
  if (s.includes("dim")) return "embedding_bad_dimension";
  if (s.toLowerCase().includes("upsert")) return "vectorize_upsert_failed";
  if (s.toLowerCase().includes("insert")) return "vectorize_insert_failed";
  return "internal_error";
};

const cryptoRandomId = () =>
  (typeof crypto !== "undefined" && "randomUUID" in crypto)
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2);

function splitText(t: string, size = 800, overlap = 120) {
  const out: string[] = [];
  let i = 0;
  while (i < t.length) {
    const end = Math.min(t.length, i + size);
    out.push(t.slice(i, end));
    i = end - overlap;
    if (i < 0) i = 0;
    if (i >= t.length) break;
  }
  return out.filter(Boolean);
}
