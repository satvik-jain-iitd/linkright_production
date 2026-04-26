// Server-side key management — BYOK feature removed.
// Stubs preserved so the legacy KeyManagerPanel UI degrades gracefully
// instead of 404'ing.

export async function DELETE() {
  return Response.json(
    { error: "API key management is handled server-side" },
    { status: 410 },
  );
}

export async function PATCH() {
  return Response.json(
    { error: "API key management is handled server-side" },
    { status: 410 },
  );
}
