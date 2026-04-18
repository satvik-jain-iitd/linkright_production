// LinkRight Extension — Content Script
// Runs on supported job pages. Detects job context, shows floating overlay.
// No build step: plain ES2022 + Shadow DOM for style isolation.

(function () {
  "use strict";

  // -------- Detect which ATS we're on --------
  const detectors = {
    linkedin: () => {
      if (!/linkedin\.com\/jobs\/view\//.test(location.href)) return null;
      const title = document.querySelector("h1")?.innerText?.trim();
      const company = document.querySelector('a[href*="/company/"]')?.innerText?.trim();
      const jd = document.querySelector(".jobs-description__content, .jobs-box__html-content")?.innerText?.trim();
      if (!title) return null;
      return { source: "linkedin", title, company: company ?? "", jd: jd ?? "", url: location.href };
    },
    greenhouse: () => {
      if (!/greenhouse\.io\/[^/]+\/jobs\//.test(location.href)) return null;
      const title = document.querySelector(".app-title, h1")?.innerText?.trim();
      const company = document.querySelector(".company-name, .app-company")?.innerText?.trim();
      const jd = document.querySelector("#content, .content")?.innerText?.trim();
      if (!title) return null;
      return { source: "greenhouse", title, company: company ?? "", jd: jd ?? "", url: location.href };
    },
    lever: () => {
      if (!/jobs\.lever\.co\//.test(location.href)) return null;
      const title = document.querySelector(".posting-headline h2, h1")?.innerText?.trim();
      const company = document.querySelector(".main-header-logo img")?.getAttribute("alt")?.trim();
      const jd = document.querySelector(".posting-page .section-wrapper, .section-wrapper")?.innerText?.trim();
      if (!title) return null;
      return { source: "lever", title, company: company ?? "", jd: jd ?? "", url: location.href };
    },
    ashby: () => {
      if (!/ashbyhq\.com/.test(location.href)) return null;
      const title = document.querySelector("h1")?.innerText?.trim();
      const jd = document.querySelector("article, [role=main]")?.innerText?.trim();
      if (!title) return null;
      return { source: "ashby", title, company: "", jd: jd ?? "", url: location.href };
    },
    amazon: () => {
      if (!/amazon\.jobs\/(en\/)?jobs\//.test(location.href)) return null;
      const title = document.querySelector("h1")?.innerText?.trim();
      const jd = document.querySelector("main, #job-content")?.innerText?.trim();
      if (!title) return null;
      return { source: "amazon", title, company: "Amazon", jd: jd ?? "", url: location.href };
    },
    workable: () => {
      if (!/workable\.com\/[^/]+\/jobs\//.test(location.href)) return null;
      const title = document.querySelector("h1")?.innerText?.trim();
      const jd = document.querySelector(".main, [data-ui='job-description']")?.innerText?.trim();
      if (!title) return null;
      return { source: "workable", title, company: "", jd: jd ?? "", url: location.href };
    },
    workday: () => {
      if (!/myworkdayjobs\.com/.test(location.href)) return null;
      const title = document.querySelector("h2, h1")?.innerText?.trim();
      const jd = document.querySelector("[data-automation-id='jobPostingDescription']")?.innerText?.trim();
      if (!title) return null;
      return { source: "workday", title, company: "", jd: jd ?? "", url: location.href };
    },
  };

  function detectJob() {
    for (const d of Object.values(detectors)) {
      const ctx = d();
      if (ctx) return ctx;
    }
    return null;
  }

  // -------- Message helper --------
  function sendBg(msg) {
    return new Promise((resolve) => chrome.runtime.sendMessage(msg, resolve));
  }

  // -------- Overlay UI (Shadow DOM for isolation) --------
  function createOverlay() {
    const host = document.createElement("div");
    host.id = "linkright-ext-root";
    host.style.all = "initial";
    host.style.position = "fixed";
    host.style.top = "64px";
    host.style.right = "16px";
    host.style.zIndex = "2147483600"; // above almost everything
    host.style.fontFamily = "Inter, -apple-system, Segoe UI, Roboto, sans-serif";
    const shadow = host.attachShadow({ mode: "open" });

    shadow.innerHTML = `
      <style>
        :host { all: initial; }
        .card {
          width: 320px;
          background: #FFFFFF;
          border: 1px solid #E2E8F0;
          border-radius: 16px;
          box-shadow: 0 12px 32px rgba(15,23,42,0.08);
          padding: 16px;
          color: #1A202C;
          font-family: Inter, -apple-system, Segoe UI, Roboto, sans-serif;
        }
        .collapsed {
          width: 44px; height: 44px; padding: 0; display: flex; align-items: center; justify-content: center;
          background: #0FBEAF; border-radius: 9999px; cursor: pointer; color: white; font-weight: 700;
          border: none; box-shadow: 0 8px 24px rgba(15,190,175,0.30);
        }
        h3 { margin: 0 0 8px; font-size: 15px; font-weight: 600; letter-spacing: -0.01em; }
        .brand { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
        .logo { font-weight: 700; font-size: 14px; letter-spacing: -0.02em; }
        .logo span { color: #0FBEAF; }
        .muted { color: #718096; font-size: 12px; line-height: 1.5; }
        .row { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
        .btn {
          display: inline-flex; align-items: center; justify-content: center; gap: 6px;
          width: 100%; padding: 10px 14px; border-radius: 9999px; font-size: 13px; font-weight: 600;
          border: 1px solid transparent; cursor: pointer; transition: background 0.15s;
        }
        .btn-primary { background: #FF5733; color: white; box-shadow: 0 8px 24px rgba(255,87,51,0.20); }
        .btn-primary:hover { background: #E04425; }
        .btn-secondary { background: transparent; color: #1A202C; border-color: #E2E8F0; }
        .btn-secondary:hover { border-color: #0FBEAF; color: #0FBEAF; }
        .score { font-size: 28px; font-weight: 700; color: #0FBEAF; letter-spacing: -0.02em; }
        .pill { display: inline-block; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 500; }
        .pill-teal { background: rgba(15,190,175,0.10); color: #0C9A8E; }
        .pill-gold { background: rgba(229,184,11,0.10); color: #9A7A07; }
        .pill-pink { background: rgba(240,90,121,0.10); color: #B13355; }
        .section { margin-top: 12px; padding-top: 12px; border-top: 1px solid #E2E8F0; }
        .close { background: none; border: none; color: #718096; cursor: pointer; font-size: 18px; line-height: 1; padding: 0; }
        .state-analyzing { display: flex; flex-direction: column; align-items: center; padding: 24px 8px; gap: 12px; }
        .spinner { width: 28px; height: 28px; border: 3px solid rgba(15,190,175,0.25); border-top-color: #0FBEAF; border-radius: 50%; animation: spin 0.9s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
      </style>
      <div class="card" id="lrCard">
        <div class="brand">
          <span class="logo">Link<span>Right</span></span>
          <span class="muted" style="margin-left:auto;">Apply with memory</span>
          <button class="close" id="lrClose" aria-label="Close">×</button>
        </div>
        <div id="lrBody"></div>
      </div>
    `;

    document.documentElement.appendChild(host);
    return { host, shadow };
  }

  function renderBody(shadow, state, data = {}) {
    const body = shadow.getElementById("lrBody");
    if (!body) return;

    if (state === "not-connected") {
      body.innerHTML = `
        <h3>Connect to LinkRight</h3>
        <p class="muted">Sign in to generate your apply-pack (resume + cover letter + LinkedIn DM + recruiter email) in one click.</p>
        <button class="btn btn-primary" id="lrConnect" style="margin-top:12px;">Connect account</button>
      `;
      shadow.getElementById("lrConnect")?.addEventListener("click", () => sendBg({ type: "lr:connect" }));
      return;
    }

    if (state === "analyzing") {
      body.innerHTML = `
        <div class="state-analyzing">
          <div class="spinner"></div>
          <div style="text-align:center;">
            <div style="font-weight:600; margin-bottom:4px;">Analyzing ${escapeHtml(data.company || "this role")}…</div>
            <div class="muted">Takes 5-10 seconds. You can keep browsing — we'll save the result.</div>
          </div>
        </div>
      `;
      return;
    }

    if (state === "ready") {
      const match = data.match_score ?? 0;
      const gaps = data.gaps?.length ?? 0;
      const atomsUsed = data.atoms_used ?? 0;
      const atomsTotal = data.atoms_total ?? 0;
      body.innerHTML = `
        <h3>${escapeHtml(data.title || "This role")}</h3>
        <div class="muted">${escapeHtml(data.company || "")}</div>
        <div class="row" style="margin-top:12px;">
          <div>
            <div class="score">${match}%</div>
            <div class="muted" style="font-size:11px;">Match score</div>
          </div>
          <div style="text-align:right;">
            <span class="pill ${gaps === 0 ? "pill-teal" : "pill-gold"}">${gaps} gap${gaps === 1 ? "" : "s"}</span>
          </div>
        </div>
        ${atomsTotal > 0 ? `
          <div class="muted" style="margin-top:8px;">
            Draws from ${atomsUsed} of your ${atomsTotal} memory atoms.
          </div>
        ` : ""}
        <button class="btn btn-primary" id="lrApply" style="margin-top:14px;">⚡ Generate apply-pack</button>
        ${data.insiders?.length ? `
          <div class="section">
            <div class="muted" style="margin-bottom:8px;">👥 ${data.insiders.length} insider${data.insiders.length === 1 ? "" : "s"} at ${escapeHtml(data.company || "this company")}</div>
            <button class="btn btn-secondary" id="lrInsiders">Request warm intro →</button>
          </div>
        ` : ""}
      `;
      shadow.getElementById("lrApply")?.addEventListener("click", () => {
        renderBody(shadow, "generating");
        sendBg({ type: "lr:api", path: `/api/extension/apply-pack?job_id=${encodeURIComponent(data.job_id ?? "")}`, init: { method: "POST" } })
          .then((r) => {
            if (r?.ok && r.body) renderBody(shadow, "apply-pack-ready", r.body);
            else renderBody(shadow, "error", { msg: r?.error ?? "Failed to generate" });
          });
      });
      return;
    }

    if (state === "generating") {
      body.innerHTML = `
        <div class="state-analyzing">
          <div class="spinner"></div>
          <div style="text-align:center;">
            <div style="font-weight:600; margin-bottom:4px;">Building your apply-pack…</div>
            <div class="muted">Resume + cover letter + LinkedIn DM + recruiter email. ~60 seconds.</div>
          </div>
        </div>
      `;
      return;
    }

    if (state === "apply-pack-ready") {
      body.innerHTML = `
        <h3>Apply-pack ready</h3>
        <p class="muted">All 5 artefacts drafted. Review on LinkRight — we never auto-send anything you haven't seen.</p>
        <button class="btn btn-primary" id="lrOpen" style="margin-top:12px;">Open in LinkRight →</button>
        <button class="btn btn-secondary" id="lrAutofill" style="margin-top:8px;">Autofill this form</button>
      `;
      shadow.getElementById("lrOpen")?.addEventListener("click", () => {
        window.open(`https://sync.linkright.in/resume/customize/${data.resume_id ?? ""}`, "_blank");
      });
      shadow.getElementById("lrAutofill")?.addEventListener("click", () => {
        // Hook to autofill.js (next iteration).
        alert("Autofill coming in v0.2");
      });
      return;
    }

    if (state === "error") {
      body.innerHTML = `
        <h3>Something went wrong</h3>
        <p class="muted">${escapeHtml(data.msg || "Try again in a moment.")}</p>
      `;
      return;
    }
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  // -------- Entry --------
  async function main() {
    const job = detectJob();
    if (!job) return; // URL matched manifest but DOM not ready / not a job page. Silent exit.

    const { shadow } = createOverlay();
    shadow.getElementById("lrClose")?.addEventListener("click", () => {
      document.getElementById("linkright-ext-root")?.remove();
    });

    const status = await sendBg({ type: "lr:get-status" });
    if (!status?.connected) {
      renderBody(shadow, "not-connected");
      return;
    }

    renderBody(shadow, "analyzing", job);

    // Send job context + fetch match score
    const parsed = await sendBg({
      type: "lr:api",
      path: "/api/extension/parse-job",
      init: { method: "POST", body: JSON.stringify(job) },
    });

    if (parsed?.ok && parsed.body) {
      renderBody(shadow, "ready", { ...job, ...parsed.body });
    } else if (parsed?.status === 401) {
      renderBody(shadow, "not-connected");
    } else {
      renderBody(shadow, "error", { msg: parsed?.error ?? "Could not analyze this role. Try again." });
    }
  }

  // Delay slightly so SPA routers (LinkedIn, etc.) finish their DOM updates.
  if (document.readyState === "complete") setTimeout(main, 600);
  else window.addEventListener("load", () => setTimeout(main, 600));
})();
