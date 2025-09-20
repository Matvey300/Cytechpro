# core/marketplaces.py
# Supported Amazon marketplaces and their domains

MARKETPLACES = {
    "US": "amazon.com",
    "UK": "amazon.co.uk",
    "DE": "amazon.de",
    "FR": "amazon.fr",
    "JP": "amazon.co.jp",
    "CA": "amazon.ca",
    "IN": "amazon.in",
    "IT": "amazon.it",
    "ES": "amazon.es",
    "MX": "amazon.com.mx",
    "AU": "amazon.com.au",
}


def to_domain(marketplace: str | None) -> str:
    """Normalize marketplace into full Amazon domain.

    Accepts values like 'US', 'com', 'co.uk', 'amazon.com', 'amazon.co.uk'.
    Defaults to 'amazon.com' for unknown/null inputs.
    """
    if not marketplace:
        return "amazon.com"
    s = str(marketplace).strip().lower()
    # Country code mapping (e.g., 'US' → amazon.com)
    if len(s) <= 3 and s.isalpha():
        # treat as TLD (com, de) or code (us, uk)
        if s.upper() in MARKETPLACES:
            return MARKETPLACES[s.upper()]
        # tld case like 'com'
        return f"amazon.{s}"
    # Domain variants
    if s.startswith("amazon."):
        return s
    # bare domain like 'com.mx' or 'co.uk'
    if "." in s:
        return f"amazon.{s}"
    # fallback
    return "amazon.com"
