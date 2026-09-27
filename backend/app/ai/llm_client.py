"""LLM Client - Unified interface for AI model access."""

import json
import logging
from typing import Optional, AsyncIterator
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    content: str
    model: str = ""
    tokens_used: int = 0
    finish_reason: str = ""
    confidence: float = 0.0


class LLMClient:
    """Unified LLM client supporting multiple providers.

    Supports:
    - OpenAI API (GPT-4, GPT-4o)
    - Anthropic API (Claude)
    - Local models via OpenAI-compatible API
    - Offline mode (rule-based fallback)
    """

    def __init__(self, provider: str = "openai", api_key: str = "",
                 model: str = "gpt-4o", base_url: str = "",
                 temperature: float = 0.1, max_tokens: int = 4096):
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = None

        if api_key:
            self._init_client()

    def _init_client(self):
        """Initialize the appropriate API client."""
        try:
            if self.provider == "openai":
                import openai
                kwargs = {"api_key": self.api_key}
                if self.base_url:
                    kwargs["base_url"] = self.base_url
                self._client = openai.AsyncOpenAI(**kwargs)
            elif self.provider == "anthropic":
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            else:
                # OpenAI-compatible endpoint (for local models)
                import openai
                kwargs = {"api_key": self.api_key or "not-needed"}
                if self.base_url:
                    kwargs["base_url"] = self.base_url
                self._client = openai.AsyncOpenAI(**kwargs)
        except ImportError as e:
            logger.warning(f"LLM library not installed: {e}. Using offline mode.")
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")

    @property
    def is_available(self) -> bool:
        """Check if LLM client is ready."""
        return self._client is not None

    async def complete(self, prompt: str, system: str = "",
                       temperature: float = None) -> LLMResponse:
        """Send a completion request."""
        if not self.is_available:
            return self._offline_fallback(prompt)

        temp = temperature if temperature is not None else self.temperature

        try:
            if self.provider == "anthropic":
                return await self._complete_anthropic(prompt, system, temp)
            else:
                return await self._complete_openai(prompt, system, temp)
        except Exception as e:
            logger.error(f"LLM completion failed: {e}")
            return self._offline_fallback(prompt)

    async def _complete_openai(self, prompt: str, system: str,
                                temperature: float) -> LLMResponse:
        """OpenAI-compatible completion."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=self.max_tokens,
        )

        content = response.choices[0].message.content or ""
        tokens = response.usage.total_tokens if response.usage else 0

        return LLMResponse(
            content=content,
            model=response.model,
            tokens_used=tokens,
            finish_reason=response.choices[0].finish_reason or "",
        )

    async def _complete_anthropic(self, prompt: str, system: str,
                                   temperature: float) -> LLMResponse:
        """Anthropic completion."""
        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        response = await self._client.messages.create(**kwargs)

        content = response.content[0].text if response.content else ""
        tokens = (response.usage.input_tokens + response.usage.output_tokens
                  if response.usage else 0)

        return LLMResponse(
            content=content,
            model=response.model,
            tokens_used=tokens,
            finish_reason=response.stop_reason or "",
        )

    async def generate_systemverilog(self, prompt: str,
                                      context: str = "") -> LLMResponse:
        """Specialized SV generation with RTL-aware prompting."""
        system = (
            "You are an expert SystemVerilog/UVM engineer. "
            "Generate syntactically valid SystemVerilog code. "
            "Never fabricate RTL behavior. Always state verification objectives. "
            "Generate code that compiles with Verilator and Icarus Verilog. "
            "Follow IEEE 1800-2017 SystemVerilog standard."
        )

        full_prompt = prompt
        if context:
            full_prompt = f"RTL Context:\n```\n{context}\n```\n\n{prompt}"

        return await self.complete(full_prompt, system=system)

    async def analyze_failure(self, failure_info: str,
                               rtl_context: str = "") -> LLMResponse:
        """Analyze a simulation failure."""
        system = (
            "You are an expert RTL verification engineer specializing in root cause analysis. "
            "Separate FACTS from HYPOTHESES clearly. "
            "Never fabricate waveform observations. "
            "Always provide evidence for claims. "
            "Suggest concrete debugging steps."
        )

        prompt = f"Failure Information:\n{failure_info}"
        if rtl_context:
            prompt += f"\n\nRelevant RTL:\n```\n{rtl_context}\n```"

        prompt += (
            "\n\nProvide:\n"
            "1. FACTS (directly observed)\n"
            "2. HYPOTHESES (inferred, with confidence)\n"
            "3. Suggested investigation steps\n"
            "4. Potential fix"
        )

        return await self.complete(prompt, system=system)

    def _offline_fallback(self, prompt: str) -> LLMResponse:
        """Rule-based fallback when LLM is not available."""
        return LLMResponse(
            content=(
                "[Offline Mode] LLM not available. "
                "Using deterministic analysis only. "
                "Configure LLM_API_KEY for AI-powered analysis."
            ),
            model="offline",
            tokens_used=0,
            finish_reason="offline",
            confidence=0.0,
        )


# Singleton
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create the singleton LLM client."""
    global _llm_client
    if _llm_client is None:
        from app.core.config import settings
        _llm_client = LLMClient(
            provider=settings.LLM_PROVIDER,
            api_key=settings.LLM_API_KEY or "",
            model=settings.LLM_MODEL,
            base_url=settings.LLM_BASE_URL or "",
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )
    return _llm_client
