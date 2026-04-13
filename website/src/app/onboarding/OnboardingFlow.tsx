"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ChatMessage, type Message } from "./ChatMessage";
import { ConfirmDenyButtons } from "./ConfirmDenyButtons";
import { StepLifeOS } from "./StepLifeOS";
import { ConfidenceProgressBar } from "@/components/ConfidenceProgressBar";
import { CareerGraph, type CytoElement } from "@/components/CareerGraph";

// ── Types ──────────────────────────────────────────────────────────────────

// [BYOK-REMOVED] type Step = 1 | 2 | 3 | 4 | 5;
type Step = 1 | 2 | 3 | 4;

const ROLE_OPTIONS = [
  "Product Manager",
  "Software Engineer",
  "Data Analyst",
  "UX Designer",
  "Marketing",
  "Finance",
  "Operations",
  "Other",
];

// [BYOK-REMOVED] const PROVIDER_MODEL_MAP: Record<string, string> = {
// [BYOK-REMOVED]   groq:        "llama-3.1-8b-instant",
// [BYOK-REMOVED]   cerebras:    "llama3.1-8b",
// [BYOK-REMOVED]   sambanova:   "Meta-Llama-3.1-8B-Instruct",
// [BYOK-REMOVED]   siliconflow: "Qwen/Qwen3-8B",
// [BYOK-REMOVED]   openrouter:  "meta-llama/llama-3.2-3b-instruct:free",
// [BYOK-REMOVED]   gemini:      "gemini-1.5-flash-8b",
// [BYOK-REMOVED] };

interface Education {
  institution: string;
  degree: string;
  year: string;
}

interface ConversationTurn {
  userAnswer: string;
  paraphrase: string;
  confirmed: boolean;
}

// ── Step 1: Welcome + Target Roles ────────────────────────────────────────

function StepWelcome({
  selectedRoles,
  onRolesChange,
  onNext,
}: {
  selectedRoles: string[];
  onRolesChange: (roles: string[]) => void;
  onNext: () => void;
}) {
  const toggle = (role: string) => {
    onRolesChange(
      selectedRoles.includes(role)
        ? selectedRoles.filter((r) => r !== role)
        : [...selectedRoles, role]
    );
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-foreground">
          Welcome to LinkRight
        </h1>
        <p className="mt-2 text-muted">
          What kind of roles are you targeting?
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        {ROLE_OPTIONS.map((role) => {
          const selected = selectedRoles.includes(role);
          return (
            <button
              key={role}
              onClick={() => toggle(role)}
              className={`rounded-full px-4 py-2 text-sm font-medium border transition-colors ${
                selected
                  ? "bg-primary-500 border-primary-500 text-white"
                  : "bg-surface border-border text-foreground hover:border-primary-400 hover:text-primary-600"
              }`}
            >
              {role}
            </button>
          );
        })}
      </div>

      <button
        onClick={onNext}
        disabled={selectedRoles.length === 0}
        className="w-full rounded-xl bg-primary-500 px-6 py-3 text-base font-semibold text-white hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        Get Started
      </button>
    </div>
  );
}

// [BYOK-REMOVED] ── Step 2: API Key Setup (entire component removed) ─────────
// [BYOK-REMOVED] StepApiKey component was here — users no longer manage API keys.
// [BYOK-REMOVED] See git history for the full component if needed.

// ── Step 3: Career Basics Form ────────────────────────────────────────────

