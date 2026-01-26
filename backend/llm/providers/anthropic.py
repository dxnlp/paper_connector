"""
Anthropic Claude LLM provider implementation.
"""

from typing import Optional
import httpx

from ..base import LLMResponse, LLMError
from ..config import LLMConfig


class AnthropicProvider:
    """Anthropic Claude LLM provider implementation."""

    def __init__(self, config: LLMConfig):
        self._config = config

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def is_available(self) -> bool:
        return bool(self._config.anthropic_api_key)

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Send a completion request to Anthropic API."""
        key = api_key or self._config.anthropic_api_key
        if not key:
            raise LLMError("ANTHROPIC_API_KEY not configured", self.name)

        headers = {
            "x-api-key": key,
            "anthropic-version": self._config.anthropic_api_version,
            "content-type": "application/json"
        }

        # Anthropic uses 'system' as a top-level param, not in messages
        payload = {
            "model": model or self._config.anthropic_model,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self._config.anthropic_api_url,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()

                # Anthropic response format: content is an array of content blocks
                content = ""
                if data.get("content"):
                    # Extract text from content blocks
                    text_blocks = [
                        block["text"]
                        for block in data["content"]
                        if block.get("type") == "text"
                    ]
                    content = "".join(text_blocks)

                return LLMResponse(
                    content=content,
                    model=data.get("model", self._config.anthropic_model),
                    provider=self.name,
                    usage=data.get("usage"),
                    finish_reason=data.get("stop_reason"),
                    raw_response=data
                )
        except httpx.HTTPStatusError as e:
            raise LLMError(
                f"API request failed with status {e.response.status_code}: {e.response.text}",
                self.name,
                e
            )
        except httpx.HTTPError as e:
            raise LLMError(f"API request failed: {e}", self.name, e)
        except (KeyError, IndexError, TypeError) as e:
            raise LLMError(f"Unexpected response format: {e}", self.name, e)
