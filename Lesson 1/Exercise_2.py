#Q1
my_list = ['apple', 'banana', 'cherry']
#Q2
my_list.append('date')
#Q3
print(len(my_list)) 
#Q4
my_list.remove('apple')
#Q5
my_list.sort()
print(my_list)
#Q6
my_set = {3, 1, 4, 1, 5, 9}
#Q7
if 7 in my_set: 
    print(7)
else: 
    print("No")
#Q8
my_tuple = ('dog', 'cat', 'fish')
#Q9
print(my_tuple[2])
#Q10
my_list = list(my_tuple)
#Q11
my_list = [[10, 20], [30, 40]]
#Q12
print(my_list[1][1])
#Q13
print(type(my_list))
#Q14
my_set = [12, 5, 8]
my_set.sort()
print(my_set[-1])

#Q15
def sort_my_set (list):
    list.sort()
    return list
print(sort_my_set([6, 4, 2]))

#Q16
def multiply_numbers(list):
    return list[0]*list[1]
#Q17

print(multiply_numbers([2, 7]))
#Q18

def calculate_square (list):
    return list[0]**list[1]
#Q19

print(calculate_square([6, 2]))

#Q20
def calculate_average (list):
    return sum(list)/len(list)

#Q21
print(calculate_average([3,4,5]))