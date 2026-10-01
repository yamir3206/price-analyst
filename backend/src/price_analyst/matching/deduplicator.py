"""Deterministic duplicate removal and cross-source product grouping."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from price_analyst.domain.local_analysis import DeduplicationGroup
from price_analyst.domain.offers import Offer
from price_analyst.normalization.query_normalizer import normalize_text

_STOP_WORDS = {
    "a",
    "and",
    "gb",
    "گیگ",
    "گیگابایت",
    "گوشی",
    "موبایل",
    "mobile",
    "phone",
    "the",
}
_BRAND_WORDS = {
    "apple",
    "اپل",
    "iphone",
    "آیفون",
    "ایفون",
    "samsung",
    "سامسونگ",
    "xiaomi",
    "شیائومی",
    "شیاومی",
    "huawei",
    "هواوی",
    "lenovo",
    "لنوو",
}
_COLOR_WORDS = {
    "black",
    "مشکی",
    "سیاه",
    "white",
    "سفید",
    "gray",
    "grey",
    "طوسی",
    "خاکستری",
    "blue",
    "آبی",
    "ابی",
    "red",
    "قرمز",
    "green",
    "سبز",
    "purple",
    "بنفش",
}


@dataclass(frozen=True, slots=True)
class DeduplicationResult:
    """Unique source records plus product-equivalence groups."""

    unique_offers: list[Offer]
    groups: list[DeduplicationGroup]
    group_by_offer_id: dict[str, str]


def _compact(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", "", normalize_text(value)).lower()


def _tokens(value: str | None) -> set[str]:
    if not value:
        return set()
    return {
        token
        for token in normalize_text(value).split()
        if token not in _STOP_WORDS and token not in _BRAND_WORDS and token not in _COLOR_WORDS
    }


def _canonical_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "", ""))


def product_identity_key(offer: Offer) -> str:
    """Build a conservative product key while ignoring seller and price."""

    brand = normalize_text(offer.brand or "")
    capacity = _compact(offer.capacity)
    model_tokens = _tokens(offer.model)
    title_tokens = _tokens(offer.title)
    product_tokens = model_tokens or title_tokens
    if not product_tokens:
        product_tokens = set(normalize_text(offer.normalized_title).split())
    title_key = " ".join(sorted(product_tokens))
    return f"brand={brand}|capacity={capacity}|product={title_key}"


def _exact_fingerprint(offer: Offer) -> str:
    price = ""
    if offer.price is not None:
        price = f"{offer.price.currency.value}:{offer.price.amount}"
    return "|".join(
        (
            offer.source.value,
            offer.source_offer_id,
            normalize_text(offer.seller or ""),
            price,
            _canonical_url(offer.product_url),
        )
    )


def _preferred_offer(current: Offer, candidate: Offer) -> Offer:
    current_rank = (not current.details_fetched, current.price is None, current.offer_id)
    candidate_rank = (not candidate.details_fetched, candidate.price is None, candidate.offer_id)
    return candidate if candidate_rank < current_rank else current


def deduplicate_offers(offers: list[Offer]) -> DeduplicationResult:
    """Remove exact repeated records and retain all product-comparison members.

    Offers from different marketplaces or sellers are not discarded merely
    because they describe the same product. They are grouped so callers can
    compare them while the full deterministic records remain available.
    """

    unique_by_fingerprint: dict[str, Offer] = {}
    fingerprint_order: list[str] = []
    members_by_key: dict[str, list[str]] = {}
    offer_by_id = {offer.offer_id: offer for offer in offers}
    for offer in offers:
        fingerprint = _exact_fingerprint(offer)
        if fingerprint not in unique_by_fingerprint:
            fingerprint_order.append(fingerprint)
            unique_by_fingerprint[fingerprint] = offer
        else:
            unique_by_fingerprint[fingerprint] = _preferred_offer(
                unique_by_fingerprint[fingerprint], offer
            )
        members_by_key.setdefault(product_identity_key(offer), []).append(offer.offer_id)

    unique_offers = [unique_by_fingerprint[fingerprint] for fingerprint in fingerprint_order]
    groups: list[DeduplicationGroup] = []
    group_by_offer_id: dict[str, str] = {}
    for canonical_key in sorted(members_by_key):
        member_ids = sorted(set(members_by_key[canonical_key]))
        representative = min(
            (offer_by_id[offer_id] for offer_id in member_ids),
            key=lambda offer: (
                not offer.details_fetched,
                offer.price is None,
                offer.offer_id,
            ),
        )
        digest = hashlib.sha256(canonical_key.encode("utf-8")).hexdigest()[:16]
        group_id = f"product:{digest}"
        groups.append(
            DeduplicationGroup(
                group_id=group_id,
                canonical_key=canonical_key,
                representative_offer_id=representative.offer_id,
                offer_ids=member_ids,
            )
        )
        for offer_id in member_ids:
            group_by_offer_id[offer_id] = group_id

    return DeduplicationResult(
        unique_offers=unique_offers,
        groups=groups,
        group_by_offer_id=group_by_offer_id,
    )
