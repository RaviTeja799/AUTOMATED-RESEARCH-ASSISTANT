"""
LLM service using Groq API (fast, free, no local model needed).
"""
from typing import Optional, AsyncGenerator

from groq import AsyncGroq

from app.core.config import settings
from app.core.exceptions import LLMError
from app.utils.logger import app_logger


class LLMService:
    """LLM service backed by Groq."""

    def __init__(self):
        self.api_key = settings.groq_api_key
        self.model = settings.groq_model
        self.temperature = settings.groq_temperature
        self.max_tokens = settings.groq_max_tokens
        self.client: Optional[AsyncGroq] = None
        app_logger.info(f"LLMService initializing with Groq model: {self.model}")

    async def initialize(self) -> None:
        try:
            self.client = AsyncGroq(api_key=self.api_key)
            app_logger.info("Groq LLM service ready")
        except Exception as e:
            app_logger.error(f"Failed to initialize Groq client: {e}")
            raise LLMError("Failed to initialize Groq client", detail=str(e))

    async def is_available(self) -> bool:
        try:
            if self.client is None:
                await self.initialize()
            # Quick test call
            await self.client.models.list()
            return True
        except Exception as e:
            app_logger.warning(f"Groq not available: {e}")
            return False

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        if self.client is None:
            await self.initialize()

        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=max_tokens or self.max_tokens,
            )

            return response.choices[0].message.content

        except Exception as e:
            app_logger.error(f"Groq generation failed: {e}")
            raise LLMError("Failed to generate response", detail=str(e))

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        if self.client is None:
            await self.initialize()

        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                stream=True,
            )

            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta

        except Exception as e:
            app_logger.error(f"Groq streaming failed: {e}")
            raise LLMError("Failed to stream response", detail=str(e))

    async def cleanup(self) -> None:
        self.client = None
        app_logger.info("LLM service cleaned up")
