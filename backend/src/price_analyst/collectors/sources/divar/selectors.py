"""Divar public HTML selectors."""

JSON_LD_SELECTOR = 'script[type="application/ld+json"]'
LISTING_LINK_SELECTOR = 'a[href*="/v/"]'
PRICE_SELECTORS = (
    '[data-testid*="price"]',
    '[data-price]',
    '[itemprop="price"]',
    '[class*="price"]',
)
