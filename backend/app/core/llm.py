"""
OpenAI LLM Client for code generation

Uses OpenAI GPT-5 via GitHub Models for high-quality code generation and analysis.
"""

import asyncio
import logging
from typing import Optional, AsyncGenerator
from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Client for OpenAI GPT-5 via GitHub Models"""

    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        endpoint: str = None,
        timeout: float = 300.0,
    ):
        self.api_key = api_key or settings.github_token
        self.model = model or settings.openai_model
        self.endpoint = endpoint or settings.openai_endpoint
        self.timeout = timeout
        self._client: Optional[OpenAI] = None

    def _get_client(self) -> OpenAI:
        """Get or create OpenAI client"""
        if self._client is None:
            self._client = OpenAI(
                base_url=self.endpoint,
                api_key=self.api_key,
                timeout=self.timeout,
                max_retries=2,
            )
        return self._client

    def _is_reasoning_model(self) -> bool:
        """Check if the current model is a reasoning model (GPT-5, o-series).
        These models have different parameter requirements."""
        return any(tag in self.model for tag in ("gpt-5", "o1", "o3", "o4"))

    def _model_params(self, max_tokens: int, temperature: float) -> dict:
        """Return the correct API parameters for the current model.
        
        GPT-5 and o-series models:
        - Require max_completion_tokens instead of max_tokens
        - Only support temperature=1 (default), so we omit it
        
        Older models use max_tokens and support custom temperature.
        """
        if self._is_reasoning_model():
            return {"max_completion_tokens": max_tokens}
        return {"max_tokens": max_tokens, "temperature": temperature}

    async def close(self):
        """Close the client"""
        if self._client:
            self._client.close()
            self._client = None

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
    ) -> str | AsyncGenerator[str, None]:
        """
        Generate text completion from OpenAI GPT-5.

        Args:
            prompt: User prompt
            system: System prompt (optional)
            temperature: Sampling temperature (0.0 - 1.0)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response

        Returns:
            Generated text or async generator if streaming
        """
        if stream:
            return self._stream_response(prompt, system, temperature, max_tokens)
        else:
            return await self._generate_response(prompt, system, temperature, max_tokens)

    async def _generate_response(
        self,
        prompt: str,
        system: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Non-streaming generation"""
        try:
            client = self._get_client()
            
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            # Run sync client in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            params = self._model_params(max_tokens, temperature)
            response = await loop.run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    messages=messages,
                    model=self.model,
                    **params,
                )
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {e}")

    async def _stream_response(
        self,
        prompt: str,
        system: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        """Streaming generation"""
        try:
            client = self._get_client()
            
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            # Run sync streaming in thread pool
            loop = asyncio.get_event_loop()
            params = self._model_params(max_tokens, temperature)
            response = await loop.run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    messages=messages,
                    model=self.model,
                    stream=True,
                    **params,
                )
            )
            
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise RuntimeError(f"OpenAI streaming error: {e}")

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        Chat completion with message history.

        Args:
            messages: List of messages [{"role": "user/assistant/system", "content": "..."}]
            temperature: Sampling temperature
            max_tokens: Maximum tokens

        Returns:
            Assistant response text
        """
        try:
            client = self._get_client()

            # Run sync client in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            params = self._model_params(max_tokens, temperature)
            response = await loop.run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    messages=messages,
                    model=self.model,
                    **params,
                )
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"OpenAI chat error: {e}")


# Global client instance
_openai_client: Optional[OpenAIClient] = None


def get_openai_client() -> OpenAIClient:
    """Get global OpenAI client instance"""
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAIClient()
    return _openai_client


# Alias for backward compatibility
get_claude_client = get_openai_client


async def generate_completion(
    user_prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 8192,
) -> str:
    """
    Convenience function for generating completions.

    Uses OpenAI GPT-5 for high-quality code generation.
    """
    client = get_openai_client()

    messages = [{"role": "user", "content": user_prompt}]

    try:
        return await client.chat(
            messages=[{"role": "system", "content": system_prompt}] + messages if system_prompt else messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as e:
        logger.error(f"[LLM] generate_completion failed: {e}")
        raise


async def check_llm_health() -> bool:
    """Check if OpenAI API is accessible"""
    try:
        client = get_openai_client()
        response = await client.chat(
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=1024,  # Reasoning models need headroom for chain-of-thought
        )
        return response is not None and len(response) > 0
    except Exception:
        return False


# Alias for backward compatibility
check_claude_health = check_llm_health
