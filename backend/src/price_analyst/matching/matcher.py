"""Deterministic matching of normalized queries to normalized offers."""

from __future__ import annotations

import re
from collections.abc import Iterable

from price_analyst.domain.local_analysis import OfferMatch
from price_analyst.domain.offers import Offer
from price_analyst.domain.queries import NormalizedQuery
from price_analyst.normalization.query_normalizer import normalize_text

_MATCH_THRESHOLD = 0.55
_STOP_WORDS = {
    "a",
    "and",
    "buy",
    "for",
    "gb",
    "گیگ",
    "گیگابایت",
    "گوشی",
    "موبایل",
    "mobile",
    "phone",
    "قیمت",
    "خرید",
    "the",
}
_BRAND_ALIASES = {
    "سامسونگ": "samsung",
    "samsung": "samsung",
    "اپل": "apple",
    "apple": "apple",
    "آیفون": "iphone",
    "ایفون": "iphone",
    "iphone": "iphone",
    "شیائومی": "xiaomi",
    "شیاومی": "xiaomi",
    "xiaomi": "xiaomi",
    "هواوی": "huawei",
    "huawei": "huawei",
    "لنوو": "lenovo",
    "lenovo": "lenovo",
}


def _tokens(value: str | None) -> set[str]:
    if not value:
        return set()
    normalized = normalize_text(value)
    return {token for token in normalized.split() if token not in _STOP_WORDS}


def _canonical_brand(value: str | None) -> str | None:
    if not value:
        return None
    normalized = normalize_text(value)
    return _BRAND_ALIASES.get(normalized, normalized)


def _compact(value: str | None) -> str | None:
    if not value:
        return None
    return re.sub(r"\s+", "", normalize_text(value)).lower() or None


def _offer_tokens(offer: Offer) -> set[str]:
    values = [offer.title, offer.brand, offer.model, offer.capacity]
    values.extend(offer.specifications.values())
    result: set[str] = set()
    for value in values:
        result.update(_tokens(value))
    return result


def match_offer(
    query: NormalizedQuery,
    offer: Offer,
    *,
    threshold: float = _MATCH_THRESHOLD,
) -> OfferMatch:
    """Score explicit token/attribute evidence and never infer missing fields."""

    query_tokens = _tokens(query.normalized_text)
    title_tokens = _tokens(offer.title)
    offer_tokens = _offer_tokens(offer)
    matched_fields: list[str] = []
    mismatched_fields: list[str] = []
    missing_fields: list[str] = []

    if query_tokens:
        overlap = len(query_tokens & offer_tokens) / len(query_tokens)
    else:
        overlap = 0.0

    score = 0.60 * overlap
    query_brand = _canonical_brand(query.brand)
    offer_brand = _canonical_brand(offer.brand)
    if query_brand:
        if offer_brand:
            if offer_brand == query_brand:
                score += 0.20
                matched_fields.append("brand")
            else:
                score -= 0.35
                mismatched_fields.append("brand")
        elif query_brand in {_canonical_brand(token) for token in title_tokens}:
            score += 0.10
            matched_fields.append("brand_from_title")
        else:
            missing_fields.append("brand")

    query_capacity = _compact(query.capacity)
    offer_capacity = _compact(offer.capacity)
    if query_capacity:
        capacity_in_title = query_capacity in {_compact(token) for token in title_tokens}
        if offer_capacity == query_capacity or capacity_in_title:
            score += 0.15
            matched_fields.append("capacity")
        elif offer_capacity:
            score -= 0.30
            mismatched_fields.append("capacity")
        else:
            missing_fields.append("capacity")

    query_model_tokens = _tokens(query.model)
    if query_model_tokens:
        model_overlap = len(query_model_tokens & offer_tokens) / len(query_model_tokens)
        if model_overlap >= 0.5:
            score += 0.15 * model_overlap
            matched_fields.append("model")
        else:
            missing_fields.append("model")

    if query_tokens <= title_tokens:
        matched_fields.append("title_tokens")
        score += 0.10

    score = min(1.0, max(0.0, score))
    if mismatched_fields:
        score = min(score, 0.49)
    is_match = score >= threshold and not mismatched_fields
    if not is_match and not mismatched_fields and not missing_fields:
        missing_fields.append("matching_evidence")
    return OfferMatch(
        offer_id=offer.offer_id,
        score=round(score, 6),
        is_match=is_match,
        matched_fields=matched_fields,
        mismatched_fields=mismatched_fields,
        missing_fields=missing_fields,
    )


def match_offers(
    query: NormalizedQuery,
    offers: Iterable[Offer],
    *,
    threshold: float = _MATCH_THRESHOLD,
) -> list[OfferMatch]:
    """Return stable match decisions in input order."""

    return [match_offer(query, offer, threshold=threshold) for offer in offers]


__all__ = ["match_offer", "match_offers"]
