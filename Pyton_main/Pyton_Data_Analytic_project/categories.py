
import os
from typing import List

def choose_marketplace(supported: List[str]) -> str:
    """Interactive chooser for marketplace."""
    print(f"Available: {', '.join(supported)}")
    while True:
        val = input("> Choose marketplace [US/UK]: ").strip().upper()
        if val in supported:
            return val
        print("Invalid input, please enter US or UK.")

def _mock_categories(keyword: str) -> List[str]:
    """Fallback categories when SerpApi is not configured yet."""
    kw = keyword.lower()
    if "head" in kw or "науш" in kw:
        return [
            "Electronics > Headphones > Over-Ear",
            "Electronics > Headphones > In-Ear",
            "Electronics > Headphones > Earbuds",
        ]
    return [f"Generic > {keyword.title()}"]

def search_categories_by_keyword(keyword: str, marketplace: str) -> List[str]:
    """Returns list of category paths by keyword.
    NOTE: For MVP we keep a mock implementation. You can switch to SerpApi
    later by replacing this function.
    """
    serp_key = os.getenv("SERPAPI_API_KEY")
    if not serp_key:
        return _mock_categories(keyword)
    # TODO: implement real SerpApi flow here (optional for MVP)
    return _mock_categories(keyword)

def multi_select_categories(candidates: List[str]) -> List[str]:
    """Simple multi-select prompt."""
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
    # Detail level -2: keep last 2 nodes
    clean = []
    for p in out:
        parts = [x.strip() for x in p.split(">")]
        clean.append(" > ".join(parts[-2:]) if len(parts) >= 2 else p)
    return sorted(set(clean))