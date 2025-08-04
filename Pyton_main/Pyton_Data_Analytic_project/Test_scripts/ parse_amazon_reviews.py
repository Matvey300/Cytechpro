import os
import pandas as pd
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

HTML_DIR = "DATA/review_pages"
ASIN = "B08WM3LMJF"
PAGES = 10

reviews = []

for page in range(1, PAGES + 1):
    file_path = os.path.join(HTML_DIR, f"{ASIN}_p{page}.html")

    if not os.path.exists(file_path):
        print(f"❌ Файл {file_path} не найден. Пропускаем.")
        continue

    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
        
        review_blocks = soup.find_all("li", {"data-hook": "review"}) 

        if not review_blocks:
            print(f"⚠️ На странице {page} не найдено отзывов.")
            continue

        for r in review_blocks:
            try:
                # Автор
                author_tag = r.find("span", class_="a-profile-name")
                author = author_tag.get_text(strip=True) if author_tag else "N/A"

                # Рейтинг
                rating_tag = r.find("i", {"data-hook": "review-star-rating"}) or r.find("i", {"data-hook": "cmps-review-star-rating"})
                rating_str = rating_tag.find("span").get_text(strip=True) if rating_tag else ""
                rating = float(rating_str.split()[0]) if rating_str else None

                # Заголовок отзыва
                title_tag = r.find("a", {"data-hook": "review-title"})
                title = title_tag.get_text(strip=True) if title_tag else "N/A"

                # Дата и страна
                date_tag = r.find("span", {"data-hook": "review-date"})
                date_str = date_tag.get_text(strip=True) if date_tag else ""
                try:
                    date_obj = date_parser.parse(date_str.split(" on ")[-1].strip())
                    date_iso = date_obj.strftime("%Y-%m-%d")
                except:
                    date_iso = None

                location = date_str.split(" in ")[-1].split(" on ")[0].strip() if " in " in date_str else "N/A"

                # Тело отзыва
                body_tag = r.find("span", {"data-hook": "review-body"})
                body = body_tag.get_text(separator=" ", strip=True) if body_tag else "N/A"

                # Verified Purchase
                verified_tag = r.find("span", {"data-hook": "avp-badge"})
                verified = True if verified_tag and "Verified Purchase" in verified_tag.text else False

                # Полезность
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

                reviews.append({
                    "asin": ASIN,
                    "author": author,
                    "location": location,
                    "date": date_iso,
                    "rating": rating,
                    "title": title,
                    "body": body,
                    "verified_purchase": verified,
                    "helpful_votes": helpful_votes
                })

            except Exception as e:
                print(f"⚠️ Пропущен отзыв из-за ошибки: {e}")
                continue

    print(f"✅ Обработано отзывов на странице {page}: {len(review_blocks)}")

# Сохраняем
df = pd.DataFrame(reviews)
output_file = f"DATA/{ASIN}_reviews_final.csv"
df.to_csv(output_file, index=False, encoding="utf-8-sig")
print(f"🎉 Сохранено {len(reviews)} отзывов в файл: {output_file}")
