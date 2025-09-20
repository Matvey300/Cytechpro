
from core.log import print_error, print_success


def save_html(rawdata_dir, asin, page_num, html):
    """
    Save raw HTML content of a product's review page.

    Parameters:
    - rawdata_dir (Path): Directory to save raw HTML files.
    - asin (str): ASIN of the product.
    - page_num (int): Page number of the reviews.
    - html (str): Raw HTML content to be saved.

    Example:
        save_html(Path("DATA/raw"), "B000123ABC", 1, "<html>...</html>")
    """
    rawdata_dir.mkdir(parents=True, exist_ok=True)
    raw_html_path = rawdata_dir / f"{asin}_p{page_num}.html"
    try:
        with open(raw_html_path, "w", encoding="utf-8") as f:
            f.write(html)
        print_success(f"[→] Saved HTML: {raw_html_path}")
    except Exception as e:
        print_error(f"[✖] Failed to save HTML for {asin} page {page_num}: {e}")
        raise


# New function to save multiple review pages as HTML files
def save_review_pages(rawdata_dir, asin, pages):
    """
    Save multiple pages of reviews as HTML files.

    Parameters:
    - rawdata_dir (Path): Directory to save HTML files.
    - asin (str): ASIN of the product.
    - pages (List[str]): List of raw HTML strings for each review page.
    """
    for i, html in enumerate(pages, 1):
        save_html(rawdata_dir, asin, i, html)


def save_review_pages_html(rawdata_dir, asin, pages):
    """
    Compatibility wrapper for saving multiple review pages as HTML files.
    This function is used in the review pipeline.

    Parameters:
    - rawdata_dir (Path): Directory to save HTML files.
    - asin (str): ASIN of the product.
    - pages (List[str]): List of raw HTML strings for each review page.
    """
    save_review_pages(rawdata_dir, asin, pages)
