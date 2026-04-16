"""
CODEBASE BOOK BUILDER
Reads code files one function at a time, explains in Romanized Hindi,
appends to specs/CODEBASE_BOOK.md. Uses local LM Studio model — zero Claude tokens.

Usage:
    python repo/scripts/annotate.py              # annotate all files
    python repo/scripts/annotate.py --file path  # annotate one file
    python repo/scripts/annotate.py --check      # check model availability only
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import requests

# ── Config ────────────────────────────────────────────────────────────────────

LMSTUDIO_URL = "http://localhost:1234/v1"
CODEBASE_BOOK = Path("specs/CODEBASE_BOOK.md")

# Model preference order (best first)
MODEL_PREFERENCE = [
    "deepseek-r1-distill-qwen-1.5b",
    "qwen2.5-0.5b-instruct",
    "smollm2-135m-instruct",
]

# File patterns to annotate
CODE_PATTERNS = [
    "repo/website/**/*.ts",
    "repo/website/**/*.tsx",
    "repo/worker/**/*.py",
    "repo/oracle-backend/**/*.py",
]

# Skip these directories
SKIP_DIRS = {"node_modules", ".next", "__pycache__", ".git", "dist", "build"}

# ── Model detection ────────────────────────────────────────────────────────────

def get_available_model() -> str | None:
    try:
        r = requests.get(f"{LMSTUDIO_URL}/models", timeout=3)
        models = [m["id"] for m in r.json().get("data", [])]
        for preferred in MODEL_PREFERENCE:
            for available in models:
                if preferred in available.lower():
                    return available
        return models[0] if models else None
    except Exception:
        return None


def check_server() -> bool:
    try:
        requests.get(f"{LMSTUDIO_URL}/models", timeout=3)
        return True
    except Exception:
        return False

# ── Code parsing ───────────────────────────────────────────────────────────────

def extract_python_functions(source: str) -> list[dict]:
    """Extract functions/classes from Python source with line numbers."""
    snippets = []
    try:
        tree = ast.parse(source)
        lines = source.splitlines()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                # Only top-level and first-level nested
                start = node.lineno - 1
                end = node.end_lineno
                code = "\n".join(lines[start:end])
                snippets.append({
                    "name": node.name,
                    "start": node.lineno,
                    "end": node.end_lineno,
                    "code": code,
                })
    except SyntaxError:
        pass
    return snippets


def extract_ts_functions(source: str) -> list[dict]:
    """Extract functions from TypeScript using regex (no full parser needed)."""
    snippets = []
    lines = source.splitlines()

    # Match: function name, arrow functions assigned to const, export default function
    pattern = re.compile(
        r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(\w+)\s*[(<]"
        r"|^(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\(",
        re.MULTILINE,
    )

    for match in pattern.finditer(source):
        name = match.group(1) or match.group(2)
        start_line = source[: match.start()].count("\n")
        # Grab next 40 lines as the snippet (simple heuristic)
        end_line = min(start_line + 40, len(lines))
        code = "\n".join(lines[start_line:end_line])
        snippets.append({
            "name": name,
            "start": start_line + 1,
            "end": end_line,
            "code": code,
        })

    return snippets

# ── LLM call ──────────────────────────────────────────────────────────────────

def annotate_snippet(model: str, file_path: str, snippet: dict) -> str:
    """Send one snippet to LM Studio, get Romanized Hindi explanation."""
    prompt = f"""You are explaining code to a non-technical product manager who wants to learn.
Explain the following code snippet in simple Romanized Hindi (e.g. "Yeh function user ka login handle karta hai").
- No English technical jargon without explaining it first
- Line by line explanation, one line per code line
- Keep it simple enough for someone who has never coded

File: {file_path}
Lines: {snippet['start']}-{snippet['end']}

```
{snippet['code']}
```

Write ONLY the explanation. No intro, no outro."""

    try:
        r = requests.post(
            f"{LMSTUDIO_URL}/chat/completions",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 800,
            },
            timeout=120,
        )
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[Error getting annotation: {e}]"

# ── Book writer ────────────────────────────────────────────────────────────────

def append_to_book(file_path: str, snippet: dict, explanation: str) -> None:
    CODEBASE_BOOK.parent.mkdir(parents=True, exist_ok=True)

    # Init book if it doesn't exist
    if not CODEBASE_BOOK.exists():
        CODEBASE_BOOK.write_text("# Codebase Book\n\nRomanized Hindi explanations of every function.\nBuilt incrementally by local model — never manually edited.\n\n---\n\n")

    entry = f"""## `{snippet['name']}` — {file_path}
**Lines {snippet['start']}–{snippet['end']}** | `{snippet['code'].splitlines()[0][:60]}...`

{explanation}

---

"""
    with open(CODEBASE_BOOK, "a") as f:
        f.write(entry)


def already_annotated(snippet_name: str, file_path: str) -> bool:
    if not CODEBASE_BOOK.exists():
        return False
    content = CODEBASE_BOOK.read_text()
    return f"`{snippet_name}` — {file_path}" in content

# ── Main ──────────────────────────────────────────────────────────────────────

def get_files(single_file: str | None) -> list[Path]:
    if single_file:
        return [Path(single_file)]

    files = []
    root = Path(".")
    for pattern in CODE_PATTERNS:
        for f in root.glob(pattern):
            if not any(skip in f.parts for skip in SKIP_DIRS):
                files.append(f)
    return sorted(files)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="Annotate a single file")
    parser.add_argument("--check", action="store_true", help="Check model availability only")
    args = parser.parse_args()

    # Server check
    if not check_server():
        print("LM Studio server nahi chal raha.")
        print("LM Studio kholo → Local Server tab → Start Server")
        sys.exit(1)

    model = get_available_model()
    if not model:
        print("Koi model nahi mila. LM Studio mein ek model load karo.")
        sys.exit(1)

    print(f"Model: {model}")

    if args.check:
        print("Server aur model ready hain.")
        return

    files = get_files(args.file)
    print(f"{len(files)} files milein annotation ke liye.\n")

    total_annotated = 0

    for file_path in files:
        source = file_path.read_text(errors="ignore")
        suffix = file_path.suffix

        if suffix == ".py":
            snippets = extract_python_functions(source)
        elif suffix in (".ts", ".tsx"):
            snippets = extract_ts_functions(source)
        else:
            continue

        if not snippets:
            continue

        print(f"\n{file_path} — {len(snippets)} functions")

        for snippet in snippets:
            rel_path = str(file_path)
            if already_annotated(snippet["name"], rel_path):
                print(f"  skip: {snippet['name']} (already done)")
                continue

            print(f"  annotating: {snippet['name']} (lines {snippet['start']}-{snippet['end']})...")
            explanation = annotate_snippet(model, rel_path, snippet)
            append_to_book(rel_path, snippet, explanation)
            total_annotated += 1
            time.sleep(0.5)  # throttle slightly

    print(f"\nDone. {total_annotated} functions annotated → {CODEBASE_BOOK}")


if __name__ == "__main__":
    main()
