# ASIN_data_import.py
# All comments in English.

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Iterable, List, Tuple

import pandas as pd
import requests
from bs4 import BeautifulSoup


@dataclass(frozen=True)
class MarketCfg:
    base: str      # e.g. "https://www.amazon.com"
    locale: str    # e.g. "en_US"
    currency: str  # e.g. "USD"


def _marketplace_config(region: str) -> MarketCfg:
    """Return marketplace settings for a given region code."""
    region = (region or "").upper()
    if region == "US":
        return MarketCfg(base="https://www.amazon.com",  locale="en_US", currency="USD")
    if region == "UK":
        return MarketCfg(base="https://www.amazon.co.uk", locale="en_GB", currency="GBP")
    # Fallback to US if something unexpected is passed
    return MarketCfg(base="https://www.amazon.com", locale="en_US", currency="USD")


def _headers(locale: str) -> dict:
    """Basic anti-bot-ish headers. Adjust if needed."""
    return {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }


_ASIN_RE = re.compile(r"/([A-Z0-9]{10})(?:[/?]|$)")


def _extract_asins_from_html(html: str) -> List[str]:
    """Extract ASINs from a search result page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    asins: set[str] = set()

    # 1) Try product containers with 'data-asin'
    for div in soup.select("div.s-result-item[data-asin]"):
        asin = div.get("data-asin", "").strip()
        if len(asin) == 10 and asin.isalnum():
            asins.add(asin)

    # 2) Fallback: scan all hrefs for '/dp/ASIN' or '/gp/.../ASIN'
    for a in soup.select("a[href]"):
        href = a["href"]
        m = _ASIN_RE.search(href)
        if m:
            candidate = m.group(1)
            if len(candidate) == 10 and candidate.isalnum():
                asins.add(candidate)

    return list(asins)


def _search_url(cfg: MarketCfg, query: str, page: int) -> str:
    """Build Amazon search URL for a given query and page."""
    # Simple search; you can enrich with department/category filters later.
    return f"{cfg.base}/s?k={requests.utils.quote(query)}&page={page}"


def _fetch_asins_via_search(
    cfg: MarketCfg,
    query: str,
    max_items: int = 100,
    max_pages: int = 10,
    delay_sec: float = 1.5,
) -> List[str]:
    """Fetch ASINs by iterating search result pages until max_items or max_pages is reached."""
    session = requests.Session()
    session.headers.update(_headers(cfg.locale))

    found: List[str] = []
    seen: set[str] = set()

    for page in range(1, max_pages + 1):
        url = _search_url(cfg, query=query, page=page)
        resp = session.get(url, timeout=20)
        if resp.status_code != 200:
            # Soft break on blocks or errors
            break

        page_asins = _extract_asins_from_html(resp.text)
        for a in page_asins:
            if a not in seen:
                seen.add(a)
                found.append(a)
                if len(found) >= max_items:
                    return found

        # Polite delay between pages
        time.sleep(delay_sec)

    return found


def _last_two_nodes(category_path: str) -> str:
    """Return the last two nodes of a 'A > B > C' path; fallback to full if <2 nodes."""
    parts = [p.strip() for p in (category_path or "").split(">") if p.strip()]
    if len(parts) >= 2:
        return " ".join(parts[-2:])
    if parts:
        return parts[-1]
    return category_path or ""


def Collect_ASIN_DATA(category_path: str, region: str) -> pd.DataFrame:
    """
    Public entry-point used by the app.
    Inputs:
      - category_path: normalized category path, e.g. "Electronics > Headphones > Earbuds"
      - region: "US" or "UK"
    Output:
      - pandas.DataFrame with columns at least: ['asin', 'region', 'category_path']
    """
    cfg = _marketplace_config(region)

    # For MVP we convert category path to a search query using the two last nodes.
    # Example: "Electronics > Headphones > Earbuds" -> "Headphones Earbuds"
    query = _last_two_nodes(category_path)

    # Fetch up to 100 ASINs via plain search (you can swap this to your existing parser)
    asins = _fetch_asins_via_search(cfg, query=query, max_items=100, max_pages=10, delay_sec=1.0)

    df = pd.DataFrame({"asin": asins})
    # Normalize + metadata expected by the pipeline
    df = df.drop_duplicates(subset=["asin"]).reset_index(drop=True)
    df["region"] = region.upper()
    df["category_path"] = category_path

    return df