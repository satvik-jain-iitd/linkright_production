// Minimal HS256 JWT implementation for the browser-extension auth flow.
// Uses Node's built-in webcrypto — no new npm dependency.
//
// Wave 8 Package:
//   - signExtensionToken(userId, ttlMs)  → 30-day extension-scoped JWT.
//   - verifyExtensionToken(token)        → returns { sub, exp } or null.
//
// Secret: EXTENSION_JWT_SECRET env var (min 32 bytes, set in Vercel).
// If unset, sign() refuses — we never silently issue unsigned tokens.

const DEFAULT_TTL_MS = 30 * 24 * 60 * 60 * 1000; // 30 days

function b64urlEncode(buf: Uint8Array | string): string {
  const bytes = typeof buf === "string" ? new TextEncoder().encode(buf) : buf;
  const b64 = Buffer.from(bytes).toString("base64");
  return b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function b64urlDecode(s: string): Uint8Array {
  const padded = s.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (s.length % 4)) % 4);
  return new Uint8Array(Buffer.from(padded, "base64"));
}

async function hmacKey(secret: string): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign", "verify"],
  );
}

function getSecretOrThrow(): string {
  const s = process.env.EXTENSION_JWT_SECRET ?? "";
  if (s.length < 32) {
    throw new Error(
      "EXTENSION_JWT_SECRET is missing or shorter than 32 bytes — extension auth disabled. Generate one with `openssl rand -hex 32` and set it in Vercel env.",
    );
  }
  return s;
}

export interface ExtensionClaims {
  sub: string;    // Supabase user id
  email?: string;
  iat: number;    // seconds
  exp: number;    // seconds
  scope: "extension";
}

export async function signExtensionToken(
  userId: string,
  opts: { email?: string; ttlMs?: number } = {},
): Promise<{ token: string; ttlMs: number; exp: number }> {
  const ttlMs = opts.ttlMs ?? DEFAULT_TTL_MS;
  const now = Math.floor(Date.now() / 1000);
  const claims: ExtensionClaims = {
    sub: userId,
    email: opts.email,
    iat: now,
    exp: now + Math.floor(ttlMs / 1000),
    scope: "extension",
  };

  const header = b64urlEncode(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const payload = b64urlEncode(JSON.stringify(claims));
  const signingInput = `${header}.${payload}`;

  const key = await hmacKey(getSecretOrThrow());
  const sigBuf = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(signingInput));
  const sig = b64urlEncode(new Uint8Array(sigBuf));

  return {
    token: `${signingInput}.${sig}`,
    ttlMs,
    exp: claims.exp,
  };
}

export async function verifyExtensionToken(token: string): Promise<ExtensionClaims | null> {
  if (!token || typeof token !== "string") return null;
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  const [header, payload, sig] = parts;

  try {
    const key = await hmacKey(getSecretOrThrow());
    // Webcrypto types want BufferSource; ensure ArrayBuffer-backed Uint8Array.
    const sigBytes = new Uint8Array(b64urlDecode(sig));
    const signedBytes = new TextEncoder().encode(`${header}.${payload}`);
    const ok = await crypto.subtle.verify(
      "HMAC",
      key,
      sigBytes as BufferSource,
      signedBytes as BufferSource,
    );
    if (!ok) return null;

    const claims = JSON.parse(new TextDecoder().decode(b64urlDecode(payload))) as ExtensionClaims;
    if (claims.scope !== "extension") return null;
    if (typeof claims.exp !== "number" || claims.exp * 1000 < Date.now()) return null;
    if (typeof claims.sub !== "string" || !claims.sub) return null;
    return claims;
  } catch {
    return null;
  }
}

/** Typical handler guard: reads Authorization: Bearer <token>, returns claims or null. */
export async function authorizeExtensionRequest(request: Request): Promise<ExtensionClaims | null> {
  const header = request.headers.get("authorization") ?? "";
  const match = header.match(/^Bearer\s+(.+)$/i);
  if (!match) return null;
  return verifyExtensionToken(match[1].trim());
}
