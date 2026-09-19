"""Deterministic Torob JSON-LD and HTML parser."""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from price_analyst.collectors.sources.torob.normalizer import (
    canonical_url,
    currency_from_label,
    parse_availability,
    parse_condition,
    parse_money,
    parse_numeric_money,
    product_id_from_url,
    redirect_id,
)
from price_analyst.collectors.sources.torob.selectors import (
    JSON_LD_SELECTOR,
    PRODUCT_LINK_SELECTOR,
    REDIRECT_LINK_SELECTOR,
    SHOP_LINK_SELECTOR,
)
from price_analyst.domain.enums import Availability, Currency, Marketplace, OfferCondition
from price_analyst.domain.money import Money
from price_analyst.domain.offers import Offer, SearchCandidate
from price_analyst.domain.queries import NormalizedQuery
from price_analyst.normalization.query_normalizer import normalize_query, normalize_text


class TorobParser:
    """Parser with a structured-data-first strategy and a small DOM fallback."""

    def __init__(self, *, base_url: str = "https://torob.com") -> None:
        self._base_url = base_url.rstrip("/")

    def parse_search_html(self, html: str, *, observed_at: datetime) -> list[SearchCandidate]:
        del observed_at
        soup = BeautifulSoup(html, "html.parser")
        candidates = self._search_json_ld(soup)
        candidates.extend(self._search_dom(soup))
        return self._deduplicate_candidates(candidates)

    def parse_product_html(
        self,
        html: str,
        *,
        product_url: str,
        observed_at: datetime,
    ) -> list[Offer]:
        soup = BeautifulSoup(html, "html.parser")
        product_schema = self._product_schema(soup)
        canonical_product_url = canonical_url(product_url, self._base_url)
        product_id = product_id_from_url(canonical_product_url) or str(
            product_schema.get("sku") or "unknown"
        )
        title = self._product_title(soup, product_schema)
        if not title:
            return []

        normalized = self._normalized_attributes(title)
        image_url = self._image_url(product_schema, soup)
        brand = self._brand(product_schema) or normalized.brand
        seller_offers = self._seller_offers(
            soup,
            title=title,
            normalized=normalized,
            product_url=canonical_product_url,
            image_url=image_url,
            brand=brand,
            observed_at=observed_at,
        )
        if seller_offers:
            return seller_offers
        return self._schema_offers(
            product_schema,
            product_id=product_id,
            title=title,
            normalized=normalized,
            product_url=canonical_product_url,
            image_url=image_url,
            brand=brand,
            observed_at=observed_at,
        )

    def _search_json_ld(self, soup: BeautifulSoup) -> list[SearchCandidate]:
        candidates: list[SearchCandidate] = []
        for payload in self._json_ld_objects(soup):
            if self._is_type(payload, "ItemList"):
                items = payload.get("itemListElement", [])
                if isinstance(items, list):
                    for entry in items:
                        if not isinstance(entry, dict):
                            continue
                        item = entry.get("item", entry)
                        if isinstance(item, dict):
                            candidate = self._candidate_from_schema(item)
                            if candidate:
                                candidates.append(candidate)
            elif self._is_type(payload, "Product"):
                candidate = self._candidate_from_schema(payload)
                if candidate:
                    candidates.append(candidate)
        return candidates

    def _search_dom(self, soup: BeautifulSoup) -> list[SearchCandidate]:
        candidates: list[SearchCandidate] = []
        for anchor in soup.select(PRODUCT_LINK_SELECTOR):
            href = self._as_text(anchor.get("href"))
            if not href:
                continue
            url = canonical_url(urljoin(f"{self._base_url}/", href), self._base_url)
            source_id = product_id_from_url(url)
            if not source_id:
                continue
            title = self._anchor_title(anchor)
            if not title:
                continue
            container = self._search_container(anchor)
            text = (
                container.get_text(" ", strip=True)
                if container
                else anchor.get_text(" ", strip=True)
            )
            candidates.append(
                SearchCandidate(
                    source=Marketplace.TOROB,
                    source_offer_id=source_id,
                    title=title,
                    url=url,
                    price=parse_money(text),
                    availability=Availability.UNKNOWN,
                    condition=OfferCondition.UNKNOWN,
                    metadata={"collection_stage": "search", "parser": "dom"},
                )
            )
        return candidates

    def _candidate_from_schema(self, item: dict[str, Any]) -> SearchCandidate | None:
        name = self._as_text(item.get("name"))
        raw_url = self._as_text(item.get("url") or item.get("@id"))
        if not name or not raw_url:
            return None
        url = canonical_url(urljoin(f"{self._base_url}/", raw_url), self._base_url)
        source_id = product_id_from_url(url) or self._as_text(item.get("sku"))
        if not source_id:
            return None
        offer = self._first_schema_offer(item.get("offers"))
        return SearchCandidate(
            source=Marketplace.TOROB,
            source_offer_id=source_id,
            title=name,
            url=url,
            price=self._schema_price(offer),
            seller=self._schema_seller(offer),
            availability=parse_availability(self._as_text((offer or {}).get("availability"))),
            condition=parse_condition(self._as_text((offer or {}).get("itemCondition"))),
            brand=self._brand(item),
            metadata={"collection_stage": "search", "parser": "json_ld"},
        )

    def _seller_offers(
        self,
        soup: BeautifulSoup,
        *,
        title: str,
        normalized: NormalizedQuery,
        product_url: str,
        image_url: str | None,
        brand: str | None,
        observed_at: datetime,
    ) -> list[Offer]:
        offers: list[Offer] = []
        seen: set[str] = set()
        for index, anchor in enumerate(soup.select(REDIRECT_LINK_SELECTOR)):
            href = self._as_text(anchor.get("href"))
            if not href:
                continue
            redirect_url = urljoin(f"{self._base_url}/", href)
            container = self._offer_container(anchor)
            text = (
                container.get_text(" ", strip=True)
                if container
                else anchor.get_text(" ", strip=True)
            )
            price = parse_money(text)
            if price is None:
                continue
            offer_id = f"torob:{redirect_id(redirect_url, str(index))}"
            if offer_id in seen:
                continue
            seen.add(offer_id)
            shop_link = container.select_one(SHOP_LINK_SELECTOR) if container else None
            seller = self._as_text(shop_link.get_text(" ", strip=True)) if shop_link else None
            offers.append(
                self._make_offer(
                    offer_id=offer_id,
                    source_offer_id=offer_id.removeprefix("torob:"),
                    title=title,
                    normalized=normalized,
                    price=price,
                    seller=seller,
                    product_url=product_url,
                    image_url=image_url,
                    brand=brand,
                    availability=parse_availability(text),
                    condition=parse_condition(text),
                    observed_at=observed_at,
                    metadata={
                        "collection_stage": "detail",
                        "parser": "dom",
                        "seller_link_url": redirect_url,
                    },
                )
            )
        return offers

    def _schema_offers(
        self,
        product: dict[str, Any],
        *,
        product_id: str,
        title: str,
        normalized: NormalizedQuery,
        product_url: str,
        image_url: str | None,
        brand: str | None,
        observed_at: datetime,
    ) -> list[Offer]:
        raw_offers = product.get("offers")
        offer_records: list[dict[str, Any]] = []
        if isinstance(raw_offers, list):
            offer_records = [item for item in raw_offers if isinstance(item, dict)]
        elif isinstance(raw_offers, dict):
            nested = raw_offers.get("offers")
            if isinstance(nested, list):
                offer_records = [item for item in nested if isinstance(item, dict)]
            elif raw_offers.get("@type") == "Offer":
                offer_records = [raw_offers]

        offers: list[Offer] = []
        for index, record in enumerate(offer_records):
            price = self._schema_price(record)
            if price is None:
                continue
            source_offer_id = self._as_text(record.get("sku") or record.get("@id"))
            if not source_offer_id:
                source_offer_id = f"{product_id}:schema:{index}"
            offers.append(
                self._make_offer(
                    offer_id=f"torob:{source_offer_id}",
                    source_offer_id=source_offer_id,
                    title=title,
                    normalized=normalized,
                    price=price,
                    seller=self._schema_seller(record),
                    product_url=product_url,
                    image_url=image_url,
                    brand=brand,
                    availability=parse_availability(self._as_text(record.get("availability"))),
                    condition=parse_condition(self._as_text(record.get("itemCondition"))),
                    observed_at=observed_at,
                    metadata={"collection_stage": "detail", "parser": "json_ld"},
                )
            )

        if offers:
            return offers
        if not isinstance(raw_offers, dict):
            return []
        low_price = raw_offers.get("lowPrice")
        if low_price is None:
            return []
        currency = currency_from_label(
            self._as_text(raw_offers.get("priceCurrency")),
            Currency.IRR,
        )
        price = parse_numeric_money(low_price, currency)
        if price is None:
            return []
        return [
            self._make_offer(
                offer_id=f"torob:{product_id}:aggregate",
                source_offer_id=f"{product_id}:aggregate",
                title=title,
                normalized=normalized,
                price=price,
                seller=None,
                product_url=product_url,
                image_url=image_url,
                brand=brand,
                availability=Availability.UNKNOWN,
                condition=OfferCondition.UNKNOWN,
                observed_at=observed_at,
                metadata={
                    "collection_stage": "detail",
                    "parser": "json_ld",
                    "aggregate": "true",
                },
            )
        ]

    def _make_offer(
        self,
        *,
        offer_id: str,
        source_offer_id: str,
        title: str,
        normalized: NormalizedQuery,
        price: Money | None,
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
            source=Marketplace.TOROB,
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

    def _product_schema(self, soup: BeautifulSoup) -> dict[str, Any]:
        for payload in self._json_ld_objects(soup):
            if self._is_type(payload, "Product"):
                return payload
        return {}

    def _product_title(self, soup: BeautifulSoup, product: dict[str, Any]) -> str | None:
        heading = soup.find("h1")
        heading_text = heading.get_text(" ", strip=True) if heading else None
        return self._as_text(heading_text) or self._as_text(product.get("name"))

    def _image_url(self, product: dict[str, Any], soup: BeautifulSoup) -> str | None:
        image = product.get("image")
        if isinstance(image, list) and image:
            return self._as_text(image[0])
        if isinstance(image, str):
            return image
        first = soup.select_one("img[src]")
        return self._as_text(first.get("src") if first else None)

    def _brand(self, item: dict[str, Any]) -> str | None:
        brand = item.get("brand")
        if isinstance(brand, dict):
            return self._as_text(brand.get("name"))
        return self._as_text(brand)

    def _normalized_attributes(self, title: str) -> NormalizedQuery:
        try:
            return normalize_query(title)
        except ValueError:
            normalized_title = normalize_text(title)
            return NormalizedQuery(
                original=title,
                normalized_text=normalized_title,
                variants=[normalized_title],
            )

    def _first_schema_offer(self, offers: Any) -> dict[str, Any] | None:
        if isinstance(offers, list):
            return next((item for item in offers if isinstance(item, dict)), None)
        return offers if isinstance(offers, dict) else None

    def _schema_price(self, offer: dict[str, Any] | None) -> Money | None:
        if not offer:
            return None
        currency = currency_from_label(self._as_text(offer.get("priceCurrency")), Currency.IRR)
        value = offer.get("price")
        if value is None:
            value = offer.get("lowPrice")
        return parse_numeric_money(value, currency)

    def _schema_seller(self, offer: dict[str, Any] | None) -> str | None:
        if not offer:
            return None
        seller = offer.get("seller")
        if isinstance(seller, dict):
            return self._as_text(seller.get("name"))
        return self._as_text(seller)

    def _anchor_title(self, anchor: Tag) -> str | None:
        aria = self._as_text(anchor.get("aria-label"))
        if aria:
            return aria
        image = anchor.find("img", alt=True)
        alt = self._as_text(image.get("alt") if image else None)
        if alt:
            return alt.replace("تصویر ", "", 1).strip()
        return self._as_text(anchor.get_text(" ", strip=True))

    def _search_container(self, anchor: Tag) -> Tag | None:
        for parent in anchor.parents:
            if not isinstance(parent, Tag):
                continue
            if parent.name in {"article", "li"}:
                return parent
            if parent.select_one(REDIRECT_LINK_SELECTOR):
                return parent
        return None

    def _offer_container(self, anchor: Tag) -> Tag | None:
        for parent in anchor.parents:
            if not isinstance(parent, Tag):
                continue
            if parent.name in {"article", "li"}:
                return parent
            if parent.select_one(SHOP_LINK_SELECTOR) and parent.get_text(" ", strip=True):
                return parent
        return self._search_container(anchor)

    def _json_ld_objects(self, soup: BeautifulSoup) -> Iterator[dict[str, Any]]:
        for script in soup.select(JSON_LD_SELECTOR):
            raw = script.string or script.get_text()
            try:
                payload = json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                continue
            yield from self._flatten_json_ld(payload)

    def _flatten_json_ld(self, payload: Any) -> Iterator[dict[str, Any]]:
        if isinstance(payload, list):
            for item in payload:
                yield from self._flatten_json_ld(item)
        elif isinstance(payload, dict):
            graph = payload.get("@graph")
            if isinstance(graph, list):
                for item in graph:
                    yield from self._flatten_json_ld(item)
            else:
                yield payload

    def _is_type(self, payload: dict[str, Any], expected: str) -> bool:
        value = payload.get("@type")
        return expected in value if isinstance(value, list) else value == expected

    def _deduplicate_candidates(self, candidates: list[SearchCandidate]) -> list[SearchCandidate]:
        by_id: dict[str, SearchCandidate] = {}
        order: list[str] = []
        for candidate in candidates:
            key = candidate.source_offer_id
            if key not in by_id:
                by_id[key] = candidate
                order.append(key)
                continue
            current = by_id[key]
            if current.price is None and candidate.price is not None:
                by_id[key] = candidate
        return [by_id[key] for key in order]

    @staticmethod
    def _as_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
