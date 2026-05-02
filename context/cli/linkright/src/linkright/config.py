"""LinkRight config loader — ~/.linkright/config.yaml.

Single source of truth for MongoDB URI, Oracle URL/secret, default LLM mode,
and user identity. Created on first `linkright init`.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import yaml


LINKRIGHT_HOME = Path(os.environ.get("LINKRIGHT_HOME", str(Path.home() / ".linkright")))
CONFIG_PATH = LINKRIGHT_HOME / "config.yaml"


def _autoload_env() -> None:
    """Auto-load API keys from ~/.linkright/.env on module import.

    Existing env vars are NEVER overridden — explicit shell exports always
    win. Lets users configure free-tier API keys (Groq, Cerebras, Gemini)
    once in ~/.linkright/.env and have every `linkright` invocation pick
    them up without manual sourcing.

    2026-05-01: added after the agent_claude $14 burn taught us that
    direct mode is the default safe path AND it requires API keys to be
    in env. No-op if file doesn't exist.
    """
    env_path = LINKRIGHT_HOME / ".env"
    if not env_path.exists():
        return
    try:
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            # 2026-05-01 fix: strip inline `# comment` (standard .env spec).
            # If the value contains a `#` not inside quotes, treat it as comment.
            if val and not (val.startswith('"') or val.startswith("'")):
                # find unquoted # and cut at first whitespace+# pattern
                comment_idx = val.find(" #")
                if comment_idx != -1:
                    val = val[:comment_idx].rstrip()
            val = val.strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val
    except Exception:
        pass  # never break linkright on broken .env


_autoload_env()


@dataclass
class Config:
    user_id: str = "local"
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "linkright"
    oracle_url: str = ""
    oracle_secret: str = ""
    default_llm_mode: str = "agent"  # agent | direct
    default_skill_mode: str = "product_manager"
    # Set by `linkright setup` wizard. Read by resume/cli.py to set
    # LR_AGENT_BACKEND env var so the pipeline routes through the user's pick.
    agent_backend: str = "claude"           # claude | opencode | gemini | ollama | custom
    embedder_tier: str = "fastembed"        # fastembed | sentence_transformers | oracle
    render_pdf: bool = True                 # if False, skip Playwright step_15
    schema_version: int = 2

    @classmethod
    def load(cls) -> "Config":
        """Load from ~/.linkright/config.yaml if present, else return defaults.

        Env vars ORACLE_BACKEND_URL / ORACLE_BACKEND_SECRET override file values.
        """
        data: dict[str, Any] = {}
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH) as f:
                data = yaml.safe_load(f) or {}
        cfg = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        # Env overrides for Oracle credentials (don't store secrets in config file by default)
        cfg.oracle_url = os.environ.get("ORACLE_BACKEND_URL", cfg.oracle_url)
        cfg.oracle_secret = os.environ.get("ORACLE_BACKEND_SECRET", cfg.oracle_secret)
        return cfg

    def save(self) -> None:
        LINKRIGHT_HOME.mkdir(parents=True, exist_ok=True)
        # Don't persist secrets to YAML — env is the source of truth
        serializable = {k: v for k, v in asdict(self).items() if k != "oracle_secret"}
        with open(CONFIG_PATH, "w") as f:
            yaml.safe_dump(serializable, f, sort_keys=False)

    def profile_dir(self) -> Path:
        return LINKRIGHT_HOME / "profile"

    def runs_dir(self) -> Path:
        return LINKRIGHT_HOME / "runs"

    def work_dir(self) -> Path:
        return LINKRIGHT_HOME / "work"

    def cache_dir(self) -> Path:
        return LINKRIGHT_HOME / "cache"
