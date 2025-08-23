def download_amazon_reviews(
    asin,
    collection_dir,
    recent_only=False,
    max_pages=None,
    delay=2.0,
    cleanup=True
):
    os.makedirs(collection_dir, exist_ok=True)
    raw_dir = os.path.join(collection_dir, "RawData")
    os.makedirs(raw_dir, exist_ok=True)

    # Selenium setup (interactive login)
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(options=chrome_options)
    driver.get("https://www.amazon.com/")
    input("🔐 Please log in to Amazon in the opened browser window, then press Enter...")

    # Load product page for metadata
    product_url = f"https://www.amazon.com/dp/{asin}"
    driver.get(product_url)
    time.sleep(delay)
    page_source = driver.page_source
    product_soup = BeautifulSoup(page_source, 'html.parser')
    category_path = extract_category_path(product_soup)
    bsr = extract_bsr(product_soup)
    price = extract_price(product_soup)
    review_count = extract_review_count(product_soup)

    # Load reviews
    reviews_url = f"https://www.amazon.com/product-reviews/{asin}/?sortBy=recent"
    driver.get(reviews_url)
    time.sleep(delay)

    reviews = []
    page = 1
    while True:
        print(f"[DEBUG] Loading page {page} for ASIN {asin}")
        html = driver.page_source
        html_file = os.path.join(raw_dir, f"reviews_{asin}_p{page}.html")
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html)
        soup = BeautifulSoup(html, 'html.parser')
        review_blocks = extract_review_blocks(soup)
        if not review_blocks:
            break
        for div in review_blocks:
            r = parse_review_div(div)
            r['category_path'] = category_path
            r['price'] = price
            r['review_count'] = review_count
            r['bsr'] = bsr
            reviews.append(r)
        if max_pages and page >= max_pages:
            break
        try:
            next_btn = driver.find_element(By.CSS_SELECTOR, 'li.a-last a')
            if not next_btn.is_displayed() or not next_btn.is_enabled():
                break
            next_btn.click()
            page += 1
            time.sleep(delay)
        except NoSuchElementException:
            break
        except Exception:
            break

    driver.quit()

    # Optional recent filter
    if recent_only:
        import datetime
        cutoff = datetime.date.today() - datetime.timedelta(days=365)
        reviews = [
            r for r in reviews
            if r['date'] and normalize_date(r['date']) and dateparser.parse(r['date']).date() >= cutoff
        ]

    # Save to CSV
    df = pd.DataFrame(reviews)
    if not df.empty:
        df['date'] = df['date'].apply(normalize_date)
    csv_path = os.path.join(collection_dir, 'reviews.csv')
    df.to_csv(csv_path, index=False)
    print(f"Saved {len(df)} reviews to {csv_path}")

    if cleanup:
        shutil.rmtree(raw_dir, ignore_errors=True)
