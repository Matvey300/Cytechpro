# Guessing game
my_num = int(input("Guess number: "))
while my_num != 5:
    print("Nope, wrong guess")
    my_num = int(input("Please guess again: "))
print("Nicely done, it was 5")


# Q1
my_result = 0
for num in range(100):
    if num % 3 == 0 or num % 5 == 0:
        my_result = my_result + num
        print(my_result)


# Q2
my_num = int(input("Input number: "))
i = 2
while i < my_num:
    if my_num % i == 0 and my_num != 1:
        print("Not a prime number ", i)
        break
if i > my_num - 1:
    print("That was prime number", i)


# Q3


# Q4


# Q5
