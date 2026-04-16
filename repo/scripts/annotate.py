"""
CODEBASE BOOK BUILDER
Reads code one function at a time, explains in Romanized Hindi,
appends to specs/CODEBASE_BOOK.md. Uses local LM Studio — zero Claude tokens.

Setup:
    1. LM Studio kholo → Local Server → Start Server
    2. deepseek-r1-distill-qwen-1.5b load karo

Usage:
    python repo/scripts/annotate.py              # full codebase
    python repo/scripts/annotate.py --file path  # single file
    python repo/scripts/annotate.py --check      # server check only
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
import time
from pathlib import Path

import requests

LMSTUDIO_URL = "http://localhost:1234/v1"
MODEL = "deepseek-r1-distill-qwen-1.5b"
CODEBASE_BOOK = Path("specs/CODEBASE_BOOK.md")
SKIP_DIRS = {"node_modules", ".next", "__pycache__", ".git", "dist", "build"}
CODE_PATTERNS = [
    "repo/website/**/*.ts",
    "repo/website/**/*.tsx",
    "repo/worker/**/*.py",
    "repo/oracle-backend/**/*.py",
]


def check_server() -> bool:
    try:
        requests.get(f"{LMSTUDIO_URL}/models", timeout=3)
        return True
    except Exception:
        return False


def extract_python_functions(source: str) -> list[dict]:
    snippets = []
    try:
        tree = ast.parse(source)
        lines = source.splitlines()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                start = node.lineno - 1
                end = node.end_lineno
                snippets.append({
                    "name": node.name,
                    "start": node.lineno,
                    "end": node.end_lineno,
                    "code": "\n".join(lines[start:end]),
                })
    except SyntaxError:
        pass
    return snippets


def extract_ts_functions(source: str) -> list[dict]:
    snippets = []
    lines = source.splitlines()
    pattern = re.compile(
        r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(\w+)\s*[(<]"
        r"|^(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\(",
        re.MULTILINE,
    )
    for match in pattern.finditer(source):
        name = match.group(1) or match.group(2)
        start_line = source[: match.start()].count("\n")
        end_line = min(start_line + 40, len(lines))
        snippets.append({
            "name": name,
            "start": start_line + 1,
            "end": end_line,
            "code": "\n".join(lines[start_line:end_line]),
        })
    return snippets


def annotate(file_path: str, snippet: dict) -> str:
    prompt = f"""Explain this code in simple Romanized Hindi for a non-technical person.
Line by line — one explanation per code line. No jargon without explaining it.

File: {file_path} | Lines: {snippet['start']}-{snippet['end']}

```
{snippet['code']}
```

Only write the explanation:"""

    try:
        r = requests.post(
            f"{LMSTUDIO_URL}/chat/completions",
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 600,
            },
            timeout=120,
        )
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[Error: {e}]"


def already_done(name: str, path: str) -> bool:
    if not CODEBASE_BOOK.exists():
        return False
    return f"`{name}` — {path}" in CODEBASE_BOOK.read_text()


def append_to_book(file_path: str, snippet: dict, explanation: str) -> None:
    CODEBASE_BOOK.parent.mkdir(parents=True, exist_ok=True)
    if not CODEBASE_BOOK.exists():
        CODEBASE_BOOK.write_text(
            "# Codebase Book\n\nRomanized Hindi explanations — built by local model.\n\n---\n\n"
        )
    entry = (
        f"## `{snippet['name']}` — {file_path}\n"
        f"**Lines {snippet['start']}–{snippet['end']}**\n\n"
        f"{explanation}\n\n---\n\n"
    )
    with open(CODEBASE_BOOK, "a") as f:
        f.write(entry)


def get_files(single: str | None) -> list[Path]:
    if single:
        return [Path(single)]
    files = []
    for pattern in CODE_PATTERNS:
        for f in Path(".").glob(pattern):
            if not any(s in f.parts for s in SKIP_DIRS):
                files.append(f)
    return sorted(files)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="Single file to annotate")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if not check_server():
        print("LM Studio server nahi chal raha. Local Server tab mein Start karo.")
        sys.exit(1)

    print(f"Server ready. Model: {MODEL}")
    if args.check:
        return

    files = get_files(args.file)
    print(f"{len(files)} files found.\n")
    total = 0

    for file_path in files:
        source = file_path.read_text(errors="ignore")
        snippets = (
            extract_python_functions(source)
            if file_path.suffix == ".py"
            else extract_ts_functions(source)
        )
        if not snippets:
            continue

        print(f"{file_path} — {len(snippets)} functions")
        for s in snippets:
            rel = str(file_path)
            if already_done(s["name"], rel):
                print(f"  skip: {s['name']}")
                continue
            print(f"  {s['name']} (lines {s['start']}-{s['end']})...")
            append_to_book(rel, s, annotate(rel, s))
            total += 1
            time.sleep(0.3)

    print(f"\nDone. {total} functions → {CODEBASE_BOOK}")


if __name__ == "__main__":
    main()
