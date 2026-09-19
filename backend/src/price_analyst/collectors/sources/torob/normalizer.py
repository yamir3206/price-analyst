"""Torob-specific scalar normalization with no semantic guessing."""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from hashlib import sha256
from urllib.parse import parse_qs, urljoin, urlsplit, urlunsplit

from price_analyst.domain.enums import Availability, Currency, OfferCondition
from price_analyst.domain.money import Money

_DIGIT_TRANSLATION = str.maketrans(
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

_CURRENCY_PATTERN = re.compile(
    r"(?P<number>[0-9۰-۹٠-٩][0-9۰-۹٠-٩\s.,٬٫]*)\s*"
    r"(?P<currency>تومان|تومن|ریال|rial|toman|irr|irt)",
    re.IGNORECASE,
)
_SCALE_PATTERN = re.compile(
    r"(?P<number>[0-9۰-۹٠-٩]+(?:[.,٫][0-9۰-۹٠-٩]+)?)\s*"
    r"(?P<scale>میلیارد|میلیون)\s*"
    r"(?P<currency>تومان|تومن|ریال|rial|toman|irr|irt)?",
    re.IGNORECASE,
)


def normalize_digits(value: str) -> str:
    return value.translate(_DIGIT_TRANSLATION)


def currency_from_label(label: str | None, default: Currency = Currency.IRT) -> Currency:
    if not label:
        return default
    normalized = normalize_digits(label).strip().lower()
    if normalized in {"ریال", "rial", "irr"}:
        return Currency.IRR
    if normalized in {"تومان", "تومن", "toman", "irt"}:
        return Currency.IRT
    return default


def _integer_from_group(value: str) -> int | None:
    digits = re.sub(r"\D", "", normalize_digits(value))
    return int(digits) if digits else None


def parse_numeric_money(value: object, currency: Currency) -> Money | None:
    """Parse numeric JSON-LD prices while preserving the declared currency."""

    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return Money(amount=value, currency=currency) if value >= 0 else None
    if isinstance(value, float):
        if value < 0:
            return None
        float_amount = int(Decimal(str(value)).to_integral_value(ROUND_HALF_UP))
        return Money(amount=float_amount, currency=currency)

    raw = normalize_digits(str(value)).strip()
    if not raw:
        return None
    parsed_amount: int | None = None
    try:
        if re.fullmatch(r"\d+(?:\.\d+)?", raw):
            parsed_amount = int(Decimal(raw).to_integral_value(ROUND_HALF_UP))
        else:
            parsed_amount = _integer_from_group(raw)
    except (InvalidOperation, ValueError):
        return None
    return (
        Money(amount=parsed_amount, currency=currency)
        if parsed_amount is not None and parsed_amount >= 0
        else None
    )


def parse_money(text: str | None, default: Currency = Currency.IRT) -> Money | None:
    """Parse a displayed Torob price with an explicit or configured currency."""

    if not text:
        return None
    normalized = normalize_digits(text)
    scaled = _SCALE_PATTERN.search(normalized)
    if scaled:
        try:
            number = Decimal(
                scaled.group("number").replace(",", ".").replace("٫", ".")
            )
            multiplier = (
                Decimal("1000000000")
                if scaled.group("scale") == "میلیارد"
                else Decimal("1000000")
            )
            amount = int((number * multiplier).to_integral_value(ROUND_HALF_UP))
            return Money(
                amount=amount,
                currency=currency_from_label(scaled.group("currency"), default),
            )
        except (InvalidOperation, ValueError):
            return None

    match = _CURRENCY_PATTERN.search(normalized)
    if not match:
        return None
    displayed_amount = _integer_from_group(match.group("number"))
    if displayed_amount is None:
        return None
    return Money(
        amount=displayed_amount,
        currency=currency_from_label(match.group("currency"), default),
    )


def canonical_url(url: str, base_url: str = "https://torob.com") -> str:
    absolute = urljoin(f"{base_url.rstrip('/')}/", url)
    parts = urlsplit(absolute)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def product_id_from_url(url: str) -> str | None:
    match = re.search(r"/p/([^/?#]+)/?", urlsplit(url).path)
    return match.group(1) if match else None


def redirect_id(url: str, fallback: str) -> str:
    query = parse_qs(urlsplit(url).query)
    prk = query.get("prk", [None])[0]
    return prk or f"redirect-{sha256(url.encode('utf-8')).hexdigest()[:20]}-{fallback}"


def parse_availability(value: str | None) -> Availability:
    if not value:
        return Availability.UNKNOWN
    normalized = normalize_digits(value).lower()
    if "outofstock" in normalized or "out_of_stock" in normalized or "ناموجود" in normalized:
        return Availability.OUT_OF_STOCK
    if "instock" in normalized or "in_stock" in normalized or "موجود" in normalized:
        return Availability.IN_STOCK
    return Availability.UNKNOWN


def parse_condition(value: str | None) -> OfferCondition:
    if not value:
        return OfferCondition.UNKNOWN
    normalized = normalize_digits(value).lower()
    if any(token in normalized for token in ("used", "کارکرده", "استوک", "دست دوم")):
        return OfferCondition.USED
    if any(token in normalized for token in ("refurbished", "refurb", "بازسازی")):
        return OfferCondition.REFURBISHED
    if "new" in normalized or "نو" in normalized:
        return OfferCondition.NEW
    return OfferCondition.UNKNOWN
