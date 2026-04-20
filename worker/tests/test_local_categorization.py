"""Categorization quality benchmark: local Oracle Ollama models vs Groq 70B.

Tests TWO extraction approaches:
  A) Current JSON approach (forces model to write JSON directly)
  B) New Markdown approach (model writes simple markdown, script converts to JSON)

Hypothesis: small models fail at JSON but can write markdown reliably.
Prompt is fetched from Langfuse ('nugget_extractor' for JSON, 'nugget_extractor_md' for Markdown).

Setup (SSH tunnel needed — port 11434 is firewalled):
    ssh -i ~/Desktop/oracle_new -L 11434:localhost:11434 -N -f opc@80.225.198.184

Run:
    python tests/test_local_categorization.py

Env vars:
    GROQ_API_KEY          — Groq baseline
    ORACLE_OLLAMA_URL     — Ollama (default: http://localhost:11434)
    LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_BASE_URL — Langfuse
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Fallback prompts (used when Langfuse unavailable) ────────────────────────

_JSON_PROMPT_FALLBACK = """\
You are a career data extractor. Extract atomic nuggets from career text.
For each nugget, classify using the Two-Layer model:
- Layer A (Resume): work_experience, independent_project, skill, education, certification, award, publication, volunteer, summary, contact_info
- Layer B (Life): Relationships, Health, Finance, Inner_Life, Logistics, Recreation

Return JSON array. Each nugget:
{
  "nugget_text": "atomic fact/achievement/metric",
  "question": "What did [person] achieve/do at [company]?",
  "alt_questions": ["alternative phrasing 1", "alternative phrasing 2"],
  "answer": "Self-contained answer with key facts/metrics (>30 chars)",
  "primary_layer": "A" or "B",
  "section_type": "work_experience" (if Layer A, one of 10 types),
  "life_domain": "Relationships" (if Layer B, one of 6 domains),
  "resume_relevance": 0.0-1.0 float,
  "resume_section_target": "experience" or "skills" etc,
  "importance": "P0=career-defining achievement (top 3 ever), P1=strong supporting achievement, P2=contextual/supporting fact, P3=peripheral/background",
  "factuality": "fact"/"opinion"/"aspiration",
  "temporality": "past"/"present"/"future",
  "company": "company name or null",
  "role": "role title or null",
  "event_date": "YYYY-MM or YYYY (approximate ok, extract from any date hint in context, null only if truly unknown)",
  "people": ["collaborator or stakeholder name if mentioned, else empty array"],
  "tags": ["tag1", "tag2"],
  "leadership_signal": "none"/"team_lead"/"individual"
}

RULES:
- Every work_experience nugget MUST have both company AND role fields set
- The answer field MUST be self-contained: include company name, role, and timeframe
- If a metric exists in source text, it MUST appear in the answer
- Return ONLY valid JSON array, no other text.\
"""

_MD_PROMPT_FALLBACK = """\
You are a career data extractor. Extract atomic career facts from the text below.

Write each fact in this EXACT format — one per section, separated by a blank line:

## nugget
type: work_experience
company: Company Name
role: Job Title
importance: P1
answer: At Company, as Job Title, [what was done and what result — include all numbers/metrics]
tags: tag1, tag2, tag3
leadership: none

