
import pandas as pd

from catboost import CatBoostRegressor

# Загрузка данных
df_reviews = pd.read_csv("/Users/Matvej1/CyberPro/Pyton_main/Pyton_Data_Analytic_project/DATA/search_results.csv")
df_search = pd.read_csv("/Users/Matvej1/CyberPro/Pyton_main/Pyton_Data_Analytic_project/DATA/all_reviews.csv")

df_search['product_name'] = df_search['title'].astype(str).str.slice(0, 50)

# Признаки
from textblob import TextBlob
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

df_features = df_grouped \
    .merge(verified_ratio, on='asin', how='left') \
    .merge(avg_length, on='asin', how='left') \
    .merge(review_variance, on='asin', how='left') \
    .merge(unique_authors, on='asin', how='left')

# Модель
X = df_features[[
    'avg_rating', 'review_count', 'verified_share',
    'avg_length', 'review_variance', 'num_unique_authors'
]]
y = df_features['total_helpful_votes']

model = CatBoostRegressor(n_estimators=100, random_state=42, verbose=0)
model.fit(X, y)

# Residuals
df_features['y_pred'] = model.predict(X)
df_features['residual'] = df_features['total_helpful_votes'] - df_features['y_pred']
df_features['abs_residual'] = df_features['residual'].abs()

# Подозрительные ASIN
sus = df_features[df_features['verified_share'] < 0.5] \
    .sort_values(by='abs_residual', ascending=False).head(10)

sus = sus.merge(df_search[['asin', 'product_name']], on='asin', how='left')

# Вывод
print(sus[['asin', 'product_name', 'verified_share', 'total_helpful_votes',
           'y_pred', 'residual', 'avg_rating', 'review_count', 'review_variance']])
