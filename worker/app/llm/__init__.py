from .base import LLMProvider, LLMResponse
from .openrouter import OpenRouterProvider
from .groq import GroqProvider
from .gemini import GeminiProvider
from .openai_compat import OpenAICompatProvider

_OPENAI_COMPAT_URLS = {
    "cerebras":    "https://api.cerebras.ai/v1",
    "sambanova":   "https://api.sambanova.ai/v1",
    "siliconflow": "https://api.siliconflow.cn/v1",
    "nvidia":      "https://integrate.api.nvidia.com/v1",
    "github":      "https://models.inference.ai.azure.com",
    "mistral":     "https://api.mistral.ai/v1",
}

def get_provider(provider_name: str, api_key: str, model_id: str) -> LLMProvider:
    if provider_name == "openrouter":
        return OpenRouterProvider(api_key=api_key, model_id=model_id)
    if provider_name == "groq":
        return GroqProvider(api_key=api_key, model_id=model_id)
    if provider_name == "gemini":
        return GeminiProvider(api_key=api_key, model_id=model_id)
    if provider_name in _OPENAI_COMPAT_URLS:
        return OpenAICompatProvider(
            api_key=api_key,
            model_id=model_id,
            base_url=_OPENAI_COMPAT_URLS[provider_name],
        )
    raise ValueError(f"Unknown provider: {provider_name}")
