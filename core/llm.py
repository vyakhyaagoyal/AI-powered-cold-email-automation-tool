"""
LLM provider abstraction.

Add a new provider by subclassing BaseLLMProvider and registering it in
get_llm_provider() below — nothing else in the codebase needs to change.
Switching providers is a one-line change in .env (LLM_PROVIDER=...).
"""
# from curses import raw
import json
import re
from abc import ABC, abstractmethod

from config import Config
from prompts import build_prompt


class LLMError(Exception):
    """Raised when the LLM call fails or returns an unusable response."""


def _parse_json_response(raw: str) -> dict:
    cleaned = raw.strip()

    # Remove markdown fences
    cleaned = re.sub(r"^```(?:json)?", "", cleaned)
    cleaned = re.sub(r"```$", "", cleaned)
    cleaned = cleaned.strip()

    # Extract first JSON object
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)

    try:
        data = json.loads(cleaned)
    except Exception as exc:
        print("\n===== INVALID JSON RECEIVED =====")
        print(cleaned)
        print("=================================\n")
        raise LLMError(f"Invalid JSON from LLM: {exc}") from exc

    if not isinstance(data, dict):
        raise LLMError("LLM did not return a JSON object.")

    if "subject" not in data:
        raise LLMError("Missing 'subject' field.")

    if "body" not in data:
        raise LLMError("Missing 'body' field.")

    return {
        "subject": data["subject"].strip(),
        "body": data["body"].strip(),
    }


class BaseLLMProvider(ABC):
    def __init__(self, config: Config):
        self.config = config

    @abstractmethod
    async def _complete(self, prompt: str) -> str:
        """Return the raw text completion from the underlying model."""

    async def generate_email(self, company_name: str, website_url: str, website_content: str) -> dict:
        """Generate {"subject": ..., "body": ...} for a company using its scraped content."""
        prompt = build_prompt(company_name, website_url, website_content)

        try:
            raw = await self._complete(prompt)
        except Exception as exc:
            raise LLMError(f"LLM API call failed: {exc}") from exc

        print("\n========== RAW LLM RESPONSE ==========")
        print(raw)
        print("======================================\n")

        try:
            return _parse_json_response(raw)
        except LLMError:
            retry_prompt = (
                f"{prompt}\n\nIMPORTANT: Your previous response was not valid JSON. "
                "Return ONLY a single valid JSON object with exactly two keys: "
                '"subject" and "body". Use double quotes and escape newlines as \\n\\n. '
                "Do not use markdown fences or extra text."
            )
            raw = await self._complete(retry_prompt)
            print("\n========== RETRY LLM RESPONSE ==========")
            print(raw)
            print("======================================\n")
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

class GroqProvider(BaseLLMProvider):
    def __init__(self, config: Config):
        super().__init__(config)
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(
            api_key=config.llm_api_key,
            base_url="https://api.groq.com/openai/v1",
        )

    async def _complete(self, prompt: str) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.config.llm_model or "llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You must return ONLY valid JSON. "
                            "Do not wrap it in markdown. "
                            "Escape newlines correctly."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.4,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            raise LLMError(f"Groq API call failed: {exc}") from exc

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
    provider = config.llm_provider.lower().strip()

    if provider == "openai":
        return OpenAIProvider(config)

    if provider == "anthropic":
        return AnthropicProvider(config)

    if provider == "gemini":
        return GeminiProvider(config)

    if provider == "groq":
        return GroqProvider(config)

    raise ValueError(
        f"Unsupported LLM_PROVIDER '{config.llm_provider}'. "
        "Use 'openai', 'anthropic', 'gemini', or 'groq'."
    )
