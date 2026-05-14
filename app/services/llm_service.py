"""
LLM service for interacting with Ollama.
"""
from typing import Optional, List, Dict, Any, AsyncGenerator
import asyncio

import httpx
from ollama import AsyncClient

from app.core.config import settings
from app.core.exceptions import LLMError, OllamaError
from app.utils.logger import app_logger


class LLMService:
    """Service for LLM interactions using Ollama."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        """
        Initialize LLM service.
        
        Args:
            base_url: Ollama API base URL
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        """
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_model
        self.temperature = temperature or settings.ollama_temperature
        self.max_tokens = max_tokens or settings.ollama_max_tokens
        self.client: Optional[AsyncClient] = None
        
        app_logger.info(f"Initializing LLMService with model: {self.model}")
    
    async def initialize(self) -> None:
        """Initialize the Ollama client."""
        try:
            self.client = AsyncClient(host=self.base_url)
            app_logger.info(f"LLM service initialized: {self.base_url}")
        except Exception as e:
            app_logger.error(f"Failed to initialize LLM service: {e}")
            raise OllamaError("Failed to initialize Ollama client", detail=str(e))
    
    async def is_available(self) -> bool:
        """
        Check if Ollama service is available.
        
        Returns:
            True if available, False otherwise
        """
        try:
            if self.client is None:
                await self.initialize()
            
            # Try to list models as a health check
            await self.client.list()
            return True
        except Exception as e:
            app_logger.warning(f"Ollama service not available: {e}")
            return False
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate text completion.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            
        Returns:
            Generated text
        """
        if self.client is None:
            await self.initialize()
        
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = await self.client.chat(
                model=self.model,
                messages=messages,
                options={
                    "temperature": temperature or self.temperature,
                    "num_predict": max_tokens or self.max_tokens,
                }
            )
            
            return response['message']['content']
            
        except Exception as e:
            app_logger.error(f"LLM generation failed: {e}")
            raise LLMError("Failed to generate response", detail=str(e))
    
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Generate text completion with streaming.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            
        Yields:
            Generated text chunks
        """
        if self.client is None:
            await self.initialize()
        
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            stream = await self.client.chat(
                model=self.model,
                messages=messages,
                stream=True,
                options={
                    "temperature": temperature or self.temperature,
                    "num_predict": max_tokens or self.max_tokens,
                }
            )
            
            async for chunk in stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    yield chunk['message']['content']
                    
        except Exception as e:
            app_logger.error(f"LLM streaming failed: {e}")
            raise LLMError("Failed to generate streaming response", detail=str(e))
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self.client is not None:
            # Ollama AsyncClient doesn't need explicit cleanup
            self.client = None
            app_logger.info("LLM service cleaned up")
