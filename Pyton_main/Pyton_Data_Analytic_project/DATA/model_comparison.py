
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
from catboost import CatBoostRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import r2_score, mean_squared_error
import matplotlib.pyplot as plt

# Загрузка данных
df_search = pd.read_csv("/Users/Matvej1/CyberPro/Pyton_main/Pyton_Data_Analytic_project/DATA/search_results.csv")
df_reviews = pd.read_csv("/Users/Matvej1/CyberPro/Pyton_main/Pyton_Data_Analytic_project/DATA/all_reviews.csv")

# Подготовка
df_reviews.columns = df_reviews.columns.astype(str).str.strip()
df_search.columns = df_search.columns.astype(str).str.strip()
df_search['product_name'] = df_search['title'].astype(str).str.slice(0, 50)

# Sentiment (если нужно)
from textblob import TextBlob
df_reviews['sentiment'] = df_reviews['body'].astype(str).apply(lambda x: TextBlob(x).sentiment.polarity)

# Группировка
df_grouped = df_reviews.groupby('asin', as_index=False).agg(
    avg_rating=('rating', 'mean'),
    review_count=('asin', 'count'),
    total_helpful_votes=('helpful_votes', 'sum'),
    avg_sentiment=('sentiment', 'mean')
)

# Модели
X = df_grouped[['avg_rating', 'review_count']]
y = df_grouped['total_helpful_votes']

models = {
    'Linear Regression': LinearRegression(),
    'Random Forest': RandomForestRegressor(n_estimators=100, random_state=42),
    'Gradient Boosting': GradientBoostingRegressor(n_estimators=100, random_state=42),
    'XGBoost': XGBRegressor(n_estimators=100, random_state=42, verbosity=0),
    'LightGBM': LGBMRegressor(n_estimators=100, random_state=42, verbose=-1),
    'CatBoost': CatBoostRegressor(n_estimators=100, random_state=42, verbose=0),
    'Neural Network (MLP)': MLPRegressor(hidden_layer_sizes=(64, 64), max_iter=1000, random_state=42)
}

results = []
for name, model in models.items():
    model.fit(X, y)
    y_pred = model.predict(X)
    r2 = r2_score(y, y_pred)
    rmse = mean_squared_error(y, y_pred, squared=False)
    results.append({'Model': name, 'R2 Score': r2, 'RMSE': rmse})

# Таблица сравнения
df_results = pd.DataFrame(results).sort_values(by='R2 Score', ascending=False)
print(df_results)

# Визуализация
plt.figure(figsize=(10, 5))
plt.barh(df_results['Model'], df_results['R2 Score'], color='skyblue')
plt.xlabel('R² Score')
plt.title('Model Performance Comparison')
plt.gca().invert_yaxis()
plt.tight_layout()
plt.show()
