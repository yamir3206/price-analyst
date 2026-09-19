"""Orchestration for deterministic local analysis."""

from __future__ import annotations

from dataclasses import dataclass

from price_analyst.analysis.charts import build_price_charts
from price_analyst.analysis.classification import classify_offers
from price_analyst.analysis.opportunities import calculate_opportunities
from price_analyst.analysis.statistics import primary_statistics, statistics_by_currency
from price_analyst.domain.enums import Availability
from price_analyst.domain.local_analysis import LocalAnalysis
from price_analyst.domain.offers import Offer
from price_analyst.domain.queries import NormalizedQuery
from price_analyst.domain.statistics import PriceStatistics
from price_analyst.matching.deduplicator import deduplicate_offers
from price_analyst.matching.matcher import match_offers


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Analysis envelope plus the legacy single-statistics projection."""

    analysis: LocalAnalysis
    primary_statistics: PriceStatistics | None


def analyze_offers(
    query: NormalizedQuery,
    offers: list[Offer],
    *,
    match_threshold: float = 0.55,
    include_unknown_currency: bool = False,
    max_opportunities: int = 20,
) -> AnalysisResult:
    """Analyze full offers without removing them from the returned snapshot."""

    if not 0 <= match_threshold <= 1:
        raise ValueError("match_threshold must be between zero and one")
    deduplication = deduplicate_offers(offers)
    matches = match_offers(query, offers, threshold=match_threshold)
    match_by_id = {match.offer_id: match for match in matches}
    comparable_unique_offers = [
        offer
        for offer in deduplication.unique_offers
        if match_by_id.get(offer.offer_id, None)
        and match_by_id[offer.offer_id].is_match
        and offer.availability is not Availability.OUT_OF_STOCK
    ]
    reports = statistics_by_currency(
        comparable_unique_offers,
        include_unknown=include_unknown_currency,
    )
    classifications = classify_offers(offers, matches, reports)
    charts = build_price_charts(
        offers,
        matches,
        classifications,
        deduplication.groups,
        reports,
    )
    opportunities = calculate_opportunities(
        deduplication.unique_offers,
        matches,
        classifications,
        reports,
        max_results=max_opportunities,
    )
    analysis = LocalAnalysis(
        matches=matches,
        deduplication_groups=deduplication.groups,
        classifications=classifications,
        statistics_by_currency=reports,
        price_charts=charts,
        opportunities=opportunities,
    )
    return AnalysisResult(
        analysis=analysis,
        primary_statistics=primary_statistics(reports),
    )
