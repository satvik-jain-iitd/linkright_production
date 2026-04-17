"""Module 1: Embedding retrieval quality diagnostics.

For each target JD × 2 company scopes (unscoped, American Express),
call hybrid_retrieve() and inspect the results:
- Method tier (hybrid / bm25_only / fts_fallback / raw_text_fallback)
- Result count
- P0/P1 nugget count in top-8
- Total answer char length
- JD-keyword token overlap %

Generates a markdown report for manual review. No production code modified.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.tools.hybrid_retrieval import hybrid_retrieve, format_nuggets_for_llm


# Company scopes tested per JD. "American Express" chosen because it's Satvik's
# most recent role (9 nuggets per pre-flight) — representative scope test.
_COMPANY_SCOPES = [None, "American Express"]


def _tokenize(text: str) -> set[str]:
    """Lowercase word tokens, 3+ chars, stripped of punctuation."""
    return {w.lower() for w in re.findall(r"\w+", text) if len(w) >= 3}


def _keyword_coverage(keywords: list[str], text: str) -> float:
    """Fraction of keywords (as multi-word phrases OR tokens) present in text."""
    if not keywords:
        return 0.0
    text_lower = text.lower()
    text_tokens = _tokenize(text)
    hits = 0
    for kw in keywords:
        kw_lower = kw.lower()
        # Full phrase match OR all tokens of the phrase present
        if kw_lower in text_lower:
            hits += 1
            continue
        kw_tokens = _tokenize(kw)
        if kw_tokens and kw_tokens.issubset(text_tokens):
            hits += 1
    return hits / len(keywords)


async def test_retrieval_quality_per_jd(
    live_sb,
    satvik_user_id,
    target_jds,
    retrieval_cache,
    report_writer,
):
    """Run retrieval for 3 JDs × 2 scopes; produce markdown report.

    Report structure:
    1. Overview of all user nuggets (catalog) — so reviewer knows what's available
    2. Per-JD: top-5 retrieved answers in full (not truncated)
    3. Per-JD: coverage metric — what fraction of user's nuggets were retrieved
    4. Overall BM25-vs-ideal gap — which nuggets should have been retrieved but weren't

    Goal: let user decide if BM25 recall is sufficient or if hybrid (BM25+vector)
    is needed.
    """
    report_path: Path = report_writer("retrieval_quality")
    rows: list[dict] = []
    failures: list[str] = []

    # Fetch ALL user nuggets once for the catalog section + coverage analysis
    all_nuggets_result = (
        live_sb.table("career_nuggets")
        .select("id,company,role,section_type,importance,answer,tags")
        .eq("user_id", satvik_user_id)
        .execute()
    )
    all_nuggets = all_nuggets_result.data or []
    nugget_by_id = {n["id"]: n for n in all_nuggets}

    with report_path.open("w") as f:
        f.write("# Module 1: Retrieval Quality Report\n\n")
        f.write(f"**User:** `{satvik_user_id}`  \n")
        f.write(f"**Total nuggets available:** {len(all_nuggets)}  \n")
        f.write(f"**JDs tested:** {len(target_jds)}  \n")
        f.write(f"**Company scopes per JD:** {[s or 'unscoped' for s in _COMPANY_SCOPES]}  \n\n")

        # --- Section 0: Nugget Catalog ---
        f.write("## 0. Nugget Catalog (what's available in Satvik's career_nuggets)\n\n")
        by_co: dict[str, list[dict]] = {}
        for n in all_nuggets:
            by_co.setdefault(n.get("company") or "—unscoped—", []).append(n)
        for co, ns in sorted(by_co.items(), key=lambda x: -len(x[1])):
            f.write(f"### {co} ({len(ns)} nuggets)\n")
            for n in ns:
                ans_short = n["answer"][:150].replace("\n", " ")
                f.write(f"- **[{n.get('importance','?')}·{n.get('section_type','?')}]** {ans_short}…\n")
            f.write("\n")
        f.write("\n---\n\n")

        f.write("## Per-JD Retrieval Results\n\n")
        for jd in target_jds:
            jd_id = jd["id"]
            # Match production query pattern (orchestrator.py:754):
            # {company_name} {top-5 keywords joined by space}
            # Shorter queries avoid plainto_tsquery over-restrictiveness.
            jd_query = " ".join(jd["keywords"][:5])
            f.write(f"### {jd['title']} @ {jd['company']} (`{jd_id}`)\n\n")
            f.write(f"**JD keywords (top-5):** `{jd_query}`  \n")
            f.write(f"**All JD keywords:** {', '.join(jd['keywords'])}  \n\n")

            # Summary row
            f.write(
                "| Scope | Method | N | P0/P1 | Total chars | KW coverage |\n"
                "|---|---|---|---|---|---|\n"
            )

            scope_results: dict[str | None, list] = {}
            for company in _COMPANY_SCOPES:
                effective_query = f"{company} {jd_query}" if company else jd_query
                results, method = await hybrid_retrieve(
                    live_sb, satvik_user_id, effective_query,
                    company=company, limit=8,
                )
                retrieval_cache[(jd_id, company)] = results
                scope_results[company] = results

                count = len(results)
                p01 = sum(1 for r in results if r.importance in ("P0", "P1"))
                total_chars = sum(len(r.answer) for r in results)
                answers_joined = " ".join(r.answer for r in results)
                kw_cov = _keyword_coverage(jd["keywords"], answers_joined)

                scope_label = company or "unscoped"
                f.write(
                    f"| {scope_label} | {method} | {count} | {p01} | {total_chars} | {kw_cov:.0%} |\n"
                )

                rows.append({
                    "jd": jd_id, "scope": scope_label, "method": method,
                    "count": count, "p01": p01, "total_chars": total_chars,
                    "kw_cov": kw_cov, "results": results,
                })

                # Collect diagnostic failures
                if method != "hybrid":
                    failures.append(f"{jd_id}/{scope_label}: method={method} (expected hybrid)")
                if count < 5:
                    failures.append(f"{jd_id}/{scope_label}: {count} results (expected >=5)")
                if p01 < 2:
                    failures.append(f"{jd_id}/{scope_label}: only {p01} P0/P1 (expected >=2)")
                if kw_cov < 0.30:
                    failures.append(f"{jd_id}/{scope_label}: kw_cov {kw_cov:.0%} (expected >=30%)")

            # Top-5 full answers for MANUAL relevance review (unscoped pass)
            f.write("\n#### Top-5 Retrieved Nuggets (unscoped pass — what would feed Phase 4a)\n\n")
            f.write("| # | Rel? | Company | Imp | Score | Answer (first 300 chars) |\n")
            f.write("|---|---|---|---|---|---|\n")
            unscoped = scope_results.get(None) or []
            for i, r in enumerate(unscoped[:5], 1):
                ans = r.answer[:300].replace("|", "\\|").replace("\n", " ")
                f.write(
                    f"| {i} | ☐ | {r.company or '—'} | {r.importance} | "
                    f"{r.rrf_score:.3f} | {ans}… |\n"
                )

            # Recall gap analysis: which nuggets were MISSED by BM25 but substring-match the JD?
            retrieved_ids = {r.nugget_id for r in unscoped}
            jd_text_lower = " ".join(jd["keywords"]).lower()
            missed_relevant = []
            for n in all_nuggets:
                if n["id"] in retrieved_ids:
                    continue
                ans_lower = n["answer"].lower()
                # Count how many JD keywords (multi-word phrase match) appear in this nugget
                phrase_hits = sum(1 for kw in jd["keywords"] if kw.lower() in ans_lower)
                if phrase_hits >= 1:  # at least one JD keyword literally in the nugget
                    missed_relevant.append((phrase_hits, n))

            missed_relevant.sort(key=lambda x: -x[0])
            if missed_relevant:
                f.write(f"\n#### ⚠️ Potentially relevant nuggets MISSED by BM25 ({len(missed_relevant)} found)\n\n")
                f.write("These nuggets contain at least one JD keyword as a literal substring but were not in the top-8.\n")
                f.write("If these look relevant, BM25 is not enough → need vector search (hybrid tier).\n\n")
                f.write("| Phrase hits | Company | Imp | Answer (250ch) |\n")
                f.write("|---|---|---|---|\n")
                for hits, n in missed_relevant[:5]:
                    ans = n["answer"][:250].replace("|", "\\|").replace("\n", " ")
                    f.write(f"| {hits} | {n.get('company') or '—'} | {n.get('importance','?')} | {ans}… |\n")
            else:
                f.write("\n✅ No obvious missed-relevance nuggets — BM25 recall likely sufficient for this JD.\n")

            f.write("\n")

        # Summary
        f.write("\n---\n\n## Summary\n\n")
        f.write(f"- **Total rows:** {len(rows)}\n")
        methods = {r["method"] for r in rows}
        f.write(f"- **Methods observed:** {methods}\n")
        f.write(f"- **Avg result count:** {sum(r['count'] for r in rows) / max(1, len(rows)):.1f}\n")
        f.write(f"- **Avg KW coverage:** {sum(r['kw_cov'] for r in rows) / max(1, len(rows)):.0%}\n")
        f.write(f"- **Avg P0/P1 in top-8:** {sum(r['p01'] for r in rows) / max(1, len(rows)):.1f}\n")

        if failures:
            f.write("\n### ⚠️ Automated Check Failures\n\n")
            for msg in failures:
                f.write(f"- {msg}\n")

        # ---- BM25-vs-hybrid recommendation ----
        f.write("\n### 🎯 BM25-only vs Hybrid Evaluation\n\n")
        f.write(
            "Decision question: for each JD, inspect the top-5 retrieved nuggets above and the "
            "'missed relevance' section. Key signals:\n\n"
            "- ✅ **BM25 is enough** if: top-5 nuggets cover the JD well AND missed-relevance "
            "list is empty or irrelevant\n"
            "- ❌ **Need vector/hybrid** if: top-5 is dominated by a few nuggets with shallow "
            "keyword match while missed-relevance list contains clearly relevant experiences "
            "(e.g., same concept in different wording)\n"
            "- 🟡 **Marginal** — BM25 works for some JDs but not others. Consider hybrid as "
            "insurance for semantic edge cases.\n\n"
            "**Semantic recall test:** If a JD mentions a concept and a nugget describes that "
            "concept using synonyms (e.g., JD says 'RBAC' but nugget says 'role-based access "
            "control'), BM25 will miss it. Hybrid would catch it.\n\n"
        )

        f.write("\n### 📝 Manual Review Instructions\n\n")
        f.write(
            "For each JD above, in the 'Top-5 Retrieved Nuggets' table:\n"
            "- Mark each row with ✅ (relevant) / 🟡 (partial) / ❌ (irrelevant) in the 'Rel?' column\n\n"
            "Then in the 'Potentially relevant nuggets MISSED' table:\n"
            "- Is the missed nugget actually relevant? If yes → hybrid needed.\n"
            "- If no → BM25 is sufficient.\n\n"
            "**Overall verdict space (fill in after review):**\n"
            "- BM25 sufficient: ☐\n"
            "- Hybrid needed: ☐\n"
            "- Marginal — use hybrid as insurance: ☐\n"
        )

    print(f"\n[Module 1] Report written: {report_path}")
    print(f"[Module 1] Failures: {len(failures)}")

    # Don't fail the test on automated checks — report is the deliverable.
    # User reviews the markdown report and decides pass/fail based on manual review.
    assert report_path.exists(), "report must be written"
    assert len(retrieval_cache) == len(target_jds) * len(_COMPANY_SCOPES), (
        f"retrieval_cache missing entries: got {len(retrieval_cache)}, "
        f"expected {len(target_jds) * len(_COMPANY_SCOPES)}"
    )
