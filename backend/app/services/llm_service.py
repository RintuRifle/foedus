"""
Foedus — LLM Service (Gemini 1.5 Flash)
Central wrapper for all AI agent calls.
Uses google.genai SDK (new) with structured Pydantic output.
"""

import asyncio
import json
from typing import Any, Optional, Type, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.config import settings
from app.utils.logger import logger

T = TypeVar("T", bound=BaseModel)


class LLMService:
    """
    Gemini 1.5 Flash wrapper for the agent pipeline.

    Features:
    - Structured JSON output via Pydantic models
    - Automatic retry with exponential backoff
    - Token usage tracking
    """

    MODEL_NAME = "gemini-flash-lite-latest"
    MAX_RETRIES = 3
    BASE_DELAY = 2.0

    def __init__(self):
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not set — LLM calls will fail")
            self._configured = False
            self._client = None
            return

        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._configured = True
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._call_count = 0

    async def call(
        self,
        prompt: str,
        system_instruction: str = "",
        response_schema: Optional[Type[T]] = None,
        temperature: float = 0.3,
        max_output_tokens: int = 4096,
    ) -> T | str:
        """
        Call Gemini with optional structured Pydantic output.

        Returns parsed Pydantic model if response_schema provided, else raw string.
        """
        if not self._configured:
            raise RuntimeError("Gemini API key not configured")

        config_dict = {
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        }

        if response_schema:
            config_dict["response_mime_type"] = "application/json"
            config_dict["response_schema"] = response_schema

        if system_instruction:
            config_dict["system_instruction"] = system_instruction

        config = types.GenerateContentConfig(**config_dict)

        for attempt in range(self.MAX_RETRIES):
            try:
                response = self._client.models.generate_content(
                    model=self.MODEL_NAME,
                    contents=prompt,
                    config=config,
                )
                self._track_usage(response)

                if response_schema:
                    return self._parse_structured(response.text, response_schema)
                return response.text

            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "resource_exhausted" in error_str:
                    wait = self.BASE_DELAY * (2 ** attempt)
                    logger.warning(f"Rate limited — waiting {wait}s (attempt {attempt + 1})")
                    await asyncio.sleep(wait)
                elif "safety" in error_str:
                    logger.warning(f"Safety filter triggered: {e}")
                    if response_schema:
                        return self._empty_schema(response_schema)
                    return ""
                elif attempt < self.MAX_RETRIES - 1:
                    wait = self.BASE_DELAY * (2 ** attempt)
                    logger.warning(f"LLM error: {e} — retrying in {wait}s")
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"LLM call failed after {self.MAX_RETRIES} attempts: {e}")
                    raise

        raise RuntimeError(f"LLM call failed after {self.MAX_RETRIES} retries due to rate limits.")

    async def call_plain(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.4,
        max_output_tokens: int = 8192,
    ) -> str:
        """Call Gemini for free-form text output (proposal writing)."""
        return await self.call(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

    def _parse_structured(self, text: str, schema: Type[T]) -> T:
        """Parse JSON response into Pydantic model."""
        try:
            data = json.loads(text)
            return schema.model_validate(data)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to parse structured output: {e}")
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0].strip()
                data = json.loads(json_str)
                return schema.model_validate(data)
            elif "```" in text:
                json_str = text.split("```")[1].split("```")[0].strip()
                data = json.loads(json_str)
                return schema.model_validate(data)
            raise

    def _empty_schema(self, schema: Type[T]) -> T:
        """Create a default instance when LLM fails (safety filter, etc.)."""
        fields = {}
        for name, field_info in schema.model_fields.items():
            if field_info.default is not None:
                fields[name] = field_info.default
            elif field_info.annotation == str:
                fields[name] = ""
            elif field_info.annotation == float:
                fields[name] = 0.0
            elif field_info.annotation == int:
                fields[name] = 0
            elif field_info.annotation == bool:
                fields[name] = False
            elif field_info.annotation == list:
                fields[name] = []
        try:
            return schema.model_validate(fields)
        except Exception:
            return schema.model_construct(**fields)

    def _track_usage(self, response: Any):
        """Track token usage for plan limit enforcement."""
        self._call_count += 1
        try:
            usage = response.usage_metadata
            self._total_input_tokens += usage.prompt_token_count
            self._total_output_tokens += usage.candidates_token_count
        except Exception:
            pass

    @property
    def usage_stats(self) -> dict:
        return {
            "calls": self._call_count,
            "input_tokens": self._total_input_tokens,
            "output_tokens": self._total_output_tokens,
            "total_tokens": self._total_input_tokens + self._total_output_tokens,
        }


# Singleton
llm_service = LLMService()
