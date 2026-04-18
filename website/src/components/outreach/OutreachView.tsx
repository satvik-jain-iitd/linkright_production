"use client";

// Wave 2 — Outreach artefacts surface (DM + recruiter email).
// Two tabs, each with its own draft + regen + copy flow. Draws from the
// resume_job's company/role/JD + the user's top career_nuggets.

import { useState } from "react";
import Link from "next/link";

type Tab = "dm" | "email";

interface Props {
  resumeJobId: string;
  targetCompany: string | null;
  targetRole: string | null;
}

export function OutreachView({
  resumeJobId,
  targetCompany,
  targetRole,
}: Props) {
  const [tab, setTab] = useState<Tab>("dm");
  const [recipientName, setRecipientName] = useState("");

  // DM state
  const [dmContent, setDmContent] = useState("");
  const [dmGenerating, setDmGenerating] = useState(false);
  const [dmError, setDmError] = useState("");
  const [dmCopied, setDmCopied] = useState(false);

  // Email state
  const [emailSubject, setEmailSubject] = useState("");
  const [emailContent, setEmailContent] = useState("");
  const [emailGenerating, setEmailGenerating] = useState(false);
  const [emailError, setEmailError] = useState("");
  const [emailCopied, setEmailCopied] = useState(false);

  const generateDm = async () => {
    setDmGenerating(true);
    setDmError("");
    try {
      const res = await fetch("/api/outreach/dm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resume_job_id: resumeJobId,
          recipient_name: recipientName.trim() || undefined,
        }),
      });
      const body = await res.json();
      if (!res.ok) {
        setDmError(body.error ?? "Couldn't draft DM.");
      } else {
        setDmContent(body.content ?? "");
      }
    } catch {
      setDmError("Network error — try again.");
    } finally {
      setDmGenerating(false);
    }
  };

  const generateEmail = async () => {
    setEmailGenerating(true);
    setEmailError("");
    try {
      const res = await fetch("/api/outreach/email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resume_job_id: resumeJobId,
          recipient_name: recipientName.trim() || undefined,
        }),
      });
      const body = await res.json();
      if (!res.ok) {
        setEmailError(body.error ?? "Couldn't draft email.");
      } else {
        setEmailSubject(body.subject ?? "");
        setEmailContent(body.content ?? "");
      }
    } catch {
      setEmailError("Network error — try again.");
    } finally {
      setEmailGenerating(false);
    }
  };

  const copy = async (text: string, which: "dm" | "email") => {
    await navigator.clipboard.writeText(text);
    if (which === "dm") {
      setDmCopied(true);
      setTimeout(() => setDmCopied(false), 1600);
    } else {
      setEmailCopied(true);
      setTimeout(() => setEmailCopied(false), 1600);
    }
  };

  const contextLabel = [targetRole, targetCompany].filter(Boolean).join(" · ");

  return (
    <div>
      <div className="mb-2">
        <p className="text-xs font-medium uppercase tracking-[0.14em] text-cta">
          Outreach
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">
          Draft DM + recruiter email.
        </h1>
        <p className="mt-1 text-sm text-muted">
          {contextLabel
            ? `For: ${contextLabel}`
            : "Pulled from your profile + the JD. Review before you send."}
        </p>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <label className="text-xs font-semibold text-foreground">
          Recipient name (optional)
        </label>
        <input
          value={recipientName}
          onChange={(e) => setRecipientName(e.target.value)}
          placeholder="Ayushi, Priya, hiring manager…"
          className="flex-1 min-w-[240px] max-w-md rounded-lg border border-border bg-white px-3 py-1.5 text-sm focus:border-accent focus:outline-none"
        />
      </div>

      {/* Tabs */}
      <div className="mt-6 flex gap-6 border-b border-border">
        {[
          { key: "dm" as Tab, label: "LinkedIn DM" },
          { key: "email" as Tab, label: "Recruiter email" },
        ].map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            className={
              tab === t.key
                ? "-mb-px border-b-2 border-accent pb-2.5 text-sm font-semibold text-foreground"
                : "pb-2.5 text-sm font-medium text-muted transition hover:text-foreground"
            }
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* DM pane */}
      {tab === "dm" && (
        <div className="mt-5 space-y-3">
          {!dmContent && !dmGenerating && (
            <div className="rounded-2xl border border-dashed border-border bg-white p-10 text-center">
              <p className="text-sm font-semibold">
                Draft a short, specific LinkedIn DM.
              </p>
              <p className="mt-1 text-xs text-muted">
                One highlight from your profile, tied to one JD requirement.
                3–5 sentences. Under 600 characters.
              </p>
              <button
                type="button"
                onClick={generateDm}
                className="mt-4 rounded-full bg-cta px-5 py-2 text-sm font-semibold text-white shadow-cta transition hover:bg-cta-hover"
              >
                Draft DM →
              </button>
            </div>
          )}
          {dmGenerating && (
            <div className="rounded-2xl border border-accent/30 bg-accent/5 p-4 text-sm text-primary-700">
              Drafting…
            </div>
          )}
          {dmError && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {dmError}
            </div>
          )}
          {dmContent && (
            <div className="space-y-3">
              <textarea
                value={dmContent}
                onChange={(e) => setDmContent(e.target.value)}
                rows={7}
                className="w-full resize-y rounded-2xl border border-border bg-white p-4 text-[14px] leading-[1.55] focus:border-accent focus:outline-none"
              />
              <div className="flex flex-wrap items-center justify-between gap-3">
                <span className="text-xs text-muted">
                  {dmContent.length} / 600 characters
                </span>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={generateDm}
                    disabled={dmGenerating}
                    className="rounded-full border border-border bg-white px-3.5 py-1.5 text-xs font-semibold text-foreground transition hover:border-accent"
                  >
                    Regenerate
                  </button>
                  <button
                    type="button"
                    onClick={() => copy(dmContent, "dm")}
                    className="rounded-full bg-accent px-4 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-accent-hover"
                  >
                    {dmCopied ? "Copied ✓" : "Copy DM"}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Email pane */}
      {tab === "email" && (
        <div className="mt-5 space-y-3">
          {!emailContent && !emailGenerating && (
            <div className="rounded-2xl border border-dashed border-border bg-white p-10 text-center">
              <p className="text-sm font-semibold">
                Draft a short, specific recruiter email.
              </p>
              <p className="mt-1 text-xs text-muted">
                Subject line + 3 paragraphs. Two highlights from your profile,
                one clear ask.
              </p>
              <button
                type="button"
                onClick={generateEmail}
                className="mt-4 rounded-full bg-cta px-5 py-2 text-sm font-semibold text-white shadow-cta transition hover:bg-cta-hover"
              >
                Draft email →
              </button>
            </div>
          )}
          {emailGenerating && (
            <div className="rounded-2xl border border-accent/30 bg-accent/5 p-4 text-sm text-primary-700">
              Drafting…
            </div>
          )}
          {emailError && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {emailError}
            </div>
          )}
          {emailContent && (
            <div className="space-y-3">
              <div>
                <label className="text-xs font-semibold text-foreground">
                  Subject
                </label>
                <input
                  value={emailSubject}
                  onChange={(e) => setEmailSubject(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm font-semibold focus:border-accent focus:outline-none"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-foreground">
                  Body
                </label>
                <textarea
                  value={emailContent}
                  onChange={(e) => setEmailContent(e.target.value)}
                  rows={14}
                  className="mt-1 w-full resize-y rounded-2xl border border-border bg-white p-4 text-[14px] leading-[1.55] focus:border-accent focus:outline-none"
                />
              </div>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <span className="text-xs text-muted">
                  {emailContent.length} characters
                </span>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={generateEmail}
                    disabled={emailGenerating}
                    className="rounded-full border border-border bg-white px-3.5 py-1.5 text-xs font-semibold text-foreground transition hover:border-accent"
                  >
                    Regenerate
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      const full = `Subject: ${emailSubject}\n\n${emailContent}`;
                      copy(full, "email");
                    }}
                    className="rounded-full bg-accent px-4 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-accent-hover"
                  >
                    {emailCopied ? "Copied ✓" : "Copy email"}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      <div className="mt-10 rounded-xl border border-border bg-white p-4 text-xs text-muted">
        Cover letter for the same role?{" "}
        <Link
          href={`/dashboard/cover-letters?resume_job=${resumeJobId}`}
          className="font-semibold text-accent hover:text-accent-hover"
        >
          Generate it here →
        </Link>
      </div>
    </div>
  );
}
