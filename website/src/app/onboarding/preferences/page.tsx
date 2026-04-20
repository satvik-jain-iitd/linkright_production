// Wave 2 / Screen 07 — Preferences.
// Design handoff: specs/design-handoff-v2-2026-04-18 → screens-build.jsx Screen07.
// Chip-based multi-select for target roles, location, cities, company stage.
// Notice period + compensation range (no work authorisation per v2 audit).

"use client";

import { useEffect, useState, useMemo } from "react";
import { useRouter } from "next/navigation";

type Prefs = {
  location_preference: string;
  preferred_locations: string[];
  preferred_stages: string[];
  target_roles: string[];
  min_comp_usd: number | null;
  max_comp_usd: number | null;
  notice_period_days: number | null;
};

const EMPTY: Prefs = {
  location_preference: "any",
  preferred_locations: [],
  preferred_stages: [],
  target_roles: [],
  min_comp_usd: null,
  max_comp_usd: null,
  notice_period_days: null,
};

const STEPS = [
  { n: 1, label: "Resume", state: "done" as const },
  { n: 2, label: "Profile", state: "done" as const },
  { n: 3, label: "Preferences", state: "active" as const },
  { n: 4, label: "First match", state: "todo" as const },
];

const LOCATION_OPTIONS = [
  { v: "remote_only", label: "Remote" },
  { v: "hybrid_ok", label: "Hybrid" },
  { v: "onsite_ok", label: "Onsite" },
  { v: "any", label: "Any" },
];

const CITY_SUGGESTIONS = [
  "Bangalore",
  "Delhi NCR",
  "Mumbai",
  "Pune",
  "Hyderabad",
  "Chennai",
  "Remote-India",
];

const STAGE_OPTIONS = [
  { v: "seed", label: "Seed" },
  { v: "series_a", label: "Series A" },
  { v: "series_b", label: "Series B" },
  { v: "series_c", label: "Series C" },
  { v: "series_d_plus", label: "Series D+" },
  { v: "public", label: "Public" },
  { v: "bootstrapped", label: "Bootstrapped" },
];

const NOTICE_PERIOD_OPTIONS = [
  { v: 0, label: "Immediate" },
  { v: 15, label: "15 days" },
  { v: 30, label: "30 days" },
  { v: 60, label: "60 days" },
  { v: 90, label: "90 days" },
];

const SUGGESTED_ROLES = [
  "Senior Product Manager",
  "Principal Product Manager",
  "Group Product Manager",
  "Product Lead",
  "Director of Product",
  "Software Engineer",
  "Senior Software Engineer",
  "Staff Engineer",
  "Data Analyst",
  "Data Scientist",
  "Engineering Manager",
];

