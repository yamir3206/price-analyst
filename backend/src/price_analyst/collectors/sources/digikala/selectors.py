"""Digikala public HTML selectors."""

JSON_LD_SELECTOR = 'script[type="application/ld+json"]'
PRODUCT_LINK_SELECTOR = 'a[href*="/product/dkp-"]'
PRICE_SELECTORS = (
    '[data-testid*="price"]',
    '[data-price]',
    '[itemprop="price"]',
    '[class*="price"]',
)
SELLER_SELECTORS = (
    '[data-testid*="seller"]',
    '[data-seller]',
    '[itemprop="seller"]',
)
