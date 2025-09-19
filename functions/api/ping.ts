export const onRequest = async () =>
  new Response(JSON.stringify({ ok: true }), {
    headers: { "Content-Type": "application/json" }
  });
