"use client";

import { useEffect, useState, useCallback } from "react";

// ─── Types ───────────────────────────────────────────────────────────────────

interface ScannerSettings {
  positive_role_keywords: string[];
  negative_role_keywords: string[];
  target_countries: string[];
  sources_enabled: Record<string, boolean>;
  enrichment_model: string;
  enrichment_enabled: boolean;
  enrichment_fields: string[];
}

interface SourceConfig {
  adzuna_app_id?: string;
  adzuna_app_key?: string;
  jsearch_api_key?: string;
  serpapi_key?: string;
  sources_enabled: Record<string, boolean>;
}

interface HealthStats {
  total: number;
  by_status: Record<string, number>;
  by_source: Record<string, number>;
  enrichment_pending: number;
}

type Tab = "search" | "sources" | "snippets" | "enrichment" | "health";

const TABS: { id: Tab; label: string }[] = [
  { id: "search", label: "General Search" },
  { id: "sources", label: "Sources" },
  { id: "snippets", label: "Browser Snippets" },
  { id: "enrichment", label: "Enrichment" },
  { id: "health", label: "Job Health" },
];

const COUNTRIES = [
  { code: "IN", label: "India" },
  { code: "AE", label: "UAE / Dubai" },
  { code: "US", label: "USA" },
  { code: "GB", label: "UK" },
  { code: "remote", label: "Remote" },
];

const ENRICHMENT_FIELDS = [
  { id: "remote_ok", label: "Remote OK" },
  { id: "work_type", label: "Work type" },
  { id: "employment_type", label: "Employment type" },
  { id: "experience_level", label: "Experience level" },
  { id: "department", label: "Department" },
  { id: "industry", label: "Industry" },
  { id: "company_stage", label: "Company stage" },
  { id: "salary_min", label: "Salary (slow)" },
  { id: "reporting_to", label: "Reporting to" },
  { id: "skills_required", label: "Skills required" },
];

const SOURCE_DEFS = [
  { id: "wellfound", label: "Wellfound", cost: "Free", desc: "Startup PM jobs globally. No setup needed.", needsKey: false },
  { id: "iimjobs", label: "iimjobs.com", cost: "Free", desc: "PM-specific India jobs. No setup needed.", needsKey: false },
  { id: "remotive", label: "Remotive", cost: "Free", desc: "Remote-first global PM jobs. No setup needed.", needsKey: false },
  { id: "adzuna", label: "Adzuna", cost: "Free (API key)", desc: "India + UAE jobs. Register at developer.adzuna.com.", needsKey: true, keyField: "adzuna" },
  { id: "jsearch", label: "JSearch (RapidAPI)", cost: "~$50/mo", desc: "Aggregates LinkedIn + Indeed + Glassdoor + ZipRecruiter.", needsKey: true, keyField: "jsearch" },
  { id: "serpapi", label: "SerpAPI (Google Jobs)", cost: "~$50/mo", desc: "Google Jobs — covers Naukri, LinkedIn, Glassdoor via Google.", needsKey: true, keyField: "serpapi" },
];

