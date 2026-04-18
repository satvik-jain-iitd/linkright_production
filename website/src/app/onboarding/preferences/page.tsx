// Onboarding screen 2 — preferences.
// Runs AFTER resume upload (screen 1) and BEFORE the job browse view (screen 3).
// Nugget extraction + embedding runs in the background while user fills this.

"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type Prefs = {
  location_preference: string;
  preferred_locations: string[];
  preferred_stages: string[];
  preferred_tier_flags: string[];
  industries_target: string[];
  industries_background: string[];
  visa_status: string;
  target_roles: string[];
  min_comp_usd: number | null;
};

const EMPTY: Prefs = {
  location_preference: "any",
  preferred_locations: [],
  preferred_stages: [],
  preferred_tier_flags: [],
  industries_target: [],
  industries_background: [],
  visa_status: "unknown",
  target_roles: [],
  min_comp_usd: null,
};

// Chip options — kept in sync with companies_global constraints
const STAGES = [
  "seed",
  "series_a",
  "series_b",
  "series_c",
  "series_d_plus",
  "public",
  "bootstrapped",
];
const TIER_FLAGS = [
  "faang",
  "yc_backed",
  "unicorn",
  "public_tier1",
  "proven_founders",
];
const INDUSTRIES = [
  "fintech",
  "payments",
  "b2b_saas",
  "consumer",
  "ecommerce",
  "marketplace",
  "ai",
  "llm",
  "developer_tools",
  "healthtech",
  "edtech",
  "hrtech",
  "productivity",
  "mobility",
  "travel",
  "crypto",
];

export default function PreferencesPage() {
  const router = useRouter();
  const [prefs, setPrefs] = useState<Prefs>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [targetRolesInput, setTargetRolesInput] = useState("");
  const [locationsInput, setLocationsInput] = useState("");

  useEffect(() => {
    (async () => {
      const r = await fetch("/api/preferences");
      const body = await r.json();
      if (r.ok && body.preferences) {
        const p = body.preferences;
        setPrefs({ ...EMPTY, ...p });
        setTargetRolesInput((p.target_roles ?? []).join(", "));
        setLocationsInput((p.preferred_locations ?? []).join(", "));
      }
      setLoading(false);
    })();
  }, []);

  function toggle(arrayKey: keyof Prefs, value: string) {
    setPrefs((p) => {
      const current = (p[arrayKey] as string[]) ?? [];
      const next = current.includes(value)
        ? current.filter((x) => x !== value)
        : [...current, value];
      return { ...p, [arrayKey]: next };
    });
  }

  async function save(proceedToBrowse: boolean) {
    setSaving(true);
    const payload = {
      ...prefs,
      target_roles: targetRolesInput
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      preferred_locations: locationsInput
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    };
    const r = await fetch("/api/preferences", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    setSaving(false);
    if (!r.ok) {
      const body = await r.json().catch(() => ({}));
      alert(`Save failed: ${body.error ?? r.status}`);
      return;
    }
    if (proceedToBrowse) router.push("/onboarding/find");
  }

  if (loading) {
    return (
      <div className="p-8 max-w-3xl mx-auto">
        <p className="text-sm text-muted-foreground">Loading your preferences...</p>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">What are you looking for?</h1>
      <p className="text-sm text-muted-foreground mb-8">
        We're processing your resume in the background. While we do, tell us what matters to you.
      </p>

      {/* Target roles */}
      <section className="mb-6">
        <label className="block text-sm font-medium mb-1">Target roles</label>
        <input
          type="text"
          placeholder="Product Manager, Senior PM, Staff PM"
          value={targetRolesInput}
          onChange={(e) => setTargetRolesInput(e.target.value)}
          className="w-full px-3 py-2 rounded-lg border border-border bg-background"
        />
        <p className="text-xs text-muted-foreground mt-1">Comma-separated</p>
      </section>

      {/* Location */}
      <section className="mb-6">
        <label className="block text-sm font-medium mb-1">Location preference</label>
        <div className="flex gap-2 flex-wrap">
          {(["remote_only", "hybrid_ok", "onsite_ok", "any"] as const).map((v) => (
            <button
              key={v}
              onClick={() => setPrefs({ ...prefs, location_preference: v })}
              className={`px-3 py-1.5 rounded-lg border text-sm ${
                prefs.location_preference === v
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border"
              }`}
            >
              {v.replace("_", " ")}
            </button>
          ))}
        </div>
        <input
          type="text"
          placeholder="Bangalore, SF, Remote"
          value={locationsInput}
          onChange={(e) => setLocationsInput(e.target.value)}
          className="w-full px-3 py-2 mt-3 rounded-lg border border-border bg-background"
        />
        <p className="text-xs text-muted-foreground mt-1">Specific cities/regions (comma-separated)</p>
      </section>

      {/* Work authorisation removed per v2 design audit — not a reliable
          filter for most Indian candidates and adds friction. Defaults to
          "unknown" on submit and the scout ranker simply ignores it. */}

      {/* Stage */}
      <section className="mb-6">
        <label className="block text-sm font-medium mb-1">Preferred company stages</label>
        <div className="flex gap-2 flex-wrap">
          {STAGES.map((s) => (
            <button
              key={s}
              onClick={() => toggle("preferred_stages", s)}
              className={`px-3 py-1.5 rounded-lg border text-sm ${
                prefs.preferred_stages.includes(s)
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border"
              }`}
            >
              {s.replace(/_/g, " ")}
            </button>
          ))}
        </div>
      </section>

      {/* Tier flags */}
      <section className="mb-6">
        <label className="block text-sm font-medium mb-1">Company type emphasis</label>
        <div className="flex gap-2 flex-wrap">
          {TIER_FLAGS.map((f) => (
            <button
              key={f}
              onClick={() => toggle("preferred_tier_flags", f)}
              className={`px-3 py-1.5 rounded-lg border text-sm ${
                prefs.preferred_tier_flags.includes(f)
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border"
              }`}
            >
              {f.replace(/_/g, " ")}
            </button>
          ))}
        </div>
      </section>

      {/* Industries target */}
      <section className="mb-6">
        <label className="block text-sm font-medium mb-1">Industries you want to work in</label>
        <div className="flex gap-2 flex-wrap">
          {INDUSTRIES.map((i) => (
            <button
              key={i}
              onClick={() => toggle("industries_target", i)}
              className={`px-3 py-1.5 rounded-lg border text-sm ${
                prefs.industries_target.includes(i)
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border"
              }`}
            >
              {i.replace(/_/g, " ")}
            </button>
          ))}
        </div>
      </section>

      {/* Industries background */}
      <section className="mb-6">
        <label className="block text-sm font-medium mb-1">Industries from your past experience</label>
        <div className="flex gap-2 flex-wrap">
          {INDUSTRIES.map((i) => (
            <button
              key={i + "-bg"}
              onClick={() => toggle("industries_background", i)}
              className={`px-3 py-1.5 rounded-lg border text-sm ${
                prefs.industries_background.includes(i)
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border"
              }`}
            >
              {i.replace(/_/g, " ")}
            </button>
          ))}
        </div>
      </section>

      {/* Actions */}
      <div className="flex gap-3 mt-8">
        <button
          onClick={() => save(false)}
          disabled={saving}
          className="px-4 py-2 rounded-lg border border-border"
        >
          {saving ? "Saving..." : "Save"}
        </button>
        <button
          onClick={() => save(true)}
          disabled={saving}
          className="px-6 py-2 rounded-lg bg-primary text-primary-foreground"
        >
          {saving ? "Saving..." : "Save & browse jobs →"}
        </button>
      </div>
    </div>
  );
}
