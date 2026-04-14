/**
 * POST /api/resume/fit-bullet
 *
 * Per-bullet width optimization. User clicks a bullet in the resume preview
 * and requests "Fit to one line". Uses Oracle 1B with the bullet's verbose
 * context to intelligently rewrite without losing key content.
 *
 * Input:
 *   verbose_context — full story behind this bullet (100-200 words)
 *   current_bullet  — current HTML text (with <b> tags)
 *   action          — "shrink" | "expand"
 *
 * Output:
 *   fitted_bullet — rewritten HTML
 *   fill_pct      — width fill percentage after rewrite
 *   status        — PASS | TOO_SHORT | OVERFLOW
 *   attempts      — how many tries it took
 */

import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";
import { measureBulletWidth, BULLET_BUDGET } from "@/lib/bullet-width";

const ORACLE_URL = process.env.ORACLE_BACKEND_URL ?? "";
const ORACLE_SECRET = process.env.ORACLE_BACKEND_SECRET ?? "";

const MAX_ATTEMPTS = 2;

// ── Oracle 1B rewrite call ──────────────────────────────────────────────────

async function oracleRewrite(system: string, user: string): Promise<string | null> {
  if (!ORACLE_URL) return null;
  try {
    const resp = await fetch(`${ORACLE_URL.replace(/\/$/, "")}/lifeos/rewrite`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${ORACLE_SECRET}`,
      },
      body: JSON.stringify({ system, prompt: user, temperature: 0.1 }),
      signal: AbortSignal.timeout(10000),
    });
    if (!resp.ok) return null;
    const data = (await resp.json()) as { text?: string };
    return data.text?.trim() ?? null;
  } catch {
    return null;
  }
}

// ── Groq fallback (if Oracle is down) ───────────────────────────────────────

async function groqRewrite(system: string, user: string): Promise<string | null> {
  try {
    const { groqChat } = await import("@/lib/groq");
    const text = await groqChat(
      [
        { role: "system", content: system },
        { role: "user", content: user },
      ],
      { maxTokens: 300, temperature: 0.1 }
    );
    return text?.trim() ?? null;
  } catch {
    return null;
  }
}

// ── Build rewrite prompt ────────────────────────────────────────────────────

function buildPrompt(
  verboseContext: string,
  currentBullet: string,
  action: "shrink" | "expand",
  measure: ReturnType<typeof measureBulletWidth>
): { system: string; user: string } {
  const direction = action === "shrink" ? "shorter" : "longer";
  const delta = Math.abs(measure.surplus_or_deficit);
  const target = BULLET_BUDGET.target_95;

  const system = `You are a resume bullet rewriter. Your ONLY job is to make the bullet ${direction} to fit exactly one line.

Rules:
- Output ONLY the rewritten bullet HTML. Nothing else — no explanation, no quotes.
- Preserve <b>...</b> formatting tags on the first 1-2 impactful words.
- XYZ format: lead with impact/outcome, then measurement, then action.
- Do NOT lose key metrics, company names, or outcomes.
- Target width: ${target.toFixed(1)} CU (character-units). Current: ${measure.weighted_total.toFixed(1)} CU.
- Need to ${action} by ~${delta.toFixed(1)} CU (roughly ${Math.round(delta)} characters).`;

  const user = `FULL CONTEXT (what this bullet is about — DO NOT include in output, just understand it):
${verboseContext}

CURRENT BULLET (rewrite this):
${currentBullet}

REWRITE it ${direction}. Output ONLY the rewritten HTML:`;

  return { system, user };
}

// ── Route handler ───────────────────────────────────────────────────────────

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!rateLimit(`fit-bullet:${user.id}`, 30)) {
    return rateLimitResponse("bullet width optimization");
  }

  let body: {
    verbose_context?: string;
    current_bullet?: string;
    action?: "shrink" | "expand";
  };

  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { verbose_context, current_bullet, action = "shrink" } = body;

  if (!current_bullet || current_bullet.trim().length < 10) {
    return Response.json({ error: "current_bullet is required (min 10 chars)" }, { status: 400 });
  }

  if (action !== "shrink" && action !== "expand") {
    return Response.json({ error: "action must be 'shrink' or 'expand'" }, { status: 400 });
  }

  // Use verbose_context if available, else use bullet text itself as context
  const context = verbose_context?.trim() || current_bullet;

  // ── Measure current width ──────────────────────────────────────────────

  const currentMeasure = measureBulletWidth(current_bullet);

  // Already fits? Return as-is
  if (currentMeasure.status === "PASS") {
    return Response.json({
      fitted_bullet: current_bullet,
      fill_pct: currentMeasure.fill_pct,
      status: currentMeasure.status,
      attempts: 0,
      message: "Already fits within 90-100% width",
    });
  }

  // ── Rewrite loop (max 2 attempts) ─────────────────────────────────────

  let bestBullet = current_bullet;
  let bestMeasure = currentMeasure;
  let attempts = 0;

  for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
    attempts++;
    const { system, user: userPrompt } = buildPrompt(context, bestBullet, action, bestMeasure);

    // Try Oracle 1B first, fall back to Groq
    let rewritten = await oracleRewrite(system, userPrompt);
    if (!rewritten) {
      rewritten = await groqRewrite(system, userPrompt);
    }
    if (!rewritten) {
      break; // Both failed — return best so far
    }

    // Clean up: strip markdown fences, quotes, extra whitespace
    rewritten = rewritten
      .replace(/^```(?:html)?\n?/m, "")
      .replace(/\n?```$/m, "")
      .replace(/^["']|["']$/g, "")
      .trim();

    // Measure rewritten bullet
    const newMeasure = measureBulletWidth(rewritten);

    // Is it better than current best?
    const currentDistance = Math.abs(bestMeasure.fill_pct - 95);
    const newDistance = Math.abs(newMeasure.fill_pct - 95);

    if (newDistance < currentDistance) {
      bestBullet = rewritten;
      bestMeasure = newMeasure;
    }

    // Good enough?
    if (newMeasure.status === "PASS") {
      bestBullet = rewritten;
      bestMeasure = newMeasure;
      break;
    }
  }

  return Response.json({
    fitted_bullet: bestBullet,
    fill_pct: bestMeasure.fill_pct,
    status: bestMeasure.status,
    surplus_or_deficit: bestMeasure.surplus_or_deficit,
    attempts,
  });
}
