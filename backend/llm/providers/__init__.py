"""
Provider registry and factory functions.
"""

from typing import Optional

from ..base import LLMProvider, LLMError
from ..config import get_config, ProviderName
from .minimax import MiniMaxProvider
from .openai import OpenAIProvider
from .anthropic import AnthropicProvider

# Provider registry - lazy initialized
_providers: dict[str, LLMProvider] = {}


def _get_or_create_provider(name: ProviderName) -> LLMProvider:
    """Get or create a provider instance."""
    if name not in _providers:
        config = get_config()
        if name == "minimax":
            _providers[name] = MiniMaxProvider(config)
        elif name == "openai":
            _providers[name] = OpenAIProvider(config)
        elif name == "anthropic":
            _providers[name] = AnthropicProvider(config)
        else:
            raise LLMError(f"Unknown provider: {name}", name)
    return _providers[name]


def get_provider(name: Optional[ProviderName] = None) -> LLMProvider:
    """
    Get an LLM provider by name.

    Args:
        name: Provider name. If None, uses default from config.

    Returns:
        Configured LLM provider instance

    Raises:
        LLMError: If provider is unknown or unavailable
    """
    config = get_config()
    provider_name = name or config.default_provider

    provider = _get_or_create_provider(provider_name)

    if not provider.is_available:
        raise LLMError(
            f"Provider '{provider_name}' is not available. "
            f"Check that the API key is configured.",
            provider_name
        )

    return provider


def list_available_providers() -> list[str]:
    """List all configured and available providers."""
    available = []
    for name in ["minimax", "openai", "anthropic"]:
        try:
            provider = _get_or_create_provider(name)
            if provider.is_available:
                available.append(name)
        except Exception:
            pass
    return available


def reset_providers() -> None:
    """Reset provider cache. Useful for testing."""
    global _providers
    _providers = {}
