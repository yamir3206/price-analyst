"""Gemini client boundary with strict JSON response validation."""

from __future__ import annotations

import json
from typing import Any

import httpx

from price_analyst.ai.prompts import SYSTEM_INSTRUCTION, render_user_prompt
from price_analyst.collectors.retry import RetryPolicy, with_retry
from price_analyst.domain.ai_analysis import AIAnalysis, CompactAnalysisDataset


class GeminiUnavailableError(RuntimeError):
    """Raised when AI analysis is deliberately disabled or unavailable."""


class GeminiResponseError(RuntimeError):
    """Raised when Gemini does not return the required structured response."""


class DisabledGeminiClient:
    """Safe default: deterministic search never depends on Gemini."""

    enabled = False

    async def analyze(self, dataset: CompactAnalysisDataset) -> AIAnalysis:
        del dataset
        raise GeminiUnavailableError("Gemini analysis is not configured")


class GeminiHttpClient:
    """Minimal server-side Gemini REST client; the API key never enters URLs."""

    enabled = True

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float,
        max_output_tokens: int,
        retry_policy: RetryPolicy,
        endpoint: str = "https://generativelanguage.googleapis.com/v1beta",
    ) -> None:
        if not api_key:
            raise ValueError("api_key must not be empty")
        self._client = client
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_output_tokens = max_output_tokens
        self._retry_policy = retry_policy
        self._endpoint = endpoint.rstrip("/")

    async def analyze(self, dataset: CompactAnalysisDataset) -> AIAnalysis:
        prompt = render_user_prompt(dataset)
        payload = {
            "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": self._max_output_tokens,
                "responseMimeType": "application/json",
            },
        }

        async def request() -> httpx.Response:
            response = await self._client.post(
                f"{self._endpoint}/models/{self._model}:generateContent",
                headers={
                    "content-type": "application/json",
                    "x-goog-api-key": self._api_key,
                },
                json=payload,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            return response

        try:
            response = await with_retry(request, policy=self._retry_policy)
        except httpx.HTTPStatusError as exc:
            raise GeminiUnavailableError(
                f"Gemini returned HTTP status {exc.response.status_code}."
            ) from exc
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise GeminiUnavailableError("Gemini request failed due to a network error.") from exc

        try:
            response_payload = response.json()
            text = self._response_text(response_payload)
            decoded = json.loads(self._strip_code_fence(text))
            if not isinstance(decoded, dict):
                raise GeminiResponseError("Gemini JSON response must be an object.")
            required_fields = set(AIAnalysis.model_fields)
            if missing := required_fields - decoded.keys():
                raise GeminiResponseError(
                    f"Gemini response omitted required fields: {sorted(missing)}."
                )
            return AIAnalysis.model_validate(decoded)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise GeminiResponseError("Gemini returned invalid structured JSON.") from exc

    @staticmethod
    def _response_text(payload: Any) -> str:
        try:
            candidates = payload["candidates"]
            parts = candidates[0]["content"]["parts"]
            text = parts[0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise GeminiResponseError("Gemini response did not contain text content.") from exc
        if not isinstance(text, str) or not text.strip():
            raise GeminiResponseError("Gemini response text was empty.")
        return text.strip()

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        if not text.startswith("```"):
            return text
        lines = text.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
