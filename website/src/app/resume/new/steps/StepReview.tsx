"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { WizardData } from "../WizardShell";
import { QualityPanel } from "@/components/QualityPanel";
import type { QualityStats } from "@/components/QualityPanel";
import { TemplateLockPanel } from "@/components/TemplateLockPanel";

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
  { label: "Make more impactful", prompt: "Make more impactful" },
  {
    label: "Expand to fill width (98%)",
    prompt:
      "Expand this bullet point to fill approximately 98% of the line width. Add meaningful detail, context, or metrics. Keep it to a single line.",
  },
  { label: "Make more concise", prompt: "Make more concise" },
  { label: "Quantify with metrics", prompt: "Quantify with metrics" },
  { label: "Improve action verb", prompt: "Improve action verb" },
  {
    label: "Justify",
    prompt:
      "Rewrite this bullet point so it reads as justified, professional prose with no informal language or hedging.",
  },
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

  // Template lock state
  const [lockedSections, setLockedSections] = useState<string[]>([]);
  const [savedTemplate, setSavedTemplate] = useState(false);
  const [savingTemplate, setSavingTemplate] = useState(false);

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
        setSelectedElement({
          html: e.data.html,
          selector: e.data.selector,
          preview: e.data.preview,
        });
        setSelectorMode(false);
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
          <button
            onClick={downloadHtml}
            className="rounded-xl border border-border bg-surface px-4 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-surface-hover"
          >
            Download HTML
          </button>
          <button
            onClick={printResume}
            className="rounded-full bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover"
          >
            Print / Save PDF
          </button>
        </div>
      </div>

      {/* Stats bar */}
      {stats && (
        <div className="flex flex-wrap gap-3">
          {stats.avg_brs !== undefined && (
            <div className="rounded-xl border border-border bg-surface px-4 py-3">
              <div className="text-xs text-muted">Avg BRS</div>
              <div className="text-lg font-bold text-accent">
                {Math.round((stats.avg_brs as number) * 100)}%
              </div>
            </div>
          )}
          {stats.tier_1_count !== undefined && (
            <div className="rounded-xl border border-border bg-surface px-4 py-3">
              <div className="text-xs text-muted">Tier 1 Bullets</div>
              <div className="text-lg font-bold text-accent">
                {stats.tier_1_count as number}
              </div>
            </div>
          )}
          {stats.final_fits_page !== undefined && (
            <div className="rounded-xl border border-border bg-surface px-4 py-3">
              <div className="text-xs text-muted">One Page</div>
              <div className="text-lg font-bold text-accent">
                {(stats.final_fits_page as boolean) ? "Yes" : "No"}
              </div>
            </div>
          )}
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
                <p>Click &quot;Select Element&quot; below, then click</p>
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
                {selectorMode ? "Cancel" : "Select El"}
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
