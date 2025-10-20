import os
import subprocess
import time

import pandas as pd
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


# === ФУНКЦИЯ: Сбор HTML отзывов с Amazon ===
def scrape_reviews(asin, country, pages, save_dir, profile_path):
    domain = "amazon." + country
    base_url = (
        f"https://www.{domain}/product-reviews/{asin}/?pageNumber=1&language=en_US&sortBy=recent"
    )

    chrome_options = Options()
    chrome_options.add_argument(f"--user-data-dir={profile_path}")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")

    if subprocess.run(["pgrep", "-i", "chrome"], capture_output=True, text=True).stdout.strip():
        print("❌ Chrome запущен! Закрой его и запусти скрипт снова.")
        return

    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=chrome_options
        )
        driver.get(f"https://www.{domain}/")
    except WebDriverException as e:
        print("❌ Chrome не запустился:", str(e))
        return

    input("🔐 Залогинься в открытом окне Chrome, затем нажми Enter...")

    for page in range(1, pages + 1):
        print(f"[{asin}] Скачиваем страницу {page}...")

        if page == 1:
            driver.get(base_url)
        else:
            time.sleep(4)

        html = driver.page_source
        filename = os.path.join(save_dir, f"{asin}_p{page}.html")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"✅ Сохранено: {filename}")

        if page < pages:
            try:
                next_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "li.a-last a"))
                )
                next_button.click()
            except (NoSuchElementException, TimeoutException):
                print("⚠️ Кнопка 'Следующая страница' не найдена.")
                break

    driver.quit()


# === ФУНКЦИЯ: Парсинг HTML файлов в DataFrame ===
def parse_reviews(asin, html_dir, pages):
    reviews = []

    for page in range(1, pages + 1):
        file_path = os.path.join(html_dir, f"{asin}_p{page}.html")
        if not os.path.exists(file_path):
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
            review_blocks = soup.find_all("li", {"data-hook": "review"})

            for r in review_blocks:
                try:
                    author = r.find("span", class_="a-profile-name").get_text(strip=True)
                    rating_tag = r.find("i", {"data-hook": "review-star-rating"}) or r.find(
                        "i", {"data-hook": "cmps-review-star-rating"}
                    )
                    rating = (
                        float(rating_tag.find("span").get_text(strip=True).split()[0])
                        if rating_tag
                        else None
                    )
                    title = r.find("a", {"data-hook": "review-title"}).get_text(strip=True)
                    date_raw = r.find("span", {"data-hook": "review-date"}).get_text(strip=True)
                    date_iso = (
                        date_parser.parse(date_raw.split(" on ")[-1].strip()).strftime("%Y-%m-%d")
                        if "on" in date_raw
                        else None
                    )
                    location = (
                        date_raw.split(" in ")[-1].split(" on ")[0].strip()
                        if " in " in date_raw
                        else "N/A"
                    )
                    body = r.find("span", {"data-hook": "review-body"}).get_text(
                        separator=" ", strip=True
                    )
                    verified_tag = r.find("span", {"data-hook": "avp-badge"})
                    verified = bool(verified_tag and "Verified Purchase" in verified_tag.text)
                    helpful_tag = r.find("span", {"data-hook": "helpful-vote-statement"})
                    if helpful_tag:
                        txt = helpful_tag.get_text(strip=True)
                        if "One person found this helpful" in txt:
                            helpful_votes = 1
                        elif "people found this helpful" in txt:
                            helpful_votes = int(txt.split()[0].replace(",", ""))
                        else:
                            helpful_votes = 0
                    else:
                        helpful_votes = 0

                    reviews.append(
                        {
                            "asin": asin,
                            "author": author,
                            "location": location,
                            "date": date_iso,
                            "rating": rating,
                            "title": title,
                            "body": body,
                            "verified_purchase": verified,
                            "helpful_votes": helpful_votes,
                        }
                    )

                except Exception:
                    continue

    return pd.DataFrame(reviews)


# === MAIN ===
def main():
    asin_file = (
        input("📄 Введите путь к файлу со списком ASIN (по умолчанию search_results.csv): ").strip()
        or "DATA/search_results.csv"
    )
    if not os.path.exists(asin_file):
        print("❌ Файл не найден.")
        return

    df_asins = pd.read_csv(asin_file)
    country = input("🌍 Введите код страны (например, com, co.uk, de): ").strip()
    pages = input("📑 Сколько страниц отзывов собирать? (по умолчанию 10): ").strip()
    pages = int(pages) if pages.isdigit() else 10

    SAVE_DIR = "DATA/review_pages"
    PROFILE_PATH = "/Users/Matvej1/chrome-amazon-profile"
    os.makedirs(SAVE_DIR, exist_ok=True)

    all_reviews = []

    for _, row in df_asins.iterrows():
        asin = row["asin"]
        if row["country"] != country:
            continue

        print(f"🔍 Обработка ASIN: {asin}")
        scrape_reviews(asin, country, pages, SAVE_DIR, PROFILE_PATH)
        df_reviews = parse_reviews(asin, SAVE_DIR, pages)
        all_reviews.append(df_reviews)

    if all_reviews:
        result_df = pd.concat(all_reviews, ignore_index=True)
        result_df.to_csv("DATA/all_reviews.csv", index=False, encoding="utf-8-sig")
        print("✅ Все отзывы сохранены в DATA/all_reviews.csv")
    else:
        print("⚠️ Отзывы не найдены.")


if __name__ == "__main__":
    main()
