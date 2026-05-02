"""Markdown → structured dict parser, ported from
website/src/app/api/onboarding/parse-resume/route.ts markdownToJson().
"""

from __future__ import annotations

import re


def parse_resume_markdown(text: str) -> dict:
    """Return {education, skills, certifications, experiences, projects}."""
    return {
        "education": _parse_education(text),
        "skills": _parse_skills(text),
        "certifications": _parse_certifications(text),
        "experiences": _parse_experiences(text),
        "projects": _parse_top_level_projects(text),
    }


def _parse_education(text: str) -> list[dict]:
    m = re.search(r"## EDUCATION\n([\s\S]*?)(?=\n## |\n###|$)", text, re.IGNORECASE)
    if not m:
        return []
    out = []
    for line in m.group(1).split("\n"):
        l = line.strip()
        if not l.startswith("- "):
            continue
        # Accept pipe, em-dash, or en-dash as field separator (matches prod route.ts).
        parts = [p.strip() for p in re.split(r"\s*[\|—–]\s*", l[2:])]
        entry = {
            "degree": parts[0] if len(parts) > 0 else "",
            "institution": parts[1] if len(parts) > 1 else "",
            "year": parts[2] if len(parts) > 2 else "",
        }
        if entry["degree"] or entry["institution"]:
            out.append(entry)
    return out


def _parse_skills(text: str) -> list[str]:
    m = re.search(r"## SKILLS\n([\s\S]*?)(?=\n## |\n###|$)", text, re.IGNORECASE)
    if not m:
        return []
    first_nonempty = next((l for l in m.group(1).split("\n") if l.strip()), "")
    return [s.strip() for s in first_nonempty.split(",") if s.strip()]


def _parse_certifications(text: str) -> list[str]:
    m = re.search(r"## CERTIFICATIONS\n([\s\S]*?)(?=\n## |\n###|$)", text, re.IGNORECASE)
    if not m:
        return []
    return [
        l.strip()[2:].strip()
        for l in m.group(1).split("\n")
        if l.strip().startswith("- ") and l.strip()[2:].strip()
    ][:10]


def _parse_experiences(text: str) -> list[dict]:
    m = re.search(r"## EXPERIENCE\n([\s\S]*?)(?=\n## |$)", text, re.IGNORECASE)
    if not m:
        return []
    blocks = re.split(r"(?m)^(?=### )", m.group(1))
    blocks = [b for b in blocks if b.strip()]
    out = []
    for block in blocks:
        lines = block.split("\n")
        header = re.sub(r"^###\s*", "", lines[0]).strip()
        # Accept pipe, em-dash (—), or en-dash (–) as separator.
        # Production parser only accepts pipe — see finding logged for Step 1.
        parts = [p.strip() for p in re.split(r"\s*[\|—–]\s*", header)]
        if len(parts) < 2:
            continue
        company = parts[0] if len(parts) > 0 else ""
        role = parts[1] if len(parts) > 1 else ""
        start_date = parts[2] if len(parts) > 2 else ""
        end_date = parts[3] if len(parts) > 3 else ""
        # Handle case where date range is one field with internal "–" (e.g. "Jul 2024 – Present")
        # After splitting on — and –, a "Jul 2024 – Present" becomes ["Jul 2024", "Present"] which is fine.
        body = "\n".join(lines[1:])
        bullets, projects = _parse_experience_body(body)
        out.append({
            "company": company,
            "role": role,
            "start_date": start_date,
            "end_date": end_date,
            "bullets": bullets,
            "projects": projects,
        })
    return out


def _parse_experience_body(body: str) -> tuple[list[str], list[dict]]:
    bullets: list[str] = []
    projects: list[dict] = []
    current: dict | None = None
    after_one_liner = False

    for raw in body.split("\n"):
        line = raw.strip()
        if not line:
            continue
        # **Project: Name** or Project: Name
        m1 = re.match(r"^\*\*Project:\s*(.+?)\*\*$", line)
        m2 = re.match(r"^Project:\s*(.+)$", line, re.IGNORECASE)
        pm = m1 or m2
        if pm:
            if current:
                projects.append(current)
            current = {"title": pm.group(1).strip(), "one_liner": "", "key_achievements": []}
            after_one_liner = False
            continue
        # One-liner:
        ol = re.match(r"^One-liner:\s*(.+)$", line, re.IGNORECASE)
        if ol and current and not after_one_liner:
            current["one_liner"] = ol.group(1).strip()
            after_one_liner = True
            continue
        # Bullet — accept "- ", "• ", "●", "* " (LLM drift: production only accepts "- ")
        b = None
        if line.startswith("- "):
            b = line[2:].strip()
        elif line.startswith("• ") or line.startswith("● "):
            b = line[2:].strip()
        elif line.startswith("* "):
            b = line[2:].strip()
        if b:
            if current:
                current["key_achievements"].append(b)
            else:
                bullets.append(b)

    if current:
        projects.append(current)
    return bullets, projects


def _parse_top_level_projects(text: str) -> list[dict]:
    m = re.search(r"## PROJECTS\n([\s\S]*?)(?=\n## |$)", text, re.IGNORECASE)
    if not m:
        return []
    blocks = re.split(r"(?m)^(?=### )", m.group(1))
    blocks = [b for b in blocks if b.strip()]
    out = []
    for block in blocks:
        lines = block.split("\n")
        header = re.sub(r"^###\s*", "", lines[0]).strip()
        # Accept pipe, em-dash, or en-dash as field separator (matches prod).
        parts = [p.strip() for p in re.split(r"\s*[\|—–]\s*", header)]
        title = parts[0] if parts else ""
        year = parts[1] if len(parts) > 1 else ""
        body = "\n".join(lines[1:])
        one_liner = ""
        bullets = []
        for raw in body.split("\n"):
            line = raw.strip()
            if not line:
                continue
            ol = re.match(r"^One-liner:\s*(.+)$", line, re.IGNORECASE)
            if ol and not one_liner:
                one_liner = ol.group(1).strip()
                continue
            if line.startswith("- "):
                bullets.append(line[2:].strip())
        out.append({
            "title": title,
            "year": year,
            "one_liner": one_liner,
            "key_achievements": bullets,
        })
    return out
