import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from lightgbm import LGBMRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.neural_network import MLPRegressor
from textblob import TextBlob

# Загрузка данных
df_search = pd.read_csv(
    "/Users/Matvej1/CyberPro/Pyton_main/Pyton_Data_Analytic_project/DATA/search_results.csv"
)
df_reviews = pd.read_csv(
    "/Users/Matvej1/CyberPro/Pyton_main/Pyton_Data_Analytic_project/DATA/all_reviews.csv"
)

# Подготовка
df_reviews.columns = df_reviews.columns.astype(str).str.strip()
df_search.columns = df_search.columns.astype(str).str.strip()
df_search["product_name"] = df_search["title"].astype(str).str.slice(0, 50)

# Sentiment
df_reviews["sentiment"] = (
    df_reviews["body"].astype(str).apply(lambda x: TextBlob(x).sentiment.polarity)
)

# Средняя длина отзыва
df_reviews["body_length"] = df_reviews["body"].astype(str).apply(len)

# Группировка по ASIN
df_grouped = df_reviews.groupby("asin", as_index=False).agg(
    avg_rating=("rating", "mean"),
    review_count=("asin", "count"),
    total_helpful_votes=("helpful_votes", "sum"),
    avg_sentiment=("sentiment", "mean"),
)

# Дополнительные признаки
verified_ratio = (
    df_reviews.groupby("asin")["verified_purchase"]
    .apply(lambda x: (x == True).sum() / len(x))
    .reset_index(name="verified_share")
)

avg_length = df_reviews.groupby("asin")["body_length"].mean().reset_index(name="avg_length")
review_variance = df_reviews.groupby("asin")["rating"].var().reset_index(name="review_variance")
unique_authors = (
    df_reviews.groupby("asin")["author"].nunique().reset_index(name="num_unique_authors")
)

# Объединяем всё
df_features = (
    df_grouped.merge(verified_ratio, on="asin", how="left")
    .merge(avg_length, on="asin", how="left")
    .merge(review_variance, on="asin", how="left")
    .merge(unique_authors, on="asin", how="left")
)

# Признаки и целевая переменная
X = df_features[
    [
        "avg_rating",
        "review_count",
        "verified_share",
        "avg_length",
        "review_variance",
        "num_unique_authors",
    ]
]
y = df_features["total_helpful_votes"]

# Модели
models = {
    "Linear Regression": LinearRegression(),
    "Random Forest": RandomForestRegressor(n_estimators=100, random_state=42),
    "Gradient Boosting": GradientBoostingRegressor(n_estimators=100, random_state=42),
    "LightGBM": LGBMRegressor(n_estimators=100, random_state=42, verbose=-1),
    "CatBoost": CatBoostRegressor(n_estimators=100, random_state=42, verbose=0),
    "Neural Network (MLP)": MLPRegressor(
        hidden_layer_sizes=(64, 64), max_iter=1000, random_state=42
    ),
}

# Обучение и оценка
results = []
for name, model in models.items():
    model.fit(X, y)
    y_pred = model.predict(X)
    r2 = r2_score(y, y_pred)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    results.append({"Model": name, "R2 Score": r2, "RMSE": rmse})

df_results = pd.DataFrame(results).sort_values(by="R2 Score", ascending=False)
print(df_results)

# Визуализация
plt.figure(figsize=(10, 5))
plt.barh(df_results["Model"], df_results["R2 Score"], color="seagreen")
plt.xlabel("R² Score")
plt.title("Model Performance (Extended Features)")
plt.gca().invert_yaxis()
plt.tight_layout()
plt.show()