const SNIPPETS = [
  {
    id: "linkedin",
    label: "LinkedIn Jobs",
    desc: "Run while logged in on linkedin.com — downloads PM jobs from India",
    code: `(async()=>{const c=document.cookie.match(/JSESSIONID="([^"]+)"/)?.[1]||'';const r=await fetch('/voyager/api/jobs/search?decorationId=com.linkedin.voyager.deco.jobs.web.shared.WebLimitedJobPosting-58&count=100&q=jobSearch&query=(keywords:product%20manager,locationUnion:(geoId:102713980))',{headers:{'csrf-token':c,'x-restli-protocol-version':'2.0.0'}});const d=await r.json();const j=(d.elements||[]).map(e=>({title:e.title||'',company_name:e.companyDetails?.company?.name||'',location:e.formattedLocation||'',job_url:'https://www.linkedin.com/jobs/view/'+e.jobPostingId,source:'linkedin'}));const csv=['title,company_name,location,job_url,source',...j.map(x=>Object.values(x).map(v=>'"'+String(v).replace(/"/g,'""')+'"').join(','))].join('\\n');const a=Object.assign(document.createElement('a'),{href:URL.createObjectURL(new Blob([csv],{type:'text/csv'})),download:'linkedin_jobs.csv'});a.click();})();`,
  },
  {
    id: "naukri",
    label: "Naukri.com",
    desc: "Works without login — paste in any browser console",
    code: `(async()=>{let j=[];for(let p=1;p<=5;p++){const r=await fetch('https://www.naukri.com/jobapi/v3/search?noOfResults=20&urlType=search_by_key_loc&searchType=adv&keyword=product+manager&location=india&pageNo='+p,{headers:{'Appid':'109','SystemId':'Naukri'}});const d=await r.json();j=[...j,...(d.jobDetails||[]).map(x=>({title:x.title,company_name:x.companyName,location:x.placeholders?.[1]?.label||'',job_url:x.jdURL,source:'naukri'}))]}; const csv=['title,company_name,location,job_url,source',...j.map(x=>Object.values(x).map(v=>'"'+String(v||'').replace(/"/g,'""')+'"').join(','))].join('\\n');const a=Object.assign(document.createElement('a'),{href:URL.createObjectURL(new Blob([csv],{type:'text/csv'})),download:'naukri_jobs.csv'});a.click();})();`,
  },
  {
    id: "indeed",
    label: "Indeed India",
    desc: "Run on in.indeed.com results page after searching 'product manager'",
    code: `(()=>{const d=window.mosaic?.providerData?.['mosaic-provider-jobcards']?.pageData?.results||[];const j=d.map(x=>({title:x.title,company_name:x.company,location:x.formattedLocation||'',job_url:'https://in.indeed.com/viewjob?jk='+x.jobkey,source:'indeed'}));const csv=['title,company_name,location,job_url,source',...j.map(x=>Object.values(x).map(v=>'"'+String(v||'').replace(/"/g,'""')+'"').join(','))].join('\\n');const a=Object.assign(document.createElement('a'),{href:URL.createObjectURL(new Blob([csv],{type:'text/csv'})),download:'indeed_jobs.csv'});a.click();})();`,
  },
  {
    id: "naukrigulf",
    label: "Naukrigulf (Dubai/UAE)",
    desc: "Works without login — for UAE/Dubai PM jobs",
    code: `(async()=>{const r=await fetch('https://www.naukrigulf.com/jobapi/v3/search?noOfResults=50&keyword=product+manager&location=uae&pageNo=1',{headers:{'Appid':'109','SystemId':'Naukrigulf'}});const d=await r.json();const j=(d.jobDetails||[]).map(x=>({title:x.title,company_name:x.companyName,location:'UAE',job_url:x.jdURL,source:'naukrigulf'}));const csv=['title,company_name,location,job_url,source',...j.map(x=>Object.values(x).map(v=>'"'+String(v||'').replace(/"/g,'""')+'"').join(','))].join('\\n');const a=Object.assign(document.createElement('a'),{href:URL.createObjectURL(new Blob([csv],{type:'text/csv'})),download:'naukrigulf_jobs.csv'});a.click();})();`,
  },
];

// ─── Shared UI atoms ──────────────────────────────────────────────────────────

function Chip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-[10px] bg-[#F1F5F9] text-sm text-foreground font-medium">
      {label}
      <button onClick={onRemove} className="text-muted hover:text-foreground leading-none">&times;</button>
    </span>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted mb-3">{children}</p>
  );
}

function SaveBtn({ onClick, saving, label = "Save settings" }: { onClick: () => void; saving: boolean; label?: string }) {
  return (
    <button
      onClick={onClick}
      disabled={saving}
      className="rounded-full bg-cta text-white text-sm font-semibold px-5 py-2 hover:opacity-90 disabled:opacity-50 transition-opacity"
    >
      {saving ? "Saving…" : label}
    </button>
  );
}

// ─── Tab: General Search ─────────────────────────────────────────────────────

