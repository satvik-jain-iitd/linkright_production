"""Abstract LLM provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int
    model: str


class LLMProvider(ABC):
    def __init__(self, api_key: str, model_id: str):
        self.api_key = api_key
        self.model_id = model_id

    @abstractmethod
    async def complete(self, system: str, user: str, temperature: float = 0.3) -> LLMResponse:
        """Send a completion request and return the response."""
        ...

    @abstractmethod
    async def validate_key(self) -> bool:
        """Check if the API key is valid. Returns True/False."""
        ...
