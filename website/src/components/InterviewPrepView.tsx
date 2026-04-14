"use client";

import { useCallback, useEffect, useState } from "react";

interface PrepData {
  id: string;
  company: string;
  role: string;
  company_research: { dimension: string; findings: string; sources: string[] }[];
  round_breakdown: { round_name: string; likely_format: string; question_categories: string[]; prep_priority: string }[];
  star_stories: { question_type: string; example_question: string; situation: string; task: string; action: string; result: string; reflection: string; source_nugget: string }[];
  talking_points: { theme: string; key_message: string; supporting_evidence: string[] }[];
  questions_to_ask: { question: string; why_ask: string; when_to_ask: string }[];
}

function CollapsibleSection({ title, count, children, defaultOpen = false }: { title: string; count: number; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-2.5 bg-background hover:bg-surface transition-colors text-left"
      >
        <span className="text-sm font-medium text-foreground">{title}</span>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted bg-gray-100 rounded-full px-2 py-0.5">{count}</span>
          <svg className={`h-4 w-4 text-muted transition-transform ${open ? "rotate-180" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>
      {open && <div className="px-4 py-3 space-y-3 border-t border-border">{children}</div>}
    </div>
  );
}

export function InterviewPrepView({ applicationId }: { applicationId: string }) {
  const [prep, setPrep] = useState<PrepData | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  const fetchPrep = useCallback(async () => {
    try {
      const res = await fetch(`/api/interview-prep?application_id=${applicationId}`);
      const data = await res.json();
      setPrep(data.prep ?? null);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [applicationId]);

  useEffect(() => { fetchPrep(); }, [fetchPrep]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const res = await fetch("/api/interview-prep", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ application_id: applicationId }),
      });
      const data = await res.json();
      if (data.status === "generating") {
        // Poll for result
        const poll = setInterval(async () => {
          const r = await fetch(`/api/interview-prep?application_id=${applicationId}`);
          const d = await r.json();
          if (d.prep) { setPrep(d.prep); clearInterval(poll); setGenerating(false); }
        }, 4000);
        setTimeout(() => { clearInterval(poll); setGenerating(false); }, 90000);
      } else if (data.status === "already_exists") {
        fetchPrep();
        setGenerating(false);
      }
    } catch {
      setGenerating(false);
    }
  };

  if (loading) return <div className="text-sm text-muted">Loading interview prep...</div>;

  if (!prep) {
    return (
      <button
        onClick={handleGenerate}
        disabled={generating}
        className="w-full rounded-lg bg-purple-50 px-4 py-2.5 text-sm font-medium text-purple-700 hover:bg-purple-100 transition-colors disabled:opacity-50"
      >
        {generating ? "Generating prep (~30s)..." : "Prep for Interview"}
      </button>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Interview Prep</p>
        <span className="text-xs text-purple-600 font-medium">{prep.company} - {prep.role}</span>
      </div>

      {/* STAR Stories — most important, open by default */}
      <CollapsibleSection title="STAR Stories" count={prep.star_stories?.length ?? 0} defaultOpen>
        {prep.star_stories?.map((story, i) => (
          <div key={i} className="rounded-lg bg-surface p-3 space-y-1.5">
            <div className="flex items-start justify-between gap-2">
              <p className="text-sm font-medium text-foreground">{story.question_type}</p>
              <span className="text-[10px] text-muted shrink-0">{story.source_nugget?.slice(0, 30)}...</span>
            </div>
            <p className="text-xs text-accent italic">"{story.example_question}"</p>
            <div className="text-xs text-foreground space-y-1 leading-relaxed">
              <p><span className="font-medium text-gray-500">S:</span> {story.situation}</p>
              <p><span className="font-medium text-gray-500">T:</span> {story.task}</p>
              <p><span className="font-medium text-gray-500">A:</span> {story.action}</p>
              <p><span className="font-medium text-gray-500">R:</span> {story.result}</p>
              <p className="italic text-muted"><span className="font-medium">Reflection:</span> {story.reflection}</p>
            </div>
          </div>
        ))}
      </CollapsibleSection>

      {/* Company Research */}
      <CollapsibleSection title="Company Research" count={prep.company_research?.length ?? 0}>
        {prep.company_research?.map((dim, i) => (
          <div key={i}>
            <p className="text-sm font-medium text-foreground mb-0.5">{dim.dimension}</p>
            <p className="text-xs text-muted leading-relaxed">{dim.findings}</p>
          </div>
        ))}
      </CollapsibleSection>

      {/* Round Breakdown */}
      <CollapsibleSection title="Expected Rounds" count={prep.round_breakdown?.length ?? 0}>
        {prep.round_breakdown?.map((round, i) => (
          <div key={i} className="rounded-lg bg-surface p-2.5">
            <div className="flex items-center justify-between mb-1">
              <p className="text-sm font-medium text-foreground">{round.round_name}</p>
              <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${
                round.prep_priority === "high" ? "bg-red-50 text-red-600" :
                round.prep_priority === "medium" ? "bg-amber-50 text-amber-600" :
                "bg-gray-50 text-gray-500"
              }`}>{round.prep_priority}</span>
            </div>
            <p className="text-xs text-muted mb-1">{round.likely_format}</p>
            <div className="flex flex-wrap gap-1">
              {round.question_categories.map((cat, j) => (
                <span key={j} className="text-[10px] bg-gray-100 text-gray-600 rounded px-1.5 py-0.5">{cat}</span>
              ))}
            </div>
          </div>
        ))}
      </CollapsibleSection>

      {/* Talking Points */}
      <CollapsibleSection title="Key Talking Points" count={prep.talking_points?.length ?? 0}>
        {prep.talking_points?.map((tp, i) => (
          <div key={i}>
            <p className="text-sm font-medium text-foreground">{tp.theme}</p>
            <p className="text-xs text-muted mb-1">{tp.key_message}</p>
            <ul className="text-[10px] text-gray-500 list-disc pl-4 space-y-0.5">
              {tp.supporting_evidence.map((e, j) => <li key={j}>{e}</li>)}
            </ul>
          </div>
        ))}
      </CollapsibleSection>

      {/* Questions to Ask */}
      <CollapsibleSection title="Questions to Ask" count={prep.questions_to_ask?.length ?? 0}>
        {prep.questions_to_ask?.map((q, i) => (
          <div key={i} className="rounded-lg bg-surface p-2.5">
            <p className="text-sm font-medium text-foreground mb-0.5">{q.question}</p>
            <p className="text-xs text-muted">{q.why_ask}</p>
            <p className="text-[10px] text-gray-400 mt-0.5">Ask during: {q.when_to_ask}</p>
          </div>
        ))}
      </CollapsibleSection>
    </div>
  );
}