function TabSearch({ settings, onSave }: { settings: ScannerSettings; onSave: (patch: Partial<ScannerSettings>) => Promise<void> }) {
  const [posKw, setPosKw] = useState<string[]>(settings.positive_role_keywords);
  const [negKw, setNegKw] = useState<string[]>(settings.negative_role_keywords);
  const [countries, setCountries] = useState<string[]>(settings.target_countries);
  const [newPos, setNewPos] = useState("");
  const [newNeg, setNewNeg] = useState("");
  const [saving, setSaving] = useState(false);

  function addKw(list: string[], setList: (l: string[]) => void, val: string) {
    const trimmed = val.trim().toLowerCase();
    if (trimmed && !list.includes(trimmed)) setList([...list, trimmed]);
  }

  function toggleCountry(code: string) {
    setCountries((prev) => prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]);
  }

  async function handleSave() {
    setSaving(true);
    await onSave({ positive_role_keywords: posKw, negative_role_keywords: negKw, target_countries: countries });
    setSaving(false);
  }

  return (
    <div className="space-y-8 max-w-2xl">
      <section>
        <SectionLabel>Include roles (title must contain at least one)</SectionLabel>
        <div className="flex flex-wrap gap-2 mb-3">
          {posKw.map((k) => <Chip key={k} label={k} onRemove={() => setPosKw(posKw.filter((x) => x !== k))} />)}
        </div>
        <div className="flex gap-2">
          <input
            value={newPos} onChange={(e) => setNewPos(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") { addKw(posKw, setPosKw, newPos); setNewPos(""); } }}
            placeholder="e.g. senior pm"
            className="flex-1 rounded-[10px] border border-border px-3 py-2 text-sm focus:outline-none focus:border-accent"
          />
          <button onClick={() => { addKw(posKw, setPosKw, newPos); setNewPos(""); }}
            className="rounded-lg border border-border px-4 py-2 text-sm hover:bg-[#F8FAFC]">
            + Add
          </button>
        </div>
      </section>

      <section>
        <SectionLabel>Exclude roles (reject if title contains any)</SectionLabel>
        <div className="flex flex-wrap gap-2 mb-3">
          {negKw.map((k) => <Chip key={k} label={k} onRemove={() => setNegKw(negKw.filter((x) => x !== k))} />)}
        </div>
        <div className="flex gap-2">
          <input
            value={newNeg} onChange={(e) => setNewNeg(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") { addKw(negKw, setNegKw, newNeg); setNewNeg(""); } }}
            placeholder="e.g. software engineer"
            className="flex-1 rounded-[10px] border border-border px-3 py-2 text-sm focus:outline-none focus:border-accent"
          />
          <button onClick={() => { addKw(negKw, setNegKw, newNeg); setNewNeg(""); }}
            className="rounded-lg border border-border px-4 py-2 text-sm hover:bg-[#F8FAFC]">
            + Add
          </button>
        </div>
      </section>

      <section>
        <SectionLabel>Target regions</SectionLabel>
        <div className="flex flex-wrap gap-3">
          {COUNTRIES.map((c) => (
            <label key={c.code} className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={countries.includes(c.code)} onChange={() => toggleCountry(c.code)}
                className="rounded accent-accent" />
              <span className="text-sm text-foreground">{c.label}</span>
            </label>
          ))}
        </div>
      </section>

      <SaveBtn onClick={handleSave} saving={saving} />
    </div>
  );
}

// ─── Tab: Sources ─────────────────────────────────────────────────────────────

function TabSources({ settings, config, onToggle, onSaveKey }: {
  settings: ScannerSettings;
  config: SourceConfig;
  onToggle: (id: string, enabled: boolean) => Promise<void>;
  onSaveKey: (fields: Partial<SourceConfig>) => Promise<void>;
}) {
  const [expandedKey, setExpandedKey] = useState<string | null>(null);
  const [keyInputs, setKeyInputs] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState<string | null>(null);

  async function handleToggle(id: string) {
    const current = (settings.sources_enabled || {})[id] ?? (["wellfound", "iimjobs", "remotive"].includes(id));
    await onToggle(id, !current);
  }

  async function handleSaveKey(sourceId: string) {
    setSaving(sourceId);
    if (sourceId === "adzuna") {
      const [id, key] = (keyInputs["adzuna"] || "").split("|");
      await onSaveKey({ adzuna_app_id: id?.trim(), adzuna_app_key: key?.trim() });
    } else if (sourceId === "jsearch") {
      await onSaveKey({ jsearch_api_key: keyInputs["jsearch"]?.trim() });
    } else if (sourceId === "serpapi") {
      await onSaveKey({ serpapi_key: keyInputs["serpapi"]?.trim() });
    }
    setSaving(null);
    setExpandedKey(null);
  }

  return (
    <div className="max-w-2xl space-y-3">
      {SOURCE_DEFS.map((src) => {
        const enabled = (settings.sources_enabled || {})[src.id] ?? ["wellfound", "iimjobs", "remotive"].includes(src.id);
        return (
          <div key={src.id} className="rounded-[20px] border border-border bg-white p-5">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 mb-1">
                  <span className="text-sm font-semibold text-foreground">{src.label}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-[10px] font-medium ${
                    src.cost === "Free" || src.cost === "Free (API key)"
                      ? "bg-green-50 text-green-700"
                      : "bg-amber-50 text-amber-700"
                  }`}>{src.cost}</span>
                </div>
                <p className="text-xs text-muted">{src.desc}</p>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                {src.needsKey && !enabled && (
                  <button
                    onClick={() => setExpandedKey(expandedKey === src.id ? null : src.id)}
                    className="text-xs rounded-lg border border-border px-3 py-1.5 hover:bg-[#F8FAFC] text-foreground"
                  >
                    Configure key
                  </button>
                )}
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" checked={enabled} onChange={() => handleToggle(src.id)} className="sr-only peer" />
                  <div className="w-10 h-6 bg-[#E2E8F0] peer-checked:bg-accent rounded-full transition-colors" />
                  <div className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full shadow transition-transform peer-checked:translate-x-4" />
                </label>
              </div>
            </div>

            {expandedKey === src.id && (
              <div className="mt-4 pt-4 border-t border-border">
                {src.id === "adzuna" ? (
                  <div className="space-y-2">
                    <p className="text-xs text-muted mb-2">Get your keys at <strong>developer.adzuna.com</strong> (free registration)</p>
                    <div className="flex gap-2">
                      <input placeholder="App ID" className="flex-1 rounded-[10px] border border-border px-3 py-2 text-sm" defaultValue={config.adzuna_app_id || ""} onChange={(e) => setKeyInputs({ ...keyInputs, adzuna: `${e.target.value}|${(keyInputs["adzuna"] || "").split("|")[1] || ""}` })} />
                      <input placeholder="App Key" type="password" className="flex-1 rounded-[10px] border border-border px-3 py-2 text-sm" onChange={(e) => setKeyInputs({ ...keyInputs, adzuna: `${(keyInputs["adzuna"] || "").split("|")[0] || ""}|${e.target.value}` })} />
                    </div>
                  </div>
                ) : (
                  <div className="flex gap-2">
                    <input placeholder="API Key" type="password" className="flex-1 rounded-[10px] border border-border px-3 py-2 text-sm" onChange={(e) => setKeyInputs({ ...keyInputs, [src.id]: e.target.value })} />
                  </div>
                )}
                <div className="flex gap-2 mt-3">
                  <button onClick={() => handleSaveKey(src.id)} disabled={saving === src.id}
                    className="rounded-full bg-cta text-white text-sm font-semibold px-4 py-1.5 hover:opacity-90 disabled:opacity-50">
                    {saving === src.id ? "Saving…" : "Save & enable"}
                  </button>
                  <button onClick={() => setExpandedKey(null)} className="rounded-lg border border-border px-4 py-1.5 text-sm hover:bg-[#F8FAFC]">Cancel</button>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Tab: Browser Snippets ───────────────────────────────────────────────────

function TabSnippets() {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);
  const [uploadFor, setUploadFor] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<{ valid: number; invalid_count: number; preview: unknown[] } | null>(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<string | null>(null);

  function copy(id: string, code: string) {
    navigator.clipboard.writeText(code);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  }

  async function handleFilePreview(f: File, sourceId: string) {
    setFile(f);
    setImportResult(null);
    const text = await f.text();
    const lines = text.split("\n").filter(Boolean);
    const headers = lines[0].split(",").map((h) => h.replace(/"/g, "").trim().toLowerCase());
    const rows = lines.slice(1).map((line) => {
      const vals = line.match(/("(?:[^"]|"")*"|[^,]*)/g) || [];
      const row: Record<string, string> = {};
      headers.forEach((h, i) => { row[h] = (vals[i] || "").replace(/^"|"$/g, "").replace(/""/g, '"'); });
      return row;
    });

    const resp = await fetch("/api/admin/import-jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rows, source_type: `manual_${sourceId}`, dry_run: true }),
    });
    const data = await resp.json();
    setPreview(data);
  }

  async function handleCommit(sourceId: string) {
    if (!file) return;
    setImporting(true);
    const text = await file.text();
    const lines = text.split("\n").filter(Boolean);
    const headers = lines[0].split(",").map((h) => h.replace(/"/g, "").trim().toLowerCase());
    const rows = lines.slice(1).map((line) => {
      const vals = line.match(/("(?:[^"]|"")*"|[^,]*)/g) || [];
      const row: Record<string, string> = {};
      headers.forEach((h, i) => { row[h] = (vals[i] || "").replace(/^"|"$/g, "").replace(/""/g, '"'); });
      return row;
    });

    const resp = await fetch("/api/admin/import-jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rows, source_type: `manual_${sourceId}` }),
    });
    const data = await resp.json();
    setImporting(false);
    setImportResult(data.ok ? `✓ Imported ${data.inserted} jobs (${data.skipped} duplicates skipped)` : `Error: ${data.error}`);
    setPreview(null);
    setFile(null);
  }

  return (
    <div className="max-w-2xl space-y-4">
      <div className="rounded-[20px] border border-border bg-[#F8FAFC] p-5 mb-2">
        <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted mb-3">How to use</p>
        <ol className="space-y-1.5 text-sm text-muted list-decimal list-inside">
          <li>Log into the portal in Chrome</li>
          <li>Open DevTools → Console (F12 or Cmd+Option+J)</li>
          <li>Paste the snippet and press Enter</li>
          <li>A CSV file will download automatically</li>
          <li>Upload the CSV below</li>
        </ol>
      </div>

      {SNIPPETS.map((s) => (
        <div key={s.id} className="rounded-[20px] border border-border bg-white p-5">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-semibold text-foreground">{s.label}</span>
            <button
              onClick={() => setExpanded(expanded === s.id ? null : s.id)}
              className="text-xs text-accent hover:underline"
            >
              {expanded === s.id ? "Hide snippet ↑" : "Show snippet ↓"}
            </button>
          </div>
          <p className="text-xs text-muted mb-3">{s.desc}</p>

          {expanded === s.id && (
            <div className="relative mb-3">
              <pre className="font-mono text-xs bg-[#F8FAFC] rounded-[10px] p-4 overflow-x-auto whitespace-pre-wrap break-all text-[#334155]">
                {s.code}
              </pre>
              <button
                onClick={() => copy(s.id, s.code)}
                className="absolute top-2 right-2 text-xs rounded-lg border border-border bg-white px-2.5 py-1 hover:bg-[#F8FAFC]"
              >
                {copied === s.id ? "Copied ✓" : "Copy"}
              </button>
            </div>
          )}

          <div className="flex items-center gap-3">
            {uploadFor !== s.id ? (
              <button
                onClick={() => { setUploadFor(s.id); setPreview(null); setFile(null); setImportResult(null); }}
                className="text-sm rounded-lg border border-border px-4 py-2 hover:bg-[#F8FAFC]"
              >
                Upload CSV
              </button>
            ) : (
              <div className="space-y-3 w-full">
                <input type="file" accept=".csv" onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) handleFilePreview(f, s.id);
                }} className="text-sm" />

                {preview && (
                  <div className="text-sm space-y-1">
                    <p className="text-foreground">
                      <span className="text-green-600 font-semibold">{preview.valid} valid</span>
                      {preview.invalid_count > 0 && <span className="text-red-500 ml-2">{preview.invalid_count} invalid</span>}
                    </p>
                    <div className="flex gap-2 mt-2">
                      <button onClick={() => handleCommit(s.id)} disabled={importing}
                        className="rounded-full bg-cta text-white text-sm font-semibold px-4 py-1.5 hover:opacity-90 disabled:opacity-50">
                        {importing ? "Importing…" : `Import ${preview.valid} jobs`}
                      </button>
                      <button onClick={() => { setUploadFor(null); setPreview(null); setFile(null); }}
                        className="rounded-lg border border-border px-4 py-1.5 text-sm hover:bg-[#F8FAFC]">
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
                {importResult && <p className="text-sm font-medium text-foreground">{importResult}</p>}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Tab: Enrichment ─────────────────────────────────────────────────────────

function TabEnrichment({ settings, onSave }: { settings: ScannerSettings; onSave: (patch: Partial<ScannerSettings>) => Promise<void> }) {
  const [model, setModel] = useState(settings.enrichment_model || "oracle");
  const [enabled, setEnabled] = useState(settings.enrichment_enabled ?? true);
  const [fields, setFields] = useState<string[]>(settings.enrichment_fields || []);
  const [saving, setSaving] = useState(false);
  const [oracleStatus, setOracleStatus] = useState<"unknown" | "ok" | "error">("unknown");

  useEffect(() => {
    fetch("/api/admin/oracle-status").then((r) => r.json()).then((d) => {
      setOracleStatus(d.ok ? "ok" : "error");
    }).catch(() => setOracleStatus("error"));
  }, []);

  function toggleField(id: string) {
    setFields((prev) => prev.includes(id) ? prev.filter((f) => f !== id) : [...prev, id]);
  }

  async function handleSave() {
    setSaving(true);
    await onSave({ enrichment_model: model, enrichment_enabled: enabled, enrichment_fields: fields });
    setSaving(false);
  }

  return (
    <div className="max-w-2xl space-y-8">
      <section>
        <SectionLabel>Enrichment model</SectionLabel>
        <div className="flex gap-4">
          {[
            { id: "oracle", label: "Oracle (local)", note: "Free, slow, unlimited" },
            { id: "cerebras", label: "Cerebras", note: "Faster, uses API credits" },
            { id: "groq", label: "Groq", note: "Rate-limited, avoid for bulk" },
          ].map((m) => (
            <label key={m.id} className={`flex-1 border rounded-[10px] p-4 cursor-pointer transition-colors ${model === m.id ? "border-accent bg-accent/5" : "border-border hover:bg-[#F8FAFC]"}`}>
              <input type="radio" name="model" value={m.id} checked={model === m.id} onChange={() => setModel(m.id)} className="sr-only" />
              <p className="text-sm font-semibold text-foreground">{m.label}</p>
              <p className="text-xs text-muted mt-0.5">{m.note}</p>
            </label>
          ))}
        </div>

        {model === "oracle" && (
          <div className="flex items-center gap-2 mt-3">
            <span className={`w-2 h-2 rounded-full ${oracleStatus === "ok" ? "bg-green-500" : oracleStatus === "error" ? "bg-red-400" : "bg-amber-400"}`} />
            <span className="text-xs text-muted">
              oracle.linkright.in — {oracleStatus === "ok" ? "Connected" : oracleStatus === "error" ? "Unreachable" : "Checking…"}
            </span>
          </div>
        )}
      </section>

      <section>
        <SectionLabel>Fields to extract</SectionLabel>
        <div className="grid grid-cols-2 gap-2">
          {ENRICHMENT_FIELDS.map((f) => (
            <label key={f.id} className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={fields.includes(f.id)} onChange={() => toggleField(f.id)} className="rounded accent-accent" />
              <span className="text-sm text-foreground">{f.label}</span>
            </label>
          ))}
        </div>
      </section>

      <section className="flex items-center justify-between rounded-[10px] border border-border p-4">
        <div>
          <p className="text-sm font-medium text-foreground">Enable enrichment</p>
          <p className="text-xs text-muted mt-0.5">Run Oracle model on pending jobs every 30 min</p>
        </div>
        <label className="relative inline-flex items-center cursor-pointer">
          <input type="checkbox" checked={enabled} onChange={() => setEnabled(!enabled)} className="sr-only peer" />
          <div className="w-10 h-6 bg-[#E2E8F0] peer-checked:bg-accent rounded-full transition-colors" />
          <div className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full shadow transition-transform peer-checked:translate-x-4" />
        </label>
      </section>

      <SaveBtn onClick={handleSave} saving={saving} />
    </div>
  );
}

// ─── Tab: Job Health ─────────────────────────────────────────────────────────

function TabHealth() {
  const [stats, setStats] = useState<HealthStats | null>(null);
  const [cleaning, setCleaning] = useState(false);
  const [cleanResult, setCleanResult] = useState<string | null>(null);

  const load = useCallback(async () => {
    const r = await fetch("/api/admin/job-health");
    const d = await r.json();
    setStats(d);
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleClean() {
    setCleaning(true);
    const r = await fetch("/api/admin/job-health", { method: "DELETE" });
    const d = await r.json();
    setCleaning(false);
    setCleanResult(`Deleted ${d.deleted || 0} expired jobs`);
    load();
  }

  if (!stats) return <p className="text-sm text-muted">Loading…</p>;

  const statRow = [
    { label: "Total", val: stats.total },
    { label: "Active", val: stats.by_status?.active || 0 },
    { label: "Expired", val: stats.by_status?.expired || 0 },
    { label: "Unknown", val: stats.by_status?.unknown || 0 },
    { label: "Enrichment pending", val: stats.enrichment_pending },
  ];

  return (
    <div className="max-w-2xl space-y-6">
      <div className="grid grid-cols-3 gap-3">
        {statRow.map((s) => (
          <div key={s.label} className="rounded-[20px] border border-border bg-white p-4">
            <p className="text-2xl font-bold text-foreground">{s.val.toLocaleString()}</p>
            <p className="text-xs text-muted mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      <section>
        <SectionLabel>By source</SectionLabel>
        <div className="rounded-[20px] border border-border bg-white overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-[#FAFBFC]">
                <th className="text-left px-4 py-3 text-xs font-medium text-muted uppercase tracking-wide">Source</th>
                <th className="text-right px-4 py-3 text-xs font-medium text-muted uppercase tracking-wide">Jobs</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(stats.by_source).sort(([, a], [, b]) => b - a).map(([src, cnt]) => (
                <tr key={src} className="border-b border-border last:border-0">
                  <td className="px-4 py-3 text-foreground font-mono text-xs">{src}</td>
                  <td className="px-4 py-3 text-right text-foreground font-semibold">{cnt.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="flex items-center gap-4">
        <button onClick={handleClean} disabled={cleaning}
          className="rounded-lg border border-red-200 text-red-600 text-sm px-4 py-2 hover:bg-red-50 disabled:opacity-50">
          {cleaning ? "Cleaning…" : `Clean expired jobs (${(stats.by_status?.expired || 0).toLocaleString()})`}
        </button>
        {cleanResult && <p className="text-sm text-muted">{cleanResult}</p>}
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function AdminSourcesPage() {
  const [activeTab, setActiveTab] = useState<Tab>("search");
  const [settings, setSettings] = useState<ScannerSettings | null>(null);
  const [config, setConfig] = useState<SourceConfig>({ sources_enabled: {} });
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetch("/api/admin/scanner-settings").then((r) => r.json()),
      fetch("/api/admin/source-config").then((r) => r.json()),
    ]).then(([s, c]) => {
      setSettings(s);
      setConfig(c);
      setLoading(false);
    });
  }, []);

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  }

  const handleSaveSettings = useCallback(async (patch: Partial<ScannerSettings>) => {
    const r = await fetch("/api/admin/scanner-settings", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(patch),
    });
    if (r.ok) {
      setSettings((prev) => prev ? { ...prev, ...patch } : prev);
      showToast("Settings saved");
    }
  }, []);

  const handleToggleSource = useCallback(async (id: string, enabled: boolean) => {
    const newEnabled = { ...(settings?.sources_enabled || {}), [id]: enabled };
    await fetch("/api/admin/source-config", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sources_enabled: newEnabled }),
    });
    setSettings((prev) => prev ? { ...prev, sources_enabled: newEnabled } : prev);
    showToast(`${id} ${enabled ? "enabled" : "disabled"}`);
  }, [settings]);

  const handleSaveKey = useCallback(async (fields: Partial<SourceConfig>) => {
    await fetch("/api/admin/source-config", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(fields),
    });
    setConfig((prev) => ({ ...prev, ...fields }));
    showToast("API key saved");
  }, []);

  if (loading) return <div className="text-sm text-muted">Loading…</div>;
  if (!settings) return <div className="text-sm text-red-500">Failed to load settings</div>;

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-foreground">Job Sources</h1>
        <p className="text-sm text-muted mt-1">Configure how PM jobs are discovered and annotated</p>
      </div>

      {/* Tab nav */}
      <div className="flex border-b border-border mb-8 gap-0">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`px-5 py-3 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === t.id
                ? "border-accent text-accent"
                : "border-transparent text-muted hover:text-foreground"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "search" && <TabSearch settings={settings} onSave={handleSaveSettings} />}
      {activeTab === "sources" && <TabSources settings={settings} config={config} onToggle={handleToggleSource} onSaveKey={handleSaveKey} />}
      {activeTab === "snippets" && <TabSnippets />}
      {activeTab === "enrichment" && <TabEnrichment settings={settings} onSave={handleSaveSettings} />}
      {activeTab === "health" && <TabHealth />}

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 rounded-[10px] bg-foreground text-white text-sm px-4 py-2.5 shadow-lg">
          {toast}
        </div>
      )}
    </div>
  );
}
