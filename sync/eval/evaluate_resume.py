"""Resume Quality Evaluation Script.

Takes a final HTML resume file and produces a quality scorecard.
Runs static analysis (no MCP tools needed) to measure:
- AI word violations (Rule 32 banned vocabulary)
- Width fill distribution (character count heuristic)
- Structural patterns (triple adjectives, gerund starts, etc.)
- Page structure completeness

Usage:
    python -m sync.eval.evaluate_resume path/to/resume.html
"""

import json
import re
import sys
from pathlib import Path

# Rule 32 banned vocabulary
BANNED_WORDS = {
    "crucial", "pivotal", "vibrant", "groundbreaking", "meticulous",
    "intricate", "renowned", "profound", "additionally", "furthermore",
    "moreover", "notably", "delve", "foster", "cultivate", "encompass",
    "garner", "underscore", "bolster",
}

BANNED_PHRASES = [
    "a testament to", "serves as", "stands as", "plays a key role",
    "it is worth noting", "it should be noted", "setting the stage",
    "in the heart of", "not just", "but also",
]

# Expected sections in a complete resume
EXPECTED_SECTIONS = [
    "Professional Summary",
    "Professional Experience",
    "Core Competencies",
    "Education",
]


def extract_visible_text(html: str) -> str:
    """Strip HTML tags and return visible text."""
    text = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"&#\d+;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_bullets(html: str) -> list[str]:
    """Extract bullet text from li-content spans."""
    pattern = r'<span class="li-content">(.*?)</span>'
    matches = re.findall(pattern, html, re.DOTALL)
    return [re.sub(r"<[^>]+>", "", m).strip() for m in matches]


def extract_edge_to_edge_lines(html: str) -> list[str]:
    """Extract edge-to-edge line text."""
    pattern = r'<span class="edge-to-edge-line[^"]*">(.*?)</span>'
    matches = re.findall(pattern, html, re.DOTALL)
    return [re.sub(r"<[^>]+>", "", m).strip() for m in matches]


def check_banned_words(text: str) -> list[dict]:
    """Find Rule 32 violations in text."""
    violations = []
    text_lower = text.lower()

    for word in BANNED_WORDS:
        pattern = r"\b" + re.escape(word) + r"\b"
        for match in re.finditer(pattern, text_lower):
            violations.append({
                "type": "banned_word",
                "word": word,
                "position": match.start(),
            })

    for phrase in BANNED_PHRASES:
        idx = text_lower.find(phrase)
        if idx != -1:
            violations.append({
                "type": "banned_phrase",
                "phrase": phrase,
                "position": idx,
            })

    return violations


def check_structural_patterns(bullets: list[str]) -> list[dict]:
    """Detect AI writing structural patterns."""
    issues = []

    # Check gerund starts (3+ bullets starting with -ing)
    gerund_count = sum(
        1 for b in bullets
        if re.match(r"^[A-Z][a-z]+ing\b", b)
    )
    if gerund_count >= 3:
        issues.append({
            "type": "gerund_starts",
            "count": gerund_count,
            "message": f"{gerund_count} bullets start with gerund (-ing verb)",
        })

    # Check for triple adjective chains
    for i, b in enumerate(bullets):
        triple = re.findall(r"\b(\w+), (\w+),? and (\w+)\b", b)
        if triple:
            issues.append({
                "type": "triple_adjective",
                "bullet_index": i,
                "match": triple[0],
            })

    # Count em dashes
    all_text = " ".join(bullets)
    em_dash_count = all_text.count("\u2014") + all_text.count("&mdash;")
    if em_dash_count > 1:
        issues.append({
            "type": "em_dash_overuse",
            "count": em_dash_count,
            "message": f"{em_dash_count} em dashes found (max 1 per resume)",
        })

    return issues


def check_sections(html: str) -> dict:
    """Verify expected sections are present."""
    found = []
    missing = []
    for section in EXPECTED_SECTIONS:
        if section in html:
            found.append(section)
        else:
            missing.append(section)
    return {"found": found, "missing": missing}


def evaluate(html_path: str) -> dict:
    """Run full evaluation on a resume HTML file."""
    path = Path(html_path)
    if not path.exists():
        return {"error": f"File not found: {html_path}"}

    html = path.read_text(encoding="utf-8")
    visible_text = extract_visible_text(html)
    bullets = extract_bullets(html)
    edge_lines = extract_edge_to_edge_lines(html)

    # AI word violations
    ai_violations = check_banned_words(visible_text)

    # Structural patterns
    structural_issues = check_structural_patterns(bullets)

    # Section completeness
    sections = check_sections(html)

    # Character count distribution for bullets
    bullet_char_counts = [len(b) for b in bullets]
    edge_char_counts = [len(l) for l in edge_lines]

    # Bullets in target range (88-96 chars)
    bullets_in_range = sum(1 for c in bullet_char_counts if 88 <= c <= 96)
    bullet_range_pct = (
        (bullets_in_range / len(bullet_char_counts) * 100)
        if bullet_char_counts else 0
    )

    scorecard = {
        "file": str(path),
        "prompt_version": "v3.0.0",
        "metrics": {
            "total_bullets": len(bullets),
            "total_edge_lines": len(edge_lines),
            "ai_word_violations": len(ai_violations),
            "structural_issues": len(structural_issues),
            "sections_found": len(sections["found"]),
            "sections_missing": len(sections["missing"]),
            "bullet_char_range_pct": round(bullet_range_pct, 1),
            "avg_bullet_chars": (
                round(sum(bullet_char_counts) / len(bullet_char_counts), 1)
                if bullet_char_counts else 0
            ),
        },
        "details": {
            "ai_violations": ai_violations,
            "structural_issues": structural_issues,
            "missing_sections": sections["missing"],
            "bullet_char_counts": bullet_char_counts,
            "edge_line_char_counts": edge_char_counts,
        },
        "score": "PASS" if (
            len(ai_violations) == 0
            and len(structural_issues) == 0
            and len(sections["missing"]) == 0
        ) else "NEEDS_REVIEW",
    }

    return scorecard


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m sync.eval.evaluate_resume <path/to/resume.html>")
        sys.exit(1)

    scorecard = evaluate(sys.argv[1])
    print(json.dumps(scorecard, indent=2))

    # Summary
    m = scorecard["metrics"]
    print(f"\n--- SCORECARD ---")
    print(f"Bullets: {m['total_bullets']}, Edge lines: {m['total_edge_lines']}")
    print(f"AI violations: {m['ai_word_violations']}")
    print(f"Structural issues: {m['structural_issues']}")
    print(f"Sections: {m['sections_found']} found, {m['sections_missing']} missing")
    print(f"Bullet char range (88-96): {m['bullet_char_range_pct']}%")
    print(f"Avg bullet chars: {m['avg_bullet_chars']}")
    print(f"Overall: {scorecard['score']}")


if __name__ == "__main__":
    main()
