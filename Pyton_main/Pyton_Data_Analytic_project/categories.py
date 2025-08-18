# All comments in English.

import os
from typing import List

# SerpApi key is expected in env var SERPAPI_API_KEY
# Marketplace mapping: US -> amazon.com, UK -> amazon.co.uk

def choose_marketplace(supported: List[str]) -> str:
    """Interactive marketplace chooser for US/UK."""
    print(f"Available marketplaces: {', '.join(supported)}")
    while True:
        val = input("> Choose marketplace [US/UK]: ").strip().upper()
        if val in supported:
            return val
        print("Invalid input, please enter US or UK.")

def search_categories_by_keyword(keyword: str, marketplace: str) -> List[str]:
    """Return a list of category paths matching the keyword via SerpApi (placeholder).
       Implementation: query SerpApi Amazon engine, extract breadcrumbs/departments, dedupe.
       For MVP we return a mocked list to wire the flow; will replace with real SerpApi parsing.
    """
    # TODO: implement with SerpApi (google-search-results); parse categories from results.
    # For now we return a stub list that looks like normalized category paths.
    kw = keyword.strip().lower()
    if "headphone" in kw or "науш" in kw:
        return [
            "Electronics > Headphones > Over-Ear",
            "Electronics > Headphones > In-Ear",
            "Electronics > Headphones > Earbuds",
        ]
    return [f"Generic > {keyword.title()}"]

def multi_select_categories(candidates: List[str]) -> List[str]:
    """Text-based multi-select: user enters indices separated by commas."""
    if not candidates:
        return []
    print("\nSelect categories (comma separated indices):")
    for i, c in enumerate(candidates, 1):
        print(f"{i}. {c}")
    raw = input("> Your choice (e.g., 1,3): ").strip()
    if not raw:
        return []
    out = []
    for token in raw.split(","):
        token = token.strip()
        if token.isdigit():
            idx = int(token)
            if 1 <= idx <= len(candidates):
                out.append(candidates[idx-1])
    # Detail level -2: keep last 2 nodes of path
    out2 = []
    for p in out:
        parts = [x.strip() for x in p.split(">")]
        out2.append(" > ".join(parts[-2:]) if len(parts) >= 2 else p)
    # De-dup
    return sorted(set(out2))