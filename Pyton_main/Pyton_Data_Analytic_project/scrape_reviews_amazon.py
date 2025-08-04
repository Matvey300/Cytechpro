import time
import os
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# === SETTINGS ===
ASINS = ["B08WM3LMJF"]
PAGES_PER_ASIN = 10
SAVE_DIR = "DATA/review_pages"
PROFILE_PATH = "/Users/Matvej1/chrome-amazon-profile"

# === Создание папки для сохранения файлов ===
os.makedirs(SAVE_DIR, exist_ok=True)

# === Chrome Options ===
chrome_options = Options()
chrome_options.add_argument(f'--user-data-dir={PROFILE_PATH}')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')

# === Проверка, закрыт ли Chrome ===
if subprocess.run(["pgrep", "-i", "chrome"], capture_output=True, text=True).stdout.strip():
    print("❌ Chrome запущен! Закрой его (⌘ + Q) и запусти скрипт снова.")
    exit(1)

# === Запуск Chrome ===
try:
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.get("https://www.amazon.com/")
except WebDriverException as e:
    print("❌ Chrome не запустился:", str(e))
    exit(1)

# === Вручную залогинься в открытом окне Chrome ===
input("🔑 Залогинься вручную на Amazon в открытом окне, затем вернись сюда и нажми Enter...")

# === Начинаем сбор отзывов ===
for asin in ASINS:
    # URL для первой страницы с сортировкой по самым новым отзывам
    start_url = f"https://www.amazon.com/product-reviews/{asin}/?pageNumber=1&language=en_US&sortBy=recent"
    
    for page in range(1, PAGES_PER_ASIN + 1):
        print(f"[{asin}] Скачиваем страницу {page}...")

        try:
            # На первой итерации переходим по стартовому URL
            if page == 1:
                driver.get(start_url)
            else:
                # На следующих итерациях просто ждем, так как клик уже сделан
                time.sleep(5)
            
            # Сохраняем HTML-код страницы
            html = driver.page_source
            filename = os.path.join(SAVE_DIR, f"{asin}_p{page}.html")
            with open(filename, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"✅ Сохранено: {filename}")
            
            # Находим кнопку "Следующая страница" и эмулируем клик
            if page < PAGES_PER_ASIN:
                try:
                    next_page_button = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "li.a-last a"))
                    )
                    next_page_button.click()
                    print(f"➡️ Кликнули на кнопку 'Следующая страница' для перехода на страницу {page + 1}")
                except (NoSuchElementException, TimeoutException):
                    print("Не удалось найти кнопку 'Следующая страница'. Завершаем сбор.")
                    break

        except Exception as e:
            print(f"❌ Ошибка на странице {page}: {str(e)}")
            break

# === Закрываем Chrome ===
driver.quit()
print("✅ Все отзывы собраны.")