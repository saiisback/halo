"""
Claude LLM Client for code generation

Uses Anthropic Claude API for high-quality code generation and analysis.
Supports extended thinking for complex reasoning tasks.
"""

import asyncio
import logging
from typing import Optional, AsyncGenerator
from anthropic import Anthropic

from app.core.config import settings

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Client for Anthropic Claude API"""

    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        timeout: float = 300.0,
    ):
        self.api_key = api_key or settings.anthropic_api_key
        self.model = model or settings.claude_model
        self.timeout = timeout
        self._client: Optional[Anthropic] = None

    def _get_client(self) -> Anthropic:
        """Get or create Anthropic client"""
        if self._client is None:
            self._client = Anthropic(
                api_key=self.api_key,
                timeout=self.timeout,
                max_retries=2,
            )
        return self._client

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
        thinking: bool = False,
        thinking_budget: int = 10000,
    ) -> str | AsyncGenerator[str, None]:
        """
        Generate text completion from Claude.

        Args:
            prompt: User prompt
            system: System prompt (optional)
            temperature: Sampling temperature (0.0 - 1.0)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            thinking: Whether to enable extended thinking
            thinking_budget: Token budget for thinking (only used when thinking=True)

        Returns:
            Generated text or async generator if streaming
        """
        if stream:
            return self._stream_response(prompt, system, temperature, max_tokens)
        else:
            return await self._generate_response(
                prompt, system, temperature, max_tokens, thinking, thinking_budget
            )

    async def _generate_response(
        self,
        prompt: str,
        system: Optional[str],
        temperature: float,
        max_tokens: int,
        thinking: bool = False,
        thinking_budget: int = 10000,
    ) -> str:
        """Non-streaming generation"""
        try:
            client = self._get_client()

            messages = [{"role": "user", "content": prompt}]

            kwargs = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
            }

            if system:
                kwargs["system"] = system

            if thinking:
                kwargs["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": thinking_budget,
                }
                # Extended thinking requires temperature=1 on Claude
                kwargs["temperature"] = 1
            else:
                kwargs["temperature"] = temperature

            # Run sync client in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.messages.create(**kwargs),
            )

            # Extract text from response - may contain thinking + text blocks
            text_parts = []
            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)

            return "".join(text_parts)
        except Exception as e:
            raise RuntimeError(f"Claude API error: {e}")

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

            messages = [{"role": "user", "content": prompt}]

            kwargs = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }

            if system:
                kwargs["system"] = system

            # Run sync streaming in thread pool
            loop = asyncio.get_event_loop()
            stream = await loop.run_in_executor(
                None,
                lambda: client.messages.stream(**kwargs),
            )

            with stream as s:
                for text in s.text_stream:
                    yield text
        except Exception as e:
            raise RuntimeError(f"Claude streaming error: {e}")

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        thinking: bool = False,
        thinking_budget: int = 10000,
    ) -> str:
        """
        Chat completion with message history.

        Args:
            messages: List of messages [{"role": "user/assistant", "content": "..."}]
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            thinking: Whether to enable extended thinking
            thinking_budget: Token budget for thinking

        Returns:
            Assistant response text
        """
        try:
            client = self._get_client()

            # Claude uses system as a top-level param, not a message role
            system_prompt = None
            chat_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_prompt = msg["content"]
                else:
                    chat_messages.append(msg)

            kwargs = {
                "model": self.model,
                "messages": chat_messages,
                "max_tokens": max_tokens,
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            if thinking:
                kwargs["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": thinking_budget,
                }
                kwargs["temperature"] = 1
            else:
                kwargs["temperature"] = temperature

            # Run sync client in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.messages.create(**kwargs),
            )

            # Extract text from response
            text_parts = []
            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)

            return "".join(text_parts)
        except Exception as e:
            raise RuntimeError(f"Claude chat error: {e}")


# Global client instance
_claude_client: Optional[ClaudeClient] = None


def get_claude_client() -> ClaudeClient:
    """Get global Claude client instance"""
    global _claude_client
    if _claude_client is None:
        _claude_client = ClaudeClient()
    return _claude_client


async def generate_completion(
    user_prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 8192,
    thinking: bool = False,
    thinking_budget: int = 10000,
) -> str:
    """
    Convenience function for generating completions.

    Uses Claude for high-quality code generation.
    Supports extended thinking for complex reasoning tasks.
    """
    client = get_claude_client()

    try:
        return await client.generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            thinking=thinking,
            thinking_budget=thinking_budget,
        )
    except Exception as e:
        logger.error(f"[LLM] generate_completion failed: {e}")
        raise


async def check_llm_health() -> bool:
    """Check if Claude API is accessible"""
    try:
        client = get_claude_client()
        response = await client.generate(
            prompt="hi",
            max_tokens=64,
        )
        return response is not None and len(response) > 0
    except Exception:
        return False
