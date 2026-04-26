// Server-side key management — BYOK feature removed.
// Stub preserved so the legacy KeyManagerPanel "test" button degrades
// gracefully instead of 404'ing.

export async function POST() {
  return Response.json(
    {
      valid: false,
      message: "API key management is handled server-side",
    },
    { status: 410 },
  );
}