Rules:
- type: one of: work_experience, skill, education, certification, award, independent_project, volunteer
- company + role: required for work_experience; leave blank for other types
- importance: P0=career-defining (top 3 achievements ever), P1=strong, P2=supporting fact, P3=background
- answer: MUST include company name, role, and any metric from source. >30 words. First person.
- tags: comma-separated skill/theme tags (3-6 tags per nugget)
- leadership: none | team_lead | individual
- Extract each achievement as a SEPARATE nugget (atomic — one fact per ## block)
- NEVER fabricate. Only extract what is explicitly stated.
- Do not add any text outside the ## nugget blocks.\
"""

LAYER_A_TYPES = {
    "work_experience", "independent_project", "skill", "education",
    "certification", "award", "publication", "volunteer", "summary", "contact_info",
}
LAYER_B_DOMAINS = {
    "Relationships", "Health", "Finance", "Inner_Life", "Logistics", "Recreation",
}
VALID_IMPORTANCE = {"P0", "P1", "P2", "P3"}


def _get_prompt(name: str, fallback: str) -> tuple[str, str]:
    """Fetch prompt from Langfuse. Returns (text, version)."""
    sk = os.environ.get("LANGFUSE_SECRET_KEY", "")
    pk = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    base = os.environ.get("LANGFUSE_BASE_URL", "https://us.cloud.langfuse.com")
    if not sk or not pk:
        return fallback, "local-fallback"
    try:
        from langfuse import Langfuse
        lf = Langfuse(public_key=pk, secret_key=sk, host=base)
        prompt = lf.get_prompt(name)
        text = prompt.compile()
        logger.info("Fetched Langfuse prompt '%s' v%s", name, prompt.version)
        return text, str(prompt.version)
    except Exception as exc:
        logger.warning("Langfuse fetch failed for '%s' (%s) — using fallback", name, exc)
        return fallback, "local-fallback"


# ── Markdown → JSON converter ─────────────────────────────────────────────────

def _markdown_to_nuggets(md_text: str) -> list[dict] | None:
    """Convert markdown nugget blocks to list of dicts."""
    blocks = re.split(r'^## nugget', md_text, flags=re.MULTILINE | re.IGNORECASE)
    nuggets = []
    for block in blocks:
        if not block.strip():
            continue
        nug: dict = {}
        for line in block.strip().split("\n"):
            line = line.strip()
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            key = key.strip().lower()
            val = val.strip()
            if key == "type":
                nug["section_type"] = val
            elif key == "company":
                nug["company"] = val or None
            elif key == "role":
                nug["role"] = val or None
            elif key == "importance":
                nug["importance"] = val if val in VALID_IMPORTANCE else "P2"
            elif key == "answer":
                nug["answer"] = val
            elif key == "tags":
                nug["tags"] = [t.strip() for t in val.split(",") if t.strip()]
            elif key == "leadership":
                nug["leadership_signal"] = val

        if not nug.get("answer"):
            continue

        # Derive remaining fields
        st = nug.get("section_type", "")
        nug["primary_layer"] = "A" if st in LAYER_A_TYPES else "B"
        nug["nugget_text"] = nug["answer"][:80]
        nug["question"] = f"What did the person achieve at {nug.get('company', 'their company')}?"
        nug["alt_questions"] = [f"Tell me about {nug.get('company', 'this role')}", "What was the outcome?"]
        nug["factuality"] = "fact"
        nug["temporality"] = "past"
        nug["resume_relevance"] = 0.8 if st == "work_experience" else 0.5
        nug["resume_section_target"] = "experience" if st == "work_experience" else st
        nug["people"] = []
        nug["event_date"] = None

        nuggets.append(nug)
    return nuggets if nuggets else None


# ── JSON parser (existing approach) ──────────────────────────────────────────

def _parse_json(raw: str) -> list[dict] | None:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass
    start, end = raw.find("["), raw.rfind("]")
    if start != -1 and end != -1:
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            pass
    return None


# ── Scoring ───────────────────────────────────────────────────────────────────

@dataclass
class ModelResult:
    model: str
    provider: str
    approach: str  # "json" or "markdown"
    latency_s: float = 0.0
    valid_parse: bool = False
    nugget_count: int = 0
    section_type_valid: int = 0
    company_role_present: int = 0
    work_nugget_count: int = 0
    importance_valid: int = 0
    answer_self_contained: int = 0
    raw_output: str = ""
    errors: list[str] = field(default_factory=list)

    def score_pct(self, num: int, denom: int) -> int:
        return round(100 * num / max(denom, 1))

    def passes(self) -> bool:
        n = max(self.nugget_count, 1)
        w = max(self.work_nugget_count, 1)
        return (
            self.valid_parse
            and self.nugget_count >= 3
            and self.score_pct(self.section_type_valid, n) >= 75
            and self.score_pct(self.company_role_present, w) >= 75
        )


def _score(nuggets: list[dict], result: ModelResult) -> None:
    for nug in nuggets:
        result.nugget_count += 1
        if nug.get("section_type") in LAYER_A_TYPES or nug.get("section_type") in LAYER_B_DOMAINS:
            result.section_type_valid += 1
        if nug.get("section_type") == "work_experience":
            result.work_nugget_count += 1
            if nug.get("company") and nug.get("role"):
                result.company_role_present += 1
            else:
                result.errors.append(f"missing company/role: {(nug.get('answer',''))[:50]}")
        if nug.get("importance") in VALID_IMPORTANCE:
            result.importance_valid += 1
        if len(nug.get("answer", "") or "") > 30:
            result.answer_self_contained += 1


# ── LLM calls ────────────────────────────────────────────────────────────────

async def _call_groq(api_key: str, system_prompt: str, user_text: str) -> tuple[str, float]:
    t0 = time.time()
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text},
                ],
                "temperature": 0,
                "max_tokens": 4000,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"], time.time() - t0


async def _call_ollama(ollama_url: str, model: str, system_prompt: str, user_text: str) -> tuple[str, float]:
    t0 = time.time()
    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(
            f"{ollama_url.rstrip('/')}/v1/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text},
                ],
                "temperature": 0,
                "stream": False,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"], time.time() - t0


async def test_model(
    model: str,
    provider: str,
    system_prompt: str,
    approach: str,
    career_text: str,
    groq_key: str = "",
    ollama_url: str = "http://localhost:11434",
) -> ModelResult:
    result = ModelResult(model=model, provider=provider, approach=approach)
    try:
        if provider == "groq":
            raw, latency = await _call_groq(groq_key, system_prompt, career_text)
        else:
            raw, latency = await _call_ollama(ollama_url, model, system_prompt, career_text)
        result.latency_s = latency
        result.raw_output = raw

        if approach == "json":
            nuggets = _parse_json(raw)
        else:
            nuggets = _markdown_to_nuggets(raw)

        if nuggets:
            result.valid_parse = True
            _score(nuggets, result)
        else:
            result.errors.append("parse failed")
    except httpx.TimeoutException:
        result.errors.append("timeout (>180s)")
    except Exception as exc:
        result.errors.append(f"call failed: {exc}")
    return result


async def run_benchmark() -> None:
    groq_key = os.environ.get("GROQ_API_KEY", "")
    ollama_url = os.environ.get("ORACLE_OLLAMA_URL", "http://localhost:11434")

    # Fetch prompts from Langfuse
    json_prompt, json_v = _get_prompt("nugget_extractor", _JSON_PROMPT_FALLBACK)
    md_prompt, md_v = _get_prompt("nugget_extractor_md", _MD_PROMPT_FALLBACK)

    # Full resume fixture (raw resume text — first step input)
    fixture_path = Path(__file__).parent / "fixtures" / "career_satvik.txt"
    full_text = fixture_path.read_text()
    career_text = full_text[:3000]  # one batch — fair comparison across all models

    print("\n" + "=" * 90)
    print("NUGGET EXTRACTION BENCHMARK: JSON vs Markdown Approach")
    print("=" * 90)
    print(f"JSON prompt:     Langfuse 'nugget_extractor' v{json_v}  ({len(json_prompt)} chars)")
    print(f"Markdown prompt: Langfuse 'nugget_extractor_md' v{md_v}  ({len(md_prompt)} chars)")
    print(f"Input:           career_satvik.txt — first 3000 chars of {len(full_text)}-char resume")
    print(f"Ollama URL:      {ollama_url}")
    print(f"\nMarkdown prompt:\n{md_prompt[:500]}...")
    print("=" * 90)

    ollama_models = [
        "gemma4:e2b",
        "llama3.2:3b",
        "qwen2.5:3b",
        "deepseek-r1:1.5b",
        "gemma2:2b",
        "qwen3:1.7b",
        "qwen2.5:1.5b",
        "llama3.2:1b",
        "gemma3:1b",
        "smollm2:135m",
    ]

    all_results: list[ModelResult] = []

    # ── Groq 70B baseline — both approaches ──────────────────────────────────
    if groq_key:
        for approach, prompt in [("json", json_prompt), ("markdown", md_prompt)]:
            logger.info("Groq baseline (%s approach)...", approach)
            r = await test_model("llama-3.3-70b-versatile", "groq", prompt, approach, career_text, groq_key=groq_key)
            all_results.append(r)
            logger.info("  → %d nuggets, valid=%s, %.1fs", r.nugget_count, r.valid_parse, r.latency_s)
            if r.raw_output:
                print(f"\nGroq {approach} output (first 500 chars):\n{r.raw_output[:500]}\n")
    else:
        logger.warning("GROQ_API_KEY not set — skipping baseline")

    # ── Local models — markdown approach ONLY (JSON has been shown to fail) ──
    # We test JSON first to confirm, then markdown to find winner
    for model in ollama_models:
        for approach, prompt in [("json", json_prompt), ("markdown", md_prompt)]:
            logger.info("  %s [%s]...", model, approach)
            r = await test_model(model, "ollama", prompt, approach, career_text, ollama_url=ollama_url)
            all_results.append(r)
            logger.info("  → %d nuggets, valid=%s, %.1fs", r.nugget_count, r.valid_parse, r.latency_s)
            if r.raw_output and approach == "markdown":
                print(f"\n{model} markdown output (first 300 chars):\n{r.raw_output[:300]}\n")

    # ── Results table ─────────────────────────────────────────────────────────
    print("\n" + "=" * 100)
    print("RESULTS: JSON vs MARKDOWN APPROACH")
    print("=" * 100)
    print(f"{'Model':<28} {'Approach':<10} {'Lat':>6} {'Valid':>5} {'N':>4} {'sec%':>5} {'c+r%':>5} {'imp%':>5} {'ans%':>5} {'PASS':>5}")
    print("-" * 100)

    for r in all_results:
        n = max(r.nugget_count, 1)
        w = max(r.work_nugget_count, 1)
        print(
            f"{r.model:<28} {r.approach:<10} {r.latency_s:>6.1f} "
            f"{'Y' if r.valid_parse else 'N':>5} {r.nugget_count:>4} "
            f"{r.score_pct(r.section_type_valid, n):>5} "
            f"{r.score_pct(r.company_role_present, w):>5} "
            f"{r.score_pct(r.importance_valid, n):>5} "
            f"{r.score_pct(r.answer_self_contained, n):>5} "
            f"{'✅' if r.passes() else '❌':>5}"
        )
        for e in r.errors[:1]:
            print(f"  ⚠  {e}")

    print("=" * 100)

    md_winners = [r for r in all_results if r.approach == "markdown" and r.passes() and r.provider == "ollama"]
    json_winners = [r for r in all_results if r.approach == "json" and r.passes() and r.provider == "ollama"]

    print(f"\nJSON winners:     {[r.model for r in json_winners] or 'none'}")
    print(f"Markdown winners: {[r.model for r in md_winners] or 'none'}")

    if md_winners:
        fastest = min(md_winners, key=lambda r: r.latency_s)
        print(f"\n✅ Best local model (markdown): {fastest.model} ({fastest.latency_s:.1f}s)")
        print(f"   Switch: NUGGET_LLM_MODEL={fastest.model} NUGGET_LLM_BASE_URL=http://localhost:11434/v1")
        print(f"   Also: update nugget_extractor.py to use Langfuse 'nugget_extractor_md' + markdown parser")
    else:
        print("\n❌ No local model passes on markdown either — keep Groq 70B")
        print("   Recommendation: design a simpler markdown prompt with fewer fields")

    # ── Show sample nuggets from Groq markdown approach ───────────────────────
    groq_md = next((r for r in all_results if r.provider == "groq" and r.approach == "markdown"), None)
    if groq_md and groq_md.raw_output:
        print(f"\n{'='*80}\nGROQ MARKDOWN RAW OUTPUT (full)\n{'='*80}")
        print(groq_md.raw_output[:2000])

    groq_json = next((r for r in all_results if r.provider == "groq" and r.approach == "json"), None)
    if groq_json and groq_json.raw_output:
        print(f"\n{'='*80}\nGROQ JSON RAW OUTPUT (first 1000 chars)\n{'='*80}")
        print(groq_json.raw_output[:1000])


if __name__ == "__main__":
    asyncio.run(run_benchmark())
