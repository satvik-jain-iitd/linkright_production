// Server-side key management — BYOK feature removed.
// Stubs preserved so the legacy KeyManagerPanel UI degrades gracefully
// instead of 404'ing.

export async function GET() {
  return Response.json({
    keys: [],
    message: "API key management is handled server-side",
  });
}

export async function POST() {
  return Response.json(
    { error: "API key management is handled server-side" },
    { status: 410 },
  );
}
