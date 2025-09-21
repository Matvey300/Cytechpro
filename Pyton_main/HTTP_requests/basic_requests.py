import requests

print(requests)
# requests.get
# requests.post
# requests.put
# requests.patch
# requests.delete
# url = 'https://httpbin.org/post/'
# body = {
#     'key1' : 12,
#     'key2' : 'hello',
#     'key3' : [1, 4, 5, 56, True],
# }
# responce = requests.get(url, json=body)
# print (responce.json())
url = "https://official-joke-api.appspot.com/jokes/random"
urlw = "http://api.weatherapi.com/v1"

# # # Q1
# while True:
#     response = requests.get(url).json()
#     print (response)
#     setup = response['setup']
#     punchline = response['punchline']
#     if 'banana' in str(setup) or 'banana' in str(punchline):
#         print (response['setup'])
#         print (response['punchline'])
#         break

# i = 1
# ratings = []

# while i <= 10:
#     response = requests.get(url).json()
#     setup = response['setup']
#     punchline = response['punchline']
#     joke_id = response['id']

#     print('-' * 40)
#     print(f"\nJoke {i}")
#     print(setup)
#     print(punchline)

#     while True:
#         try:
#             rating = int(input("Input score from 0 to 9: "))
#             if 0 <= rating <= 9:
#                 break
#             else:
#                 print("Please enter a number between 0 and 9.")
#         except ValueError:
#             print("That's not a number. Try again.")

#     ratings.append({'id': joke_id, 'setup': setup, 'punchline': punchline, 'rating': rating})
#     i += 1

# # Optional: вывод всех оценок
# print("\nYour Ratings Summary:")
# for r in ratings:
#     print(f"Joke ID {r['id']}: rating {r['rating']}")
#     print (f"Average rating: {sum(r['rating'] for r in ratings) / len(ratings)}")

# # Q3
# response = requests.get(url).json()
# setup = response['setup']
# punchline = response['punchline']

# print('-' * 40)
# print("\nJoke")
# print(setup)
# print(punchline)

# # Q4
# long_jokes = []
# i = 1
# while i <= 10:
#     response = requests.get(url).json()
#     setup = response['setup']
#     punchline = response['punchline']
#     joke_id = response['id']
#     if len(setup)+ len(punchline) > 50:
#         long_jokes.append ({'id': joke_id, 'setup': setup, 'punchline': punchline})


# for r in long_jokes:
#     print(f"Joke ID {r['id']}: rating {r['rating']}")

API_KEY = "f5619756d1a94a3796b150247251207"
city = "Moscow"
date = "2025-06-07"

urlw = "http://api.weatherapi.com/v1/history.json"


params = {
    "key": API_KEY,
    "q": city,
    "dt": date,
    # 'lang': 'en'  # можно заменить на 'ru' для русского языка
}

response = requests.get(urlw, params=params)

if response.status_code == 200:
    data = response.json()
    day_data = data["forecast"]["forecastday"][0]["day"]

    location = data["location"]["name"]
    country = data["location"]["country"]

    temp_c = day_data["avgtemp_c"]
    max_temp = day_data["maxtemp_c"]
    min_temp = day_data["mintemp_c"]
    condition = day_data["condition"]["text"]

    print(f"\n📅 Weather in {city} on {date}:")
    print(f"   Avg Temp: {day_data['avgtemp_c']}°C")
    print(f"   Max Temp: {day_data['maxtemp_c']}°C")
    print(f"   Min Temp: {day_data['mintemp_c']}°C")
    print(f"   Condition: {day_data['condition']['text']}")
else:
    print(f"❌ Error: {response.status_code} — {response.text}")
