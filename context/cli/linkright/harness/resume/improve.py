"""linkright resume improve — REFINE existing bullets, NOT regenerate.

Conceptual distinction (per Satvik 2026-05-01):
  - SCRATCH REGEN (linkright resume tailor): run pipeline → generate NEW bullets
    from nuggets. Each call produces fresh content.
  - IMPROVE (this command): read EXISTING bullets, identify what's MISSING vs
    target dim, run TARGETED refinement LLM call to fix only that deficiency
    while preserving everything else (metrics, bolds, verb, structure).

Per-dim refinement strategies:
  - width_hit_rate  → bullets out of [108,118] char band → trim/expand
  - xyz_format_purity → bullets missing X/Y/Z → restructure
  - keyword_coverage → JD keywords missing → naturally incorporate
  - verb_diversity → repeated/weak verbs → swap with stronger alternatives
  - metric_density → bullets without numbers → add metric from source nugget

MVP (this turn): width_hit_rate only. Pattern extends to other dims.

Reuses existing infrastructure:
  - tier_chat with klass=B (surgical edit) — free Cerebras qwen-235B path
  - fabrication guards (v8 metric_extract, v9 jd_keyphrase) for output validation
  - step_14 + step_15 to re-render HTML + PDF after improvement
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Optional

from ._paths import RUNS_ROOT


def _plain_chars(html: str) -> int:
    """Char count after stripping HTML tags + collapsing whitespace."""
    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"\s+", " ", text).strip()
    return len(text)


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def improve_width(run_dir: Path, dry_run: bool = False) -> dict:
    """Identify out-of-band bullets and refine them with targeted LLM call.

    Reads 12_condensed_bullets.json. For each bullet outside [108,118] char band,
    sends to tier_chat klass=B with a TARGETED prompt: "trim/expand to land in
    target band, preserve all bold tags + numbers + lead verb verbatim."

    Writes improved bullets back to 12_condensed_bullets.json. Caller should
    re-run step_14 + step_15 separately to regenerate HTML + PDF.

    Returns counts dict.
    """
    from linkright.llm.direct import tier_chat
    from linkright.resume.lib.width_config import (
        STEP12_MIN_CHARS, STEP12_MAX_CHARS, STEP12_TARGET_MIDPOINT,
    )

    bullets_path = run_dir / "artifacts" / "12_condensed_bullets.json"
    if not bullets_path.exists():
        return {"error": f"Missing {bullets_path}"}

    by_company = json.loads(bullets_path.read_text())
    counts = {"total": 0, "in_band": 0, "out_of_band": 0,
              "improved": 0, "unchanged": 0, "failed": 0}

    # 2026-05-02: load step_10 verbose paragraphs as source material for expansion.
    # Pre-fix the LLM was asked to expand bullets without source content, so it
    # either rewrote the bold portion (fail) or invented filler (fabrication risk).
    # Feeding the bullet's parent verbose paragraph gives factual room to expand.
    v10_path = run_dir / "artifacts" / "10_verbose_bullets.json"
    v10 = json.loads(v10_path.read_text()) if v10_path.exists() else {}

    def _find_verbose_context(company: str, bullet_html: str) -> str:
        para_pool = (v10.get(company) or {}).get("paragraphs") or []
        bullet_plain = _strip_html(bullet_html).lower()[:40]
        for p in para_pool:
            ctx_text = p.get("verbose_context") or ""
            if not ctx_text:
                continue
            p_plain = _strip_html(p.get("text_html") or "").lower()[:40]
            if p_plain and (p_plain in bullet_plain or bullet_plain in p_plain):
                return ctx_text
        # Fallback: first non-empty verbose_context from the company (less precise)
        for p in para_pool:
            if p.get("verbose_context"):
                return p["verbose_context"]
        return ""

    for company, bullets in by_company.items():
        for b in bullets:
            counts["total"] += 1
            html = b.get("text_html", "")
            current_len = _plain_chars(html)

            if STEP12_MIN_CHARS <= current_len <= STEP12_MAX_CHARS:
                counts["in_band"] += 1
                continue

            counts["out_of_band"] += 1
            direction = "trim" if current_len > STEP12_MAX_CHARS else "expand"
            delta = abs(current_len - STEP12_TARGET_MIDPOINT)

            print(f"  → bullet ({current_len}c, {direction} ~{delta}c): {_strip_html(html)[:80]}...",
                  file=sys.stderr)

            if dry_run:
                continue

            # 2026-05-02: deterministic article + phrase + numeral tweaks BEFORE LLM.
            # Zero-fabrication, fast, free. If tweaks alone land in band, no LLM needed.
            # Per Satvik 2026-05-02: commit ANY partial gain even if not fully in band,
            # so incremental progress is never lost — the LLM fallback (if it runs)
            # operates on the tweaked baseline, not the original.
            if direction == "expand":
                tweaked_html, tweak_rules = _apply_width_expand_tweaks(
                    html, STEP12_MIN_CHARS, STEP12_MAX_CHARS,
                )
                tweaked_len = _plain_chars(tweaked_html)
                orig_bolds = set(re.findall(r"<b[^>]*>(.*?)</b>", html, re.I | re.DOTALL))
                new_bolds = set(re.findall(r"<b[^>]*>(.*?)</b>", tweaked_html, re.I | re.DOTALL))
                bolds_intact = (orig_bolds == new_bolds)

                if STEP12_MIN_CHARS <= tweaked_len <= STEP12_MAX_CHARS and bolds_intact:
                    b["text_html"] = tweaked_html
                    b["improved_by"] = "improve_width_tweaks"
                    counts["improved"] += 1
                    print(f"     ✓ tweaks → {tweaked_len}c [{', '.join(tweak_rules)}]",
                          file=sys.stderr)
                    continue

                # Partial-gain commit: tweaks moved length closer to target,
                # bolds intact — save now so the gain isn't lost if LLM fails.
                if tweak_rules and bolds_intact and tweaked_len > current_len:
                    b["text_html"] = tweaked_html
                    b["improved_by"] = "improve_width_tweaks(partial)"
                    print(f"     · partial commit → {tweaked_len}c "
                          f"[{', '.join(tweak_rules)}], LLM will refine further",
                          file=sys.stderr)
                    html = tweaked_html
                    current_len = tweaked_len
                elif tweak_rules:
                    print(f"     · tweaks applied → {tweaked_len}c "
                          f"[{', '.join(tweak_rules)}] — bolds drifted, NOT committing",
                          file=sys.stderr)

            verbose_context = (
                _find_verbose_context(company, html) if direction == "expand" else ""
            )

            extra_source = (
                f"\n\nSOURCE MATERIAL (factually true; pull 1-2 details from here):\n"
                f"{verbose_context}\n"
                if verbose_context else ""
            )

            # 2026-05-02 NEW-4: mask bolds with sentinels BEFORE LLM call so
            # LLM cannot mangle them by construction. Restore after. This
            # eliminates the prior LLM-changes-bold-content failure mode that
            # validation kept rejecting. Per Satvik's directive to find
            # full-proof solutions, not pattern-on-pattern band-aids.
            masked_html, bold_spans_for_restore = _protect_bolds(html)
            sys_prompt = (
                f"Refine ONE resume bullet to land in {STEP12_MIN_CHARS}-{STEP12_MAX_CHARS} "
                f"plain-text characters (target: {STEP12_TARGET_MIDPOINT}). "
                f"Currently {current_len} chars (masked); need to {direction} by ~{delta}.\n\n"
                f"HARD CONSTRAINTS:\n"
                f"- The string contains sentinel tokens like `\\x00B0\\x00`, `\\x00B1\\x00` etc. "
                f"PRESERVE THESE TOKENS EXACTLY — do not split, modify, translate, or remove. "
                f"They are placeholders for protected content (numbers/metrics/verbs).\n"
                f"- Preserve all visible numbers, %, $, K, M, B, named entities verbatim\n"
                f"- Output ONLY the rewritten bullet text (with sentinels intact) — no "
                f"preamble, no quotes, no commentary"
                f"{extra_source}"
            )
            try:
                new_masked, _ = tier_chat(
                    system=sys_prompt,
                    user=masked_html,
                    klass="B",
                    intent="improve_width",
                    max_tokens=300,
                )
                new_masked = new_masked.strip().split("\n")[0].strip().strip('"')

                # Restore bolds. If LLM dropped any sentinel, restoration fails
                # gracefully — placeholder stays as text artifact, validation
                # rejects.
                new_html = _restore_bolds(new_masked, bold_spans_for_restore)
                new_len = _plain_chars(new_html)

                # Validate: bolds preserved by construction (sentinel-restoration
                # guarantees text-inside-<b> is identical to input). Verify the
                # SENTINELS survived (so all bolds restored correctly).
                expected_sentinel_count = len(bold_spans_for_restore)
                missing_sentinels = sum(
                    1 for i in range(expected_sentinel_count)
                    if f"\x00B{i}\x00" not in new_masked
                )
                bolds_intact = (missing_sentinels == 0)

                if STEP12_MIN_CHARS <= new_len <= STEP12_MAX_CHARS and bolds_intact:
                    b["text_html"] = new_html
                    b["improved_by"] = "improve_width"
                    counts["improved"] += 1
                    print(f"     ✓ improved → {new_len}c (bolds masked + restored)",
                          file=sys.stderr)
                else:
                    counts["unchanged"] += 1
                    reason = []
                    if not (STEP12_MIN_CHARS <= new_len <= STEP12_MAX_CHARS):
                        reason.append(f"still out of band ({new_len}c)")
                    if not bolds_intact:
                        reason.append(f"LLM dropped {missing_sentinels} sentinel(s) — bold restore broken")
                    print(f"     ✗ rejected: {'; '.join(reason)}", file=sys.stderr)
            except Exception as e:
                counts["failed"] += 1
                print(f"     ✗ LLM error: {type(e).__name__}", file=sys.stderr)

    partial_count = sum(
        1 for co in by_company for b in by_company[co]
        if isinstance(b, dict) and "improve_width_tweaks(partial)" in str(b.get("improved_by", ""))
    )
    counts["partial"] = partial_count
    if not dry_run and (counts["improved"] > 0 or partial_count > 0):
        bullets_path.write_text(json.dumps(by_company, indent=2))
        print(f"\n✓ Wrote {counts['improved']} full + {partial_count} partial "
              f"improvements back to {bullets_path.name}", file=sys.stderr)

    return counts


def improve_keywords(run_dir: Path, max_keywords: int = 6, dry_run: bool = False) -> dict:
    """Identify JD keywords missing from resume → naturally incorporate into best-fit bullets.

    Strategy:
      1. Load JD keywords from 07_jd_parse_strategy.json
      2. Compute which are MISSING from current 14_final_resume.html
      3. For top N missing (keyword importance — first N from JD's prioritized list):
         - Find shortest non-improved bullet (room to add words; not yet touched)
         - Send to LLM with: "incorporate '{keyword}' naturally OR return UNCHANGED
           if it doesn't fit the bullet's actual experience"
         - LLM's UNCHANGED escape hatch prevents hallucination
      4. Validate output contains the keyword + bolds preserved + length sane
      5. Apply ONLY if validates

    Returns counts dict.
    """
    from linkright.llm.direct import tier_chat

    bullets_path = run_dir / "artifacts" / "12_condensed_bullets.json"
    strat_path = run_dir / "artifacts" / "07_jd_parse_strategy.json"
    html_path = run_dir / "artifacts" / "14_final_resume.html"
    if not all(p.exists() for p in (bullets_path, strat_path, html_path)):
        return {"error": "missing required artifacts"}

    by_company = json.loads(bullets_path.read_text())
    strat = json.loads(strat_path.read_text())
    keywords = strat.get("parsed", {}).get("jd_keywords", []) or []

    html_text = re.sub(r"<[^>]+>", " ", html_path.read_text()).lower()
    missing = [k for k in keywords if k.lower() not in html_text]

    counts = {
        "total_keywords": len(keywords),
        "missing_before": len(missing),
        "attempted": 0,
        "incorporated": 0,
        "skipped_unchanged_by_llm": 0,
        "validation_failed": 0,
    }
    print(f"  Total JD keywords: {len(keywords)}; missing: {len(missing)}", file=sys.stderr)

    # Flatten bullets with company tag for selection
    all_bullets: list[tuple[str, dict]] = []
    for company, bullets in by_company.items():
        for b in bullets:
            all_bullets.append((company, b))

    touched_indices: set[int] = set()

    for kw in missing[:max_keywords]:
        # Pick the shortest UNTOUCHED bullet (room to grow)
        candidates = [(i, c, b) for i, (c, b) in enumerate(all_bullets) if i not in touched_indices]
        if not candidates:
            break
        candidates.sort(key=lambda t: _plain_chars(t[2].get("text_html", "")))
        # Skip extremely short bullets (already at floor) — pick first that has room
        target = next(((i, c, b) for i, c, b in candidates
                       if 80 <= _plain_chars(b.get("text_html", "")) <= 115),
                      candidates[0] if candidates else None)
        if target is None:
            break
        idx, company, bullet = target
        original_html = bullet.get("text_html", "")
        original_len = _plain_chars(original_html)

        counts["attempted"] += 1
        print(f"\n  → keyword '{kw}' → {company} bullet ({original_len}c)", file=sys.stderr)
        print(f"     before: {_strip_html(original_html)[:100]}...", file=sys.stderr)

        if dry_run:
            touched_indices.add(idx)
            continue

        sys_prompt = (
            f"Refine ONE existing resume bullet to naturally incorporate a missing JD keyword.\n\n"
            f"MISSING KEYWORD: \"{kw}\"\n"
            f"CURRENT BULLET LENGTH: {original_len} chars\n"
            f"TARGET LENGTH: {original_len + 5} to {original_len + 12} chars (small addition only)\n\n"
            f"HARD RULES:\n"
            f"- If '{kw}' genuinely fits the bullet's experience, weave it in (1-3 added words)\n"
            f"- If '{kw}' does NOT fit (would be fabrication), return bullet UNCHANGED verbatim\n"
            f"- Never invent metrics/projects/activities not in original\n"
            f"- Keep every <b>...</b> span and ITS contents intact\n"
            f"- Keep all numbers, %, $, K, M, B, company names verbatim\n"
            f"- Keep lead verb\n"
            f"- Output ONLY the rewritten bullet HTML — no preamble, no quotes, no explanation"
        )
        try:
            new_html, _usage = tier_chat(
                system=sys_prompt,
                user=original_html,
                klass="B",
                intent="improve_keyword_coverage",
                max_tokens=300,
            )
            new_html = new_html.strip().split("\n")[0].strip().strip('"')
            new_len = _plain_chars(new_html)

            # Always mark bullet as touched — don't pick same one again on failure.
            touched_indices.add(idx)

            # Validations: keyword present + ALL original bolded TEXT still in output
            # + length within ±20 of original + word-bag overlap ≥ 75% (prevents
            # LLM from silently dropping content while adding the keyword).
            keyword_present = kw.lower() in _strip_html(new_html).lower()
            orig_bold_text = set(re.findall(r"<b[^>]*>(.*?)</b>", original_html, re.I | re.DOTALL))
            new_plain = _strip_html(new_html).lower()
            orig_plain = _strip_html(original_html).lower()
            bolds_preserved = all(_strip_html(t).lower() in new_plain for t in orig_bold_text)
            length_sane = (original_len - 5) <= new_len <= (original_len + 25)
            # Word-bag overlap check — original tokens (>3 chars, no kw itself) must
            # mostly survive into new text. Catches "LLM rewrote whole bullet" failures.
            orig_words = {w for w in re.findall(r"\w{4,}", orig_plain) if w != kw.lower()}
            new_words = set(re.findall(r"\w{4,}", new_plain))
            overlap = len(orig_words & new_words) / max(len(orig_words), 1)
            content_preserved = overlap >= 0.75

            if new_html.strip() == original_html.strip():
                counts["skipped_unchanged_by_llm"] += 1
                print(f"     → LLM left unchanged (keyword didn't fit)", file=sys.stderr)
                continue

            if keyword_present and bolds_preserved and length_sane and content_preserved:
                bullet["text_html"] = new_html
                bullet["improved_by"] = bullet.get("improved_by", "") + ";improve_keywords"
                bullet["keywords_added"] = (bullet.get("keywords_added") or []) + [kw]
                counts["incorporated"] += 1
                print(f"     ✓ incorporated '{kw}' → {new_len}c (overlap {overlap*100:.0f}%)",
                      file=sys.stderr)
                print(f"     after:  {_strip_html(new_html)[:100]}...", file=sys.stderr)
            else:
                counts["validation_failed"] += 1
                reasons = []
                if not keyword_present: reasons.append(f"'{kw}' missing in output")
                if not bolds_preserved: reasons.append("original bold text lost")
                if not length_sane: reasons.append(f"length {new_len}c out of [{original_len-5}, {original_len+25}]")
                if not content_preserved: reasons.append(f"content overlap only {overlap*100:.0f}% (need ≥75%)")
                print(f"     ✗ rejected: {'; '.join(reasons)}", file=sys.stderr)
        except Exception as e:
            counts["validation_failed"] += 1
            touched_indices.add(idx)
            print(f"     ✗ LLM error: {type(e).__name__}: {str(e)[:80]}", file=sys.stderr)

    if not dry_run and counts["incorporated"] > 0:
        bullets_path.write_text(json.dumps(by_company, indent=2))
        print(f"\n✓ Wrote {counts['incorporated']} keyword incorporations back to "
              f"{bullets_path.name}", file=sys.stderr)

    return counts


# Bring the width-config constants into this module's scope (lazy-loaded above
# in improve_width; replicate here so improve_keywords can reference without
# recursive import).
from linkright.resume.lib.width_config import (
    STEP12_MIN_CHARS as STEP12_MIN_CHARS_LOCAL,
    STEP12_MAX_CHARS as STEP12_MAX_CHARS_LOCAL,
    STEP12_TARGET_MIDPOINT as STEP12_TARGET_LOCAL,
)


def improve_skills_keyword_fill(run_dir: Path, dry_run: bool = False) -> dict:
    """Append missing JD keywords to Skills section + rescue any dropped by step_07.

    Per Satvik 2026-05-01: "if keywords can't be naturally fitted into bullets,
    put them in Skills section in clean comma-separated format without
    categorization." Skills section is the ATS keyword dump zone — bullets
    stay narrative + metric-rich, Skills carries keyword coverage.

    WHY we write to 07_jd_parse_strategy.json (not 01_resume_parsed.json):
    step_14 renderer reads parsed_p12.skills (the dict from step_07), NOT
    parsed.skills (the flat list from step_01). Earlier write target was a
    silent no-op — additions never reached the rendered HTML. Single-bucket
    dict {"Skills": [...]} satisfies both step_14's dict iteration and the
    "no categorization" user intent (HTML render flattens regardless).

    Algorithm:
      1. Read parsed_p12 from 07_jd_parse_strategy.json (the dict step_14 reads)
      2. Flatten existing parsed_p12.skills categories
      3. Rescue any parsed.skills (step_01 flat list) that step_07 LLM dropped
      4. Find JD keywords missing from HTML corpus + flat skills
      5. Write a single-bucket {"Skills": flat_list} back to parsed_p12.skills

    Caller follows up with re_render() to regenerate HTML+PDF.
    Returns counts dict.
    """
    parsed_path = run_dir / "artifacts" / "01_resume_parsed.json"
    strat_path = run_dir / "artifacts" / "07_jd_parse_strategy.json"
    html_path = run_dir / "artifacts" / "14_final_resume.html"
    if not strat_path.exists():
        return {"error": "missing 07_jd_parse_strategy.json"}

    strat_artifact = json.loads(strat_path.read_text())
    parsed_p12 = strat_artifact["parsed"] if "parsed" in strat_artifact else strat_artifact

    skills_dict_existing = parsed_p12.get("skills") or {}
    if not isinstance(skills_dict_existing, dict):
        skills_dict_existing = {}

    flat_from_07: list[str] = []
    seen_lower: set[str] = set()
    for _cat, _items in skills_dict_existing.items():
        for _it in (_items or []):
            if _it and _it.lower() not in seen_lower:
                flat_from_07.append(_it)
                seen_lower.add(_it.lower())

    flat_from_01: list[str] = []
    if parsed_path.exists():
        p01 = json.loads(parsed_path.read_text())
        for _it in (p01.get("parsed", {}).get("skills") or []):
            if _it and _it.lower() not in seen_lower:
                flat_from_01.append(_it)
                seen_lower.add(_it.lower())

    flat_existing = flat_from_07 + flat_from_01
    jd_keywords = parsed_p12.get("jd_keywords") or []

    corpus_text = ""
    if html_path.exists():
        corpus_text = re.sub(r"<[^>]+>", " ", html_path.read_text()).lower()
    full_corpus = corpus_text + " " + " ".join(flat_existing).lower()

    missing = [kw for kw in jd_keywords if kw.lower() not in full_corpus]

    counts = {
        "total_jd_keywords": len(jd_keywords),
        "already_covered": len(jd_keywords) - len(missing),
        "missing_to_add": len(missing),
        "skills_07_before": len(flat_from_07),
        "skills_rescued_from_01": len(flat_from_01),
    }
    print(f"  JD keywords: {len(jd_keywords)} total, "
          f"{counts['already_covered']} already covered, "
          f"{len(missing)} missing", file=sys.stderr)
    if flat_from_01:
        print(f"  rescuing {len(flat_from_01)} skills dropped by step_07 "
              f"(present in step_01 parse but lost in JD strategy)",
              file=sys.stderr)

    additions: list[str] = []
    for kw in missing:
        if kw.lower() not in seen_lower:
            additions.append(kw)
            seen_lower.add(kw.lower())

    final_flat = flat_existing + additions
    counts["skills_after"] = len(final_flat)
    counts["added"] = len(additions)

    if not additions and not flat_from_01 and skills_dict_existing:
        return counts

    if missing:
        print(f"  → adding to Skills: {additions[:8]}{'...' if len(additions) > 8 else ''}",
              file=sys.stderr)
    if dry_run:
        return counts

    parsed_p12["skills"] = {"Skills": final_flat}
    if "parsed" in strat_artifact:
        strat_artifact["parsed"] = parsed_p12
    else:
        strat_artifact = parsed_p12
    strat_path.write_text(json.dumps(strat_artifact, indent=2))

    print(f"  ✓ Skills: {len(flat_from_07)} (07) + {len(flat_from_01)} (rescued from 01) "
          f"+ {len(additions)} (JD-keyword fills) = {len(final_flat)} total",
          file=sys.stderr)
    return counts


# Acronym candidates that take a definite article ("the AML risk engine").
# Per Satvik 2026-05-02 (memory `feedback_expand_deterministic_dictionaries`):
# comprehensive coverage across all common job domains so the deterministic
# width-tweak toolkit works on any resume, not just current samples.
# ~250 acronyms grouped by domain.
_ARTICLE_CANDIDATES = {
    # Tech / Web
    "REST", "OAuth", "JWT", "gRPC", "GraphQL", "WebSocket", "SSL", "TLS",
    "JSON", "XML", "HTML", "CSS", "DOM", "AJAX", "CRUD", "MVC", "MVVM",
    "IDE", "CLI", "GUI", "SDK", "API", "APIs", "CDN", "DNS", "HTTP",
    "HTTPS", "FTP", "SFTP", "SSH", "VPN", "LAN", "WAN", "ISP", "URL",
    "URI", "UUID", "BLOB", "MIME", "OAS", "RPC", "SOAP",
    # Cloud / Infrastructure
    "AWS", "GCP", "Azure", "EC2", "S3", "RDS", "IAM", "VPC", "EKS", "ECS",
    "GKE", "AKS", "ELB", "EBS", "EFS", "SNS", "SQS", "KMS", "SAM",
    "CloudFormation", "CloudFront", "CloudWatch", "Route53",
    # DevOps / SRE
    "CI/CD", "K8s", "Docker", "GitOps", "IaC", "SRE", "MTTR", "MTBF",
    "SLI", "SLO", "SLA", "RTO", "RPO", "DR", "HA",
    # Data / Database
    "SQL", "NoSQL", "ORM", "ETL", "ELT", "OLAP", "OLTP", "ACID", "BASE",
    "BI", "DW", "CDC", "RDBMS", "DBMS", "PII",
    # AI / ML
    "ML", "AI", "LLM", "NLP", "CV", "RNN", "CNN", "GAN", "RL", "ASR",
    "TTS", "OCR", "GPU", "TPU", "BERT", "GPT", "LSTM", "DNN", "MLOps",
    # Security / Compliance
    "SAML", "SSO", "SCIM", "RBAC", "ABAC", "ACL", "MFA", "2FA", "PHI",
    "HIPAA", "PCI", "GDPR", "CCPA", "SOC", "SOC2", "ISO", "ISO27001",
    "NIST", "FedRAMP", "SOX", "GLBA", "BSA", "OFAC", "KYC", "AML", "CFT",
    "AML/CFT", "FATCA", "PSD2",
    # Business / Finance
    "KPI", "OKR", "ROI", "P&L", "EBITDA", "MRR", "ARR", "ACV", "TCV",
    "LTV", "CAC", "NPS", "CSAT", "GMV", "FX", "IRR", "NPV", "COGS",
    "TAM", "SAM", "SOM", "CES",
    # Product / UX
    "MVP", "POC", "PRD", "BRD", "TRD", "JTBD", "DAU", "MAU", "WAU",
    "RICE", "AARRR", "QBR", "UX", "UI", "PM", "PMF", "ICE", "PIRATE",
    # Methodology / Process
    "SAFe", "Scrum", "XP", "Kanban", "Lean", "PI", "BRD", "PRD",
    "V2MOM", "RACI", "DACI", "MoSCoW",
    # Healthcare
    "EMR", "EHR", "FDA", "ICD", "CPT", "HL7", "FHIR", "EOB", "RCM",
    # Marketing / Sales
    "SEO", "SEM", "CTR", "CPM", "CPC", "CPL", "CPA", "ROAS", "MQL",
    "CRM", "MAP", "CMS", "DMP", "DSP", "SSP", "CTA", "UTM", "ABM",
    # HR / Ops / Org
    "HRMS", "ATS", "LMS", "ERP", "ESS", "FTE", "PTO", "MBO", "PIP",
    "L&D", "DEI",
    # SaaS Business / Vendor
    "SaaS", "PaaS", "IaaS", "B2B", "B2C", "B2B2C", "D2C", "G2C",
    # Database brands & infra (often need "the" for proper-noun reads)
    "AWS", "GCP", "MCP",
    # Compliance & Standards (mixed cases preserved)
    "SOC", "PCI-DSS",
}

# Short → long preposition / phrase swaps. Each "short" maps to a list of
# alternatives so we can rotate through them within one bullet — using the
# same target word 3× yields awkward repetition (e.g. "across X across Y
# across Z"), caught by the logical-sanity check.
# 2026-05-02 expanded per memory `feedback_expand_deterministic_dictionaries`
# — broader coverage across job domains.
_EXPAND_PHRASE_SWAPS: dict[str, list[str]] = {
    " via ":      [" through ", " by means of "],                    # +3 / +8
    " by ":       [" through "],                                     # +4
    " in ":       [" across ", " throughout ", " within "],          # +2 / +8 / +4
    " for ":      [" supporting ", " regarding ", " across "],       # +6 / +5 / +3
    " on ":       [" regarding ", " across "],                       # +5 / +3
    " to ":       [" towards "],                                     # +5
    " with ":     [" alongside ", " along with "],                   # +4 / +5
    " of ":       [" associated with "],                             # +12
    " from ":     [" originating from ", " starting from "],         # +12 / +9
    " at ":       [" within "],                                      # +3
    " over ":     [" spanning ", " throughout "],                    # +5 / +9
    " across ":   [" spanning ", " throughout ", " within "],        # +5 / +9 / +4
    " using ":    [" leveraging "],                                  # +5  (filtered: see below)
    " during ":   [" throughout "],                                  # +5
    " after ":    [" subsequent to "],                               # +12
    " before ":   [" prior to "],                                    # +6
    " about ":    [" regarding "],                                   # +4
    " among ":    [" across "],                                      # +1
    " between ":  [" spanning "],                                    # +0
    " through ":  [" by way of "],                                   # +5
    " led ":      [" spearheaded "],                                 # +9 (verb → verb-style fill)
}
# Filter banned filler verbs ("leveraging" is on global ban list per
# `feedback_metrics_only_bolding` — though here it's a phrase-swap target
# not a bolded verb. Decision: keep banned-filler-aware filter on output).
_BANNED_FILLER_TARGETS = {"leveraging"}
_EXPAND_PHRASE_SWAPS = {
    short: [a for a in alts
            if not any(b in a for b in _BANNED_FILLER_TARGETS)]
    for short, alts in _EXPAND_PHRASE_SWAPS.items()
}
_EXPAND_PHRASE_SWAPS = {k: v for k, v in _EXPAND_PHRASE_SWAPS.items() if v}

_CONTRACTIONS = {
    "don't": "do not", "won't": "will not", "can't": "cannot",
    "isn't": "is not", "aren't": "are not", "wasn't": "was not",
    "weren't": "were not", "doesn't": "does not", "didn't": "did not",
    "hasn't": "has not", "haven't": "have not", "hadn't": "had not",
    "couldn't": "could not", "wouldn't": "would not", "shouldn't": "should not",
    "it's": "it is", "that's": "that is", "they're": "they are",
    "you're": "you are", "we're": "we are", "i'm": "I am",
}


_LOGICAL_STOPWORDS = {
    "the", "and", "for", "with", "from", "into", "that", "this", "these",
    "across", "through", "within", "via", "alongside",  # don't double-count
    # the prep targets themselves (we explicitly check non-prep words)
}


def _logical_sanity_check(html: str) -> tuple[bool, str]:
    """Reject if a non-stopword non-metric word repeats 3+ times.

    Per Satvik 2026-05-02: "should make sense logically, should not be
    illogical." A bullet with three "across" or three identical content
    words reads as a tweak-overshoot — revert.
    """
    plain = re.sub(r"<[^>]+>", " ", html).lower()
    tokens = re.findall(r"\b[a-z]{3,}\b", plain)
    counts: dict[str, int] = {}
    for t in tokens:
        if t in _LOGICAL_STOPWORDS:
            continue
        counts[t] = counts.get(t, 0) + 1
    triples = [t for t, n in counts.items() if n >= 3]
    if triples:
        return False, f"3x repeat: {triples[0]}"
    # Also flag if any prep target now appears >= 3 times after expansion —
    # that's the awkwardness we explicitly want to catch.
    prep_targets = ["across", "through", "throughout", "within",
                    "alongside", "supporting", "regarding"]
    for w in prep_targets:
        if len(re.findall(rf"\b{w}\b", plain)) >= 3:
            return False, f"3x prep-target: {w}"
    return True, ""


def _protect_bolds(html: str) -> tuple[str, list[str]]:
    """Replace <b>...</b> spans with sentinel tokens. Returns (masked, spans).

    Lets us run text transformations on the non-bold portion of a bullet
    without risking corrupting bolded metrics or verbs. Caller restores via
    `_restore_bolds(masked, spans)`.
    """
    spans: list[str] = []
    def _capture(m: re.Match) -> str:
        spans.append(m.group(0))
        return f"\x00B{len(spans)-1}\x00"
    masked = re.sub(r"<b\b[^>]*>.*?</b>", _capture, html, flags=re.S | re.I)
    return masked, spans


def _restore_bolds(masked: str, spans: list[str]) -> str:
    out = masked
    for i, s in enumerate(spans):
        out = out.replace(f"\x00B{i}\x00", s)
    return out


def _apply_width_expand_tweaks(html: str, target_min: int, target_max: int) -> tuple[str, list[str]]:
    """Deterministic width-expansion via articles, contractions, prep swaps.

    Per Satvik 2026-05-02: zero-fabrication width expansion. Bold spans are
    masked before transformation so every <b>...</b> stays byte-identical —
    rule pollution into metrics is impossible. Returns (new_html, applied).
    Stops once plain length lands in [target_min, target_max].
    """
    masked, spans = _protect_bolds(html)
    applied: list[str] = []

    def _full_len() -> int:
        restored = _restore_bolds(masked, spans)
        return len(re.sub(r"<[^>]+>", "", restored))

    if _full_len() >= target_min:
        return _restore_bolds(masked, spans), applied

    # Rule 1: add "the" before bare-mention acronyms (after a preposition).
    preps = r"(?:for|in|on|with|by|to|of|from|at|across|via|through|under|over)"
    for ac in _ARTICLE_CANDIDATES:
        pat = re.compile(rf"(\b{preps}\b\s+)({re.escape(ac)})\b")
        if pat.search(masked):
            masked = pat.sub(rf"\1the \2", masked, count=1)
            applied.append(f"article: 'the {ac}'")
            if target_min <= _full_len() <= target_max:
                return _restore_bolds(masked, spans), applied

    # Rule 2: expand contractions (rare in resumes — defensive).
    for c, full in _CONTRACTIONS.items():
        cap_c = c[0].upper() + c[1:]
        cap_full = full[0].upper() + full[1:]
        for src, dst in [(c, full), (cap_c, cap_full)]:
            if src in masked:
                masked = masked.replace(src, dst, 1)
                applied.append(f"contraction: {src}→{dst}")
                if target_min <= _full_len() <= target_max:
                    return _restore_bolds(masked, spans), applied

    # Rule 3: preposition / phrase swaps with target rotation.
    # Each `short` has multiple alternatives — rotate through them so we never
    # use the same target word more than once per bullet (avoids awkward
    # "across X across Y across Z"). After each swap, run a logical-sanity
    # check; revert if any non-stopword now appears 3+ times.
    used_targets: set[str] = set()
    for short, alternatives in _EXPAND_PHRASE_SWAPS.items():
        # Cycle through alternatives until none left or target hit
        while short in masked.lower():
            pre_swap_masked = masked
            chosen = next((a for a in alternatives
                           if a.strip().lower() not in used_targets), None)
            if chosen is None:
                break  # all alternatives exhausted for this short
            pat = re.compile(re.escape(short), re.IGNORECASE)
            new_masked = pat.sub(chosen, masked, count=1)
            if new_masked == masked:
                break
            # Logical-sanity check: revert if any non-stopword now repeats 3+ times
            ok, reason = _logical_sanity_check(new_masked)
            if not ok:
                masked = pre_swap_masked
                applied.append(f"prep:reverted({reason})")
                break  # this short exhausted — try next
            masked = new_masked
            used_targets.add(chosen.strip().lower())
            applied.append(f"prep: '{short.strip()}'→'{chosen.strip()}'")
            if target_min <= _full_len() <= target_max:
                return _restore_bolds(masked, spans), applied

    # Rule 4: numeral → word for small numerals (1-9) NOT adjacent to a metric symbol.
    NUMERAL_WORDS = {"1": "one", "2": "two", "3": "three", "4": "four",
                     "5": "five", "6": "six", "7": "seven", "8": "eight",
                     "9": "nine"}
    for digit, word in NUMERAL_WORDS.items():
        m = re.search(rf"\b{digit}\b(?!\s*[%$KMB+])(?!\s*-)", masked)
        if m:
            masked = masked[:m.start()] + word + masked[m.end():]
            applied.append(f"numeral: '{digit}'→'{word}'")
            if target_min <= _full_len() <= target_max:
                return _restore_bolds(masked, spans), applied

    return _restore_bolds(masked, spans), applied


# Comprehensive verb-synonym dictionary covering ~16 action categories
# generalizable across job domains. Per Satvik 2026-05-02: "expand your word
# dictionary to like maybe double just to ensure that all the unique possible
# combinations are covered. Like not just for some selected jobs, but for any
# jobs that you can come across, even in the future."
# Order within each list is roughly: most-natural / context-neutral first.
_VERB_SYNONYMS = {
    # Reduce / decrease cluster
    "reduced":     ["Lowered", "Slashed", "Trimmed", "Cut", "Curtailed",
                    "Decreased", "Compressed", "Shrunk", "Pared", "Minimized"],
    "cut":         ["Trimmed", "Slashed", "Reduced", "Lowered", "Pared",
                    "Curtailed"],
    "decreased":   ["Lowered", "Reduced", "Slashed", "Trimmed", "Diminished"],
    "lowered":     ["Reduced", "Cut", "Trimmed", "Slashed", "Decreased"],
    "minimized":   ["Reduced", "Curtailed", "Trimmed", "Diminished"],
    "eliminated":  ["Removed", "Eradicated", "Cleared", "Stripped"],
    # Increase / grow cluster
    "increased":   ["Lifted", "Boosted", "Elevated", "Grew", "Expanded",
                    "Amplified", "Scaled", "Raised", "Accelerated"],
    "grew":        ["Expanded", "Scaled", "Boosted", "Lifted", "Increased"],
    "expanded":    ["Grew", "Scaled", "Stretched", "Broadened", "Lifted"],
    "boosted":     ["Lifted", "Increased", "Elevated", "Amplified", "Raised"],
    "scaled":      ["Grew", "Expanded", "Multiplied", "Lifted"],
    "doubled":     ["Multiplied", "Expanded", "Lifted"],
    # Deliver / ship cluster
    "delivered":   ["Shipped", "Launched", "Released", "Deployed",
                    "Rolled out", "Debuted", "Executed"],
    "shipped":     ["Delivered", "Launched", "Released", "Deployed"],
    "launched":    ["Released", "Deployed", "Shipped", "Debuted",
                    "Rolled out", "Inaugurated"],
    "released":    ["Launched", "Shipped", "Deployed", "Debuted"],
    "deployed":    ["Launched", "Released", "Rolled out", "Shipped",
                    "Operationalized"],
    # Design / architect cluster
    "designed":    ["Architected", "Engineered", "Crafted", "Devised",
                    "Conceived", "Modeled", "Prototyped"],
    "built":       ["Constructed", "Engineered", "Crafted", "Forged",
                    "Assembled", "Erected"],
    "developed":   ["Engineered", "Built", "Crafted", "Constructed",
                    "Authored"],
    "architected": ["Designed", "Engineered", "Crafted", "Devised"],
    "engineered":  ["Architected", "Designed", "Built", "Constructed"],
    "created":     ["Built", "Engineered", "Crafted", "Forged", "Authored"],
    # Secure / win cluster
    "secured":     ["Won", "Locked in", "Captured", "Acquired", "Landed",
                    "Clinched", "Procured"],
    "won":         ["Captured", "Secured", "Clinched", "Acquired", "Landed"],
    "captured":    ["Secured", "Won", "Acquired", "Landed"],
    "acquired":    ["Captured", "Secured", "Won", "Procured"],
    "landed":      ["Won", "Secured", "Captured", "Clinched"],
    # Lead / manage cluster
    "led":         ["Spearheaded", "Steered", "Headed", "Helmed", "Directed",
                    "Drove", "Orchestrated", "Championed"],
    "managed":     ["Orchestrated", "Owned", "Directed", "Oversaw",
                    "Administered", "Supervised", "Headed"],
    "directed":    ["Led", "Steered", "Helmed", "Spearheaded"],
    "spearheaded": ["Led", "Drove", "Steered", "Championed"],
    "drove":       ["Spearheaded", "Led", "Propelled", "Powered"],
    "driven":      ["Drove", "Generated", "Propelled", "Produced",
                    "Spearheaded"],
    "owned":       ["Managed", "Directed", "Orchestrated", "Oversaw"],
    # Improve / optimize cluster
    "improved":    ["Enhanced", "Upgraded", "Refined", "Strengthened",
                    "Optimized", "Polished", "Elevated"],
    "enhanced":    ["Improved", "Upgraded", "Refined", "Strengthened",
                    "Optimized"],
    "optimized":   ["Refined", "Tuned", "Streamlined", "Enhanced"],
    "transformed": ["Revamped", "Overhauled", "Restructured", "Reimagined",
                    "Reinvented", "Modernized"],
    "streamlined": ["Optimized", "Tightened", "Simplified", "Accelerated"],
    "modernized":  ["Revamped", "Upgraded", "Updated", "Refreshed"],
    # Generate / produce cluster
    "generated":   ["Produced", "Yielded", "Earned", "Drove", "Created",
                    "Sparked", "Catalyzed"],
    "produced":    ["Generated", "Yielded", "Created", "Earned"],
    "yielded":     ["Generated", "Produced", "Earned", "Returned"],
    "earned":      ["Generated", "Yielded", "Captured", "Won"],
    # Analyze / assess cluster
    "analyzed":    ["Assessed", "Evaluated", "Examined", "Investigated",
                    "Reviewed", "Profiled", "Audited"],
    "assessed":    ["Analyzed", "Evaluated", "Reviewed", "Audited"],
    "evaluated":   ["Analyzed", "Assessed", "Examined", "Reviewed"],
    "audited":     ["Reviewed", "Assessed", "Examined", "Analyzed"],
    # Collaborate cluster
    "collaborated": ["Partnered", "Teamed", "Coordinated", "Aligned"],
    "partnered":    ["Collaborated", "Teamed", "Aligned", "Coordinated"],
    "coordinated":  ["Aligned", "Orchestrated", "Synced", "Partnered"],
    # Automate / accelerate cluster
    "automated":   ["Streamlined", "Accelerated", "Digitized",
                    "Operationalized"],
    "accelerated": ["Streamlined", "Sped up", "Boosted", "Hastened"],
    "expedited":   ["Accelerated", "Streamlined", "Sped up"],
    # Identify / discover cluster
    "identified":  ["Discovered", "Spotted", "Uncovered", "Pinpointed",
                    "Surfaced", "Recognized"],
    "discovered":  ["Identified", "Uncovered", "Spotted", "Detected"],
    "uncovered":   ["Identified", "Discovered", "Surfaced", "Exposed"],
    # Implement / deploy cluster
    "implemented": ["Deployed", "Rolled out", "Executed", "Operationalized",
                    "Instituted", "Integrated", "Installed"],
    "executed":    ["Implemented", "Deployed", "Carried out", "Performed"],
    "rolled":      ["Deployed", "Launched", "Released"],  # for "Rolled out" stem
    # Mentor / train cluster
    "mentored":    ["Coached", "Trained", "Guided", "Advised", "Counseled",
                    "Onboarded"],
    "trained":     ["Mentored", "Coached", "Taught", "Onboarded", "Guided"],
    "coached":     ["Mentored", "Trained", "Guided", "Advised"],
    # Migrate / transition cluster
    "migrated":    ["Transitioned", "Converted", "Ported", "Shifted",
                    "Refactored"],
    "transitioned": ["Migrated", "Converted", "Shifted", "Moved"],
    "refactored":  ["Restructured", "Reorganized", "Rebuilt", "Modernized"],
    # Integrate / connect cluster
    "integrated":  ["Connected", "Synced", "Unified", "Consolidated",
                    "Merged", "Aligned", "Linked", "Bridged"],
    "connected":   ["Integrated", "Linked", "Bridged", "Synced"],
    "consolidated":["Merged", "Unified", "Combined", "Integrated"],
    "merged":      ["Consolidated", "Unified", "Combined", "Integrated"],
    # Achieve / hit cluster
    "achieved":    ["Hit", "Reached", "Attained", "Secured", "Met",
                    "Surpassed", "Delivered"],
    "reached":     ["Hit", "Attained", "Achieved", "Surpassed"],
    "exceeded":    ["Surpassed", "Outperformed", "Beat", "Topped"],
    "surpassed":   ["Exceeded", "Outperformed", "Beat", "Topped"],
    # 2026-05-02 expansion (memory feedback_expand_deterministic_dictionaries):
    # broader coverage — research/negotiate/document/instrument/measure/etc.
    # Research / investigate cluster
    "researched":  ["Investigated", "Studied", "Explored", "Surveyed", "Probed"],
    "investigated": ["Researched", "Examined", "Probed", "Diagnosed"],
    "studied":     ["Examined", "Researched", "Reviewed", "Analyzed"],
    "explored":    ["Investigated", "Surveyed", "Probed", "Mapped"],
    "diagnosed":   ["Identified", "Pinpointed", "Detected", "Isolated"],
    # Negotiate / influence cluster
    "negotiated":  ["Brokered", "Closed", "Secured", "Influenced", "Sealed"],
    "influenced":  ["Persuaded", "Convinced", "Swayed", "Drove"],
    "persuaded":   ["Influenced", "Convinced", "Won over", "Steered"],
    "pitched":     ["Proposed", "Presented", "Advocated", "Sold"],
    "presented":   ["Pitched", "Briefed", "Showcased", "Communicated"],
    # Document / author cluster
    "documented":  ["Authored", "Drafted", "Catalogued", "Codified", "Recorded"],
    "authored":    ["Wrote", "Drafted", "Documented", "Composed"],
    "drafted":     ["Authored", "Wrote", "Composed", "Outlined"],
    "wrote":       ["Authored", "Drafted", "Composed", "Penned"],
    "curated":     ["Compiled", "Organized", "Aggregated", "Catalogued"],
    "codified":    ["Documented", "Standardized", "Formalized", "Captured"],
    # Quantify / measure cluster
    "measured":    ["Quantified", "Tracked", "Monitored", "Profiled", "Audited"],
    "quantified":  ["Measured", "Computed", "Estimated", "Sized"],
    "tracked":     ["Monitored", "Measured", "Logged", "Audited"],
    "monitored":   ["Tracked", "Watched", "Observed", "Logged"],
    "profiled":    ["Analyzed", "Characterized", "Surveyed", "Mapped"],
    # Negotiation / sales cluster
    "sold":        ["Pitched", "Closed", "Secured", "Landed"],
    "closed":      ["Sealed", "Won", "Secured", "Locked"],
    # Instrument / configure cluster
    "instrumented": ["Wired", "Configured", "Set up", "Installed"],
    "configured":  ["Set up", "Tuned", "Provisioned", "Initialized"],
    "tuned":       ["Optimized", "Calibrated", "Refined", "Adjusted"],
    "calibrated":  ["Tuned", "Adjusted", "Aligned", "Refined"],
    # Hire / onboard cluster
    "hired":       ["Recruited", "Onboarded", "Brought on"],
    "recruited":   ["Hired", "Onboarded", "Sourced"],
    "onboarded":   ["Trained", "Mentored", "Guided", "Brought on"],
    "promoted":    ["Elevated", "Advanced", "Lifted"],
    # Pivot / transition cluster
    "pivoted":     ["Repositioned", "Recalibrated", "Reoriented", "Steered"],
    "repositioned": ["Pivoted", "Realigned", "Redirected"],
    "redirected":  ["Steered", "Repositioned", "Pivoted"],
    "recalibrated": ["Tuned", "Adjusted", "Realigned"],
    # Validate / review cluster
    "validated":   ["Verified", "Confirmed", "Tested", "Audited"],
    "verified":    ["Validated", "Confirmed", "Tested"],
    "reviewed":    ["Audited", "Examined", "Inspected", "Evaluated"],
    "tested":      ["Validated", "Verified", "Trialed", "Piloted"],
    # Initiate / kick-off cluster
    "initiated":   ["Launched", "Kicked off", "Started", "Began"],
    "spearheaded": ["Led", "Drove", "Steered", "Championed"],  # already present
    "championed":  ["Spearheaded", "Advocated", "Drove"],
    "advocated":   ["Championed", "Promoted", "Backed"],
    # Reduce-failure / mitigate cluster
    "mitigated":   ["Curtailed", "Reduced", "Lowered", "Contained"],
    "prevented":   ["Stopped", "Averted", "Blocked", "Halted"],
    "averted":     ["Prevented", "Stopped", "Halted"],
    "resolved":    ["Fixed", "Solved", "Cleared", "Settled"],
    "fixed":       ["Resolved", "Repaired", "Patched"],
    "addressed":   ["Resolved", "Tackled", "Handled"],
    # Stakeholder / cross-fn cluster
    "aligned":     ["Synchronized", "Coordinated", "Unified", "Harmonized"],
    "synchronized": ["Aligned", "Coordinated", "Unified"],
    "facilitated": ["Enabled", "Drove", "Orchestrated"],  # "facilitated" is borderline-weak
    "enabled":     ["Empowered", "Unlocked", "Powered", "Activated"],
    "empowered":   ["Enabled", "Equipped", "Activated"],
    # Architecture / scale cluster
    "scaled":      ["Grew", "Expanded", "Multiplied", "Lifted"],  # already present
    "extended":    ["Expanded", "Broadened", "Augmented"],
    "augmented":   ["Enhanced", "Extended", "Boosted"],
    # Collaboration variants
    "consulted":   ["Advised", "Counseled", "Guided"],
    "advised":     ["Counseled", "Guided", "Consulted"],
    "guided":      ["Advised", "Coached", "Mentored", "Steered"],
    # Invent / discover cluster
    "invented":    ["Devised", "Created", "Originated", "Pioneered"],
    "pioneered":   ["Originated", "Spearheaded", "Introduced", "Initiated"],
    "originated":  ["Pioneered", "Created", "Initiated"],
    "introduced":  ["Launched", "Rolled out", "Debuted", "Pioneered"],
}


def improve_verb_diversity(run_dir: Path, dry_run: bool = False) -> dict:
    """Swap duplicate leading verbs with synonyms to lift diversity.

    Programmatic — picks a not-yet-used synonym from `_VERB_SYNONYMS`. Replaces
    only the first word of the bullet's plain text, preserving every <b> tag,
    every metric, and the bullet structure verbatim. No LLM call (no
    fabrication risk).
    """
    bullets_path = run_dir / "artifacts" / "12_condensed_bullets.json"
    if not bullets_path.exists():
        return {"error": "missing 12_condensed_bullets.json"}
    by_company = json.loads(bullets_path.read_text())

    # Pass 1 — collect verbs in render order
    rows: list[dict] = []
    for co, bullets in by_company.items():
        for i, b in enumerate(bullets):
            plain = _strip_html(b.get("text_html", "")).strip()
            verb = plain.split(" ", 1)[0].lower() if plain else ""
            rows.append({"co": co, "i": i, "verb": verb, "html": b.get("text_html", "")})

    used_verbs = set()
    swaps = 0
    for r in rows:
        v = r["verb"]
        if v not in used_verbs:
            used_verbs.add(v)
            continue
        # Duplicate — find a synonym not yet used
        synonyms = _VERB_SYNONYMS.get(v, [])
        chosen = next((s for s in synonyms if s.lower() not in used_verbs), None)
        if not chosen:
            r["skip_reason"] = f"no fresh synonym for '{v}'"
            continue
        r["new_verb"] = chosen
        used_verbs.add(chosen.lower())
        swaps += 1

    counts = {"total": len(rows), "duplicates": sum(1 for r in rows if r.get("new_verb")),
              "swapped": 0, "skipped": [r.get("skip_reason") for r in rows if r.get("skip_reason")]}

    if dry_run or swaps == 0:
        return counts

    for r in rows:
        new_verb = r.get("new_verb")
        if not new_verb:
            continue
        old_html = r["html"]
        # Replace leading verb at start; preserve case-prefix exactly.
        # Old verb may be inside <b> tags. Match: optional <b> + verb (case-insensitive) at very start.
        pattern = re.compile(
            r"^(<b>)?\s*" + re.escape(r["verb"]) + r"\b",
            re.IGNORECASE,
        )
        new_html = pattern.sub(lambda m: f"{m.group(1) or ''}{new_verb}", old_html, count=1)
        if new_html == old_html:
            continue
        by_company[r["co"]][r["i"]]["text_html"] = new_html
        by_company[r["co"]][r["i"]]["improved_by"] = (
            by_company[r["co"]][r["i"]].get("improved_by", "") + ";verb_swap"
        )
        counts["swapped"] += 1
        print(f"  ✓ {r['co']}#{r['i']}: '{r['verb']}' → '{new_verb}'", file=sys.stderr)

    bullets_path.write_text(json.dumps(by_company, indent=2))
    return counts


def improve_page_fit(run_dir: Path, dry_run: bool = False) -> dict:
    """Lift page utilization toward 95-100% target.

    Single-variable hypothesis: expand the professional summary using JD
    keywords + role context. Cheapest densification — one LLM call, fully
    reversible by run_improve's auto-rollback if overall score regresses.

    Per Satvik 2026-05-02: aim 99% overall; page_fit is the highest-leverage
    gap (weight 0.09 × 70-pt swing = +6.3 weighted). Summary at 23 words
    is the shallowest density signal — expanding to 50-60 words adds 2-3
    rendered lines and pulls util upward without touching bullets.
    """
    from linkright.llm.direct import tier_chat

    summary_path = run_dir / "artifacts" / "09_professional_summary.html"
    strat_path = run_dir / "artifacts" / "07_jd_parse_strategy.json"
    if not all(p.exists() for p in (summary_path, strat_path)):
        return {"error": "missing summary or 07_jd_parse_strategy artifacts"}

    summary_html = summary_path.read_text()
    summary_text = re.sub(r"<[^>]+>", "", summary_html).strip()
    n_words_before = len(summary_text.split())

    if n_words_before >= 55:
        return {"already_dense": n_words_before}

    strat_raw = json.loads(strat_path.read_text())
    parsed_p12 = strat_raw["parsed"] if "parsed" in strat_raw else strat_raw
    jd_keywords = parsed_p12.get("jd_keywords", [])[:8]
    target_role = parsed_p12.get("target_role", "") or ""
    target_company = parsed_p12.get("company_name", "") or ""

    print(f"  Summary: {n_words_before} words → expanding to 50-60", file=sys.stderr)

    if dry_run:
        return {"summary_before_words": n_words_before, "would_expand_to": 55}

    system = (
        "You are a senior resume writer. Output ONLY the expanded summary "
        "paragraph — no preamble, no quotes, no markdown."
    )
    user = (
        f"Expand the following professional summary to 50-60 words. "
        f"Naturally incorporate 4-6 of these JD keywords: {', '.join(jd_keywords)}. "
        f"Target role: {target_role} at {target_company}.\n\n"
        f"PRESERVE every factual claim (years, metrics, companies). "
        f"Only enrich phrasing and contextual depth. No new metrics. "
        f"No new company names. No fabrication.\n\n"
        f"ORIGINAL:\n{summary_text}\n\n"
        f"Output: ONE paragraph, 50-60 words."
    )

    text, usage = tier_chat(
        system=system, user=user, klass="C", intent="improve_page_fit_summary",
        max_tokens=400,
    )
    new_summary = text.strip().strip('"').strip("'")
    new_words = len(new_summary.split())

    if new_words < n_words_before + 10:
        return {
            "error": "LLM expansion insufficient — keeping original summary",
            "summary_before_words": n_words_before,
            "summary_after_words": new_words,
        }

    summary_path.write_text(f"<p>{new_summary}</p>")
    print(f"  ✓ Summary: {n_words_before} → {new_words} words", file=sys.stderr)

    return {
        "summary_before_words": n_words_before,
        "summary_after_words": new_words,
        "summary_text_after": new_summary[:200],
        "added": new_words - n_words_before,
    }


def re_render(run_dir: Path) -> Path:
    """Re-run step_14 (assemble HTML) + step_15 (render PDF) after improvements.

    Reads improved 12_condensed_bullets.json + existing 07/01/parsed artifacts;
    produces fresh 14_final_resume.html + 15_final_resume.pdf.
    """
    from linkright.resume import orchestrator
    orchestrator.RUN_DIR = run_dir
    orchestrator.ARTIFACTS = run_dir / "artifacts"
    orchestrator.INPUTS = run_dir / "inputs"
    orchestrator.LOG_PATH = run_dir / "logs" / "pipeline.log"

    # Load existing artifacts. step_14 expects parsed_p12 unwrapped (matches
    # the in-memory shape returned by step_07_phase_1_2). The persisted file
    # wraps as {"parsed": {...}, "usage": {...}} for telemetry — strip that.
    _strat_raw = json.loads((run_dir / "artifacts" / "07_jd_parse_strategy.json").read_text())
    parsed_p12 = _strat_raw["parsed"] if "parsed" in _strat_raw else _strat_raw
    parsed = json.loads((run_dir / "artifacts" / "01_resume_parsed.json").read_text()).get("parsed", {})
    summary = (run_dir / "artifacts" / "09_professional_summary.html").read_text()
    summary = re.sub(r"<[^>]+>", "", summary).strip()
    condensed = json.loads((run_dir / "artifacts" / "12_condensed_bullets.json").read_text())

    print("\n  → 🎨 Re-assembling HTML with improved bullets...", file=sys.stderr)
    html_path = orchestrator.step_14_assemble_html(parsed_p12, parsed, summary, condensed)
    print("  → 🖨  Re-rendering PDF...", file=sys.stderr)
    pdf_path = orchestrator.step_15_pdf(html_path)
    return pdf_path


def run_improve(run_id: Optional[str] = None, target_dim: Optional[str] = None,
                dry_run: bool = False) -> dict:
    """End-to-end improve flow: identify weakness → refine → re-render → re-score."""
    if not run_id:
        candidates = [d for d in RUNS_ROOT.iterdir()
                      if d.is_dir() and not d.name.startswith("hyp_")]
        if not candidates:
            return {"error": "no runs found"}
        run_dir = max(candidates, key=lambda p: p.stat().st_mtime)
    else:
        run_dir = RUNS_ROOT / run_id
    if not run_dir.exists():
        return {"error": f"run not found: {run_dir}"}

    print(f"=== Improve: {run_dir.name} ===", file=sys.stderr)

    # 2026-05-01: backup bullets+html+pdf BEFORE modifying — auto-rollback if score regresses
    import shutil
    artifacts = run_dir / "artifacts"
    backup_paths = {
        "bullets": artifacts / "12_condensed_bullets.json",
        "html": artifacts / "14_final_resume.html",
        "pdf": artifacts / "15_final_resume.pdf",
    }
    backup_dir = run_dir / ".pre-improve.bak"
    backup_dir.mkdir(exist_ok=True)
    for name, src in backup_paths.items():
        if src.exists():
            shutil.copy2(src, backup_dir / src.name)

    # Score before
    from .scorecard_context import build_context
    from linkright.resume.scorecard import ResumeScorecard
    ctx_before = build_context(run_dir)
    sc_before = ResumeScorecard(run_id=run_dir.name)
    sc_before.score(ctx_before)
    print(f"\nBefore: {sc_before.overall_score:.1f} / {sc_before.overall_grade}",
          file=sys.stderr)

    # Pick weakest dim if not specified
    if not target_dim:
        weakest = min(sc_before.results, key=lambda r: r.score)
        target_dim = weakest.name
    print(f"Target dim: {target_dim} (current: "
          f"{[r.score for r in sc_before.results if r.name == target_dim][0]:.1f})",
          file=sys.stderr)

    # Dispatch to per-dim improver
    if target_dim == "width_hit_rate":
        print("\nIdentifying out-of-band bullets...", file=sys.stderr)
        counts = improve_width(run_dir, dry_run=dry_run)
        print(f"\nCounts: {counts}", file=sys.stderr)
    elif target_dim == "keyword_coverage":
        # 2026-05-01: 2-stage approach per Satvik strategy:
        # (1) try natural keyword incorporation in bullets (small success rate)
        # (2) ALWAYS dump remaining missing keywords into Skills section
        print("\nStage 1 — attempt natural keyword incorporation in bullets...", file=sys.stderr)
        counts_b = improve_keywords(run_dir, dry_run=dry_run)
        print(f"  Bullet pass counts: {counts_b}", file=sys.stderr)
        print("\nStage 2 — dump remaining missing keywords into Skills section...", file=sys.stderr)
        counts_s = improve_skills_keyword_fill(run_dir, dry_run=dry_run)
        counts = {"bullets_stage": counts_b, "skills_stage": counts_s}
    elif target_dim == "skills_keyword_fill":
        # Skills-only mode (skip bullet pass)
        counts = improve_skills_keyword_fill(run_dir, dry_run=dry_run)
        print(f"\nCounts: {counts}", file=sys.stderr)
    elif target_dim == "page_fit":
        print("\nDensifying summary to lift page utilization...", file=sys.stderr)
        counts = improve_page_fit(run_dir, dry_run=dry_run)
        print(f"\nCounts: {counts}", file=sys.stderr)
    elif target_dim == "verb_diversity":
        print("\nSwapping duplicate verbs with synonyms...", file=sys.stderr)
        counts = improve_verb_diversity(run_dir, dry_run=dry_run)
        print(f"\nCounts: {counts}", file=sys.stderr)
    else:
        return {"error": f"target_dim '{target_dim}' not yet supported. "
                "Currently: width_hit_rate, keyword_coverage, skills_keyword_fill, page_fit, verb_diversity"}

    # Different improvers write counts under different keys.
    if isinstance(counts, dict) and "bullets_stage" in counts:
        # 2-stage keyword_coverage: count bullets AND skills changes
        changed = (counts.get("bullets_stage", {}).get("incorporated", 0)
                   + counts.get("skills_stage", {}).get("added", 0))
    else:
        changed = (counts.get("improved", 0)
                   + counts.get("incorporated", 0)
                   + counts.get("added", 0)
                   + counts.get("swapped", 0)
                   + counts.get("partial", 0))
    if dry_run or changed == 0:
        return {"counts": counts, "before_score": sc_before.overall_score, "rerendered": False}

    # Backup bullets BEFORE rendering — rollback if overall score regresses.
    bullets_path = run_dir / "artifacts" / "12_condensed_bullets.json"
    backup_path = bullets_path.with_suffix(".json.pre-improve.bak")
    # Note: we already wrote to bullets_path in improve_keywords/improve_width.
    # The "backup" is the ORIGINAL content — but we already overwrote. So backup
    # has to be created BEFORE the per-dim improver. Let me do simpler: re-render,
    # re-score, if regressed → restore via re-running the original artifact's bullets.
    # Pragmatic version: re-score; if regressed, log + warn user; don't auto-rollback
    # since we'd need to re-run all upstream steps anyway.

    # Re-render HTML + PDF
    re_render(run_dir)

    # Re-score
    ctx_after = build_context(run_dir)
    sc_after = ResumeScorecard(run_id=run_dir.name)
    sc_after.score(ctx_after)
    delta = sc_after.overall_score - sc_before.overall_score
    print(f"\nAfter:  {sc_after.overall_score:.1f} / {sc_after.overall_grade}  "
          f"(Δ {delta:+.1f})", file=sys.stderr)
    print(f"  {target_dim}: "
          f"{[r.score for r in sc_before.results if r.name == target_dim][0]:.1f} → "
          f"{[r.score for r in sc_after.results if r.name == target_dim][0]:.1f}",
          file=sys.stderr)
    if delta < 0:
        # AUTO-ROLLBACK — restore backups, re-score to confirm
        print(f"\n⚠️  Overall regressed by {abs(delta):.1f} pts. AUTO-ROLLBACK firing.",
              file=sys.stderr)
        for name, target in backup_paths.items():
            bak = backup_dir / target.name
            if bak.exists():
                shutil.copy2(bak, target)
        # Re-verify score is back to original
        ctx_check = build_context(run_dir)
        sc_check = ResumeScorecard(run_id=run_dir.name)
        sc_check.score(ctx_check)
        print(f"  ✓ Restored backup: {sc_check.overall_score:.1f} / {sc_check.overall_grade} "
              f"(was {sc_before.overall_score:.1f}). Run dir clean.", file=sys.stderr)
        result_status = "rolled_back"
    else:
        # Improvement kept — clean up backup
        try:
            shutil.rmtree(backup_dir)
        except Exception:
            pass
        result_status = "kept"

    return {
        "counts": counts,
        "before_score": sc_before.overall_score,
        "after_score": sc_after.overall_score,
        "delta": delta,
        "target_dim": target_dim,
        "before_dim_score": [r.score for r in sc_before.results if r.name == target_dim][0],
        "after_dim_score": [r.score for r in sc_after.results if r.name == target_dim][0],
        "status": result_status,
    }
