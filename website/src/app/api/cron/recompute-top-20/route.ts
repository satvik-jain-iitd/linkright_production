// Vercel Cron endpoint — every 30 min.
// Forwards to the worker's /cron/recompute-top-20 which runs the top-20
// ranker + auto-queues resumes for every user with an active watchlist.
//
// Auth chain:
//   Vercel Cron --(CRON_SECRET bearer)--> this route --(WORKER_SECRET bearer)--> worker
//
// vercel.json registers the schedule (every 30 min).

const WORKER_URL = process.env.WORKER_URL ?? "";
const WORKER_SECRET = process.env.WORKER_SECRET ?? "";
const CRON_SECRET = process.env.CRON_SECRET ?? "";

export async function GET(request: Request) {
  // Vercel Cron invocations set this header. We also accept a bearer match
  // on CRON_SECRET so the endpoint can be manually triggered for testing.
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
    const resp = await fetch(`${WORKER_URL}/cron/recompute-top-20`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${WORKER_SECRET}`,
      },
      body: JSON.stringify({}), // no user_id = all-users recompute
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
