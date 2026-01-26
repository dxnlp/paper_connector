"""
MiniMax LLM provider implementation.
"""

from typing import Optional
import httpx

from ..base import LLMResponse, LLMError
from ..config import LLMConfig


class MiniMaxProvider:
    """MiniMax LLM provider implementation."""

    def __init__(self, config: LLMConfig):
        self._config = config

    @property
    def name(self) -> str:
        return "minimax"

    @property
    def is_available(self) -> bool:
        return bool(self._config.minimax_api_key)

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
        """Send a completion request to MiniMax API."""
        key = api_key or self._config.minimax_api_key
        if not key:
            raise LLMError("MINIMAX_API_KEY not configured", self.name)

        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model or self._config.minimax_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self._config.minimax_api_url,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()

                return LLMResponse(
                    content=data["choices"][0]["message"]["content"],
                    model=data.get("model", self._config.minimax_model),
                    provider=self.name,
                    usage=data.get("usage"),
                    finish_reason=data["choices"][0].get("finish_reason"),
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
        except (KeyError, IndexError) as e:
            raise LLMError(f"Unexpected response format: {e}", self.name, e)
