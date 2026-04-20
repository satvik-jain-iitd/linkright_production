import { test, expect } from '@playwright/test';
import { RESUME_TEXT_HIGH } from './fixtures/test-data';
import fs from 'fs/promises';
import path from 'path';

// Walks the full signup → onboarding → profile → prefs → find → customize
// journey and dumps a bug report to test-results/journey-report/issues.md.
//
// Each step screenshots + inspects for common failure signatures (500s,
// empty states where content was expected, broken links, missing CTAs).

const REPORT_DIR = 'test-results/journey-report';

type Bug = {
  step: string;
  severity: 'blocker' | 'major' | 'minor';
  what: string;
  where: string;
};

const bugs: Bug[] = [];
function bug(b: Bug) {
  bugs.push(b);
  console.log(`[BUG · ${b.severity}] ${b.step}: ${b.what} (${b.where})`);
}

test.describe.configure({ mode: 'serial' });

test.describe('full journey smoke — signup through customize', () => {
  test.beforeAll(async () => {
    await fs.mkdir(REPORT_DIR, { recursive: true });
  });

  test.afterAll(async () => {
    const md = [
      `# Journey smoke — bug report`,
      `Run: ${new Date().toISOString()}`,
      `Base: ${process.env.PLAYWRIGHT_BASE_URL || 'default'}`,
      ``,
      `**${bugs.length} issues found**`,
      ``,
      ...bugs.map(
        (b) => `- [${b.severity.toUpperCase()}] **${b.step}** — ${b.what} · \`${b.where}\``,
      ),
    ].join('\n');
    await fs.writeFile(path.join(REPORT_DIR, 'issues.md'), md);
    console.log(`\nReport saved to ${REPORT_DIR}/issues.md`);
  });

  test.use({ storageState: 'playwright/.auth/user.json' });

  // ─── Step 1: Landing ─────────────────────────────────────────────────
  test('step 1 — landing page sanity', async ({ page }) => {
    const response = await page.goto('/');
    expect(response?.status()).toBeLessThan(400);

    const h1 = await page.getByRole('heading', { level: 1 }).first().textContent();
    if (!h1?.includes('sharper')) {
      bug({
        step: 'Landing',
        severity: 'major',
        what: `H1 missing expected copy. Got: "${h1}"`,
        where: '/',
      });
    }

    // CTA present
    const cta = page.getByRole('link', { name: /start for free/i }).first();
    if (!(await cta.isVisible().catch(() => false))) {
      bug({
        step: 'Landing',
        severity: 'blocker',
        what: 'Primary CTA "Start for free" not visible',
        where: '/',
      });
    }

    await page.screenshot({ path: path.join(REPORT_DIR, '01-landing.png'), fullPage: true });
  });

  // ─── Step 2: Pricing ─────────────────────────────────────────────────
  test('step 2 — pricing page', async ({ page }) => {
    await page.goto('/pricing');
    const h1 = await page.getByRole('heading', { level: 1 }).first().textContent();
    if (!h1?.toLowerCase().includes('start free')) {
      bug({
        step: 'Pricing',
        severity: 'minor',
        what: `Pricing H1 unexpected: "${h1}"`,
        where: '/pricing',
      });
    }
    await page.screenshot({ path: path.join(REPORT_DIR, '02-pricing.png'), fullPage: true });
  });

  // ─── Step 3: Onboarding upload + parse ───────────────────────────────
  test('step 3 — onboarding: paste resume and parse', async ({ page }) => {
    const response = await page.goto('/onboarding');
    expect(response?.status()).toBeLessThan(500);

    // Find the paste-text option. UI has a "Paste text" tab/button.
    const pasteBtn = page
      .getByRole('button', { name: /paste.*text|paste.*resume/i })
      .first();

    if (await pasteBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await pasteBtn.click();
    } else {
      bug({
        step: 'Onboarding upload',
        severity: 'major',
        what: 'Paste-text mode not discoverable from UI',
        where: '/onboarding',
      });
    }

    // Find a textarea for resume paste
    const textarea = page.locator('textarea').first();
    if (!(await textarea.isVisible({ timeout: 5000 }).catch(() => false))) {
      bug({
        step: 'Onboarding upload',
        severity: 'blocker',
        what: 'No textarea visible for resume paste',
        where: '/onboarding',
      });
      await page.screenshot({
        path: path.join(REPORT_DIR, '03-onboarding-no-textarea.png'),
        fullPage: true,
      });
      return;
    }

    await textarea.fill(RESUME_TEXT_HIGH);

    // Find the parse button
    const parseBtn = page
      .getByRole('button', {
        name: /auto-fill|parse|extract|fill from resume/i,
      })
      .first();
    if (!(await parseBtn.isVisible().catch(() => false))) {
      bug({
        step: 'Onboarding upload',
        severity: 'blocker',
        what: 'Parse/Auto-fill button not found',
        where: '/onboarding',
      });
      return;
    }

    await parseBtn.click();

    // Wait for outline to render — CareerOutlineView shows "Here's what we understood"
    const outlineAppeared = await page
      .getByText(/here.s what we understood|outline|your story/i)
      .first()
      .isVisible({ timeout: 60000 })
      .catch(() => false);

    if (!outlineAppeared) {
      bug({
        step: 'Onboarding outline',
        severity: 'blocker',
        what: 'Outline did not render within 60s after parse',
        where: '/onboarding',
      });
    }

    await page.screenshot({
      path: path.join(REPORT_DIR, '03-onboarding-parsed.png'),
      fullPage: true,
    });

    // Check outline has real data (company names from fixture)
    const amexVisible = await page
      .getByText(/amex|american express/i)
      .first()
      .isVisible({ timeout: 5000 })
      .catch(() => false);
    if (!amexVisible) {
      bug({
        step: 'Onboarding outline',
        severity: 'major',
        what: 'Company from fixture (Amex) not visible in outline',
        where: '/onboarding',
      });
    }

    // Narration block should be visible
    const narrationVisible = await page
      .getByText(/your story|first-person|narration|in your words/i)
      .first()
      .isVisible({ timeout: 3000 })
      .catch(() => false);
    if (!narrationVisible) {
      bug({
        step: 'Onboarding outline',
        severity: 'major',
        what: 'First-person narration panel not visible',
        where: '/onboarding',
      });
    }
  });

  // ─── Step 4: Profile highlights ──────────────────────────────────────
  test('step 4 — profile highlights page', async ({ page }) => {
    const resp = await page.goto('/onboarding/profile');
    expect(resp?.status()).toBeLessThan(500);
    await page.waitForLoadState('networkidle');

    // Cards should render — count them
    const cards = page.locator(
      'button:has(span.rounded-full)',
    );
    const cardCount = await cards.count().catch(() => 0);
    if (cardCount < 3) {
      bug({
        step: 'Profile highlights',
        severity: 'major',
        what: `Expected ≥3 highlight cards, found ${cardCount}`,
        where: '/onboarding/profile',
      });
    }

    // Add Highlight button should exist
    const addBtn = page
      .getByRole('button', { name: /add highlight/i })
      .first();
    if (!(await addBtn.isVisible().catch(() => false))) {
      bug({
        step: 'Profile highlights',
        severity: 'major',
        what: 'Add highlight button missing',
        where: '/onboarding/profile',
      });
    }

    // Continue CTA
    const continueBtn = page
      .getByRole('button', { name: /continue to find jobs/i })
      .first();
    if (!(await continueBtn.isVisible().catch(() => false))) {
      bug({
        step: 'Profile highlights',
        severity: 'blocker',
        what: 'Continue to find jobs CTA missing',
        where: '/onboarding/profile',
      });
    }

    await page.screenshot({
      path: path.join(REPORT_DIR, '04-profile-highlights.png'),
      fullPage: true,
    });
  });

  // ─── Step 5: Preferences ────────────────────────────────────────────
  test('step 5 — preferences page', async ({ page }) => {
    const resp = await page.goto('/onboarding/preferences');
    expect(resp?.status()).toBeLessThan(500);
    await page.waitForLoadState('networkidle');

    // Target roles field should exist
    const rolesInput = page
      .getByPlaceholder(/product manager|roles|target/i)
      .first();
    if (!(await rolesInput.isVisible().catch(() => false))) {
      bug({
        step: 'Preferences',
        severity: 'major',
        what: 'Target roles input not found',
        where: '/onboarding/preferences',
      });
    }

    // Work auth should NOT be present (v2 removal)
    const workAuthLabel = await page
      .getByText(/work authori[sz]ation/i)
      .first()
      .isVisible({ timeout: 1500 })
      .catch(() => false);
    if (workAuthLabel) {
      bug({
        step: 'Preferences',
        severity: 'minor',
        what: 'Work authorisation field still present (should be removed)',
        where: '/onboarding/preferences',
      });
    }

    await page.screenshot({
      path: path.join(REPORT_DIR, '05-preferences.png'),
      fullPage: true,
    });
  });

  // ─── Step 6: Find roles ──────────────────────────────────────────────
  test('step 6 — find roles page', async ({ page }) => {
    const resp = await page.goto('/onboarding/find');
    expect(resp?.status()).toBeLessThan(500);
    await page.waitForLoadState('networkidle');

    // Must show either ranked jobs OR a graceful empty state
    const hasJobs = await page
      .getByText(/match|top pick|best-fit|start custom application/i)
      .first()
      .isVisible({ timeout: 5000 })
      .catch(() => false);
    const hasEmpty = await page
      .getByText(/nothing matched|no matches|scout.*catching up/i)
      .first()
      .isVisible({ timeout: 5000 })
      .catch(() => false);

    if (!hasJobs && !hasEmpty) {
      bug({
        step: 'Find roles',
        severity: 'major',
        what: 'Page shows neither job list nor empty state',
        where: '/onboarding/find',
      });
    }

    await page.screenshot({
      path: path.join(REPORT_DIR, '06-find-roles.png'),
      fullPage: true,
    });
  });

  // ─── Step 7: Dashboard ───────────────────────────────────────────────
  test('step 7 — dashboard', async ({ page }) => {
    const resp = await page.goto('/dashboard');
    expect(resp?.status()).toBeLessThan(500);
    await page.waitForLoadState('networkidle');

    // Either dashboard or redirect to /onboarding
    const url = page.url();
    if (!url.includes('/dashboard') && !url.includes('/onboarding')) {
      bug({
        step: 'Dashboard',
        severity: 'major',
        what: `Dashboard redirected to unexpected URL: ${url}`,
        where: '/dashboard',
      });
    }

    // Notifications bell
    const bell = page.locator('button[aria-label="Open notifications"]');
    if (!(await bell.isVisible({ timeout: 3000 }).catch(() => false))) {
      bug({
        step: 'Dashboard',
        severity: 'minor',
        what: 'Notifications bell not visible in nav',
        where: '/dashboard',
      });
    }

    await page.screenshot({
      path: path.join(REPORT_DIR, '07-dashboard.png'),
      fullPage: true,
    });
  });

  // ─── Step 8: Profile settings ────────────────────────────────────────
  test('step 8 — dashboard profile settings', async ({ page }) => {
    const resp = await page.goto('/dashboard/profile');
    expect(resp?.status()).toBeLessThan(500);
    await page.waitForLoadState('networkidle');

    // Bulk upload present
    const bulkUpload = await page
      .getByText(/bulk upload a career file/i)
      .isVisible({ timeout: 3000 })
      .catch(() => false);
    if (!bulkUpload) {
      bug({
        step: 'Profile settings',
        severity: 'major',
        what: 'Bulk upload section missing',
        where: '/dashboard/profile',
      });
    }

    // Session token must NOT be present
    const sessionTokenVisible = await page
      .getByRole('heading', { name: /session token/i })
      .isVisible({ timeout: 1500 })
      .catch(() => false);
    if (sessionTokenVisible) {
      bug({
        step: 'Profile settings',
        severity: 'minor',
        what: 'Deprecated session token UI still showing',
        where: '/dashboard/profile',
      });
    }

    // LinkedIn connection row
    const linkedinRow = await page
      .getByText(/^LinkedIn$/)
      .isVisible({ timeout: 2000 })
      .catch(() => false);
    if (!linkedinRow) {
      bug({
        step: 'Profile settings',
        severity: 'minor',
        what: 'LinkedIn connection row not visible',
        where: '/dashboard/profile',
      });
    }

    await page.screenshot({
      path: path.join(REPORT_DIR, '08-profile-settings.png'),
      fullPage: true,
    });
  });

  // ─── Step 9: Broadcast connect ───────────────────────────────────────
  test('step 9 — broadcast connect', async ({ page }) => {
    const resp = await page.goto('/dashboard/broadcast/connect');
    expect(resp?.status()).toBeLessThan(500);
    await page.waitForLoadState('networkidle');

    const connectBtn = await page
      .getByRole('link', { name: /connect linkedin/i })
      .first()
      .isVisible({ timeout: 3000 })
      .catch(() => false);
    const connectDisabled = await page
      .getByText(/coming soon/i)
      .first()
      .isVisible({ timeout: 3000 })
      .catch(() => false);
    if (!connectBtn && !connectDisabled) {
      bug({
        step: 'Broadcast connect',
        severity: 'major',
        what: 'Neither Connect LinkedIn CTA nor coming-soon state visible',
        where: '/dashboard/broadcast/connect',
      });
    }

    await page.screenshot({
      path: path.join(REPORT_DIR, '09-broadcast-connect.png'),
      fullPage: true,
    });
  });

  // ─── Step 10: Applications kanban ───────────────────────────────────
  test('step 10 — applications kanban', async ({ page }) => {
    const resp = await page.goto('/dashboard/applications');
    expect(resp?.status()).toBeLessThan(500);
    await page.waitForLoadState('networkidle');

    // All 6 columns
    for (const col of ['Wishlist', 'Drafting', 'Applied', 'Interview', 'Offer', 'Closed']) {
      const visible = await page
        .getByText(new RegExp(`^${col}$`, 'i'))
        .first()
        .isVisible({ timeout: 2000 })
        .catch(() => false);
      if (!visible) {
        bug({
          step: 'Applications kanban',
          severity: 'minor',
          what: `Kanban column "${col}" missing`,
          where: '/dashboard/applications',
        });
      }
    }

    await page.screenshot({
      path: path.join(REPORT_DIR, '10-applications.png'),
      fullPage: true,
    });
  });

  // ─── Step 11: Interview prep hub ────────────────────────────────────
  test('step 11 — interview prep hub', async ({ page }) => {
    const resp = await page.goto('/dashboard/interview-prep');
    expect(resp?.status()).toBeLessThan(500);
    await page.waitForLoadState('networkidle');

    const drillCount = await page.getByText(/product sense|behavioural|case|sql/i).count();
    if (drillCount < 4) {
      bug({
        step: 'Interview prep',
        severity: 'minor',
        what: `Expected ≥4 drill cards, found ${drillCount}`,
        where: '/dashboard/interview-prep',
      });
    }

    await page.screenshot({
      path: path.join(REPORT_DIR, '11-interview-prep.png'),
      fullPage: true,
    });
  });

  // ─── Step 12: Highlights CRUD via UI ─────────────────────────────────
  test('step 12 — add highlight flow works end-to-end', async ({ page }) => {
    await page.goto('/onboarding/profile');
    await page.waitForLoadState('networkidle');

    const addBtn = page.getByRole('button', { name: /add highlight/i }).first();
    if (!(await addBtn.isVisible({ timeout: 3000 }).catch(() => false))) {
      bug({
        step: 'Highlight CRUD',
        severity: 'major',
        what: 'Add highlight button missing (cannot test create flow)',
        where: '/onboarding/profile',
      });
      return;
    }
    await addBtn.click();

    // Modal should open with title + body inputs
    const titleInput = page.getByPlaceholder(/e\.g\. led|title|one-line/i).first();
    if (!(await titleInput.isVisible({ timeout: 3000 }).catch(() => false))) {
      bug({
        step: 'Highlight CRUD',
        severity: 'blocker',
        what: 'Highlight editor modal did not open',
        where: '/onboarding/profile',
      });
      return;
    }

    await titleInput.fill('Journey-smoke test highlight');
    const bodyInput = page.getByPlaceholder(/problem.*what you did|a few sentences|specifics/i).first();
    await bodyInput.fill(
      'Automated end-to-end journey smoke test that verifies the add-highlight flow works.',
    );

    const saveBtn = page.getByRole('button', { name: /add highlight|save changes/i }).first();
    await saveBtn.click();

    // Modal closes + new card appears
    const closed = await titleInput
      .waitFor({ state: 'detached', timeout: 8000 })
      .then(() => true)
      .catch(() => false);
    if (!closed) {
      bug({
        step: 'Highlight CRUD',
        severity: 'major',
        what: 'Modal did not close after save',
        where: '/onboarding/profile',
      });
    }

    await page.screenshot({
      path: path.join(REPORT_DIR, '12-add-highlight.png'),
      fullPage: true,
    });
  });
});
