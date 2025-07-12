import requests
print (requests)
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
url = 'https://official-joke-api.appspot.com/jokes/random'

while True:
    responce =requests.get(url)
    print (responce)
    setup = responce.json()['setup'] 
    punchline = responce.json()['punchline']
    if 'banana' in str(setup) or 'banana' in str(punchline):
        print (responce.json()['setup'])
        print (responce.json()['punchline'])
        break

i=1
Rating = {'j_ID', 0,
          'rating', 0,}
while i < 11:
    responce =requests.get(url)
    setup = responce.json()['setup'] 
    punchline = responce.json()['punchline']
    id = responce.json()['id']
    print ('-'*20)
    print (f'\n Joke {i}')
    print (f'\n {setup}')
    print (f'\n {punchline}')
    print (f'\n {punchline}')

    Rating['j_ID', i] = id
    Rating['rating', i] = int(input('Input score from 0 to 9: '))
    i+=1



    





