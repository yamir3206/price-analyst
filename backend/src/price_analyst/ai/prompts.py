"""Versioned Gemini prompt metadata and compact-input rendering."""

from __future__ import annotations

import json

from price_analyst.domain.ai_analysis import CompactAnalysisDataset

ANALYSIS_PROMPT_VERSION = "price-analysis-v2"

SYSTEM_INSTRUCTION = (
    "Optional deterministic-dataset interpreter. Do not browse, invent, or\n"
    "recalculate. Separate facts, inferences, and uncertainties. Return only\n"
    "the requested JSON and use only supplied offer IDs."
)

USER_INSTRUCTION = (
    "Use this dataset as-is. Return JSON with these fields: summary,\n"
    "market_assessment, cheap_offers, expensive_offers,\n"
    "potential_opportunities, risks, missing_information, facts, inferences,\n"
    "uncertainties, confidence. Offer arrays contain IDs. Facts are observed;\n"
    "inferences are interpretations; uncertainties are missing or stale data.\n\n"
    "Dataset:\n"
)


def render_user_prompt(dataset: CompactAnalysisDataset) -> str:
    payload = json.dumps(
        dataset.model_dump(
            mode="json",
            exclude_none=True,
            exclude={"dataset_hash"},
        ),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"{USER_INSTRUCTION}{payload}"
