"""Deterministic Digikala JSON-LD and product-card parser."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from price_analyst.collectors.sources.digikala.selectors import (
    PRICE_SELECTORS,
    PRODUCT_LINK_SELECTOR,
    SELLER_SELECTORS,
)
from price_analyst.collectors.sources.public_html import (
    as_text,
    canonical_url,
    is_type,
    parent_card,
    parse_availability,
    parse_condition,
    parse_json_ld_objects,
    parse_labeled_money,
    parse_last_numeric_money,
    parse_numeric_money,
    schema_brand,
    schema_price,
    schema_seller,
)
from price_analyst.domain.enums import Availability, Currency, Marketplace, OfferCondition
from price_analyst.domain.money import Money
from price_analyst.domain.offers import Offer, SearchCandidate
from price_analyst.domain.queries import NormalizedQuery
from price_analyst.normalization.query_normalizer import normalize_query, normalize_text


class DigikalaParser:
    def __init__(self, *, base_url: str = "https://www.digikala.com") -> None:
        self._base_url = base_url.rstrip("/")

    def parse_search_html(self, html: str, *, observed_at: datetime) -> list[SearchCandidate]:
        del observed_at
        soup = BeautifulSoup(html, "html.parser")
        candidates = self._json_ld_candidates(soup)
        candidates.extend(self._dom_candidates(soup))
        return self._deduplicate(candidates)

    def parse_product_html(
        self,
        html: str,
        *,
        product_url: str,
        observed_at: datetime,
    ) -> list[Offer]:
        soup = BeautifulSoup(html, "html.parser")
        product = self._product_schema(soup)
        url = canonical_url(product_url, self._base_url)
        source_id = self._product_id(url) or as_text(product.get("sku")) or "unknown"
        title = self._title(soup, product)
        if not title:
            return []
        normalized = self._attributes(title)
        offer = self._schema_offer(product.get("offers"))
        price = schema_price(offer, default_currency=Currency.UNKNOWN)
        if price is None:
            price = self._price_from_card(soup)
        if price is None:
            return []
        text = soup.get_text(" ", strip=True)
        return [
            self._make_offer(
                offer_id=f"digikala:{source_id}",
                source_offer_id=source_id,
                title=title,
                normalized=normalized,
                price=price,
                seller=schema_seller(offer) or self._seller(soup),
                product_url=url,
                image_url=self._image(product, soup),
                brand=schema_brand(product) or normalized.brand,
                availability=parse_availability(
                    as_text((offer or {}).get("availability")) or text
                ),
                condition=parse_condition(as_text((offer or {}).get("itemCondition")) or text),
                observed_at=observed_at,
                metadata={"collection_stage": "detail", "parser": "json_ld_or_dom"},
            )
        ]

    def _json_ld_candidates(self, soup: BeautifulSoup) -> list[SearchCandidate]:
        result: list[SearchCandidate] = []
        for item in parse_json_ld_objects(soup):
            if is_type(item, "ItemList"):
                entries = item.get("itemListElement", [])
                if isinstance(entries, list):
                    for entry in entries:
                        if isinstance(entry, dict) and isinstance(entry.get("item"), dict):
                            candidate = self._candidate_from_schema(entry["item"])
                            if candidate:
                                result.append(candidate)
            elif is_type(item, "Product"):
                candidate = self._candidate_from_schema(item)
                if candidate:
                    result.append(candidate)
        return result

    def _dom_candidates(self, soup: BeautifulSoup) -> list[SearchCandidate]:
        result: list[SearchCandidate] = []
        for anchor in soup.select(PRODUCT_LINK_SELECTOR):
            href = as_text(anchor.get("href"))
            if not href:
                continue
            url = canonical_url(urljoin(f"{self._base_url}/", href), self._base_url)
            source_id = self._product_id(url)
            title = self._title_from_anchor(anchor)
            if not source_id or not title:
                continue
            card = parent_card(anchor)
            text = card.get_text(" ", strip=True) if card else anchor.get_text(" ", strip=True)
            attributes = self._attributes(title)
            result.append(
                SearchCandidate(
                    source=Marketplace.DIGIKALA,
                    source_offer_id=source_id,
                    title=title,
                    url=url,
                    price=self._price_from_card(card or anchor),
                    seller=self._seller(card or anchor),
                    availability=parse_availability(text),
                    condition=parse_condition(text),
                    brand=attributes.brand,
                    model=attributes.model,
                    capacity=attributes.capacity,
                    metadata={"collection_stage": "search", "parser": "dom"},
                )
            )
        return result

    def _candidate_from_schema(self, item: dict[str, Any]) -> SearchCandidate | None:
        title = as_text(item.get("name"))
        raw_url = as_text(item.get("url") or item.get("@id"))
        if not title or not raw_url:
            return None
        url = canonical_url(urljoin(f"{self._base_url}/", raw_url), self._base_url)
        source_id = self._product_id(url) or as_text(item.get("sku"))
        if not source_id:
            return None
        attributes = self._attributes(title)
        offer = self._schema_offer(item.get("offers"))
        return SearchCandidate(
            source=Marketplace.DIGIKALA,
            source_offer_id=source_id,
            title=title,
            url=url,
            price=schema_price(offer, default_currency=Currency.UNKNOWN),
            seller=schema_seller(offer),
            availability=parse_availability(as_text((offer or {}).get("availability"))),
            condition=parse_condition(as_text((offer or {}).get("itemCondition"))),
            brand=schema_brand(item) or attributes.brand,
            model=attributes.model,
            capacity=attributes.capacity,
            metadata={"collection_stage": "search", "parser": "json_ld"},
        )

    def _product_schema(self, soup: BeautifulSoup) -> dict[str, Any]:
        for item in parse_json_ld_objects(soup):
            if is_type(item, "Product"):
                return item
        return {}

    @staticmethod
    def _schema_offer(offers: Any) -> dict[str, Any] | None:
        if isinstance(offers, list):
            return next((item for item in offers if isinstance(item, dict)), None)
        return offers if isinstance(offers, dict) else None

    def _title(self, soup: BeautifulSoup, product: dict[str, Any]) -> str | None:
        heading = soup.find("h1")
        return as_text(heading.get_text(" ", strip=True) if heading else None) or as_text(
            product.get("name")
        )

    def _title_from_anchor(self, anchor: Tag) -> str | None:
        image = anchor.find("img", alt=True)
        if image:
            title = as_text(image.get("alt"))
            if title:
                return title.replace("تصویر ", "", 1).strip()
        strong = anchor.find(["strong", "h2", "h3"])
        if strong:
            return as_text(strong.get_text(" ", strip=True))
        return as_text(anchor.get_text(" ", strip=True))

    def _price_from_card(self, card: Tag) -> Money | None:
        for selector in PRICE_SELECTORS:
            for element in card.select(selector):
                for value in (
                    as_text(element.get("data-price")),
                    as_text(element.get("content")),
                ):
                    parsed = parse_numeric_money(value, Currency.UNKNOWN) if value else None
                    if parsed:
                        return parsed
                parsed = parse_labeled_money(
                    element.get_text(" ", strip=True),
                    default_currency=Currency.UNKNOWN,
                )
                if parsed:
                    return parsed
                parsed = parse_last_numeric_money(
                    element.get_text(" ", strip=True),
                    default_currency=Currency.UNKNOWN,
                )
                if parsed:
                    return parsed
        text = card.get_text(" ", strip=True)
        return parse_labeled_money(text, default_currency=Currency.UNKNOWN) or (
            parse_last_numeric_money(
                text,
                default_currency=Currency.UNKNOWN,
            )
        )

    def _seller(self, card: Tag) -> str | None:
        for selector in SELLER_SELECTORS:
            element = card.select_one(selector)
            if element:
                return as_text(element.get("data-seller")) or as_text(
                    element.get_text(" ", strip=True)
                )
        return None

    def _image(self, product: dict[str, Any], soup: BeautifulSoup) -> str | None:
        image = product.get("image")
        if isinstance(image, list) and image:
            return as_text(image[0])
        if isinstance(image, str):
            return image
        first = soup.select_one("img[src], img[data-src]")
        return as_text(first.get("src") or first.get("data-src") if first else None)

    def _attributes(self, title: str) -> NormalizedQuery:
        try:
            return normalize_query(title)
        except ValueError:
            normalized = normalize_text(title)
            return NormalizedQuery(
                original=title,
                normalized_text=normalized,
                variants=[normalized],
            )

    def _make_offer(
        self,
        *,
        offer_id: str,
        source_offer_id: str,
        title: str,
        normalized: NormalizedQuery,
        price: Money,
        seller: str | None,
        product_url: str,
        image_url: str | None,
        brand: str | None,
        availability: Availability,
        condition: OfferCondition,
        observed_at: datetime,
        metadata: dict[str, str],
    ) -> Offer:
        return Offer(
            offer_id=offer_id,
            source=Marketplace.DIGIKALA,
            source_offer_id=source_offer_id,
            title=title,
            normalized_title=normalize_text(title),
            price=price,
            seller=seller,
            product_url=product_url,
            image_url=image_url,
            availability=availability,
            condition=condition,
            brand=brand,
            model=normalized.model,
            capacity=normalized.capacity,
            observed_at=observed_at,
            details_fetched=True,
            metadata=metadata,
        )

    @staticmethod
    def _product_id(url: str) -> str | None:
        match = re.search(r"/product/dkp-(\d+)", url)
        return match.group(1) if match else None

    @staticmethod
    def _deduplicate(candidates: list[SearchCandidate]) -> list[SearchCandidate]:
        seen: set[str] = set()
        result: list[SearchCandidate] = []
        for candidate in candidates:
            if candidate.source_offer_id in seen:
                continue
            seen.add(candidate.source_offer_id)
            result.append(candidate)
        return result
