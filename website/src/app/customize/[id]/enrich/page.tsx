// Mind-map enrichment screen.
// Shown when user clicks "Customize resume" for a job BUT their nuggets
// aren't >=90% embedded yet. User answers follow-up questions about their
// existing nuggets to enrich the profile while background embedding completes.
// "Proceed now" button is always available — user can bail out anytime.

"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

type Nugget = {
  id: string;
  answer: string;
  company: string | null;
  role: string | null;
  importance: string;
  tags: string[] | null;
};

type Status = {
  total_extracted: number;
  total_embedded: number;
  embed_queued: number;
  ready: boolean;
};

type FollowUpSet = {
  parent_nugget_id: string;
  questions: string[];
  answered: boolean[]; // same length as questions
};

export default function EnrichPage() {
  const params = useParams<{ id: string }>();
  const jobId = params.id;
  const router = useRouter();

  const [nuggets, setNuggets] = useState<Nugget[]>([]);
  const [status, setStatus] = useState<Status | null>(null);
  const [followUps, setFollowUps] = useState<Record<string, FollowUpSet>>({});
  const [loadingNuggets, setLoadingNuggets] = useState(true);
  const [selectedQuestion, setSelectedQuestion] = useState<{
    parentId: string;
    questionIndex: number;
  } | null>(null);
  const [answerDraft, setAnswerDraft] = useState("");
  const [savingAnswer, setSavingAnswer] = useState(false);

  const loadNuggets = useCallback(async () => {
    const r = await fetch(`/api/nuggets?limit=50`);
    if (r.ok) {
      const body = await r.json();
      setNuggets(body.nuggets ?? []);
    }
    setLoadingNuggets(false);
  }, []);

  const pollStatus = useCallback(async () => {
    const r = await fetch("/api/nuggets/status");
    if (r.ok) {
      const body = await r.json();
      setStatus(body);
      if (body.ready) {
        // Don't auto-redirect; let user explicitly proceed via button.
      }
    }
  }, []);

  useEffect(() => {
    loadNuggets();
    pollStatus();
    const t = setInterval(pollStatus, 2000);
    return () => clearInterval(t);
  }, [loadNuggets, pollStatus]);

  async function expandNugget(nugget: Nugget) {
    if (followUps[nugget.id]) return; // already expanded
    // Optimistic placeholder
    setFollowUps((prev) => ({
      ...prev,
      [nugget.id]: { parent_nugget_id: nugget.id, questions: [], answered: [] },
    }));
    const r = await fetch("/api/nuggets/follow-ups", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nugget_id: nugget.id, job_discovery_id: jobId }),
    });
    const body = await r.json();
    if (!r.ok) {
      setFollowUps((prev) => {
        const next = { ...prev };
        delete next[nugget.id];
        return next;
      });
      alert(body.error ?? "Failed to generate follow-ups");
      return;
    }
    setFollowUps((prev) => ({
      ...prev,
      [nugget.id]: {
        parent_nugget_id: nugget.id,
        questions: body.questions,
        answered: body.questions.map(() => false),
      },
    }));
  }

  async function saveAnswer() {
    if (!selectedQuestion) return;
    const { parentId, questionIndex } = selectedQuestion;
    const fu = followUps[parentId];
    if (!fu) return;
    const question = fu.questions[questionIndex];
    if (!question || !answerDraft.trim()) return;
    setSavingAnswer(true);
    const r = await fetch("/api/nuggets/add-from-answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        parent_nugget_id: parentId,
        question,
        answer: answerDraft.trim(),
        job_discovery_id: jobId,
      }),
    });
    setSavingAnswer(false);
    if (!r.ok) {
      const body = await r.json().catch(() => ({}));
      alert(body.error ?? "Save failed");
      return;
    }
    // Mark answered
    setFollowUps((prev) => {
      const f = prev[parentId];
      if (!f) return prev;
      const answered = [...f.answered];
      answered[questionIndex] = true;
      return { ...prev, [parentId]: { ...f, answered } };
    });
    setSelectedQuestion(null);
    setAnswerDraft("");
    loadNuggets(); // reload to include the new nugget card
    pollStatus();
  }

  function proceed() {
    router.push(`/customize/${jobId}`);
  }

  const progressPct = status && status.total_extracted > 0
    ? Math.round((status.total_embedded / status.total_extracted) * 100)
    : 0;

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h1 className="text-2xl font-bold">Enrich your profile</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Click any experience to unlock 3 follow-up questions. Your answers sharpen the resume we'll tailor for this role.
          </p>
        </div>
        <button
          onClick={proceed}
          className="px-5 py-2 rounded-lg bg-primary text-primary-foreground"
        >
          Proceed now →
        </button>
      </div>

      {/* Progress bar */}
      {status && (
        <div className="mb-6 p-3 rounded-lg border border-border bg-surface">
          <div className="flex justify-between text-xs text-muted-foreground mb-1.5">
            <span>
              {status.total_embedded} / {status.total_extracted} signals ready
            </span>
            <span>{progressPct}%{status.ready ? " · ready to proceed" : ""}</span>
          </div>
          <div className="h-2 rounded bg-muted overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-500"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>
      )}

      {loadingNuggets && (
        <p className="text-sm text-muted-foreground">Loading your signals…</p>
      )}

      {!loadingNuggets && nuggets.length === 0 && (
        <div className="p-8 rounded-xl border border-border text-center">
          <p className="text-sm text-muted-foreground">
            No nuggets yet. Your resume is still being processed — please wait or hit Proceed to retry.
          </p>
        </div>
      )}

      {/* Nugget cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {nuggets.map((n) => {
          const fu = followUps[n.id];
          return (
            <div
              key={n.id}
              className="rounded-xl border border-border bg-surface overflow-hidden"
            >
              <button
                onClick={() => expandNugget(n)}
                className="w-full text-left p-4 hover:bg-muted/30"
              >
                <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                  <span className="px-1.5 py-0.5 rounded bg-muted font-mono">
                    {n.importance}
                  </span>
                  {n.company ? <span>{n.company}</span> : null}
                  {n.role ? <span>· {n.role}</span> : null}
                </div>
                <div className="text-sm line-clamp-3">{n.answer}</div>
              </button>
              {fu && fu.questions.length === 0 && (
                <div className="border-t border-border p-3 text-xs text-muted-foreground">
                  Generating follow-ups…
                </div>
              )}
              {fu && fu.questions.length > 0 && (
                <div className="border-t border-border divide-y divide-border">
                  {fu.questions.map((q, i) => (
                    <button
                      key={i}
                      onClick={() =>
                        setSelectedQuestion({ parentId: n.id, questionIndex: i })
                      }
                      className={`w-full text-left p-3 text-sm hover:bg-muted/30 flex items-center justify-between ${
                        fu.answered[i] ? "opacity-60" : ""
                      }`}
                    >
                      <span>{q}</span>
                      {fu.answered[i] && (
                        <span className="text-xs text-green-600 shrink-0 ml-2">✓ answered</span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Side panel — answer input */}
      {selectedQuestion && (
        <div className="fixed inset-0 z-50 bg-black/40" onClick={() => setSelectedQuestion(null)}>
          <div
            className="absolute right-0 top-0 h-full w-full max-w-lg bg-background border-l border-border p-6 overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-semibold mb-2">Your answer</h2>
            <p className="text-sm text-muted-foreground mb-4">
              {followUps[selectedQuestion.parentId]?.questions[selectedQuestion.questionIndex]}
            </p>
            <textarea
              value={answerDraft}
              onChange={(e) => setAnswerDraft(e.target.value)}
              placeholder="2-4 sentences. Include numbers, scale, or specific outcomes."
              rows={8}
              className="w-full p-3 rounded-lg border border-border bg-background text-sm"
            />
            <div className="flex gap-2 mt-4">
              <button
                onClick={() => {
                  setSelectedQuestion(null);
                  setAnswerDraft("");
                }}
                className="px-4 py-2 rounded-lg border border-border"
              >
                Cancel
              </button>
              <button
                onClick={saveAnswer}
                disabled={savingAnswer || answerDraft.trim().length < 10}
                className="px-4 py-2 rounded-lg bg-primary text-primary-foreground disabled:opacity-50"
              >
                {savingAnswer ? "Saving…" : "Save & embed"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