export default function PreferencesPage() {
  const router = useRouter();
  const [prefs, setPrefs] = useState<Prefs>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [roleInput, setRoleInput] = useState("");
  const [cityInput, setCityInput] = useState("");

  useEffect(() => {
    (async () => {
      const r = await fetch("/api/preferences");
      const body = await r.json();
      if (r.ok && body.preferences) {
        setPrefs({ ...EMPTY, ...body.preferences });
      }
      setLoading(false);
    })();
  }, []);

  function toggleArrayItem(key: "preferred_stages" | "preferred_locations" | "target_roles", value: string) {
    setPrefs((p) => {
      const current = p[key] ?? [];
      const next = current.includes(value)
        ? current.filter((x) => x !== value)
        : [...current, value];
      return { ...p, [key]: next };
    });
  }

  function addRole(value: string) {
    const clean = value.trim();
    if (!clean) return;
    setPrefs((p) =>
      p.target_roles.includes(clean)
        ? p
        : { ...p, target_roles: [...p.target_roles, clean] },
    );
    setRoleInput("");
  }

  function addCity(value: string) {
    const clean = value.trim();
    if (!clean) return;
    setPrefs((p) =>
      p.preferred_locations.includes(clean)
        ? p
        : { ...p, preferred_locations: [...p.preferred_locations, clean] },
    );
    setCityInput("");
  }

  async function save(proceedToBrowse: boolean) {
    if (proceedToBrowse && prefs.target_roles.length === 0) {
      alert("Pick at least one target role so Scout knows what to find.");
      return;
    }
    setSaving(true);
    const r = await fetch("/api/preferences", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(prefs),
    });
    setSaving(false);
    if (!r.ok) {
      const body = await r.json().catch(() => ({}));
      alert(`Save failed: ${body.error ?? r.status}`);
      return;
    }
    if (proceedToBrowse) router.push("/onboarding/find");
  }

  const roleSuggestions = useMemo(
    () =>
      SUGGESTED_ROLES.filter((r) => !prefs.target_roles.includes(r)).slice(0, 5),
    [prefs.target_roles],
  );

  if (loading) {
    return (
      <main className="mx-auto max-w-[820px] px-6 py-10">
        <p className="text-sm text-muted">Loading your preferences…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-[820px] px-6 py-10 space-y-6">
      {/* Step indicator */}
      <div className="flex items-center justify-between border-b border-border pb-5">
        <div className="flex items-center gap-2 text-xs">
          {STEPS.map((s, i) => (
            <span key={s.n} className="flex items-center gap-2">
              <span
                className={
                  s.state === "active"
                    ? "rounded-lg bg-accent px-3 py-1.5 font-semibold text-white"
                    : s.state === "done"
                      ? "rounded-[10px] bg-accent/10 px-3 py-1.5 font-medium text-primary-700"
                      : "rounded-full border border-border bg-white px-3 py-1.5 font-medium text-muted"
                }
              >
                {s.n} {s.state === "done" ? `${s.label} ✓` : s.label}
              </span>
              {i < STEPS.length - 1 && <span className="h-px w-4 bg-border" />}
            </span>
          ))}
        </div>
        <button
          type="button"
          onClick={() => router.push("/onboarding/find")}
          className="text-xs text-muted transition hover:text-foreground"
        >
          I&apos;ll decide later →
        </button>
      </div>

      <div>
        <p className="text-xs font-medium uppercase tracking-[0.12em] text-accent">
          One minute, then we show you roles.
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-foreground">
          What kind of role are you actually looking for?
        </h1>
      </div>

      <div className="rounded-2xl border border-border bg-surface p-6 shadow-sm space-y-6">
        {/* Target roles */}
        <div>
          <label className="text-sm font-semibold text-foreground">
            Target roles <span className="text-cta">*</span>
          </label>
          <p className="mt-0.5 text-xs text-muted">
            Multi-select. We&apos;ll match against all of them.
          </p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {prefs.target_roles.map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => toggleArrayItem("target_roles", r)}
                className="inline-flex items-center gap-1 rounded-[10px] bg-primary-500/10 px-3 py-1 text-xs font-medium text-primary-700"
              >
                {r} <span className="text-primary-500">✕</span>
              </button>
            ))}
            <input
              value={roleInput}
              onChange={(e) => setRoleInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === ",") {
                  e.preventDefault();
                  addRole(roleInput);
                }
              }}
              placeholder="Type a role, press Enter"
              className="min-w-[180px] rounded-full border border-border bg-white px-3 py-1 text-xs focus:border-accent focus:outline-none"
            />
          </div>
          {roleSuggestions.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {roleSuggestions.map((r) => (
                <button
                  key={r}
                  type="button"
                  onClick={() => addRole(r)}
                  className="rounded-full border border-border bg-white px-2.5 py-1 text-[11px] text-muted transition hover:border-accent hover:text-accent"
                >
                  + {r}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          {/* Location preference */}
          <div>
            <label className="text-sm font-semibold text-foreground">
              Location preference
            </label>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {LOCATION_OPTIONS.map((opt) => (
                <button
                  key={opt.v}
                  type="button"
                  onClick={() => setPrefs({ ...prefs, location_preference: opt.v })}
                  className={
                    prefs.location_preference === opt.v
                      ? "rounded-[10px] bg-primary-500/10 px-3 py-1 text-xs font-medium text-primary-700"
                      : "rounded-full border border-border bg-white px-3 py-1 text-xs font-medium text-foreground transition hover:border-accent"
                  }
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Cities */}
          <div>
            <label className="text-sm font-semibold text-foreground">Cities</label>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {prefs.preferred_locations.map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => toggleArrayItem("preferred_locations", c)}
                  className="inline-flex items-center gap-1 rounded-[10px] bg-primary-500/10 px-3 py-1 text-xs font-medium text-primary-700"
                >
                  {c} <span className="text-primary-500">✕</span>
                </button>
              ))}
              <input
                value={cityInput}
                onChange={(e) => setCityInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === ",") {
                    e.preventDefault();
                    addCity(cityInput);
                  }
                }}
                placeholder="e.g. Bangalore"
                className="min-w-[120px] rounded-full border border-border bg-white px-3 py-1 text-xs focus:border-accent focus:outline-none"
              />
            </div>
            <div className="mt-1.5 flex flex-wrap gap-1">
              {CITY_SUGGESTIONS.filter(
                (c) => !prefs.preferred_locations.includes(c),
              )
                .slice(0, 5)
                .map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => addCity(c)}
                    className="rounded-full border border-border bg-white px-2 py-0.5 text-[11px] text-muted transition hover:border-accent hover:text-accent"
                  >
                    + {c}
                  </button>
                ))}
            </div>
          </div>
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          {/* Company stage */}
          <div>
            <label className="text-sm font-semibold text-foreground">
              Company stage
            </label>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {STAGE_OPTIONS.map((s) => (
                <button
                  key={s.v}
                  type="button"
                  onClick={() => toggleArrayItem("preferred_stages", s.v)}
                  className={
                    prefs.preferred_stages.includes(s.v)
                      ? "rounded-[10px] bg-primary-500/10 px-3 py-1 text-xs font-medium text-primary-700"
                      : "rounded-full border border-border bg-white px-3 py-1 text-xs font-medium text-foreground transition hover:border-accent"
                  }
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          {/* Notice period */}
          <div>
            <label className="text-sm font-semibold text-foreground">
              Notice period
            </label>
            <select
              value={prefs.notice_period_days ?? ""}
              onChange={(e) =>
                setPrefs({
                  ...prefs,
                  notice_period_days: e.target.value ? Number(e.target.value) : null,
                })
              }
              className="mt-2 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:border-accent focus:outline-none"
            >
              <option value="">Select…</option>
              {NOTICE_PERIOD_OPTIONS.map((opt) => (
                <option key={opt.v} value={opt.v}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Compensation */}
        <div>
          <label className="text-sm font-semibold text-foreground">
            Compensation target
          </label>
          <p className="mt-0.5 text-xs text-muted">
            Annual CTC · ₹ lakhs · Hidden from recruiters.
          </p>
          <div className="mt-2 flex items-center gap-3">
            <input
              type="number"
              placeholder="45"
              value={prefs.min_comp_usd ?? ""}
              onChange={(e) =>
                setPrefs({
                  ...prefs,
                  min_comp_usd: e.target.value ? Number(e.target.value) : null,
                })
              }
              className="flex-1 rounded-lg border border-border bg-white px-3 py-2 text-sm focus:border-accent focus:outline-none"
            />
            <span className="text-muted">to</span>
            <input
              type="number"
              placeholder="70"
              value={prefs.max_comp_usd ?? ""}
              onChange={(e) =>
                setPrefs({
                  ...prefs,
                  max_comp_usd: e.target.value ? Number(e.target.value) : null,
                })
              }
              className="flex-1 rounded-lg border border-border bg-white px-3 py-2 text-sm focus:border-accent focus:outline-none"
            />
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <button
          type="button"
          onClick={() => router.push("/onboarding/profile")}
          className="inline-flex items-center gap-1 rounded-full border border-border bg-white px-4 py-2.5 text-sm font-semibold text-foreground transition hover:border-accent"
        >
          ← Back
        </button>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => save(false)}
            disabled={saving}
            className="rounded-full border border-border bg-white px-4 py-2.5 text-sm font-semibold text-foreground transition hover:border-accent disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save"}
          </button>
          <button
            type="button"
            onClick={() => save(true)}
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-lg bg-cta px-6 py-2.5 text-sm font-semibold text-white shadow-cta transition hover:bg-cta-hover disabled:opacity-50"
          >
            {saving ? "Saving…" : "Find roles →"}
          </button>
        </div>
      </div>
    </main>
  );
}
