"""
Configuration management for LLM providers.
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field
import os

ProviderName = Literal["minimax", "openai", "anthropic"]


class LLMConfig(BaseModel):
    """Configuration for LLM providers."""

    # Global settings
    default_provider: ProviderName = Field(
        default="minimax",
        description="Default LLM provider to use"
    )

    # MiniMax settings
    minimax_api_key: Optional[str] = None
    minimax_model: str = "abab6.5s-chat"
    minimax_api_url: str = "https://api.minimax.chat/v1/text/chatcompletion_v2"

    # OpenAI settings
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    openai_api_url: str = "https://api.openai.com/v1/chat/completions"

    # Anthropic settings
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_api_url: str = "https://api.anthropic.com/v1/messages"
    anthropic_api_version: str = "2023-06-01"

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Load configuration from environment variables."""
        return cls(
            default_provider=os.environ.get("LLM_PROVIDER", "minimax"),
            minimax_api_key=os.environ.get("MINIMAX_API_KEY"),
            minimax_model=os.environ.get("MINIMAX_MODEL", "abab6.5s-chat"),
            minimax_api_url=os.environ.get(
                "MINIMAX_API_URL",
                "https://api.minimax.chat/v1/text/chatcompletion_v2"
            ),
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            openai_model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
            openai_api_url=os.environ.get(
                "OPENAI_API_URL",
                "https://api.openai.com/v1/chat/completions"
            ),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            anthropic_model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
            anthropic_api_url=os.environ.get(
                "ANTHROPIC_API_URL",
                "https://api.anthropic.com/v1/messages"
            ),
            anthropic_api_version=os.environ.get("ANTHROPIC_API_VERSION", "2023-06-01"),
        )


# Global config instance
_config: Optional[LLMConfig] = None


def get_config() -> LLMConfig:
    """Get or create the global config instance."""
    global _config
    if _config is None:
        _config = LLMConfig.from_env()
    return _config


def reset_config() -> None:
    """Reset config to reload from environment. Useful for testing."""
    global _config
    _config = None
