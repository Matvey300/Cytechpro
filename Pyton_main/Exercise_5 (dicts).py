# #Q1
my_dict = {}
my_word = ""

while my_word != "stop":
    my_word = input("Input word: ")

    if my_word not in my_dict.keys():
        my_dict[my_word] = 1
    else:
        my_dict[my_word] = my_dict[my_word] + 1
print(my_dict)


# #Q2
my_dict = {}

dict_1 = {"key1": 1, "key2": 3, "key3": 4}

dict_2 = {"key1": 1, "key2": 5, "key3": 4}

for i in dict_1:
    for j in dict_2:
        if dict_1[i] == dict_2[j]:
            my_dict[i] = dict_2[j]

print(my_dict)


# #Q3

my_result = 0

dict_1 = {"key1": 1, "key2": 8, "key6": 8, "key3": "bbb"}


for i in dict_1:
    if type(dict_1[i]) == int:
        my_result = my_result + dict_1[i]

print(my_result)


# Q4

my_dict = {}
my_word = ""
my_string = input("Input sentence: ")
my_list = my_string.split()
print(my_list)
for i in my_list:
    if i not in my_dict.keys():
        my_dict[i] = 1
    else:
        my_dict[i] = my_dict[i] + 1
print(my_dict)


# Q5
dict_1 = {"key1": 1, "key2": 3, "key3": 4}
my_dict = {}
for key, value in dict_1.items():
    my_dict[value] = key
print(dict_1)
print(my_dict)

# Q6
dict_1 = {"key1": 1, "key2": 3, "key3": 4}
my_dict = {}
my_dict = dict(sorted(dict_1.items(), key=lambda dict_1: dict_1[1], reverse=True))
print(dict_1)
print(my_dict)

# Q7
my_list = (
    {"key1": 8, "key2": 3, "key3": 4},
    {"key1": 1, "key2": 4, "key3": 7},
    {"key1": 7, "key4": 4, "key3": 9},
)
j = 1
for i in my_list:
    print(f"List of Keys in Dict {j} is {i.keys()}")
    j = j + 1
sort_key = input("Print the Key you want to use for sorting: ")
for i in my_list:
    if sort_key in i.keys():
        continue
    else:
        print("Selected Key dosen't present in all dictionaries")
        break
sorted_list = sorted(my_list, key=lambda my_list: my_list[sort_key])
print(sorted_list)
