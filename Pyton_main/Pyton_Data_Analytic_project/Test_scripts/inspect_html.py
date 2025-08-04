from bs4 import BeautifulSoup

file_path = "DATA/review_pages/B08WM3LMJF_p1.html"

with open(file_path, "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

# выводим небольшой кусочек HTML для анализа
print(soup.prettify()[:5000])  # первые 5000 символов
