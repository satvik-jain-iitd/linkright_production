// ==UserScript==
// @name         LinkRight Naukri Capture
// @namespace    https://linkright.in/
// @version      0.1.0
// @description  Passively capture Naukri job pages → LinkRight Oracle PG (Sprint C Phase 1)
// @author       Satvik Jain
// @match        https://www.naukri.com/job-listings-*
// @match        https://m.naukri.com/job-listings-*
// @match        https://www.naukri.com/jobs/*
// @grant        GM_xmlhttpRequest
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_registerMenuCommand
// @grant        GM_notification
// @connect      sync-resume-engine.onrender.com
// @run-at       document-idle
// @noframes
// ==/UserScript==

(function () {
    'use strict';

    // ── Config (stored via Tampermonkey GM_setValue) ────────────────────────
    const DEFAULT_ENDPOINT = 'https://sync-resume-engine.onrender.com/api/captures';

    function cfg(key, fallback) { return GM_getValue(key, fallback); }
    function setCfg(key, value) { GM_setValue(key, value); }

    // ── Tampermonkey menu commands (always available, even when disabled) ──
    GM_registerMenuCommand('LinkRight: Set capture key', () => {
        const current = cfg('CAPTURE_KEY', '');
        const next = prompt('Enter LINKRIGHT_CAPTURE_KEY (find it in ~/.linkright/.env):', current);
        if (next !== null) {
            setCfg('CAPTURE_KEY', next.trim());
            alert('LinkRight: capture key saved (length=' + next.trim().length + ')');
        }
    });
    GM_registerMenuCommand('LinkRight: Set endpoint URL (advanced)', () => {
        const current = cfg('CAPTURE_ENDPOINT', DEFAULT_ENDPOINT);
        const next = prompt('Capture endpoint URL:', current);
        if (next !== null) setCfg('CAPTURE_ENDPOINT', next.trim() || DEFAULT_ENDPOINT);
    });
    GM_registerMenuCommand('LinkRight: Toggle capture ON/OFF', () => {
        const next = !cfg('ENABLED', true);
        setCfg('ENABLED', next);
        alert('LinkRight Naukri capture: ' + (next ? 'ENABLED' : 'DISABLED'));
    });
    GM_registerMenuCommand('LinkRight: Toggle debug logging', () => {
        const next = !cfg('DEBUG', false);
        setCfg('DEBUG', next);
        alert('LinkRight debug logging: ' + (next ? 'ON (check DevTools console)' : 'OFF'));
    });
    GM_registerMenuCommand('LinkRight: Toggle desktop notifications', () => {
        const next = !cfg('NOTIFY', false);
        setCfg('NOTIFY', next);
        alert('LinkRight notifications: ' + (next ? 'ON' : 'OFF'));
    });

    // ── Bail early if disabled or no key ────────────────────────────────────
    if (!cfg('ENABLED', true)) return;
    const KEY = cfg('CAPTURE_KEY', '');
    if (!KEY) {
        console.warn('[LinkRight] No capture key set. Tampermonkey menu → "LinkRight: Set capture key".');
        return;
    }

    function debug(...args) { if (cfg('DEBUG', false)) console.log('[LinkRight]', ...args); }

    // ── Privacy filter (mirrors server-side — fail-closed at the source) ────
    const BLOCKED_PATHS = [
        /^\/messages?(?:\/|$)/, /^\/notifications?/, /^\/connections?/,
        /^\/inbox/, /^\/profile/, /^\/myaccount/, /^\/m\/profile/,
        /^\/recruit/, /^\/m\/jobseeker\/profile/,
    ];
    function isBlockedPath(path) { return BLOCKED_PATHS.some(re => re.test(path)); }

    if (isBlockedPath(window.location.pathname)) {
        debug('Path blocked, not capturing:', window.location.pathname);
        return;
    }

    // ── Extraction: prefer JSON-LD JobPosting, fall back to DOM scraping ───
    function extractFromJsonLd() {
        const scripts = document.querySelectorAll('script[type="application/ld+json"]');
        for (const script of scripts) {
            try {
                const data = JSON.parse(script.textContent || '{}');
                const items = Array.isArray(data) ? data : [data];
                for (const item of items) {
                    if (item && item['@type'] === 'JobPosting') return item;
                }
            } catch (_) { /* malformed JSON-LD — skip */ }
        }
        return null;
    }

    function pick(...selectors) {
        for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el && el.textContent && el.textContent.trim()) return el.textContent.trim();
        }
        return null;
    }

    function extractFromDom() {
        // Selectors target Naukri's 2026 layout. If Naukri refactors, these
        // can be updated without changing the rest of the script.
        return {
            title: pick(
                'h1.styles_jd-header-title__rZwM1',
                'h1[class*="jd-header-title"]',
                'header h1',
                'h1'
            ),
            company: pick(
                'div.styles_jd-header-comp-name__MvqAI a',
                'div[class*="jd-header-comp-name"] a',
                'a[href*="/company-jobs"]',
                'a[itemprop="name"]'
            ),
            location: pick(
                'span.styles_jhc__location__W_pVs',
                'span[class*="jhc__location"]',
                'span[class*="location"]',
                'div[class*="job-location"]'
            ),
            salary: pick(
                'span.styles_jhc__salary__GVHmg',
                'span[class*="jhc__salary"]',
                'div[class*="salary"]'
            ),
            jd_text: pick(
                'section.styles_JDC__dang-inner-html__h0K4t',
                'section[class*="JDC__dang-inner-html"]',
                'div[class*="job-description"]',
                'article'
            ),
        };
    }

    function stripHtml(html) {
        if (!html) return '';
        const div = document.createElement('div');
        div.innerHTML = html;
        return (div.textContent || '').trim();
    }

    function extractExternalId(pathname) {
        // Naukri job URLs end with `-<jid>` (numeric job id), sometimes followed
        // by a query string. Pull the last numeric run.
        const m = pathname.match(/-(\d+)(?:[/?]|$)/);
        return m ? m[1] : null;
    }

    function buildPayload() {
        const jl = extractFromJsonLd();
        const dom = extractFromDom();

        const title = (jl && jl.title) || dom.title;
        const companyName = (jl && jl.hiringOrganization && jl.hiringOrganization.name) || dom.company;
        const companyWebsite = (jl && jl.hiringOrganization && jl.hiringOrganization.sameAs) || null;
        const location = (jl && jl.jobLocation && jl.jobLocation.address && jl.jobLocation.address.addressLocality) || dom.location;
        const salary = (jl && jl.baseSalary && jl.baseSalary.value && (jl.baseSalary.value.value || jl.baseSalary.value.minValue)) || dom.salary;
        const jdText = jl && jl.description ? stripHtml(jl.description) : dom.jd_text;
        const postedAt = (jl && jl.datePosted) || null;

        if (!title || !companyName) {
            debug('Insufficient data (no title or company), skipping capture.');
            return null;
        }

        return {
            source: 'naukri',
            // Strip query string — `?src=jobsearchDesk`-type params shouldn't poison dedup
            job_url: window.location.origin + window.location.pathname,
            external_id: extractExternalId(window.location.pathname),
            title: String(title).trim(),
            company_name: String(companyName).trim(),
            company_website: companyWebsite,
            location: location ? String(location).trim() : null,
            salary_text: salary ? String(salary).trim() : null,
            jd_text: jdText ? String(jdText).slice(0, 50000) : null,
            posted_at: postedAt,
            captured_at: new Date().toISOString(),
            raw_payload: {
                source_extractor: jl ? 'jsonld' : 'dom',
                jsonld_present: Boolean(jl),
                dom_keys_filled: Object.keys(dom).filter(k => dom[k]),
            },
        };
    }

    // ── POST to /api/captures (cross-origin → must use GM_xmlhttpRequest) ──
    function send(payload) {
        const endpoint = cfg('CAPTURE_ENDPOINT', DEFAULT_ENDPOINT);
        debug('POST', endpoint, payload);

        GM_xmlhttpRequest({
            method: 'POST',
            url: endpoint,
            headers: {
                'Content-Type': 'application/json',
                'X-LinkRight-Capture-Key': KEY,
            },
            data: JSON.stringify(payload),
            timeout: 15000,
            onload: (resp) => {
                if (resp.status === 201) {
                    let data = {};
                    try { data = JSON.parse(resp.responseText); } catch (_) {}
                    debug('OK', data);
                    if (cfg('NOTIFY', false)) {
                        GM_notification({
                            title: 'LinkRight: captured',
                            text: payload.title + ' @ ' + payload.company_name +
                                  ' (' + (data.dedup_status || '?') + ')',
                            silent: true,
                            timeout: 3000,
                        });
                    }
                } else {
                    console.warn('[LinkRight] capture HTTP', resp.status, resp.responseText);
                }
            },
            onerror: (err) => console.warn('[LinkRight] network error', err),
            ontimeout: () => console.warn('[LinkRight] capture timeout (>15s)'),
        });
    }

    // ── Capture trigger: wait for SPA-style late renders to settle ─────────
    let captureTimer = null;
    function scheduleCapture(reason) {
        if (captureTimer) clearTimeout(captureTimer);
        captureTimer = setTimeout(() => {
            captureTimer = null;
            const payload = buildPayload();
            if (payload) send(payload);
            else debug('No capture sent (' + reason + ')');
        }, 2000);  // 2s settle delay covers JD-text loaded via XHR after first paint
    }

    // Initial page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => scheduleCapture('initial-DCL'));
    } else {
        scheduleCapture('initial-already-loaded');
    }

    // SPA navigation detection (Naukri uses pushState between job pages)
    let lastUrl = window.location.href;
    new MutationObserver(() => {
        const cur = window.location.href;
        if (cur !== lastUrl) {
            lastUrl = cur;
            if (!isBlockedPath(window.location.pathname)) {
                scheduleCapture('SPA-nav');
            }
        }
    }).observe(document, { subtree: true, childList: true });

    debug('LinkRight Naukri capture v0.1.0 initialized for', window.location.href);
})();
