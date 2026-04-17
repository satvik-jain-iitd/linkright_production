// Vercel Cron — every 10 min.
// Forwards to worker's /cron/fetch-jds which batch-fetches full JD text
// for discoveries missing it. Scanner returns title/url; this backfills
// the body so the customize flow has real content to pass to Phase 1+2.

const WORKER_URL = process.env.WORKER_URL ?? "";
const WORKER_SECRET = process.env.WORKER_SECRET ?? "";
const CRON_SECRET = process.env.CRON_SECRET ?? "";

export async function GET(request: Request) {
  const auth = request.headers.get("authorization");
  const isVercelCron = request.headers.get("x-vercel-cron") === "1";
  const hasBearer = CRON_SECRET && auth === `Bearer ${CRON_SECRET}`;
  if (!isVercelCron && !hasBearer) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }
  if (!WORKER_URL || !WORKER_SECRET) {
    return Response.json({ error: "Worker not configured" }, { status: 503 });
  }

  try {
    const resp = await fetch(`${WORKER_URL}/cron/fetch-jds`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${WORKER_SECRET}`,
      },
      body: JSON.stringify({}),
    });
    const data = await resp.json().catch(() => ({}));
    return Response.json({ forwarded: true, worker_status: resp.status, ...data });
  } catch (err) {
    return Response.json(
      { error: err instanceof Error ? err.message : "worker call failed" },
      { status: 502 },
    );
  }
}
