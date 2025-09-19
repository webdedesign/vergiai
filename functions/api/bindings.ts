export const onRequest = async ({ env }: any) => {
  const hasAI = !!env.AI && typeof env.AI.run === "function";
  const hasV = !!env.VECTORIZE_INDEX && typeof env.VECTORIZE_INDEX.upsert === "function";
  return new Response(JSON.stringify({ hasAI, hasVECTORIZE: hasV }), {
    headers: { "Content-Type": "application/json" }
  });
};
