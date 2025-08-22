import os
import csv
import time
import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class ReviewsPipeline:
    def __init__(self, collection_dir, chrome_profile_dir=None, headless=True, timeout=15):
        self.collection_dir = Path(collection_dir)
        self.rawdata_dir = self.collection_dir / "RawData"
        self.rawdata_dir.mkdir(parents=True, exist_ok=True)
        self.chrome_profile_dir = chrome_profile_dir
        self.headless = headless
        self.timeout = timeout
        self.driver = None

    def _init_driver(self):
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        if self.chrome_profile_dir:
            options.add_argument(f"user-data-dir={self.chrome_profile_dir}")
        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_page_load_timeout(self.timeout)
        except WebDriverException as e:
            print(f"Error initializing Chrome driver: {e}")
            raise

    def _close_driver(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def _wait_for_element(self, by, identifier):
        try:
            element = WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((by, identifier))
            )
            return element
        except TimeoutException:
            return None

    def _get_reviews_from_page(self, asin, category):
        reviews = []
        review_blocks = self.driver.find_elements(By.CSS_SELECTOR, "div[data-hook='review']")
        for block in review_blocks:
            try:
                author = block.find_element(By.CSS_SELECTOR, "span.a-profile-name").text.strip()
            except NoSuchElementException:
                author = ""

            try:
                location = block.find_element(By.CSS_SELECTOR, "span.review-date").text.strip()
                # location is usually embedded in review-date text, e.g. "Reviewed in the United States on June 1, 2023"
                # We'll try to extract location and date separately
                # Example format: "Reviewed in the United States on June 1, 2023"
                # or "Reviewed in Canada 🇨🇦 on June 1, 2023"
                # We'll split by 'on' to separate location and date
                if "on" in location:
                    parts = location.split("on")
                    location = parts[0].replace("Reviewed in", "").strip()
                    date_str = parts[1].strip()
                else:
                    location = ""
                    date_str = location
            except NoSuchElementException:
                location = ""
                date_str = ""

            # Parse date to ISO format
            date_iso = ""
            if date_str:
                try:
                    date_obj = datetime.datetime.strptime(date_str, "%B %d, %Y")
                    date_iso = date_obj.date().isoformat()
                except ValueError:
                    # try alternative date format
                    try:
                        date_obj = datetime.datetime.strptime(date_str, "%b %d, %Y")
                        date_iso = date_obj.date().isoformat()
                    except ValueError:
                        date_iso = ""

            try:
                rating_str = block.find_element(By.CSS_SELECTOR, "i[data-hook='review-star-rating'] span").text.strip()
                # rating_str like "5.0 out of 5 stars"
                rating = float(rating_str.split()[0])
            except (NoSuchElementException, ValueError):
                rating = None

            try:
                title = block.find_element(By.CSS_SELECTOR, "a[data-hook='review-title'] span").text.strip()
            except NoSuchElementException:
                title = ""

            try:
                body = block.find_element(By.CSS_SELECTOR, "span[data-hook='review-body'] span").text.strip()
            except NoSuchElementException:
                body = ""

            try:
                vp_text = block.find_element(By.CSS_SELECTOR, "span[data-hook='avp-badge']").text.strip()
                verified_purchase = vp_text.lower() == "verified purchase"
            except NoSuchElementException:
                verified_purchase = False

            try:
                helpful_votes_text = block.find_element(By.CSS_SELECTOR, "span[data-hook='helpful-vote-statement']").text.strip()
                # Examples: "1 person found this helpful", "2 people found this helpful"
                helpful_votes = 0
                if helpful_votes_text:
                    helpful_votes = int(helpful_votes_text.split()[0].replace(",", ""))
            except (NoSuchElementException, ValueError):
                helpful_votes = 0

            reviews.append({
                "asin": asin,
                "author": author,
                "location": location,
                "date": date_iso,
                "rating": rating,
                "title": title,
                "body": body,
                "verified_purchase": verified_purchase,
                "helpful_votes": helpful_votes,
                "category": category,
            })
        return reviews

    def _save_html(self, asin, page_num, html):
        filename = self.rawdata_dir / f"{asin}_page_{page_num}.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)

    def _save_reviews_csv(self, reviews):
        today_str = datetime.datetime.now().strftime("%Y%m%d")
        csv_path = self.collection_dir / f"reviews_{today_str}.csv"
        file_exists = csv_path.exists()
        with open(csv_path, "a", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["asin", "author", "location", "date", "rating", "title", "body",
                          "verified_purchase", "helpful_votes", "category"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            for r in reviews:
                writer.writerow(r)

    def scrape_reviews_for_asin(self, asin, category=None, max_pages=100):
        if not self.driver:
            self._init_driver()
        base_url = f"https://www.amazon.com/product-reviews/{asin}/?pageNumber="
        page_num = 1
        total_reviews_collected = 0
        print(f"Starting scraping for ASIN: {asin}")
        while page_num <= max_pages:
            url = base_url + str(page_num)
            try:
                self.driver.get(url)
            except TimeoutException:
                print(f"Timeout loading page {page_num} for ASIN {asin}, retrying...")
                continue
            except WebDriverException as e:
                print(f"WebDriverException on page {page_num} for ASIN {asin}: {e}")
                break

            time.sleep(2)  # Wait for page to load some content

            try:
                bsr_element = self.driver.find_element(By.CSS_SELECTOR, "#cm_cr-product_info .a-row.a-spacing-mini span.a-size-base")
                bsr_text = bsr_element.text.strip()
            except NoSuchElementException:
                bsr_text = ""

            try:
                price_element = self.driver.find_element(By.CSS_SELECTOR, "#cm_cr-product_info .a-size-base.a-color-price")
                price_text = price_element.text.strip()
            except NoSuchElementException:
                price_text = ""

            try:
                total_reviews_element = self.driver.find_element(By.CSS_SELECTOR, "#cm_cr-product_info .a-size-base.cr-vote-text")
                total_reviews = total_reviews_element.text.strip()
            except NoSuchElementException:
                total_reviews = ""

            reviews_preview = self._get_reviews_from_page(asin, category)
            if reviews_preview:
                avg_rating = round(sum([r['rating'] for r in reviews_preview if r['rating'] is not None]) / len(reviews_preview), 2)
            else:
                avg_rating = None

            self._save_snapshot_record({
                "asin": asin,
                "snapshot_date": datetime.datetime.now().date().isoformat(),
                "price": price_text,
                "bsr": bsr_text,
                "review_count": total_reviews,
                "avg_rating": avg_rating,
                "category_path": category or "unknown",
                "marketplace": "amazon.com",
                "collection_id": self.collection_dir.name
            })

            print(f"[META] BSR: {bsr_text}, Price: {price_text}, Total reviews: {total_reviews}")

            # Check if page contains reviews or "no reviews" message
            no_reviews = self.driver.find_elements(By.CSS_SELECTOR, "div.a-row.a-spacing-base.a-color-secondary")
            if no_reviews:
                text = no_reviews[0].text.lower()
                if "no reviews" in text or "did not match any reviews" in text:
                    print(f"No more reviews found at page {page_num} for ASIN {asin}. Stopping.")
                    break

            html = self.driver.page_source
            self._save_html(asin, page_num, html)

            reviews = self._get_reviews_from_page(asin, category)
            if not reviews:
                print(f"No reviews parsed on page {page_num} for ASIN {asin}. Stopping.")
                break

            self._save_reviews_csv(reviews)
            total_reviews_collected += len(reviews)

            print(f"ASIN {asin} - Page {page_num} scraped, {len(reviews)} reviews collected.")

            # Check if there is a next page
            try:
                next_li = self.driver.find_element(By.CSS_SELECTOR, "li.a-last")
                if "a-disabled" in next_li.get_attribute("class"):
                    print(f"No next page after page {page_num} for ASIN {asin}.")
                    break
                try:
                    next_li.find_element(By.TAG_NAME, "a").click()
                except NoSuchElementException:
                    print(f"No clickable link in next page button on page {page_num} for ASIN {asin}.")
                    break
            except NoSuchElementException:
                print(f"No next page button found on page {page_num} for ASIN {asin}.")
                break

            page_num += 1

        print(f"Finished scraping ASIN {asin}. Total reviews collected: {total_reviews_collected}")

    def scrape_multiple_asins(self, asin_list, category=None, max_pages=100):
        try:
            self._init_driver()
            for asin in asin_list:
                self.scrape_reviews_for_asin(asin, category, max_pages)
        finally:
            self._close_driver()

    def _save_snapshot_record(self, snapshot):
        snapshot_path = self.collection_dir / "snapshots.csv"
        file_exists = snapshot_path.exists()
        fieldnames = ["asin", "snapshot_date", "price", "bsr", "review_count",
                      "avg_rating", "category_path", "marketplace", "collection_id"]
        try:
            with open(snapshot_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                # Проверка на дубли по (asin, snapshot_date) не реализована, можно добавить при необходимости
                writer.writerow(snapshot)
        except Exception as e:
            print(f"[ERROR] Failed to write snapshot: {e}")