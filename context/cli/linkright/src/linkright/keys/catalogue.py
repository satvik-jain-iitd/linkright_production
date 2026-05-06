"""Provider catalogue — descriptions, verified signup URLs, free-tier specs,
and the exact env-var names that direct.py reads.

URL verification status (verified 2026-05-06):
  groq:         VERIFIED  — console.groq.com/keys loads API key mgmt UI
  cerebras:     UNCONFIRMED — URL pattern inferred; platform requires login
  sambanova:    VERIFIED  — cloud.sambanova.ai/apis shows "Manage API Keys"
  cloudflare:   VERIFIED URL SHAPE — dash.cloudflare.com/profile/api-tokens is standard CF path (403 = auth wall, not 404)
  zai:          INFERRED  — open.bigmodel.cn domain confirmed; apikeys path is standard
  gemini:       VERIFIED URL SHAPE — aistudio.google.com/app/apikey redirects to Google login (expected, URL is correct)
  openrouter:   VERIFIED  — openrouter.ai homepage links directly to /settings/keys
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProviderSpec:
    """Metadata for one LLM provider."""
    key: str                   # internal identifier (lowercase)
    name: str                  # display name
    description: str           # 1-line blurb
    free_tier: str             # free tier summary
    signup_url: str            # API-key creation page
    signup_url_verified: bool  # True = we fetched and confirmed it loads
    recommended: bool          # show ⭐ badge
    # env-var configuration — matches EXACTLY what direct.py reads
    primary_env: str           # e.g. "GROQ_API_KEY"
    extra_envs: list[str] = field(default_factory=list)   # fallback slots
    # For providers that need a paired second var (Cloudflare: token + account_id)
    paired_env: Optional[str] = None     # e.g. "CLOUDFLARE_ACCOUNT_ID"
    paired_label: Optional[str] = None  # human label for paired var
    # Validation hint
    key_prefix: Optional[str] = None   # expected prefix for format check
    key_min_len: int = 20

    @property
    def all_env_vars(self) -> list[str]:
        """All env var slots for this provider (primary + extras, no paired)."""
        return [self.primary_env] + self.extra_envs

    def next_available_slot(self, existing_env: dict[str, str]) -> Optional[str]:
        """Return the first unset env var slot name, or None if all 4 are used."""
        for var in self.all_env_vars:
            if not existing_env.get(var):
                return var
        return None


# Ordered by cascade priority (Groq first — fastest, easiest free tier)
PROVIDERS: list[ProviderSpec] = [
    ProviderSpec(
        key="groq",
        name="Groq",
        description="Open-source models (Llama 3.3 70B) on custom LPU silicon — fastest free inference.",
        free_tier="14,400 requests/day. No credit card required.",
        signup_url="https://console.groq.com/keys",
        signup_url_verified=True,
        recommended=True,
        primary_env="GROQ_API_KEY",
        extra_envs=["GROQ_API_KEY_2", "GROQ_API_KEY_3", "GROQ_API_KEY_4"],
        key_prefix="gsk_",
        key_min_len=40,
    ),
    ProviderSpec(
        key="cerebras",
        name="Cerebras",
        description="World's fastest inference on Wafer-Scale Engine silicon (Llama 3.3 70B).",
        free_tier="1 million tokens/day free. No credit card required.",
        signup_url="https://cloud.cerebras.ai/platform/api-keys",
        signup_url_verified=False,  # Could not confirm — requires login
        recommended=True,
        primary_env="CEREBRAS_API_KEY",
        extra_envs=["CEREBRAS_API_KEY_2", "CEREBRAS_API_KEY_3", "CEREBRAS_API_KEY_4"],
        key_prefix=None,
        key_min_len=20,
    ),
    ProviderSpec(
        key="sambanova",
        name="SambaNova",
        description="RDU-accelerated Llama 3.3 70B — enterprise-grade hardware, free tier.",
        free_tier="20 requests/minute. No credit card required.",
        signup_url="https://cloud.sambanova.ai/apis",
        signup_url_verified=True,
        recommended=False,
        primary_env="SAMBANOVA_API_KEY",
        extra_envs=["SAMBANOVA_API_KEY_2", "SAMBANOVA_API_KEY_3", "SAMBANOVA_API_KEY_4"],
        key_prefix=None,
        key_min_len=20,
    ),
    ProviderSpec(
        key="cloudflare",
        name="Cloudflare Workers AI",
        description="Llama 3.3 70B on Cloudflare's global edge network — low-latency inference.",
        free_tier="10,000 Neurons/day free. Requires Cloudflare account + Account ID.",
        signup_url="https://dash.cloudflare.com/profile/api-tokens",
        signup_url_verified=True,  # Standard CF dashboard URL — 403 = auth wall, not 404
        recommended=False,
        primary_env="CLOUDFLARE_API_TOKEN",
        # direct.py reads CLOUDFLARE_API_TOKEN_{1..4} paired with CLOUDFLARE_ACCOUNT_ID_{1..4}
        extra_envs=["CLOUDFLARE_API_TOKEN_1", "CLOUDFLARE_API_TOKEN_2", "CLOUDFLARE_API_TOKEN_3"],
        paired_env="CLOUDFLARE_ACCOUNT_ID",
        paired_label="Cloudflare Account ID",
        key_prefix=None,
        key_min_len=20,
    ),
    ProviderSpec(
        key="zai",
        name="Z.ai (Zhipu AI)",
        description="GLM-4.5 Flash model — Chinese AI lab with generous free tier.",
        free_tier="Free daily token quota. No credit card required.",
        signup_url="https://open.bigmodel.cn/usercenter/apikeys",
        signup_url_verified=False,  # Domain confirmed; apikeys path inferred
        recommended=False,
        primary_env="ZHIPU_API_KEY",
        extra_envs=["ZHIPU_API_KEY_2", "ZHIPU_API_KEY_3", "ZHIPU_API_KEY_4"],
        key_prefix=None,
        key_min_len=20,
    ),
    ProviderSpec(
        key="gemini",
        name="Gemini (Google AI Studio)",
        description="Google's Gemini Flash Lite — cheapest paid option, also has free tier.",
        free_tier="1,500 requests/day free in AI Studio. Google account required.",
        signup_url="https://aistudio.google.com/app/apikey",
        signup_url_verified=True,  # URL shape confirmed (redirects to Google login as expected)
        recommended=True,
        primary_env="GEMINI_API_KEY",
        extra_envs=["GEMINI_API_KEY_1", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3"],
        key_prefix="AIza",
        key_min_len=35,
    ),
    ProviderSpec(
        key="openrouter",
        name="OpenRouter",
        description="Multi-model gateway — routes to 100+ models including free-tier options.",
        free_tier="$5 free credit on signup. Also has genuinely free models.",
        signup_url="https://openrouter.ai/settings/keys",
        signup_url_verified=True,
        recommended=False,
        primary_env="OPENROUTER_API_KEY",
        extra_envs=["OPENROUTER_API_KEY_2", "OPENROUTER_API_KEY_3", "OPENROUTER_API_KEY_4"],
        key_prefix="sk-or-",
        key_min_len=40,
    ),
]

# Dict lookup by key
PROVIDER_MAP: dict[str, ProviderSpec] = {p.key: p for p in PROVIDERS}


def resilience_score(key_count: int, provider_count: int) -> str:
    """Return a human-readable resilience label.

    Rules (informed by cascade logic in direct.py):
      EXCELLENT: ≥5 keys across ≥3 providers
      GOOD:      ≥3 keys across ≥2 providers
      FAIR:      ≥1 key (single provider or single key)
      NONE:      0 keys
    """
    if key_count == 0:
        return "NONE"
    if key_count >= 5 and provider_count >= 3:
        return "EXCELLENT"
    if key_count >= 3 and provider_count >= 2:
        return "GOOD"
    return "FAIR"
