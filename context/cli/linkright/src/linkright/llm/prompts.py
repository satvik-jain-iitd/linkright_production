"""Markdown prompt loader with frontmatter support.

Prompts live as `.md` files with optional YAML frontmatter:

    ---
    name: parse_jd
    model: gemini-2.0-flash-lite
    temperature: 0.2
    ---
    You are a JD parser. Extract keywords, career level, and strategy...

Usage:
    from linkright.llm.prompts import load_prompt
    p = load_prompt("resume/parse_jd")
    text = p.fill(jd=jd_text, mode="product_manager")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import frontmatter


PROMPTS_ROOT_ENV = "LINKRIGHT_PROMPTS_ROOT"


@dataclass
class Prompt:
    name: str
    body: str
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def model(self) -> str | None:
        return self.meta.get("model")

    @property
    def temperature(self) -> float:
        return float(self.meta.get("temperature", 0.3))

    def fill(self, **kwargs: Any) -> str:
        """Replace {name} placeholders. Uses str.replace (not .format) so JSON braces don't break."""
        out = self.body
        for k, v in kwargs.items():
            out = out.replace("{" + k + "}", str(v))
        return out


def _prompts_root() -> Path:
    import os
    env = os.environ.get(PROMPTS_ROOT_ENV)
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "prompts"


def load_prompt(rel_path: str) -> Prompt:
    """Load prompt by relative path, e.g. 'resume/parse_jd' (no .md extension)."""
    root = _prompts_root()
    path = root / f"{rel_path}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    post = frontmatter.load(path)
    return Prompt(name=rel_path, body=post.content, meta=dict(post.metadata))
