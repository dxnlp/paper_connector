"""
LLM provider abstraction layer.

Supports multiple LLM providers (MiniMax, OpenAI, Anthropic) with a unified interface.

Usage:
    from llm import get_provider, list_available_providers

    # Get default provider
    provider = get_provider()

    # Get specific provider
    provider = get_provider("openai")

    # Call the LLM
    response = await provider.complete(
        system_prompt="You are a helpful assistant.",
        user_prompt="Hello!"
    )
    print(response.content)

    # List available providers
    available = list_available_providers()
"""

from .base import LLMProvider, LLMResponse, LLMError
from .config import LLMConfig, get_config, reset_config, ProviderName
from .providers import get_provider, list_available_providers, reset_providers

__all__ = [
    # Protocol and models
    "LLMProvider",
    "LLMResponse",
    "LLMError",
    # Configuration
    "LLMConfig",
    "get_config",
    "reset_config",
    "ProviderName",
    # Provider access
    "get_provider",
    "list_available_providers",
    "reset_providers",
]
