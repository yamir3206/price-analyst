"""Deterministic candidate ranking used before detail fetches."""

from __future__ import annotations

from price_analyst.domain.offers import SearchCandidate
from price_analyst.domain.queries import NormalizedQuery
from price_analyst.normalization.query_normalizer import normalize_text


def candidate_relevance(query: NormalizedQuery, candidate: SearchCandidate) -> float:
    """Score token and explicit-attribute overlap without semantic inference."""

    query_tokens = set(normalize_text(query.normalized_text).split())
    title_tokens = set(normalize_text(candidate.title).split())
    if not query_tokens:
        return 0.0

    score = len(query_tokens & title_tokens) / len(query_tokens)
    if query.brand and candidate.brand:
        if normalize_text(candidate.brand) == normalize_text(query.brand):
            score += 0.2
    elif query.brand and normalize_text(query.brand) in title_tokens:
        score += 0.1
    compact_title = normalize_text(candidate.title).replace(" ", "")
    if query.capacity and query.capacity.lower() in compact_title:
        score += 0.1
    return min(score, 1.0)


def rank_candidates(
    query: NormalizedQuery,
    candidates: list[SearchCandidate],
    *,
    limit: int,
) -> list[SearchCandidate]:
    """Return a stable bounded selection for detail fetching."""

    ranked = sorted(
        enumerate(candidates),
        key=lambda item: (-candidate_relevance(query, item[1]), item[0]),
    )
    return [candidate for _, candidate in ranked[:limit]]
