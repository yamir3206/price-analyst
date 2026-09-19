"""Optional AI client boundary used by the later Gemini implementation."""

from price_analyst.domain.ai_analysis import AIAnalysis, CompactAnalysisDataset


class GeminiUnavailableError(RuntimeError):
    """Raised when AI analysis is deliberately disabled or unavailable."""


class DisabledGeminiClient:
    """Safe default: deterministic search never depends on Gemini."""

    async def analyze(self, dataset: CompactAnalysisDataset) -> AIAnalysis:
        del dataset
        raise GeminiUnavailableError("Gemini analysis is not configured")
