import { checkAdmin } from "@/lib/admin-auth";

export async function GET() {
  const admin = await checkAdmin();
  if (!admin.ok) return Response.json({ ok: false });

  const oracleUrl = process.env.ORACLE_BACKEND_URL || "https://oracle.linkright.in";
  const secret = process.env.ORACLE_BACKEND_SECRET || "";

  try {
    const resp = await fetch(`${oracleUrl}/health`, {
      headers: secret ? { Authorization: `Bearer ${secret}` } : {},
      signal: AbortSignal.timeout(5000),
    });
    return Response.json({ ok: resp.ok, status: resp.status });
  } catch {
    return Response.json({ ok: false, status: 0 });
  }
}
