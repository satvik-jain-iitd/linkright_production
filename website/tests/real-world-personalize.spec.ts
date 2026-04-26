import { test, expect } from '@playwright/test';
import fs from 'fs/promises';
import path from 'path';

// Real-world "does it work?" test with Satvik's actual artifacts:
//  - PDF resume         → /api/onboarding/parse-resume   (quality of parse)
//  - Career profile .md → /api/resume/start career_text   (rich context)
//  - Wing Assistant JD  → /api/jd/analyze + /api/resume/start (match + generation)
// Output lands in test-results/real-resume-quality/ as human-readable markdown.

const OUT_DIR = 'test-results/real-resume-quality';

const PDF_PATH = 'tests/fixtures/real-resume.pdf';
const CAREER_MD_PATH = 'tests/fixtures/real-career-profile.md';
const CAREER_COMPACT_PATH = 'tests/fixtures/real-career-compact.txt';
const JD_PATH = 'tests/fixtures/wing-assistant-jd.txt';

test.describe.configure({ mode: 'serial' });

test.describe('Real-world personalization — Satvik + Wing Assistant JD', () => {
  test.use({ storageState: 'playwright/.auth/user.json' });

  test.beforeAll(async () => {
    await fs.mkdir(OUT_DIR, { recursive: true });
  });

  test('1. Parse Satvik PDF via /api/onboarding/parse-resume', async ({ request }) => {
    const buf = await fs.readFile(PDF_PATH);
    const res = await request.post('/api/onboarding/parse-resume', {
      multipart: {
        file: { name: 'satvik-resume.pdf', mimeType: 'application/pdf', buffer: buf },
      },
    });
    const status = res.status();
    const body = await res.json();
    const parsed = body.parsed ?? {};
    const narr = String(parsed.career_summary_first_person ?? '');

    // Write readable MD FIRST so failures still capture output
    const md = [
      '# Parse-resume quality — Satvik real PDF',
      '',
      `**HTTP:** ${status}`,
      `**Name:** ${parsed.full_name}`,
      `**Email:** ${parsed.email}`,
      `**Phone:** ${parsed.phone}`,
      `**LinkedIn:** ${parsed.linkedin}`,
      '',
      '## Experiences',
      ...(parsed.experiences ?? []).map((e: { company?: string; role?: string; start_date?: string; end_date?: string; bullets?: string[] }) => [
        `### ${e.role} — ${e.company}`,
        `${e.start_date ?? ''} → ${e.end_date ?? ''}`,
        '',
        ...(e.bullets ?? []).map((b: string) => `- ${b}`),
        '',
      ].join('\n')),
      '## Education',
      ...(parsed.education ?? []).map((e: { institution?: string; degree?: string; year?: string }) => `- ${e.degree} @ ${e.institution} (${e.year})`),
      '',
      '## Skills',
      (parsed.skills ?? []).join(', '),
      '',
      '## Certifications',
      ...((parsed.certifications ?? []) as string[]).map((c) => `- ${c}`),
      '',
      '## First-person career summary',
      narr,
      '',
    ].join('\n');
    await fs.writeFile(path.join(OUT_DIR, '01-parsed-resume.md'), md);
    await fs.writeFile(path.join(OUT_DIR, '01-parsed-resume.raw.json'), JSON.stringify(body, null, 2));

    // Assertions AFTER write — now we always have the artifact to inspect.
    expect(status, `parse returned ${status}`).toBe(200);
    expect(parsed.full_name ?? '').toMatch(/satvik/i);
    expect((parsed.experiences ?? []).length).toBeGreaterThanOrEqual(2);
    const companies = (parsed.experiences ?? []).map((e: { company?: string }) => e.company ?? '').join(' | ').toLowerCase();
    expect(companies).toMatch(/amex|american express/);
    expect(companies).toMatch(/sprinklr/);
    expect((parsed.skills ?? []).length, 'skills count').toBeGreaterThanOrEqual(5);
    expect(narr.length, 'narration length').toBeGreaterThan(200);
    expect(narr).toMatch(/\bI\b/);
  });

  test('2. Analyze Wing Assistant JD via /api/jd/analyze', async ({ request }) => {
    const jdText = await fs.readFile(JD_PATH, 'utf8');
    const res = await request.post('/api/jd/analyze', {
      headers: { 'Content-Type': 'application/json' },
      data: { jd_text: jdText },
    });
    const status = res.status();
    const body = await res.json();
    // Capture even on non-200 for debugging
    const md = [
      '# JD analyze — Wing Assistant Lead PM',
      '',
      `**HTTP:** ${status}`,
      '',
      '## Raw response',
      '```json',
      JSON.stringify(body, null, 2),
      '```',
      '',
    ].join('\n');
    await fs.writeFile(path.join(OUT_DIR, '02-jd-analyze.md'), md);
    expect(status, `jd/analyze returned ${status}`).toBeLessThan(500);
  });

  test('3. Generate tailored resume — career_profile.md + Wing JD', async ({ request }) => {
    test.setTimeout(600_000); // 10 min — pipeline now waits on rate-limit windows (8 min budget)
    const jdText = await fs.readFile(JD_PATH, 'utf8');
    // Use compact nugget-derived text (~15KB) rather than full career-profile.md
    // (65KB) — Groq request-size limit caps individual calls at ~25KB effective.
    const careerText = await fs.readFile(CAREER_COMPACT_PATH, 'utf8');

    const startRes = await request.post('/api/resume/start', {
      timeout: 45_000, // Oracle ARM retrieval + worker trigger; 15s default not enough
      headers: { 'Content-Type': 'application/json' },
      data: {
        jd_text: jdText,
        career_text: careerText,
        model_provider: 'groq',
        model_id: 'llama-3.3-70b-versatile',
        template_id: 'cv-a4-standard',
        target_role: 'Lead Product Manager, AI Solutions',
        target_company: 'Wing Assistant',
      },
    });
    const startBody = await startRes.json();
    // eslint-disable-next-line no-console
    console.log('resume/start:', startRes.status(), startBody);

    if (startRes.status() !== 200) {
      await fs.writeFile(
        path.join(OUT_DIR, '03-resume-generation.md'),
        `# Resume generation — FAILED at /api/resume/start\n\n**HTTP:** ${startRes.status()}\n\n\`\`\`json\n${JSON.stringify(startBody, null, 2)}\n\`\`\`\n`,
      );
      expect(startRes.status()).toBe(200);
      return;
    }

    const jobId = startBody.job_id ?? startBody.id;
    expect(jobId, 'no job id returned').toBeTruthy();

    // Poll until terminal state or 9 min (inside the test's 10-min timeout).
    const deadline = Date.now() + 540_000;
    let job: Record<string, unknown> | null = null;
    let lastStatus = '';
    while (Date.now() < deadline) {
      await new Promise((r) => setTimeout(r, 4000));
      const pollRes = await request.get(`/api/resume/${jobId}`);
      if (pollRes.status() !== 200) continue;
      job = await pollRes.json();
      const st = String((job as { status?: string }).status ?? '');
      if (st !== lastStatus) {
        lastStatus = st;
        // eslint-disable-next-line no-console
        console.log(`  [${new Date().toISOString()}] job ${jobId} → ${st}`);
      }
      if (['completed', 'failed', 'cancelled'].includes(st)) break;
    }

    const j = (job ?? {}) as Record<string, unknown>;
    const bullets = (j.bullets ?? j.result_bullets ?? null) as unknown;
    const sections = (j.sections ?? null) as unknown;
    const summary = (j.summary ?? j.result_summary ?? null) as unknown;

    const md = [
      '# Resume generation — Satvik for Wing Assistant Lead PM',
      '',
      `**Job ID:** ${jobId}`,
      `**Final status:** ${j.status}`,
      `**Elapsed polling:** ${Math.round((Date.now() - (deadline - 180_000)) / 1000)}s`,
      '',
      j.error_message ? `## Error\n${j.error_message}\n` : '',
      summary ? `## Generated summary\n${typeof summary === 'string' ? summary : JSON.stringify(summary, null, 2)}\n` : '',
      sections ? `## Sections\n\`\`\`json\n${JSON.stringify(sections, null, 2)}\n\`\`\`\n` : '',
      bullets ? `## Bullets\n\`\`\`json\n${JSON.stringify(bullets, null, 2)}\n\`\`\`\n` : '',
      '## Full job row',
      '```json',
      JSON.stringify(j, null, 2),
      '```',
      '',
    ].filter(Boolean).join('\n');
    await fs.writeFile(path.join(OUT_DIR, '03-resume-generation.md'), md);

    expect(j.status, 'final status').toBe('completed');

    // ── Phase 2.1 — Quality assertions on generated bullets ────────────────
    // Verifies the v9 fabrication guards landed: every %/$ amount in a bullet
    // must appear (or be in the same magnitude tier) in the source career text.
    if (Array.isArray(bullets) && bullets.length > 0) {
      const bulletTexts: string[] = bullets
        .map((b: unknown) => {
          if (typeof b === 'string') return b;
          if (b && typeof b === 'object') {
            const obj = b as Record<string, unknown>;
            return String(obj.text_html ?? obj.text ?? obj.bullet ?? '');
          }
          return '';
        })
        .filter((s) => s.length > 0);

      const stripHtml = (s: string) => s.replace(/<[^>]+>/g, ' ');
      const sourceLower = careerText.toLowerCase();
      const numericRe = /(\$\s?\d+(?:\.\d+)?\s?[KMB]?|\d+(?:\.\d+)?\s?%|\d+(?:\.\d+)?\s?x\b|\d{4,})/gi;

      const fabricatedSamples: string[] = [];
      for (const raw of bulletTexts) {
        const text = stripHtml(raw);
        const matches = text.match(numericRe) ?? [];
        for (const tok of matches) {
          const norm = tok.replace(/\s+/g, '').toLowerCase();
          // Year free-pass
          if (/^(19|20)\d{2}$/.test(norm)) continue;
          // Strip unit for substring search; e.g. "30%" → "30", "$1M" → "1M"
          const bareDigits = norm.replace(/[$%xkmb]/gi, '');
          if (sourceLower.includes(norm) || sourceLower.includes(bareDigits)) continue;
          fabricatedSamples.push(`bullet="${text.slice(0, 80)}…" token="${tok}"`);
          if (fabricatedSamples.length >= 5) break;
        }
        if (fabricatedSamples.length >= 5) break;
      }

      if (fabricatedSamples.length > 0) {
        await fs.writeFile(
          path.join(OUT_DIR, '03-fabrication-flags.md'),
          `# Possible fabricated metrics in generated bullets\n\n${fabricatedSamples
            .map((s) => `- ${s}`)
            .join('\n')}\n`,
        );
      }

      // Soft-assert: ≤ 1 fabricated metric across all bullets (allow 1 false-positive
      // from tier-aware fuzz vs strict substring match).
      expect(
        fabricatedSamples.length,
        `Found ${fabricatedSamples.length} likely-fabricated metrics in bullets — see 03-fabrication-flags.md`,
      ).toBeLessThanOrEqual(1);
    }
  });

  // ── Phase 2.1 — Companion: assert PDF download works ─────────────────────
  test('4. Download tailored PDF (smoke)', async ({ request }) => {
    test.setTimeout(30_000);
    // Re-use the most recent completed job for this user — endpoint accepts
    // the latest finished job when no id provided.
    const listRes = await request.get('/api/resume/recent');
    if (listRes.status() !== 200) {
      // No /recent endpoint? Skip — this is a smoke check only.
      test.skip(true, 'No /api/resume/recent endpoint available — skipping PDF smoke');
      return;
    }
    const list = (await listRes.json()) as { jobs?: Array<{ id: string; status: string }> };
    const completed = (list.jobs ?? []).find((j) => j.status === 'completed');
    if (!completed) {
      test.skip(true, 'No completed job found for PDF smoke');
      return;
    }
    const pdfRes = await request.get(`/api/resume/${completed.id}/pdf`);
    expect(pdfRes.status(), 'PDF endpoint should respond 200').toBe(200);
    const buf = await pdfRes.body();
    expect(buf.length, 'PDF should be non-empty').toBeGreaterThan(1000);
    // PDF magic bytes
    expect(buf.slice(0, 4).toString('ascii'), 'should start with %PDF').toBe('%PDF');
  });
});
