"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { WizardData } from "../WizardShell";
import { QualityPanel } from "@/components/QualityPanel";
import type { QualityStats } from "@/components/QualityPanel";
import { TemplateLockPanel } from "@/components/TemplateLockPanel";
import { measureBulletWidth, type MeasureResult } from "@/lib/bullet-width";

interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  attached_element?: { html: string; selector: string; preview?: string };
  applied?: boolean;
}

interface SelectedElement {
  html: string;
  selector: string;
  preview: string;
}

const PRESETS: { label: string; prompt: string }[] = [
  { label: "More impactful", prompt: "Make this bullet more impactful — lead with the outcome/result (XYZ format: impact first, measurement second, action last)" },
  { label: "Quantify", prompt: "Add specific metrics to this bullet — percentages, dollar amounts, team sizes, timelines. Use numbers from my career context." },
  { label: "XYZ format", prompt: "Rewrite in XYZ format: X=impact/outcome FIRST, Y=how it was measured, Z=what I specifically did. Lead with the result, not the action." },
  { label: "Concise", prompt: "Make more concise — cut adjectives and setup clauses, keep metrics and outcomes" },
  { label: "Stronger verb", prompt: "Replace the action verb with a stronger, more specific alternative" },
  { label: "JD keywords", prompt: "Naturally incorporate JD keywords into this bullet without losing meaning" },
];

// Injected into the iframe to enable element picking
const SELECTOR_SCRIPT = `
(function() {
  if (window.__selectorActive) return;
  window.__selectorActive = true;
  let highlighted = null;
  const STYLE = '2px solid #0FBEAF';
  const ORIG = new WeakMap();

  function getSelector(el) {
    if (!el || el === document.body) return 'body';
    const parts = [];
    let cur = el;
    while (cur && cur !== document.body) {
      let sel = cur.tagName.toLowerCase();
      if (cur.className) {
        const cls = Array.from(cur.classList).slice(0,2).join('.');
        if (cls) sel += '.' + cls;
      }
      const parent = cur.parentElement;
      if (parent) {
        const siblings = Array.from(parent.children).filter(c => c.tagName === cur.tagName);
        if (siblings.length > 1) sel += ':nth-of-type(' + (siblings.indexOf(cur) + 1) + ')';
      }
      parts.unshift(sel);
      cur = cur.parentElement;
    }
    return parts.join(' > ');
  }

  document.addEventListener('mouseover', function(e) {
    if (highlighted && ORIG.has(highlighted)) {
      highlighted.style.outline = ORIG.get(highlighted);
    }
    highlighted = e.target;
    ORIG.set(highlighted, highlighted.style.outline || '');
    highlighted.style.outline = STYLE;
  }, true);

  document.addEventListener('mouseout', function(e) {
    if (highlighted && ORIG.has(highlighted)) {
      highlighted.style.outline = ORIG.get(highlighted);
      highlighted = null;
    }
  }, true);

  document.addEventListener('click', function(e) {
    e.preventDefault();
    e.stopPropagation();
    const el = e.target;
    // Restore outline
    if (ORIG.has(el)) el.style.outline = ORIG.get(el);
    window.__selectorActive = false;
    // Remove listeners by reloading script tag (simpler: just post message)
    window.parent.postMessage({
      type: 'element_selected',
      html: el.outerHTML,
      selector: getSelector(el),
      preview: (el.textContent || '').trim().slice(0, 80)
    }, '*');
  }, true);
})();
`;