function StepCareerBasics({
  onNext,
  onSkip,
  // [BYOK-REMOVED] modelProvider,
  // [BYOK-REMOVED] modelId,
  // [BYOK-REMOVED] apiKey,
}: {
  onNext: () => void;
  onSkip: () => void;
  // [BYOK-REMOVED] modelProvider: string;
  // [BYOK-REMOVED] modelId: string;
  // [BYOK-REMOVED] apiKey: string;
}) {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [linkedin, setLinkedin] = useState("");
  const [education, setEducation] = useState<Education[]>([
    { institution: "", degree: "", year: "" },
  ]);
  const [skillInput, setSkillInput] = useState("");
  const [skills, setSkills] = useState<string[]>([]);
  const [certifications, setCertifications] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  // Resume upload / paste state
  const [uploadMode, setUploadMode] = useState<"none" | "paste" | "file">("none");
  const [resumePasteText, setResumePasteText] = useState("");
  const [parsing, setParsing] = useState(false);
  const [parseError, setParseError] = useState("");
  const [parsed, setParsed] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const applyParsed = (data: Record<string, unknown>) => {
    if (typeof data.full_name === "string" && data.full_name) setFullName(data.full_name);
    if (typeof data.email === "string" && data.email) setEmail(data.email);
    if (typeof data.phone === "string" && data.phone) setPhone(data.phone);
    if (typeof data.linkedin === "string" && data.linkedin) setLinkedin(data.linkedin);
    if (Array.isArray(data.education) && data.education.length > 0) {
      const edu = (data.education as Array<{ institution?: string; degree?: string; year?: string }>).map((e) => ({
        institution: e.institution ?? "",
        degree: e.degree ?? "",
        year: e.year ?? "",
      }));
      setEducation(edu.length > 0 ? edu : [{ institution: "", degree: "", year: "" }]);
    }
    if (Array.isArray(data.skills) && data.skills.length > 0) {
      setSkills(data.skills.filter((s): s is string => typeof s === "string"));
    }
    if (Array.isArray(data.certifications) && data.certifications.length > 0) {
      setCertifications((data.certifications as string[]).join("\n"));
    }
    setParsed(true);
    setUploadMode("none");
  };

  const handleParsePaste = async () => {
    if (!resumePasteText.trim()) return;
    setParsing(true);
    setParseError("");
    try {
      const res = await fetch("/api/onboarding/parse-resume", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: resumePasteText.trim(),
          // [BYOK-REMOVED] model_provider: modelProvider,
          // [BYOK-REMOVED] model_id: modelId,
          // [BYOK-REMOVED] api_key: apiKey,
        }),
      });
      const data = await res.json();
      if (res.ok && data.parsed) {
        applyParsed(data.parsed);
      } else {
        setParseError(data.error ?? "Could not parse resume. Please fill in manually.");
      }
    } catch {
      setParseError("Network error. Please try again.");
    } finally {
      setParsing(false);
    }
  };

  const handleParseFile = async (file: File) => {
    // 500KB limit — larger files risk breaking the LLM token budget
    if (file.size > 500 * 1024) {
      setParseError("File too large (max 500 KB). Please paste your resume text instead.");
      setUploadMode("paste");
      return;
    }
    setParsing(true);
    setParseError("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      // [BYOK-REMOVED] formData.append("model_provider", modelProvider);
      // [BYOK-REMOVED] formData.append("model_id", modelId);
      // [BYOK-REMOVED] formData.append("api_key", apiKey);
      const res = await fetch("/api/onboarding/parse-resume", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (res.ok && data.parsed) {
        applyParsed(data.parsed);
      } else {
        setParseError(data.error ?? "Could not parse file. Please paste your resume text instead.");
        setUploadMode("paste");
      }
    } catch {
      setParseError("Network error. Please try again.");
    } finally {
      setParsing(false);
    }
  };

  const addEducation = () => {
    setEducation([...education, { institution: "", degree: "", year: "" }]);
  };

  const updateEducation = (
    idx: number,
    field: keyof Education,
    value: string
  ) => {
    setEducation(
      education.map((e, i) => (i === idx ? { ...e, [field]: value } : e))
    );
  };

  const removeEducation = (idx: number) => {
    setEducation(education.filter((_, i) => i !== idx));
  };

  const handleSkillKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "," || e.key === "Enter") {
      e.preventDefault();
      const trimmed = skillInput.trim().replace(/,$/, "");
      if (trimmed && !skills.includes(trimmed)) {
        setSkills([...skills, trimmed]);
      }
      setSkillInput("");
    }
  };

  const removeSkill = (skill: string) => {
    setSkills(skills.filter((s) => s !== skill));
  };

  const handleSave = async () => {
    if (!fullName.trim()) {
      setError("Full name is required.");
      return;
    }
    setSaving(true);
    setError("");

    const educationLines = education
      .filter((e) => e.institution || e.degree)
      .map((e) => `- ${e.degree} at ${e.institution}${e.year ? ` (${e.year})` : ""}`)
      .join("\n");

    const certLines = certifications
      .split("\n")
      .filter(Boolean)
      .map((c) => `- ${c.trim()}`)
      .join("\n");

    const careerText = [
      fullName && `Name: ${fullName}`,
      email && `Email: ${email}`,
      phone && `Phone: ${phone}`,
      linkedin && `LinkedIn: ${linkedin}`,
      educationLines && `Education:\n${educationLines}`,
      skills.length > 0 && `Skills: ${skills.join(", ")}`,
      certLines && `Certifications:\n${certLines}`,
    ]
      .filter(Boolean)
      .join("\n");

    try {
      const res = await fetch("/api/user/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ career_text: careerText }),
      });

      if (res.ok) {
        onNext();
      } else {
        const data = await res.json();
        setError(data.error ?? "Failed to save. Please try again.");
      }
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const inputClass =
    "w-full rounded-lg border border-border bg-surface px-3 py-2.5 text-sm text-foreground placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary-500";

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-foreground">
          Tell us about yourself
        </h1>
        <p className="mt-2 text-muted">
          These basics help us generate more accurate resumes. All fields except
          name are optional.
        </p>
      </div>

      {/* Resume upload shortcut */}
      {!parsed && uploadMode === "none" && (
        <div className="rounded-xl border border-dashed border-border bg-surface p-5 space-y-3">
          <p className="text-sm font-medium text-foreground">
            Have an existing resume? Auto-fill this form.
          </p>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setUploadMode("paste")}
              className="rounded-lg border border-border bg-background px-4 py-2 text-sm font-medium text-foreground hover:bg-surface-hover transition-colors"
            >
              Paste resume text
            </button>
            <button
              onClick={() => fileInputRef.current?.click()}
              className="rounded-lg border border-border bg-background px-4 py-2 text-sm font-medium text-foreground hover:bg-surface-hover transition-colors"
            >
              Upload PDF / DOCX / TXT
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.doc,.txt,.text,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleParseFile(file);
                e.target.value = "";
              }}
            />
          </div>
          {parsing && (
            <p className="text-sm text-primary-600 animate-pulse">
              Parsing your resume…
            </p>
          )}
          {parseError && (
            <p className="text-sm text-red-600">{parseError}</p>
          )}
        </div>
      )}

      {uploadMode === "paste" && (
        <div className="rounded-xl border border-primary-200 bg-primary-50 p-5 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-primary-700">
              Paste your resume text
            </p>
            <button
              onClick={() => { setUploadMode("none"); setParseError(""); }}
              className="text-xs text-muted hover:text-foreground transition-colors"
            >
              Cancel
            </button>
          </div>
          <textarea
            value={resumePasteText}
            onChange={(e) => setResumePasteText(e.target.value)}
            placeholder="Paste your resume here — all sections, plain text…"
            rows={8}
            className="w-full rounded-lg border border-primary-200 bg-white px-3 py-2.5 text-sm text-foreground placeholder:text-muted resize-none focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          {parseError && (
            <p className="text-sm text-red-600">{parseError}</p>
          )}
          <button
            onClick={handleParsePaste}
            disabled={!resumePasteText.trim() || parsing}
            className="w-full rounded-lg bg-primary-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {parsing ? "Parsing…" : "Auto-fill from resume"}
          </button>
        </div>
      )}

      {parsed && (
        <div className="flex items-center justify-between gap-2 rounded-lg border border-green-200 bg-green-50 px-4 py-2.5 text-sm text-green-700">
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            Resume parsed — fields pre-filled below. Edit anything that looks wrong.
          </div>
          <button
            onClick={() => { setParsed(false); setUploadMode("none"); setParseError(""); }}
            className="shrink-0 text-xs text-green-600 underline hover:text-green-800 transition-colors"
          >
            Change resume
          </button>
        </div>
      )}

      <div className="space-y-4">
        {/* Basic info */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-foreground">
              Full Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Jane Smith"
              className={inputClass}
            />
          </div>
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-foreground">
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="jane@example.com"
              className={inputClass}
            />
          </div>
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-foreground">
              Phone
            </label>
            <input
              type="text"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+1 (555) 000-0000"
              className={inputClass}
            />
          </div>
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-foreground">
              LinkedIn URL
            </label>
            <input
              type="text"
              value={linkedin}
              onChange={(e) => setLinkedin(e.target.value)}
              placeholder="https://linkedin.com/in/jane"
              className={inputClass}
            />
          </div>
        </div>

        {/* Education */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-foreground">
            Education
          </label>
          {education.map((edu, idx) => (
            <div key={idx} className="flex gap-2 items-start">
              <input
                type="text"
                value={edu.institution}
                onChange={(e) =>
                  updateEducation(idx, "institution", e.target.value)
                }
                placeholder="Institution"
                className="flex-1 rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <input
                type="text"
                value={edu.degree}
                onChange={(e) =>
                  updateEducation(idx, "degree", e.target.value)
                }
                placeholder="Degree"
                className="flex-1 rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <input
                type="text"
                value={edu.year}
                onChange={(e) => updateEducation(idx, "year", e.target.value)}
                placeholder="Year"
                className="w-32 rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              {education.length > 1 && (
                <button
                  onClick={() => removeEducation(idx)}
                  className="mt-1 text-muted hover:text-red-500 transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>
          ))}
          <button
            onClick={addEducation}
            className="text-sm text-primary-600 hover:text-primary-700 font-medium"
          >
            + Add Education
          </button>
        </div>

        {/* Skills */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-foreground">
            Skills
          </label>
          <input
            type="text"
            value={skillInput}
            onChange={(e) => setSkillInput(e.target.value)}
            onKeyDown={handleSkillKeyDown}
            placeholder="Type a skill and press Enter or comma"
            className={inputClass}
          />
          {skills.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-1">
              {skills.map((skill) => (
                <span
                  key={skill}
                  className="flex items-center gap-1 rounded-full bg-primary-100 text-primary-700 px-3 py-1 text-xs font-medium"
                >
                  {skill}
                  <button
                    onClick={() => removeSkill(skill)}
                    className="hover:text-primary-900 transition-colors"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Certifications */}
        <div className="space-y-1.5">
          <label className="block text-sm font-medium text-foreground">
            Certifications
          </label>
          <textarea
            value={certifications}
            onChange={(e) => setCertifications(e.target.value)}
            placeholder="One certification per line&#10;e.g. AWS Solutions Architect&#10;PMP Certified"
            rows={3}
            className="w-full rounded-lg border border-border bg-surface px-3 py-2.5 text-sm text-foreground placeholder:text-muted resize-none focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex gap-3 pb-8">
        <button
          onClick={handleSave}
          disabled={saving || !fullName.trim()}
          className="flex-1 rounded-xl bg-primary-500 px-6 py-3 text-base font-semibold text-white hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {saving ? "Saving…" : "Save & Continue"}
        </button>
        <button
          onClick={onSkip}
          className="rounded-xl border border-border px-6 py-3 text-base font-medium text-muted hover:bg-surface-hover transition-colors"
        >
          I&apos;ll add this later
        </button>
      </div>
    </div>
  );
}

// ── Step 4: TruthEngine Conversation ─────────────────────────────────────

function StepConversation({
  selectedRoles,
  // [BYOK-REMOVED] modelProvider,
  // [BYOK-REMOVED] modelId,
  // [BYOK-REMOVED] apiKey,
  onDone,
}: {
  selectedRoles: string[];
  // [BYOK-REMOVED] modelProvider: string;
  // [BYOK-REMOVED] modelId: string;
  // [BYOK-REMOVED] apiKey: string;
  onDone: () => void;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState("");
  const [sending, setSending] = useState(false);
  const [nuggetCount, setNuggetCount] = useState(0);
  const [conversationHistory, setConversationHistory] = useState<
    Array<{ role: string; content: string }>
  >([]);
  const [pendingConfirm, setPendingConfirm] = useState<{
    paraphrase: string;
    userAnswer: string;
  } | null>(null);
  const [waitingForConfirm, setWaitingForConfirm] = useState(false);
  const [showDoneConfirm, setShowDoneConfirm] = useState(false);
  const [finalStats, setFinalStats] = useState<{
    nugget_count: number;
    confidence: number;
  } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const addMessage = (role: "system" | "user", content: string): Message => {
    const msg: Message = { id: crypto.randomUUID(), role, content };
    setMessages((prev) => [...prev, msg]);
    return msg;
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, pendingConfirm]);

  // Fetch initial question on mount
  useEffect(() => {
    let mounted = true;
    async function fetchFirstQuestion() {
      setSending(true);
      try {
        const res = await fetch("/api/onboarding/question", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            target_roles: selectedRoles,
            conversation_history: [],
            confirmed_nuggets: [],
            // [BYOK-REMOVED] model_provider: modelProvider,
            // [BYOK-REMOVED] model_id: modelId,
            // [BYOK-REMOVED] api_key: apiKey,
          }),
        });
        const data = await res.json();
        if (mounted && data.question) {
          addMessage("system", data.question);
        } else if (mounted) {
          addMessage("system", "Tell me about your most recent work experience.");
        }
      } catch {
        if (mounted) {
          addMessage("system", "Tell me about your most recent work experience.");
        }
      } finally {
        if (mounted) setSending(false);
      }
    }
    fetchFirstQuestion();
    return () => { mounted = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchNextQuestion = async (
    updatedHistory: Array<{ role: string; content: string }>,
    confirmedCount: number
  ) => {
    setSending(true);
    try {
      const res = await fetch("/api/onboarding/question", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_roles: selectedRoles,
          conversation_history: updatedHistory,
          confirmed_nuggets: Array(confirmedCount).fill(""),
          // [BYOK-REMOVED] model_provider: modelProvider,
          // [BYOK-REMOVED] model_id: modelId,
          // [BYOK-REMOVED] api_key: apiKey,
        }),
      });
      const data = await res.json();
      if (data.question) {
        addMessage("system", data.question);
      }
    } catch {
      addMessage("system", "What other achievements or projects would you like to highlight?");
    } finally {
      setSending(false);
    }
  };

  const handleSend = async () => {
    const text = inputText.trim();
    if (!text || sending || waitingForConfirm) return;

    setInputText("");
    addMessage("user", text);

    const newHistory = [
      ...conversationHistory,
      { role: "user", content: text },
    ];
    setConversationHistory(newHistory);

    // Fetch paraphrase via confirm route with a preview (just use the question flow for paraphrase)
    setSending(true);
    setWaitingForConfirm(true);
    try {
      const res = await fetch("/api/onboarding/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_answer: text,
          action: "confirm",
          // [BYOK-REMOVED] model_provider: modelProvider,
          // [BYOK-REMOVED] model_id: modelId,
          // [BYOK-REMOVED] api_key: apiKey,
        }),
      });
      const data = await res.json();

      if (res.ok && data.paraphrase) {
        addMessage("system", data.paraphrase);
        // We already confirmed and created the nugget in this flow
        const newCount = nuggetCount + 1;
        setNuggetCount(newCount);
        setWaitingForConfirm(false);

        const updatedHistory = [
          ...newHistory,
          { role: "assistant", content: data.paraphrase },
        ];
        setConversationHistory(updatedHistory);

        addMessage("system", "Saved! ✓");
        await fetchNextQuestion(updatedHistory, newCount);
      } else {
        // Paraphrase extraction failed — ask to rephrase
        addMessage("system", "I had trouble processing that. Could you rephrase or add more details?");
        setWaitingForConfirm(false);
        setSending(false);
      }
    } catch {
      addMessage("system", "Something went wrong. Please try again.");
      setWaitingForConfirm(false);
      setSending(false);
    }
  };

  const handleConfirm = async () => {
    if (!pendingConfirm) return;
    setSending(true);
    try {
      const res = await fetch("/api/onboarding/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_answer: pendingConfirm.userAnswer,
          action: "confirm",
          // [BYOK-REMOVED] model_provider: modelProvider,
          // [BYOK-REMOVED] model_id: modelId,
          // [BYOK-REMOVED] api_key: apiKey,
        }),
      });
      const data = await res.json();

      if (res.ok) {
        const newCount = nuggetCount + 1;
        setNuggetCount(newCount);
        setPendingConfirm(null);
        setWaitingForConfirm(false);

        addMessage("system", "Saved! ✓");

        const updatedHistory = [
          ...conversationHistory,
          { role: "assistant", content: "Confirmed and saved." },
        ];
        setConversationHistory(updatedHistory);

        await fetchNextQuestion(updatedHistory, newCount);
      } else {
        addMessage("system", data.error ?? "Failed to save. Please try again.");
        setSending(false);
      }
    } catch {
      addMessage("system", "Failed to save. Please try again.");
      setSending(false);
    }
  };

  const handleCorrect = async (correctedText: string) => {
    if (!pendingConfirm) return;
    setSending(true);
    try {
      const res = await fetch("/api/onboarding/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_answer: pendingConfirm.userAnswer,
          action: "correct",
          correction: correctedText,
          // [BYOK-REMOVED] model_provider: modelProvider,
          // [BYOK-REMOVED] model_id: modelId,
          // [BYOK-REMOVED] api_key: apiKey,
        }),
      });
      const data = await res.json();

      if (res.ok && data.updated_paraphrase) {
        addMessage("system", data.updated_paraphrase);
        setPendingConfirm({
          paraphrase: data.updated_paraphrase,
          userAnswer: correctedText,
        });
      } else {
        addMessage("system", "Could not update paraphrase. Please confirm or try again.");
      }
    } catch {
      addMessage("system", "Network error. Please try again.");
    } finally {
      setSending(false);
    }
  };

  const handleDone = async () => {
    try {
      const res = await fetch("/api/onboarding/status");
      const data = await res.json();
      setFinalStats({
        nugget_count: data.nugget_count ?? nuggetCount,
        confidence: data.confidence ?? 0,
      });
      setShowDoneConfirm(true);
    } catch {
      setShowDoneConfirm(true);
      setFinalStats({ nugget_count: nuggetCount, confidence: 0 });
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (showDoneConfirm && finalStats) {
    return (
      <div className="space-y-6 text-center">
        <div>
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary-100">
            <svg className="h-8 w-8 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-foreground">
            Great job!
          </h2>
          <p className="mt-2 text-muted">
            You&apos;ve captured{" "}
            <span className="font-semibold text-primary-600">
              {finalStats.nugget_count} career nuggets
            </span>
            .
          </p>
        </div>
        <button
          onClick={onDone}
          className="w-full rounded-xl bg-primary-500 px-6 py-3 text-base font-semibold text-white hover:bg-primary-600 transition-colors"
        >
          Create Your First Resume
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full space-y-4">
      <div>
        <h1 className="text-3xl font-bold text-foreground">
          Let&apos;s capture your experience
        </h1>
        <p className="mt-2 text-muted">
          I&apos;ll ask you questions to understand your career. Answer
          naturally — the more detail, the better.
        </p>
      </div>

      {/* Nugget counter */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted">
          <span className="font-semibold text-primary-600">{nuggetCount}</span>{" "}
          nuggets captured
        </span>
        <button
          onClick={handleDone}
          disabled={sending}
          className="text-sm text-muted hover:text-foreground underline transition-colors"
        >
          I&apos;m done
        </button>
      </div>

      {/* Chat window */}
      <div className="flex-1 min-h-[320px] max-h-[420px] overflow-y-auto rounded-xl border border-border bg-background p-4 space-y-1">
        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}
        {pendingConfirm && (
          <div className="px-1">
            <ConfirmDenyButtons
              originalAnswer={pendingConfirm.userAnswer}
              onConfirm={handleConfirm}
              onCorrect={handleCorrect}
              disabled={sending}
            />
          </div>
        )}
        {sending && !waitingForConfirm && (
          <div className="flex justify-start mb-3">
            <div className="rounded-2xl rounded-tl-sm bg-surface border border-border px-4 py-3">
              <span className="flex gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-muted animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-1.5 h-1.5 rounded-full bg-muted animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-1.5 h-1.5 rounded-full bg-muted animate-bounce" style={{ animationDelay: "300ms" }} />
              </span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="flex gap-2 items-end">
        <textarea
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            waitingForConfirm
              ? "Please confirm or correct the paraphrase above…"
              : "Type your answer… (Enter to send, Shift+Enter for newline)"
          }
          disabled={sending || waitingForConfirm}
          rows={2}
          className="flex-1 rounded-xl border border-border bg-surface px-4 py-3 text-sm text-foreground placeholder:text-muted resize-none focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-60"
        />
        <button
          onClick={handleSend}
          disabled={!inputText.trim() || sending || waitingForConfirm}
          className="rounded-xl bg-primary-500 px-4 py-3 text-white hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
        </button>
      </div>
    </div>
  );
}

// ── Step 5: Summary / Completion screen ──────────────────────────────────

interface SummaryStats {
  nugget_count: number;
  confidence: number;
  companies?: string[];
  label?: "excellent" | "good" | "fair" | "insufficient";
}

interface GraphData {
  elements: CytoElement[];
  stats: {
    achievements: number;
    experiences: number;
    skills: number;
    companies: { name: string; role: string; count: number }[];
    topSkills: { name: string; count: number }[];
  };
}

function StepSummary({ initialStats, onBack }: { initialStats?: SummaryStats; onBack?: () => void }) {
  const router = useRouter();
  const [stats, setStats] = useState<SummaryStats | null>(initialStats ?? null);
  const [loading, setLoading] = useState(!initialStats);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [graphLoading, setGraphLoading] = useState(true);

  useEffect(() => {
    if (initialStats) return;
    let cancelled = false;
    let pollCount = 0;
    const MAX_POLLS = 12; // 60s max polling (12 × 5s)

    const fetchStats = () => {
      fetch("/api/onboarding/status")
        .then((r) => r.json())
        .then((data) => {
          if (cancelled) return;
          // data.confidence is an object { score, label, nugget_count } — not a number
          const score: number = data.confidence?.score ?? 0;
          const nuggetCount: number = data.confidence?.nugget_count ?? 0;
          const label: SummaryStats["label"] =
            score >= 90 ? "excellent" : score >= 75 ? "good" : score >= 60 ? "fair" : "insufficient";
          setStats({ nugget_count: nuggetCount, confidence: score, label });

          // Stop polling once we have real data
          if (nuggetCount > 0) cancelled = true;
        })
        .catch(() => {
          if (!cancelled) setStats({ nugget_count: 0, confidence: 0, label: "insufficient" });
        })
        .finally(() => setLoading(false));
    };

    // Fetch immediately on mount
    fetchStats();

    // Poll every 5s to pick up newly created nuggets (async atom→nugget pipeline)
    const interval = setInterval(() => {
      pollCount++;
      if (cancelled || pollCount >= MAX_POLLS) {
        clearInterval(interval);
        return;
      }
      fetchStats();
    }, 5_000);

    return () => { cancelled = true; clearInterval(interval); };
  }, [initialStats]);

  useEffect(() => {
    fetch("/api/profile/career-graph")
      .then((r) => r.json())
      .then((data) => setGraphData(data))
      .catch(() => setGraphData(null))
      .finally(() => setGraphLoading(false));
  }, []);

  const score = stats?.confidence ?? 0;
  const hasGraph = graphData && graphData.elements.length > 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary-100">
          <svg className="h-8 w-8 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 className="text-2xl font-bold text-foreground">You&apos;re ready!</h2>
        {hasGraph && (
          <p className="mt-1 text-sm text-muted">
            {graphData.stats.achievements} achievements · {graphData.stats.experiences} companies · {graphData.stats.skills} skills
          </p>
        )}
        {onBack && (
          <button
            onClick={onBack}
            className="mt-3 text-xs text-muted hover:text-foreground underline underline-offset-2 transition-colors"
          >
            ← Add more achievements
          </button>
        )}
      </div>

      {/* Career Knowledge Graph */}
      {graphLoading ? (
        <div className="h-[420px] rounded-xl border border-border bg-surface flex items-center justify-center">
          <span className="flex gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-muted animate-bounce" style={{ animationDelay: "0ms" }} />
            <span className="w-1.5 h-1.5 rounded-full bg-muted animate-bounce" style={{ animationDelay: "150ms" }} />
            <span className="w-1.5 h-1.5 rounded-full bg-muted animate-bounce" style={{ animationDelay: "300ms" }} />
          </span>
        </div>
      ) : hasGraph ? (
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted uppercase tracking-wide">Your Career Knowledge Graph</p>
          <CareerGraph elements={graphData.elements} />
        </div>
      ) : null}

      {/* Stats row */}
      {!loading && stats && (
        <div className="space-y-4 text-left">
          <ConfidenceProgressBar
            score={score}
            label={stats.label}
            nuggetCount={stats.nugget_count}
          />

          {/* Company + skills breakdown side by side */}
          {hasGraph && (
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-xl border border-border bg-surface p-4 space-y-2">
                <p className="text-[10px] font-medium text-muted uppercase tracking-wide">By Company</p>
                {graphData.stats.companies.slice(0, 5).map((c) => (
                  <div key={`${c.name}:${c.role}`} className="flex items-center justify-between">
                    <span className="text-xs text-foreground truncate max-w-[120px]">{c.name}</span>
                    <span className="text-xs text-muted shrink-0">{c.count}</span>
                  </div>
                ))}
              </div>
              <div className="rounded-xl border border-border bg-surface p-4 space-y-2">
                <p className="text-[10px] font-medium text-muted uppercase tracking-wide">Top Skills</p>
                {graphData.stats.topSkills.slice(0, 5).map((s, i) => (
                  <div key={s.name} className="flex items-center justify-between">
                    <span className="text-xs text-foreground truncate max-w-[120px]">
                      {i + 1}. {s.name}
                    </span>
                    <span className="text-xs text-muted shrink-0">{s.count}×</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {score < 60 && (
            <div className="rounded-xl border border-yellow-200 bg-yellow-50 px-4 py-3">
              <p className="text-sm text-yellow-800">
                Consider adding more details for better resume quality. You can always come back and add more experience.
              </p>
            </div>
          )}
        </div>
      )}

      {/* CTA buttons */}
      <div className="space-y-3">
        <Link
          href="/resume/new"
          className="block w-full rounded-xl bg-primary-500 px-6 py-3 text-center text-base font-semibold text-white hover:bg-primary-600 transition-colors"
        >
          Create Your First Resume
        </Link>
        <Link
          href="/dashboard"
          className="block w-full rounded-xl border border-border px-6 py-3 text-center text-base font-medium text-muted hover:bg-surface-hover transition-colors"
        >
          Go to Dashboard
        </Link>
      </div>
    </div>
  );
}

// ── Progress bar ──────────────────────────────────────────────────────────

// [BYOK-REMOVED] const STEP_LABELS = ["Roles", "API Key", "Profile", "TruthEngine", "Summary"];
const STEP_LABELS = ["Roles", "Profile", "TruthEngine", "Summary"];

function ProgressBar({ step }: { step: Step }) {
  const totalSteps = 4;
  const currentIndex = Math.min(step - 1, totalSteps - 1);

  return (
    <div className="mb-10">
      <div className="flex justify-between mb-2">
        {STEP_LABELS.map((label, idx) => (
          <span
            key={label}
            className={`text-xs font-medium ${
              idx <= currentIndex ? "text-primary-600" : "text-muted"
            }`}
          >
            {label}
          </span>
        ))}
      </div>
      <div className="h-1.5 w-full rounded-full bg-border">
        <div
          className="h-1.5 rounded-full bg-primary-500 transition-all duration-300"
          style={{ width: `${(currentIndex / (totalSteps - 1)) * 100}%` }}
        />
      </div>
    </div>
  );
}

// ── Main OnboardingFlow ───────────────────────────────────────────────────

const ROLES_KEY = "lr_selected_roles";

export function OnboardingFlow() {
  const [step, setStep] = useState<Step | null>(null); // null = loading
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);

  // On mount: restore target roles from localStorage + detect step from Supabase
  useEffect(() => {
    const saved = localStorage.getItem(ROLES_KEY);
    if (saved) {
      try { setSelectedRoles(JSON.parse(saved)); } catch { /* ignore */ }
    }

    fetch("/api/onboarding/status")
      .then((r) => r.json())
      .then((data: {
        has_career_data?: boolean;
        session_started?: boolean;
        session_complete?: boolean;
      }) => {
        if (data.session_complete || data.session_started) {
          // Interview done or in progress → jump to summary or skill step
          setStep(data.session_complete ? 4 : 3);
        } else if (data.has_career_data) {
          // Career basics saved → skip to interview step
          setStep(3);
        } else {
          // Fresh user: start from step 1 (roles) or step 2 if roles already picked
          const hasSavedRoles = !!saved && JSON.parse(saved).length > 0;
          setStep(hasSavedRoles ? 2 : 1);
        }
      })
      .catch(() => setStep(1)); // fallback: show step 1
  }, []);

  const handleRolesChange = (roles: string[]) => {
    setSelectedRoles(roles);
    localStorage.setItem(ROLES_KEY, JSON.stringify(roles));
  };

  if (step === null) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="h-6 w-6 rounded-full border-2 border-primary-500 border-t-transparent animate-spin" />
      </div>
    );
  }

  return (
    <div>
      {step <= 4 && <ProgressBar step={step} />}

      {step === 1 && (
        <StepWelcome
          selectedRoles={selectedRoles}
          onRolesChange={handleRolesChange}
          onNext={() => setStep(2)}
        />
      )}

      {/* [BYOK-REMOVED] Step 2 was StepApiKey — removed */}

      {step === 2 && (
        <StepCareerBasics
          onNext={() => setStep(3)}
          onSkip={() => setStep(3)}
          // [BYOK-REMOVED] modelProvider={modelProvider}
          // [BYOK-REMOVED] modelId={modelId}
          // [BYOK-REMOVED] apiKey={apiKey}
        />
      )}

      {step === 3 && (
        // [LIFEOS] StepConversation replaced with StepLifeOS (Custom GPT career coaching session)
        <StepLifeOS onDone={() => setStep(4)} />
      )}

      {step === 4 && <StepSummary onBack={() => setStep(3)} />}
    </div>
  );
}
