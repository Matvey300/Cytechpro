import json
from pathlib import Path

CATEGORY_FILE = Path(__file__).parent / "amazon_categories_us.json"

with CATEGORY_FILE.open("r", encoding="utf-8") as f:
    CATEGORY_TREE = json.load(f)


def search_categories(keyword, tree=None, path=None):
    """
    Recursively search for category paths where the category name contains the given keyword.
    Returns a list of paths (e.g., ['Electronics > Headphones > Over-Ear Headphones']).
    """
    if tree is None:
        tree = CATEGORY_TREE
    if path is None:
        path = []

    matches = []

    for category, subtree in tree.items():
        current_path = path + [category]
        if keyword.lower() in category.lower():
            matches.append(" > ".join(current_path))
        if isinstance(subtree, dict):
            matches.extend(search_categories(keyword, subtree, current_path))

    return matches


def fetch_amazon_categories(keyword: str):
    return search_categories(keyword)
