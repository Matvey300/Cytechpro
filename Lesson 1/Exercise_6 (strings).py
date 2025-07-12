

#Q1
my_string = ['foo', 'bar', 'baz']
res_string = []
for i in my_string:
    res_string.append(i[0])
    print (res_string[-1])
#Q2
my_string = [1, 2, 3, 4, 5]
res_string = []
for i in my_string:
    res_string.append(int(i)**2)
    print (res_string[-1])

#Q3
my_string =  [1,2,3,4,5,6,7,8]
res_string = []
for i in my_string:
    if int(i)%2 != 0:
        res_string.append(i)
        print (res_string[-1])

#Q4
list1 = [1,2,3] 
list2 = [4,5,6]
res_list = list1 + list2
print (res_list)

#Q5
my_string = ['foo', 'bar', 'baz','Messi'] 
my_dict = {}
for i in my_string:
    my_dict[i] = len(i)
print (my_dict)

#Q6
my_string = ['bad', 'mad', 'glad']
res_string = []
for i in my_string:
    if i!= "mad":
        res_string.append(i)
        print (res_string[-1])

#Q7
my_string = ['foo', 'bar', 'baz']
my_counter = 0
for i in my_string:
    if 'a' in i:
        my_counter = my_counter+1
print (my_counter)

#Q8
my_string = [1, 2, 3, 4]
res_string = []
for i in my_string:
    res_string.append(str(i)+'0')
print (res_string)

#Q9
my_string =  ['', 'foo', '', 'bar', 'baz']
res_string = []
for i in my_string:
    if i!= "":
        res_string.append(i)
print (res_string)


