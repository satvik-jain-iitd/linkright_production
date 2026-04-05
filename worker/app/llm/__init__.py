from .base import LLMProvider, LLMResponse
from .openrouter import OpenRouterProvider
from .groq import GroqProvider
from .gemini import GeminiProvider

def get_provider(provider_name: str, api_key: str, model_id: str) -> LLMProvider:
    providers = {
        "openrouter": OpenRouterProvider,
        "groq": GroqProvider,
        "gemini": GeminiProvider,
    }
    cls = providers.get(provider_name)
    if not cls:
        raise ValueError(f"Unknown provider: {provider_name}")
    return cls(api_key=api_key, model_id=model_id)
