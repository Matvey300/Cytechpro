# Q1
my_string = ["foo", "bar", "baz"]
res_string = []
# for i in my_string:
#     res_string.append(i[0])
#     print (res_string[-1])
res_string = [s[0] for s in my_string]
print(res_string)

# Q2
my_string = [1, 2, 3, 4, 5]
res_string = []
# for i in my_string:
#     res_string.append(int(i)**2)
res_string = [int(i) ** 2 for i in my_string]
print(res_string)

# Q3
my_string = [1, 2, 3, 4, 5, 6, 7, 8]
res_string = []
# for i in my_string:
#     if int(i)%2 != 0:
#         res_string.append(i)
#         print (res_string[-1])
res_string = [i for i in my_string if int(i) % 2 == 0]
print(res_string)


# Q4
list1 = [1, 2, 3]
list2 = [4, 5, 6]
res_list = list1 + list2
print(res_list)

# Q5
my_string = ["foo", "bar", "baz", "Messi"]
my_dict = {}
# for i in my_string:
#     my_dict[i] = len(i)

my_dict = {i: len(i) for i in my_string}
print(my_dict)

# Q6
my_string = ["bad", "mad", "glad"]
res_string = []
# for i in my_string:
#     if i!= "mad":
#         res_string.append(i)

res_string = [i for i in my_string if i != "mad"]
print(res_string)

# Q7
my_string = ["foo", "bar", "baz"]
my_counter = 0
# for i in my_string:
#     if 'a' in i:
my_counter = sum(1 for i in my_string if "a" in i)
print(my_counter)

# Q8
my_string = [1, 2, 3, 4]
res_string = []
# for i in my_string:
#     res_string.append(str(i)+'0')

res_string = list(int(i) * 10 for i in my_string)
print(res_string)

# Q9
my_string = ["", "foo", "", "bar", "baz"]
res_string = []
for i in my_string:
    if i != "":
        res_string.append(i)
print(res_string)
