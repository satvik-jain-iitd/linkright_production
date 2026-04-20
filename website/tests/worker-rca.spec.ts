import { test, expect } from '@playwright/test';
import fs from 'fs/promises';
import path from 'path';

// Root-cause analysis: is it the payload, the model, or the pipeline?
// Kicks 3 tiny-input jobs with different model pairings.

const OUT_DIR = 'test-results/real-resume-quality';
const JD_PATH = 'tests/fixtures/wing-assistant-jd.txt';
const TINY_PATH = 'tests/fixtures/real-career-tiny.txt';

async function runOne(
  request: import('@playwright/test').APIRequestContext,
  label: string,
  modelId: string,
  careerText: string,
  jdText: string,
): Promise<{ status: string; phase?: string; pct?: number; duration_ms?: number; error?: string; phase_timings?: unknown; llm_log?: unknown }> {
  test.setTimeout(360_000);
  const startRes = await request.post('/api/resume/start', {
    timeout: 60_000,
    headers: { 'Content-Type': 'application/json' },
    data: {
      jd_text: jdText,
      career_text: careerText,
      model_provider: 'groq',
      model_id: modelId,
      template_id: 'cv-a4-standard',
      target_role: 'Lead Product Manager, AI Solutions',
      target_company: 'Wing Assistant',
    },
  });
  const startBody = await startRes.json();
  // eslint-disable-next-line no-console
  console.log(`[${label}] start status=${startRes.status()}`, startBody);
  if (startRes.status() !== 200) return { status: `HTTP_${startRes.status()}`, error: JSON.stringify(startBody) };
  const jobId = startBody.job_id ?? startBody.id;
  const deadline = Date.now() + 300_000;
  let lastPct = -1;
  let lastPhase = '';
  let job: Record<string, unknown> | null = null;
  while (Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, 3000));
    const pollRes = await request.get(`/api/resume/${jobId}`, { timeout: 20_000 });
    if (pollRes.status() !== 200) continue;
    job = await pollRes.json();
    const pct = Number((job as { progress_pct?: number }).progress_pct ?? 0);
    const phase = String((job as { current_phase?: string }).current_phase ?? '');
    const st = String((job as { status?: string }).status ?? '');
    if (pct !== lastPct || phase !== lastPhase) {
      // eslint-disable-next-line no-console
      console.log(`  [${label}] ${new Date().toISOString()} ${st} ${pct}% "${phase}"`);
      lastPct = pct;
      lastPhase = phase;
    }
    if (['completed', 'failed', 'cancelled'].includes(st)) break;
  }
  const j = (job ?? {}) as Record<string, unknown>;
  return {
    status: String(j.status ?? ''),
    phase: String(j.current_phase ?? ''),
    pct: Number(j.progress_pct ?? 0),
    duration_ms: Number(j.duration_ms ?? 0),
    error: j.error_message ? String(j.error_message) : undefined,
    phase_timings: (j as { _phase_timings?: unknown })._phase_timings,
    llm_log: (j as { _llm_log?: unknown })._llm_log,
  };
}

test.describe.configure({ mode: 'serial' });

test.describe('Worker RCA — minimize variables', () => {
  test.use({ storageState: 'playwright/.auth/user.json' });

  let jdText = '';
  let tinyText = '';

  test.beforeAll(async () => {
    await fs.mkdir(OUT_DIR, { recursive: true });
    jdText = await fs.readFile(JD_PATH, 'utf8');
    tinyText = await fs.readFile(TINY_PATH, 'utf8');
  });

  test('A. llama-3.1-8b-instant + tiny career (fastest path)', async ({ request }) => {
    const r = await runOne(request, 'A-8b-tiny', 'llama-3.1-8b-instant', tinyText, jdText);
    await fs.writeFile(path.join(OUT_DIR, 'rca-A-8b-tiny.json'), JSON.stringify(r, null, 2));
    expect.soft(r.status, 'A status').toBe('completed');
  });

  test('B. llama-3.3-70b-versatile + tiny career', async ({ request }) => {
    const r = await runOne(request, 'B-70b-tiny', 'llama-3.3-70b-versatile', tinyText, jdText);
    await fs.writeFile(path.join(OUT_DIR, 'rca-B-70b-tiny.json'), JSON.stringify(r, null, 2));
    expect.soft(r.status, 'B status').toBe('completed');
  });
});
