# Q1
my_number = float(input("Input number: "))
if my_number > 0:
    print("Positive")
elif my_number < 0:
    print("Negative")
else:
    print("Zero")
# Q2
my_number = int(input("Input Year: "))
if my_number % 4 > 0:
    print("Not leap year")
else:
    print("Leap year")
# Q3
my_number = float(input("Input number: "))
if my_number % 2 > 0:
    print("Odd number")
else:
    print("Even number")
# Q4
num1 = float(input("Input number 1: "))
num2 = float(input("Input number 2: "))
num3 = float(input("Input number 3: "))

if num1 > num2 and num1 > num3:
    print("The largest number is ", num1)
elif num2 > num1 and num2 > num3:
    print("The largest number is ", num2)
else:
    print("The largest number is ", num3)

# Q5
my_str = input("Input Letter: ")
my_str = my_str.upper()
my_tuple = ("A", "E", "I", "O", "U")
if my_str in my_tuple:
    print("The letter is vowel")
else:
    print("The letter is consonant")

# Q6
my_string = input("Input string: ")
my_str = my_str.upper()
my_reversed_str = reversed(my_str)
if my_str == my_reversed_str:
    print("The string is palindrome")
else:
    print("The string is not palindrome")


# Q7

my_float = float(input("Input percentage: "))
if my_float > 0 and my_float <= 20:
    print("Grade E")
elif my_float > 20 and my_float <= 40:
    print("Grade D")
elif my_float > 40 and my_float <= 60:
    print("Grade C")
elif my_float > 60 and my_float <= 80:
    print("Grade B")
elif my_float > 80 and my_float <= 100:
    print("Grade A")
else:
    print("Wrong value")

# Q8
my_number = int(input("Input Year: "))
if my_number % 100 > 0:
    print("Not century year")
else:
    print("Century year")

# Q9
my_number = int(input("Input number: "))
my_number = my_number**0.5
if my_number % 1 == 0:
    print("Perfect sqare ")
else:
    print("Not perfect sqare")

# Q10
num1 = float(input("Input Length of side 1: "))
num2 = float(input("Input Length of side 2: "))
num3 = float(input("Input Length of side 3: "))

if num1 == num2 and num1 == num3:
    print("The triangle is equilateral")
elif num2 == num1 or num2 == num3 or num1 == num3:
    print("ThThe triangle is isosceles")
else:
    print("ThThe triangle is scalene")
