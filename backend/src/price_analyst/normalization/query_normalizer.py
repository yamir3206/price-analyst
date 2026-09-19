"""Deterministic normalization for Persian/English product queries."""

from __future__ import annotations

import re
import unicodedata

from price_analyst.domain.queries import NormalizedQuery

_ARABIC_TO_PERSIAN = str.maketrans(
    {
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "ة": "ه",
        "ۀ": "ه",
        "ؤ": "و",
        "إ": "ا",
        "أ": "ا",
        "ٱ": "ا",
        "ـ": "",
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

_BRAND_ALIASES: dict[str, str] = {
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
    "اچ پی": "hp",
    "hp": "hp",
}

_COLOR_ALIASES: dict[str, str] = {
    "مشکی": "black",
    "سیاه": "black",
    "black": "black",
    "سفید": "white",
    "white": "white",
    "خاکستری": "gray",
    "طوسی": "gray",
    "gray": "gray",
    "grey": "gray",
    "آبی": "blue",
    "ابی": "blue",
    "blue": "blue",
    "قرمز": "red",
    "red": "red",
    "سبز": "green",
    "green": "green",
    "بنفش": "purple",
    "purple": "purple",
    "تیتانیوم": "titanium",
    "titanium": "titanium",
}

_CAPACITY_RE = re.compile(
    r"(?P<value>\d+(?:[.,]\d+)?)\s*(?P<unit>tb|gb|mb|گیگابایت|گیگ|گیک|ترابایت|مگابایت|گ ب|ت ب)"
)


def normalize_text(value: str) -> str:
    """Normalize Unicode, Persian characters, digits, punctuation and spaces."""

    normalized = unicodedata.normalize("NFKC", value).translate(_ARABIC_TO_PERSIAN).lower()
    normalized = normalized.replace("\u200c", " ").replace("\u200f", " ").replace("\u200e", " ")
    normalized = re.sub(r"[^\w\s]", " ", normalized, flags=re.UNICODE)
    return re.sub(r"\s+", " ", normalized).strip()


def _canonical_capacity(value: str, unit: str) -> str:
    number = value.replace(",", ".")
    if number.endswith(".0"):
        number = number[:-2]
    unit_key = unit.lower()
    if unit_key in {"tb", "ترابایت", "ت ب"}:
        return f"{number}TB"
    if unit_key in {"mb", "مگابایت"}:
        return f"{number}MB"
    return f"{number}GB"


def _find_alias(text: str, aliases: dict[str, str]) -> str | None:
    for alias, canonical in sorted(aliases.items(), key=lambda item: len(item[0]), reverse=True):
        if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", text):
            return canonical
    return None


def _find_aliases(text: str, aliases: dict[str, str]) -> list[str]:
    """Return distinct aliases in source-text order for multi-word attributes."""

    matches: list[tuple[int, int, str]] = []
    for alias, canonical in aliases.items():
        match = re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", text)
        if match:
            matches.append((match.start(), -len(alias), canonical))
    matches.sort()
    return list(dict.fromkeys(item[2] for item in matches))


def normalize_query(value: str) -> NormalizedQuery:
    """Return a stable representation without making semantic guesses.

    Only a small, explicit alias dictionary is used in Phase 1. Marketplace
    adapters and later matching phases can add richer product-specific data
    without changing this API contract.
    """

    original = value.strip()
    if not original:
        raise ValueError("query must not be empty")

    normalized = normalize_text(original)
    if not normalized:
        raise ValueError("query must contain searchable characters")

    capacity_match = _CAPACITY_RE.search(normalized)
    capacity = None
    if capacity_match:
        capacity = _canonical_capacity(capacity_match.group("value"), capacity_match.group("unit"))

    brand = _find_alias(normalized, _BRAND_ALIASES)
    color_aliases = _find_aliases(normalized, _COLOR_ALIASES)
    color = " ".join(color_aliases) or None

    model_text = normalized
    if brand:
        model_text = re.sub(rf"(?<!\w){re.escape(brand)}(?!\w)", " ", model_text)
        for alias, canonical in _BRAND_ALIASES.items():
            if canonical == brand:
                model_text = re.sub(rf"(?<!\w){re.escape(alias)}(?!\w)", " ", model_text)
    if capacity_match:
        model_text = model_text.replace(capacity_match.group(0), " ")
    if color_aliases:
        for alias, canonical in _COLOR_ALIASES.items():
            if canonical in color_aliases:
                model_text = re.sub(rf"(?<!\w){re.escape(alias)}(?!\w)", " ", model_text)
    model = re.sub(r"\s+", " ", model_text).strip() or None

    attributes: dict[str, str] = {}
    if brand:
        attributes["brand"] = brand
    if capacity:
        attributes["capacity"] = capacity
    if color:
        attributes["color"] = color

    variants = [normalized]
    return NormalizedQuery(
        original=original,
        normalized_text=normalized,
        brand=brand,
        model=model,
        capacity=capacity,
        color=color,
        attributes=attributes,
        variants=variants,
    )
