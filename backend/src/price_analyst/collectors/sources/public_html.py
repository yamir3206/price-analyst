"""Shared safe helpers for independent public HTML adapters."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup, Tag

from price_analyst.domain.enums import Availability, Currency, OfferCondition
from price_analyst.domain.money import Money

_DIGITS = str.maketrans(
    {
        "۰": "0",
        "۱": "1",
        "۲": "2",
        "۳": "3",
        "۴": "4",
        "۵": "5",
        "۶": "6",
        "۷": "7",
        "۸": "8",
        "۹": "9",
        "٠": "0",
        "١": "1",
        "٢": "2",
        "٣": "3",
        "٤": "4",
        "٥": "5",
        "٦": "6",
        "٧": "7",
        "٨": "8",
        "٩": "9",
    }
)
_PRICE_LABEL = re.compile(
    r"(?P<number>[0-9۰-۹٠-٩][0-9۰-۹٠-٩\s.,٬٫]*)\s*"
    r"(?P<currency>تومان|تومن|ریال|rial|toman|irr|irt)",
    re.IGNORECASE,
)


def normalize_digits(value: str) -> str:
    return value.translate(_DIGITS)


def as_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def canonical_url(url: str, base_url: str) -> str:
    absolute = urljoin(f"{base_url.rstrip('/')}/", url)
    parts = urlsplit(absolute)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def parse_json_ld_objects(soup: BeautifulSoup) -> Iterator[dict[str, Any]]:
    for script in soup.select('script[type="application/ld+json"]'):
        raw = script.string or script.get_text()
        try:
            payload = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            continue
        yield from flatten_json_ld(payload)


def flatten_json_ld(payload: Any) -> Iterator[dict[str, Any]]:
    if isinstance(payload, list):
        for item in payload:
            yield from flatten_json_ld(item)
    elif isinstance(payload, dict):
        graph = payload.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                yield from flatten_json_ld(item)
        else:
            yield payload


def is_type(payload: dict[str, Any], expected: str) -> bool:
    value = payload.get("@type")
    return expected in value if isinstance(value, list) else value == expected


def schema_brand(item: dict[str, Any]) -> str | None:
    brand = item.get("brand")
    if isinstance(brand, dict):
        return as_text(brand.get("name"))
    return as_text(brand)


def schema_seller(offer: dict[str, Any] | None) -> str | None:
    if not offer:
        return None
    seller = offer.get("seller")
    if isinstance(seller, dict):
        return as_text(seller.get("name"))
    return as_text(seller)


def currency_from_label(label: str | None, default: Currency = Currency.UNKNOWN) -> Currency:
    normalized = normalize_digits(label or "").strip().lower()
    if normalized in {"ریال", "rial", "irr"}:
        return Currency.IRR
    if normalized in {"تومان", "تومن", "toman", "irt"}:
        return Currency.IRT
    return default


def _digits_only(value: str) -> int | None:
    digits = re.sub(r"\D", "", normalize_digits(value))
    return int(digits) if digits else None


def parse_numeric_money(value: object, currency: Currency) -> Money | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return Money(amount=value, currency=currency) if value >= 0 else None
    if isinstance(value, float):
        if value < 0:
            return None
        rounded_amount = int(Decimal(str(value)).to_integral_value(ROUND_HALF_UP))
        return Money(amount=rounded_amount, currency=currency)
    raw = normalize_digits(str(value)).strip()
    if not raw:
        return None
    amount: int | None
    try:
        if re.fullmatch(r"\d+(?:\.\d+)?", raw):
            amount = int(Decimal(raw).to_integral_value(ROUND_HALF_UP))
        else:
            amount = _digits_only(raw)
    except (InvalidOperation, ValueError):
        return None
    if amount is None or amount < 0:
        return None
    return Money(amount=amount, currency=currency)


def parse_labeled_money(
    text: str | None,
    *,
    default_currency: Currency = Currency.UNKNOWN,
) -> Money | None:
    if not text:
        return None
    match = _PRICE_LABEL.search(normalize_digits(text))
    if not match:
        return None
    amount = _digits_only(match.group("number"))
    if amount is None:
        return None
    return Money(
        amount=amount,
        currency=currency_from_label(match.group("currency"), default_currency),
    )


def parse_last_numeric_money(
    text: str | None,
    *,
    default_currency: Currency = Currency.UNKNOWN,
) -> Money | None:
    """Use the last grouped integer in a bounded card when no label exists."""

    if not text:
        return None
    normalized = normalize_digits(text)
    values = re.findall(r"[0-9]+(?:[٬,][0-9]{3})+", normalized)
    if not values:
        return None
    return parse_numeric_money(values[-1].replace("٬", ""), default_currency)


def schema_price(
    offer: dict[str, Any] | None,
    *,
    default_currency: Currency = Currency.UNKNOWN,
) -> Money | None:
    if not offer:
        return None
    currency = currency_from_label(as_text(offer.get("priceCurrency")), default_currency)
    value = offer.get("price")
    if value is None:
        value = offer.get("lowPrice")
    return parse_numeric_money(value, currency)


def parse_availability(value: str | None) -> Availability:
    normalized = normalize_digits(value or "").lower()
    if any(token in normalized for token in ("outofstock", "out_of_stock", "ناموجود")):
        return Availability.OUT_OF_STOCK
    if any(token in normalized for token in ("instock", "in_stock", "موجود")):
        return Availability.IN_STOCK
    return Availability.UNKNOWN


def parse_condition(value: str | None) -> OfferCondition:
    normalized = normalize_digits(value or "").lower()
    if any(token in normalized for token in ("used", "کارکرده", "استوک", "دست دوم", "در حد نو")):
        return OfferCondition.USED
    if any(token in normalized for token in ("refurbished", "refurb", "بازسازی")):
        return OfferCondition.REFURBISHED
    if any(token in normalized for token in ("new", "نو")):
        return OfferCondition.NEW
    return OfferCondition.UNKNOWN


def parent_card(element: Tag) -> Tag | None:
    for parent in element.parents:
        if not isinstance(parent, Tag):
            continue
        if parent.name in {"article", "li"}:
            return parent
        raw_classes = parent.get("class")
        classes = (
            " ".join(str(item) for item in raw_classes)
            if isinstance(raw_classes, list)
            else str(raw_classes or "")
        )
        if any(token in classes.lower() for token in ("card", "product", "listing", "item")):
            return parent
    return None
