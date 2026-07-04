"""
LLM provider abstraction.

Add a new provider by subclassing BaseLLMProvider and registering it in
get_llm_provider() below — nothing else in the codebase needs to change.
Switching providers is a one-line change in .env (LLM_PROVIDER=...).
"""
import json
import re
from abc import ABC, abstractmethod

from config import Config
from prompts import build_prompt


class LLMError(Exception):
    """Raised when the LLM call fails or returns an unusable response."""


def _parse_json_response(raw: str) -> dict:
    """Parse the model's raw text output into {"subject": ..., "body": ...}."""
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        # Fall back to grabbing the first {...} block in case the model added preamble
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise LLMError(f"Could not parse LLM response as JSON: {exc}") from exc
        data = json.loads(match.group(0))

    if "subject" not in data or "body" not in data:
        raise LLMError("LLM response is missing 'subject' or 'body' keys")

    return {"subject": str(data["subject"]).strip(), "body": str(data["body"]).strip()}


class BaseLLMProvider(ABC):
    def __init__(self, config: Config):
        self.config = config

    @abstractmethod
    async def _complete(self, prompt: str) -> str:
        """Return the raw text completion from the underlying model."""

    async def generate_email(self, company_name: str, website_url: str, website_content: str) -> dict:
        """Generate {"subject": ..., "body": ...} for a company using its scraped content."""
        prompt = build_prompt(company_name, website_url, website_content)
        raw = await self._complete(prompt)
        return _parse_json_response(raw)


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, config: Config):
        super().__init__(config)
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=config.llm_api_key)

    async def _complete(self, prompt: str) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.config.llm_model or "gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
        except Exception as exc:
            raise LLMError(f"OpenAI API call failed: {exc}") from exc
        return response.choices[0].message.content


class AnthropicProvider(BaseLLMProvider):
    def __init__(self, config: Config):
        super().__init__(config)
        from anthropic import AsyncAnthropic
        self.client = AsyncAnthropic(api_key=config.llm_api_key)

    async def _complete(self, prompt: str) -> str:
        try:
            response = await self.client.messages.create(
                model=self.config.llm_model or "claude-sonnet-4-6",
                max_tokens=1200,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:
            raise LLMError(f"Anthropic API call failed: {exc}") from exc
        return "".join(block.text for block in response.content if hasattr(block, "text"))


class GeminiProvider(BaseLLMProvider):
    def __init__(self, config: Config):
        super().__init__(config)
        import google.generativeai as genai
        genai.configure(api_key=config.llm_api_key)
        self.model = genai.GenerativeModel(config.llm_model or "gemini-1.5-flash")

    async def _complete(self, prompt: str) -> str:
        import asyncio
        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
        except Exception as exc:
            raise LLMError(f"Gemini API call failed: {exc}") from exc
        return response.text


def get_llm_provider(config: Config) -> BaseLLMProvider:
    """Factory: return the configured LLM provider instance."""
    provider = config.llm_provider.lower().strip()
    if provider == "openai":
        return OpenAIProvider(config)
    if provider == "anthropic":
        return AnthropicProvider(config)
    if provider == "gemini":
        return GeminiProvider(config)
    raise ValueError(
        f"Unsupported LLM_PROVIDER '{config.llm_provider}'. Use 'openai', 'anthropic', or 'gemini'."
    )