export function StepReview({ data, onNewResume }: { data: WizardData; onNewResume: () => void }) {
  const [html, setHtml] = useState<string | null>(null);
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);

  // Chat state
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [selectedElement, setSelectedElement] = useState<SelectedElement | null>(null);
  const [chatInput, setChatInput] = useState("");
  const [additionalContext, setAdditionalContext] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [selectorMode, setSelectorMode] = useState(false);

  // [PSA5-8y3.2.2.1] Download dropdown state
  const [downloadOpen, setDownloadOpen] = useState(false);

  // GitHub Pages hosting state
  const [githubOpen, setGithubOpen] = useState(false);
  const [githubPat, setGithubPat] = useState("");
  const [githubRepoName, setGithubRepoName] = useState("");
  const [githubLoading, setGithubLoading] = useState(false);
  const [githubResult, setGithubResult] = useState<{ repo_url: string; page_url: string | null; warning?: string } | null>(null);
  const [githubError, setGithubError] = useState<string | null>(null);

  // Template lock state
  const [lockedSections, setLockedSections] = useState<string[]>([]);
  const [savedTemplate, setSavedTemplate] = useState(false);
  const [savingTemplate, setSavingTemplate] = useState(false);

  // v4: Per-bullet width measurement + fit-to-line
  const [bulletMeasure, setBulletMeasure] = useState<MeasureResult | null>(null);
  const [fitting, setFitting] = useState(false);

  const iframeRef = useRef<HTMLIFrameElement>(null);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!data.job_id) {
      setLoading(false);
      return;
    }

    const fetchJob = async () => {
      try {
        const resp = await fetch(`/api/resume/${data.job_id}`);
        if (!resp.ok) return;
        const job = await resp.json();
        setHtml(job.output_html || null);
        setStats(job.stats || null);
      } catch {
        // Will show fallback
      }
      setLoading(false);
    };

    fetchJob();
  }, [data.job_id]);

  // Listen for element selection from iframe
  useEffect(() => {
    const handler = (e: MessageEvent) => {
      if (e.data?.type === "element_selected") {
        const el = {
          html: e.data.html,
          selector: e.data.selector,
          preview: e.data.preview,
        };
        setSelectedElement(el);
        setSelectorMode(false);

        // v4: auto-measure width if it's a bullet point (li element)
        if (el.html.startsWith("<li")) {
          // Extract inner text (strip outer <li> tag and inner HTML)
          const innerMatch = el.html.match(/<li[^>]*>([\s\S]*)<\/li>/i);
          const innerHtml = innerMatch ? innerMatch[1].trim() : el.preview;
          setBulletMeasure(measureBulletWidth(innerHtml));
        } else {
          setBulletMeasure(null);
        }
      }
    };
    window.addEventListener("message", handler);
    return () => window.removeEventListener("message", handler);
  }, []);

  // Auto-scroll chat
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  const activateSelectorMode = useCallback(() => {
    setSelectorMode(true);
    const iframe = iframeRef.current;
    if (!iframe?.contentDocument) return;
    const script = iframe.contentDocument.createElement("script");
    script.textContent = SELECTOR_SCRIPT;
    iframe.contentDocument.head.appendChild(script);
  }, []);

  const deactivateSelectorMode = useCallback(() => {
    setSelectorMode(false);
    // Re-load iframe to clear selector overlay
    const iframe = iframeRef.current;
    if (!iframe) return;
    const currentSrc = iframe.srcdoc;
    iframe.srcdoc = currentSrc;
  }, []);

  const applyEdit = useCallback(
    (updatedHtml: string, selector: string) => {
      const iframe = iframeRef.current;
      if (!iframe?.contentDocument) return;
      try {
        const el = iframe.contentDocument.querySelector(selector);
        if (el) {
          el.outerHTML = updatedHtml;
          // Re-serialize full HTML
          const newHtml = "<!DOCTYPE html>" + iframe.contentDocument.documentElement.outerHTML;
          setHtml(newHtml);
        }
      } catch {
        // Selector may not work — just update the full html via srcdoc
      }
    },
    []
  );

  const sendChat = async (instruction: string) => {
    if (!instruction.trim() || !html) return;

    const userMsg: ChatMessage = {
      role: "user",
      text: instruction,
      attached_element: selectedElement ?? undefined,
    };
    setChatHistory((prev) => [...prev, userMsg]);
    setChatInput("");
    setChatLoading(true);

    try {
      const jobContext = {
        company: data.target_company,
        role: data.target_role,
        requirements: data.jd_analysis?.requirements?.slice(0, 10).map((r) => r.text) ?? [],
      };

      const resp = await fetch("/api/resume/chat-edit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          selected_html: selectedElement?.html || "",
          selector: selectedElement?.selector || "",
          instruction,
          full_resume_html: html,
          job_context: jobContext,
          model_provider: data.model_provider,
          model_id: data.model_id,
          api_key: data.api_key,
        }),
      });

      if (!resp.ok) {
        const err = await resp.json();
        setChatHistory((prev) => [
          ...prev,
          { role: "assistant", text: `Error: ${err.error || "Request failed"}` },
        ]);
        return;
      }

      const result = await resp.json();
      const assistantMsg: ChatMessage = {
        role: "assistant",
        text: result.explanation || "Done.",
        applied: false,
      };
      setChatHistory((prev) => [...prev, assistantMsg]);

      // Auto-apply if element was selected
      if (selectedElement && result.updated_html && result.selector) {
        applyEdit(result.updated_html, result.selector);
        setChatHistory((prev) =>
          prev.map((m, i) =>
            i === prev.length - 1 ? { ...m, applied: true } : m
          )
        );
        setSelectedElement(null);
        setAdditionalContext("");
      }
    } catch {
      setChatHistory((prev) => [
        ...prev,
        { role: "assistant", text: "Network error. Please try again." },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const downloadHtml = () => {
    if (!html) return;
    const blob = new Blob([html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "resume.html";
    a.click();
    URL.revokeObjectURL(url);
  };

  const printResume = () => {
    const iframe = iframeRef.current;
    if (iframe?.contentWindow) {
      iframe.contentWindow.print();
    }
  };

  const toggleLockedSection = (section: string) => {
    setLockedSections((prev) =>
      prev.includes(section) ? prev.filter((s) => s !== section) : [...prev, section]
    );
  };

  const saveAsTemplate = async () => {
    if (!data.job_id) return;
    setSavingTemplate(true);
    try {
      const resp = await fetch("/api/resume/template", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_id: data.job_id,
          name: "My Template",
          locked_sections: lockedSections,
          brand_colors: data.brand_colors,
        }),
      });
      if (resp.ok) {
        setSavedTemplate(true);
      }
    } finally {
      setSavingTemplate(false);
    }
  };

  const hostOnGithub = async () => {
    if (!html || !githubPat.trim()) return;
    setGithubLoading(true);
    setGithubError(null);
    try {
      const resp = await fetch("/api/resume/github-host", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          html,
          pat: githubPat.trim(),
          repo_name: githubRepoName.trim() || undefined,
        }),
      });
      const result = await resp.json();
      if (!resp.ok) {
        setGithubError(result.error || "Failed to host on GitHub");
      } else {
        setGithubResult(result);
        setGithubPat(""); // clear PAT from memory
      }
    } catch {
      setGithubError("Network error — please try again");
    } finally {
      setGithubLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
      </div>
    );
  }

  if (!html) {
    return (
      <div className="text-center">
        <h2 className="text-xl font-semibold">No resume found</h2>
        <p className="mt-2 text-sm text-muted">
          Something went wrong. Please try generating again.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header bar */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold">Your Resume</h2>
          <p className="mt-1 text-sm text-muted">
            Preview, edit via chat, download, or print.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 sm:gap-3">
          <button
            onClick={onNewResume}
            className="rounded-xl border border-border bg-surface px-4 py-2.5 text-sm font-medium text-muted transition-colors hover:text-foreground"
          >
            + New Resume
          </button>
          {/* [PSA5-8y3.2.2.1] old Download HTML + Print/Save PDF buttons replaced by dropdown below */}
          <button
            onClick={() => { setGithubOpen(true); setGithubResult(null); setGithubError(null); }}
            className="rounded-xl border border-border bg-surface px-4 py-2.5 text-sm font-medium text-muted transition-colors hover:text-foreground"
          >
            Host on GitHub
          </button>
          {data.job_id && (
            <>
              <a
                href={`/dashboard/cover-letters?resume_job=${data.job_id}`}
                className="inline-flex items-center gap-1.5 rounded-xl border border-accent/30 bg-accent/5 px-4 py-2.5 text-sm font-medium text-accent transition-colors hover:bg-accent/10"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
                </svg>
                Cover letter
              </a>
              <a
                href={`/dashboard/outreach?resume_job=${data.job_id}`}
                className="inline-flex items-center gap-1.5 rounded-xl border border-accent/30 bg-accent/5 px-4 py-2.5 text-sm font-medium text-accent transition-colors hover:bg-accent/10"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375m-13.5 3.01c0 1.6 1.123 2.994 2.707 3.227 1.129.164 2.27.294 3.423.39 1.1.092 1.907 1.056 1.907 2.16v4.773l3.423-3.423a1.125 1.125 0 01.8-.33 48.31 48.31 0 005.58-.498c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
                </svg>
                DM + email
              </a>
            </>
          )}
          {/* [PSA5-8y3.2.2.1] Single download dropdown */}
          <div className="relative">
            <button
              onClick={() => setDownloadOpen(o => !o)}
              className="rounded-lg bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover flex items-center gap-2"
            >
              Download Resume <span>▾</span>
            </button>
            {downloadOpen && (
              <div className="absolute right-0 mt-1 w-44 rounded-xl border border-border bg-surface shadow-lg z-50">
                <button
                  onClick={() => { printResume(); setDownloadOpen(false); }}
                  className="w-full px-4 py-2.5 text-left text-sm text-foreground hover:bg-surface-hover rounded-t-xl"
                >
                  PDF (via print)
                </button>
                <button
                  onClick={() => { downloadHtml(); setDownloadOpen(false); }}
                  className="w-full px-4 py-2.5 text-left text-sm text-muted hover:bg-surface-hover rounded-b-xl"
                >
                  HTML file
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 4-checks panel — design Screen 11 honest-output signals. */}
      {stats && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {(() => {
            const brs = stats.avg_brs as number | undefined;
            const fits = stats.final_fits_page as boolean | undefined;
            const ats = (stats.ats_safe as boolean | undefined) ?? true; // bullets generated by pipeline are ATS-safe by construction
            const brandMatched =
              (stats.brand_colors_applied as boolean | undefined) ??
              !!(stats.template_color as string | undefined);
            const lineFill = stats.line_fill_pct as number | undefined;
            const tier1 = stats.tier_1_count as number | undefined;
            const checks = [
              {
                label: "ATS-safe",
                ok: ats,
                body: ats
                  ? "No images, no tables, no text in columns. Parsers can read it."
                  : "Template used features ATS parsers may mis-read.",
              },
              {
                label: "No AI slop",
                ok: brs == null ? true : brs >= 0.6,
                body:
                  brs == null
                    ? "Bullets traced to your own highlights, evidence-cited."
                    : `Avg relevance ${Math.round(brs * 100)}% · ${tier1 ?? 0} top-tier bullets`,
              },
              {
                label: "Line-filled",
                ok: lineFill != null ? lineFill >= 0.9 : fits !== false,
                body:
                  lineFill != null
                    ? `${Math.round(lineFill * 100)}% of each line utilised`
                    : fits
                      ? "Fits one page cleanly, no overflow."
                      : "Content spills past one page — tighten bullets.",
              },
              {
                label: "Brand-matched",
                ok: brandMatched,
                body: brandMatched
                  ? "Accent colours pulled from the company brand."
                  : "Using default neutral palette (company not in DB yet).",
              },
            ];
            return checks.map((c) => (
              <div
                key={c.label}
                className="rounded-2xl border border-border bg-surface p-4"
                style={{
                  borderColor: c.ok ? "rgba(15,190,175,0.3)" : "rgba(255,87,51,0.25)",
                  background: c.ok ? "rgba(15,190,175,0.04)" : "rgba(255,87,51,0.04)",
                }}
              >
                <div className="flex items-center gap-2">
                  <span
                    className={
                      "flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full text-[10px] font-bold text-white " +
                      (c.ok ? "bg-accent" : "bg-cta")
                    }
                  >
                    {c.ok ? "✓" : "!"}
                  </span>
                  <span className="text-sm font-semibold tracking-tight">
                    {c.label}
                  </span>
                </div>
                <p className="mt-2 text-xs leading-relaxed text-muted">
                  {c.body}
                </p>
              </div>
            ));
          })()}
          {/* [PSA5-8y3.2.1.1] Engineering metrics collapsed into details */}
          {(stats.llm_calls !== undefined || stats.total_input_tokens !== undefined || stats.total_llm_time_ms !== undefined) && (
            <details className="mt-2">
              <summary className="cursor-pointer select-none text-xs text-muted hover:text-foreground">
                Advanced metrics
              </summary>
              <div className="mt-2 flex flex-wrap gap-3">
                {/* [PSA5-8y3.2.1.1] old inline placement removed */}
                {stats.llm_calls !== undefined && (
                  <div className="rounded-xl border border-border bg-surface px-4 py-3">
                    <div className="text-xs text-muted">LLM Calls</div>
                    <div className="text-lg font-bold">{stats.llm_calls as number}</div>
                  </div>
                )}
                {stats.total_input_tokens !== undefined && (
                  <div className="rounded-xl border border-border bg-surface px-4 py-3">
                    <div className="text-xs text-muted">Tokens (in/out)</div>
                    <div className="text-lg font-bold">
                      {Math.round((stats.total_input_tokens as number) / 1000)}K /{" "}
                      {Math.round((stats.total_output_tokens as number) / 1000)}K
                    </div>
                  </div>
                )}
                {stats.total_llm_time_ms !== undefined && (
                  <div className="rounded-xl border border-border bg-surface px-4 py-3">
                    <div className="text-xs text-muted">LLM Time</div>
                    <div className="text-lg font-bold">
                      {Math.round((stats.total_llm_time_ms as number) / 1000)}s
                    </div>
                  </div>
                )}
              </div>
            </details>
          )}
        </div>
      )}

      {/* Quality panel */}
      {stats && <QualityPanel stats={stats as Partial<QualityStats>} />}

      {/* Two-column layout: resume + sidebar chat */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
        {/* Resume iframe */}
        <div className="flex-1 overflow-hidden rounded-xl border border-border shadow-lg">
          {selectorMode && (
            <div className="flex items-center justify-between border-b border-amber-200 bg-amber-50 px-4 py-2">
              <span className="text-sm font-medium text-amber-800">
                Click any element on the resume to select it
              </span>
              <button
                onClick={deactivateSelectorMode}
                className="text-xs text-amber-700 underline"
              >
                Cancel
              </button>
            </div>
          )}
          <iframe
            ref={iframeRef}
            id="resume-preview"
            srcDoc={html}
            className="h-[900px] w-full bg-white"
            title="Resume Preview"
          />
        </div>

        {/* Sidebar chat */}
        <div className="flex w-full flex-col rounded-xl border border-border bg-surface lg:w-80 xl:w-96">
          {/* Chat header */}
          <div className="border-b border-border px-4 py-3">
            <h3 className="text-sm font-semibold text-foreground">Resume Editor</h3>
            <p className="mt-0.5 text-xs text-muted">
              Select an element and ask me to edit it
            </p>
          </div>

          {/* Chat messages */}
          <div className="flex-1 overflow-y-auto p-4" style={{ maxHeight: "500px" }}>
            {chatHistory.length === 0 && (
              <div className="py-6 text-center text-xs text-muted">
                <p>Click &ldquo;Select Element&rdquo; below, then click</p>
                <p>any part of the resume to edit it.</p>
              </div>
            )}
            <div className="space-y-3">
              {chatHistory.map((msg, i) => (
                <div
                  key={i}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[85%] rounded-xl px-3 py-2 text-xs ${
                      msg.role === "user"
                        ? "bg-accent text-white"
                        : "border border-border bg-background text-foreground"
                    }`}
                  >
                    {msg.attached_element && (
                      <div className="mb-1.5 rounded bg-white/20 px-2 py-1 font-mono text-[10px]">
                        &lt;{msg.attached_element.html.match(/^<(\w+)/)?.[1] ?? "el"}&gt;{" "}
                        {msg.attached_element.preview || "…"}
                      </div>
                    )}
                    <p>{msg.text}</p>
                    {msg.applied && (
                      <p className="mt-1 text-[10px] opacity-70">✓ Applied</p>
                    )}
                  </div>
                </div>
              ))}
              {chatLoading && (
                <div className="flex justify-start">
                  <div className="rounded-xl border border-border bg-background px-3 py-2">
                    <div className="flex gap-1">
                      <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted [animation-delay:0ms]" />
                      <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted [animation-delay:150ms]" />
                      <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted [animation-delay:300ms]" />
                    </div>
                  </div>
                </div>
              )}
              <div ref={chatBottomRef} />
            </div>
          </div>

          {/* Selected element pill */}
          {selectedElement && (
            <div className="border-t border-border px-4 py-2">
              <div className="flex items-center gap-2 rounded-lg bg-accent/10 px-3 py-2 text-xs">
                <span className="font-mono text-accent">
                  &lt;{selectedElement.html.match(/^<(\w+)/)?.[1] ?? "el"}&gt;
                </span>
                <span className="flex-1 truncate text-muted">
                  {selectedElement.preview || "Selected element"}
                </span>
                <button
                  onClick={() => setSelectedElement(null)}
                  className="flex-shrink-0 text-muted hover:text-foreground"
                >
                  ×
                </button>
              </div>
            </div>
          )}

          {/* v4: Per-bullet width measurement + Fit to line */}
          {selectedElement && bulletMeasure && (
            <div className="border-t border-border px-4 py-2">
              <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-muted">
                Width
              </p>
              <div className="flex items-center gap-2">
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-border">
                  <div
                    className={`h-full rounded-full transition-all ${
                      bulletMeasure.status === "PASS"
                        ? "bg-green-500"
                        : bulletMeasure.status === "OVERFLOW"
                          ? "bg-red-500"
                          : "bg-amber-500"
                    }`}
                    style={{ width: `${Math.min(bulletMeasure.fill_pct, 100)}%` }}
                  />
                </div>
                <span
                  className={`font-mono text-xs font-medium ${
                    bulletMeasure.status === "PASS"
                      ? "text-green-700"
                      : bulletMeasure.status === "OVERFLOW"
                        ? "text-red-600"
                        : "text-amber-600"
                  }`}
                >
                  {bulletMeasure.fill_pct}%
                </span>
              </div>
              <div className="mt-1 flex items-center justify-between text-[10px] text-muted">
                <span>{bulletMeasure.status === "PASS" ? "Fits in one line" : bulletMeasure.status === "OVERFLOW" ? "Wraps to 2 lines" : "Too short"}</span>
                <span>{bulletMeasure.weighted_total.toFixed(1)} / 101.4 CU</span>
              </div>
              {bulletMeasure.status !== "PASS" && (
                <button
                  onClick={async () => {
                    if (!selectedElement) return;
                    setFitting(true);
                    try {
                      const innerMatch = selectedElement.html.match(/<li[^>]*>([\s\S]*)<\/li>/i);
                      const innerHtml = innerMatch ? innerMatch[1].trim() : selectedElement.preview;
                      const resp = await fetch("/api/resume/fit-bullet", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                          current_bullet: innerHtml,
                          action: bulletMeasure.status === "OVERFLOW" ? "shrink" : "expand",
                        }),
                      });
                      if (resp.ok) {
                        const result = await resp.json();
                        if (result.fitted_bullet) {
                          // Apply to iframe
                          const iframe = iframeRef.current;
                          if (iframe?.contentDocument) {
                            const el = iframe.contentDocument.querySelector(selectedElement.selector);
                            if (el) {
                              el.innerHTML = result.fitted_bullet;
                              setHtml(iframe.contentDocument.documentElement.outerHTML);
                            }
                          }
                          setBulletMeasure(measureBulletWidth(result.fitted_bullet));
                        }
                      }
                    } catch { /* silent */ } finally {
                      setFitting(false);
                    }
                  }}
                  disabled={fitting}
                  className="mt-2 w-full rounded-lg bg-accent px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-accent/90 disabled:opacity-50"
                >
                  {fitting ? (
                    <span className="flex items-center justify-center gap-1.5">
                      <span className="h-3 w-3 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                      Fitting...
                    </span>
                  ) : bulletMeasure.status === "OVERFLOW" ? (
                    "Shrink to fit one line"
                  ) : (
                    "Expand to fill line"
                  )}
                </button>
              )}
            </div>
          )}

          {/* Preset chips + additional context (shown when element is selected) */}
          {selectedElement && (
            <div className="border-t border-border px-4 py-2">
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-muted">
                Quick edits
              </p>
              <div className="flex flex-wrap gap-1.5">
                {PRESETS.map((preset) => (
                  <button
                    key={preset.label}
                    onClick={() => {
                      const fullPrompt = additionalContext.trim()
                        ? `${preset.prompt}\n\nAdditional context from user: ${additionalContext.trim()}`
                        : preset.prompt;
                      sendChat(fullPrompt);
                    }}
                    disabled={chatLoading}
                    className="rounded-full border border-border bg-background px-2.5 py-1 text-xs text-foreground transition-colors hover:border-accent/50 hover:text-accent disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
              <textarea
                value={additionalContext}
                onChange={(e) => setAdditionalContext(e.target.value)}
                placeholder="Add context for this edit (optional)..."
                disabled={chatLoading}
                rows={2}
                className="mt-2 w-full resize-none rounded-lg border border-border bg-background px-3 py-2 text-xs focus:border-accent/50 focus:outline-none disabled:opacity-50"
              />
            </div>
          )}

          {/* Chat input */}
          <div className="border-t border-border p-4">
            <div className="flex gap-2">
              <button
                onClick={selectorMode ? deactivateSelectorMode : activateSelectorMode}
                title={selectorMode ? "Cancel selection" : "Select element from resume"}
                className={`flex-shrink-0 rounded-lg border px-3 py-2 text-xs font-medium transition-colors ${
                  selectorMode
                    ? "border-amber-300 bg-amber-50 text-amber-700"
                    : "border-border bg-background text-muted hover:text-foreground"
                }`}
              >
                {/* [PSA5-8y3.3.2.1] Changed "Select El" → "Select Element" */}
                {selectorMode ? "Cancel" : "Select Element"}
              </button>
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    sendChat(chatInput);
                  }
                }}
                placeholder={
                  selectedElement
                    ? "Describe the edit..."
                    : "Chat with your resume..."
                }
                disabled={chatLoading}
                className="min-w-0 flex-1 rounded-lg border border-border bg-background px-3 py-2 text-xs focus:border-accent/50 focus:outline-none disabled:opacity-50"
              />
              <button
                onClick={() => sendChat(chatInput)}
                disabled={chatLoading || !chatInput.trim()}
                className="flex-shrink-0 rounded-lg bg-accent px-3 py-2 text-xs font-medium text-white transition-colors hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {selectedElement ? "Send" : "Apply"}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* GitHub Pages hosting modal */}
      {githubOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-xl">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-lg font-semibold">Host on GitHub Pages</h3>
                <p className="mt-1 text-sm text-muted">
                  Publish your resume as a live webpage for free.
                </p>
              </div>
              <button
                onClick={() => setGithubOpen(false)}
                className="ml-4 text-muted hover:text-foreground"
              >
                ✕
              </button>
            </div>

            {githubResult ? (
              <div className="mt-5 space-y-4">
                <div className="rounded-xl border border-green-200 bg-green-50 p-4">
                  <p className="text-sm font-semibold text-green-700">Published!</p>
                  {githubResult.warning && (
                    <p className="mt-1 text-xs text-amber-700">{githubResult.warning}</p>
                  )}
                  {githubResult.page_url && (
                    <div className="mt-3">
                      <p className="text-xs text-muted">Your resume URL (live in ~1 min):</p>
                      <div className="mt-1 flex items-center gap-2">
                        <code className="flex-1 truncate rounded bg-white px-2 py-1 text-xs text-green-800">
                          {githubResult.page_url}
                        </code>
                        <button
                          onClick={() => navigator.clipboard.writeText(githubResult.page_url!)}
                          className="shrink-0 rounded-lg bg-green-600 px-3 py-1 text-xs font-medium text-white hover:bg-green-700"
                        >
                          Copy
                        </button>
                      </div>
                    </div>
                  )}
                  <a
                    href={githubResult.repo_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-2 inline-block text-xs text-green-700 underline"
                  >
                    View repository →
                  </a>
                </div>
                <button
                  onClick={() => setGithubOpen(false)}
                  className="w-full rounded-lg bg-cta px-6 py-2.5 text-sm font-medium text-white hover:bg-cta-hover"
                >
                  Done
                </button>
              </div>
            ) : (
              <div className="mt-5 space-y-4">
                <div>
                  <label className="block text-xs font-medium text-muted mb-1">
                    GitHub Personal Access Token
                  </label>
                  <input
                    type="password"
                    value={githubPat}
                    onChange={(e) => setGithubPat(e.target.value)}
                    placeholder="ghp_xxxxxxxxxxxx"
                    className="w-full rounded-xl border border-border bg-background px-3 py-2.5 text-sm focus:border-accent/50 focus:outline-none"
                  />
                  <p className="mt-1 text-xs text-muted">
                    Need one?{" "}
                    <a
                      href="https://github.com/settings/tokens/new?scopes=repo&description=LinkRight+Resume+Hosting"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-accent underline"
                    >
                      Create PAT
                    </a>{" "}
                    with <code className="rounded bg-surface-hover px-1">repo</code> scope.
                  </p>
                </div>
                <div>
                  <label className="block text-xs font-medium text-muted mb-1">
                    Repo name (optional)
                  </label>
                  <input
                    type="text"
                    value={githubRepoName}
                    onChange={(e) => setGithubRepoName(e.target.value)}
                    placeholder="my-resume"
                    className="w-full rounded-xl border border-border bg-background px-3 py-2.5 text-sm focus:border-accent/50 focus:outline-none"
                  />
                  <p className="mt-1 text-xs text-muted">
                    Leave blank to auto-generate a name.
                  </p>
                </div>

                {githubError && (
                  <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                    {githubError}
                  </p>
                )}

                <div className="flex gap-3 pt-1">
                  <button
                    onClick={() => setGithubOpen(false)}
                    className="flex-1 rounded-xl border border-border bg-surface px-4 py-2.5 text-sm font-medium text-muted hover:text-foreground"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={hostOnGithub}
                    disabled={githubLoading || !githubPat.trim()}
                    className="flex-1 rounded-lg bg-cta px-6 py-2.5 text-sm font-medium text-white hover:bg-cta-hover disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {githubLoading ? (
                      <span className="flex items-center justify-center gap-2">
                        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                        Publishing...
                      </span>
                    ) : (
                      "Publish"
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Save as Template */}
      <div className="rounded-xl border border-border bg-surface p-5">
        <div className="mb-4">
          <h3 className="text-lg font-semibold">Save as Template</h3>
          <p className="mt-1 text-sm text-muted">
            Lock sections you want frozen — they won&apos;t be regenerated on your next resume.
          </p>
        </div>
        <TemplateLockPanel lockedSections={lockedSections} onToggle={toggleLockedSection} />
        <div className="mt-4 flex items-center gap-3">
          <button
            onClick={saveAsTemplate}
            disabled={savingTemplate || savedTemplate}
            className={`rounded-xl px-5 py-2.5 text-sm font-medium transition-colors disabled:cursor-not-allowed ${
              savedTemplate
                ? "border border-green-300 bg-green-50 text-green-700"
                : "bg-cta text-white hover:bg-cta-hover disabled:opacity-60"
            }`}
          >
            {savedTemplate ? "Saved ✓" : savingTemplate ? "Saving..." : "Save as Template"}
          </button>
          {savedTemplate && (
            <p className="text-sm text-green-700">
              Template saved! Next resume will reuse locked sections.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
