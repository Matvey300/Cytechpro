

import pandas as pd
import numpy as np
import shap
import matplotlib.pyplot as plt
from catboost import CatBoostRegressor
from textblob import TextBlob
from sklearn.metrics import r2_score, mean_squared_error

# Загрузка данных
df_search = pd.read_csv("/Users/Matvej1/CyberPro/Pyton_main/Pyton_Data_Analytic_project/DATA/search_results.csv")
df_reviews = pd.read_csv("/Users/Matvej1/CyberPro/Pyton_main/Pyton_Data_Analytic_project/DATA/all_reviews.csv")
df_search['product_name'] = df_search['title'].astype(str).str.slice(0, 50)

# Подготовка признаков
df_reviews['sentiment'] = df_reviews['body'].astype(str).apply(lambda x: TextBlob(x).sentiment.polarity)
df_reviews['body_length'] = df_reviews['body'].astype(str).apply(len)

df_grouped = df_reviews.groupby('asin', as_index=False).agg(
    avg_rating=('rating', 'mean'),
    review_count=('asin', 'count'),
    total_helpful_votes=('helpful_votes', 'sum'),
    avg_sentiment=('sentiment', 'mean')
)

verified_ratio = df_reviews.groupby('asin')['verified_purchase'].apply(
    lambda x: (x == True).sum() / len(x)
).reset_index(name='verified_share')

avg_length = df_reviews.groupby('asin')['body_length'].mean().reset_index(name='avg_length')
review_variance = df_reviews.groupby('asin')['rating'].var().reset_index(name='review_variance')
unique_authors = df_reviews.groupby('asin')['author'].nunique().reset_index(name='num_unique_authors')

df_features = df_grouped     .merge(verified_ratio, on='asin', how='left')     .merge(avg_length, on='asin', how='left')     .merge(review_variance, on='asin', how='left')     .merge(unique_authors, on='asin', how='left')

# Модель и признаки
X = df_features[[
    'avg_rating', 'review_count', 'verified_share',
    'avg_length', 'review_variance', 'num_unique_authors'
]]
y = df_features['total_helpful_votes']

model = CatBoostRegressor(n_estimators=100, random_state=42, verbose=0)
model.fit(X, y)

# SHAP
explainer = shap.Explainer(model)
shap_values = explainer(X)

# SHAP summary plot
shap.summary_plot(shap_values, X)

# Residuals
y_pred = model.predict(X)
residuals = y - y_pred
df_features['residual'] = residuals

# Top residuals
top_residuals = df_features[['asin', 'total_helpful_votes', 'residual']].copy()
top_residuals['abs_residual'] = top_residuals['residual'].abs()
top_residuals = top_residuals.sort_values(by='abs_residual', ascending=False).head(10)
print("\nTop 10 residual outliers:")
print(top_residuals)

# Residual plot
plt.figure(figsize=(10, 5))
plt.scatter(y_pred, residuals, alpha=0.6)
plt.axhline(0, color='red', linestyle='--')
plt.xlabel("Predicted helpful_votes")
plt.ylabel("Residual (Actual - Predicted)")
plt.title("Residual Plot for CatBoost")
plt.tight_layout()
plt.show()
