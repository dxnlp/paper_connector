"""
Base classes and protocols for LLM providers.
"""

from typing import Protocol, Optional, runtime_checkable
from pydantic import BaseModel


class LLMResponse(BaseModel):
    """Normalized response from any LLM provider."""
    content: str
    model: str
    provider: str
    usage: Optional[dict] = None
    finish_reason: Optional[str] = None
    raw_response: Optional[dict] = None


class LLMError(Exception):
    """Exception raised by LLM operations."""

    def __init__(self, message: str, provider: str, cause: Optional[Exception] = None):
        super().__init__(message)
        self.provider = provider
        self.cause = cause

    def __str__(self) -> str:
        base = f"[{self.provider}] {super().__str__()}"
        if self.cause:
            base += f" (caused by: {self.cause})"
        return base


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol defining the interface for LLM providers."""

    @property
    def name(self) -> str:
        """Provider identifier (e.g., 'minimax', 'openai')."""
        ...

    @property
    def is_available(self) -> bool:
        """Whether the provider is configured and available."""
        ...

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        **kwargs
    ) -> LLMResponse:
        """
        Send a completion request to the LLM.

        Args:
            system_prompt: System message to set context
            user_prompt: User message/query
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response
            **kwargs: Provider-specific parameters

        Returns:
            LLMResponse with normalized content

        Raises:
            LLMError: On API or configuration errors
        """
        ...
