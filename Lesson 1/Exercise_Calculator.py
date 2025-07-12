MATH_STR = ['(', ')', '+', '-', '*', '/']
PRIOR_MATH = ['*', '/']
def show_menu():
    while True:
        print("\n===== Calculator Menu =====")
        print("[1] Basic Calculator")
        print("[2] Smart Calculator")
        print("[exit] Exit Program")
        choice = input("Select an option: ").strip().lower()

        if choice == '1' or choice == 'basic':
            basic_calculator()
        elif choice == '2' or choice == 'smart':
            smart_calculator()
            # print("Smart Calculator coming soon!")
        elif choice == 'exit':
            print("Goodbye!")
            return
        else:
            print("Invalid selection. Please choose 1, 2, or exit.")


def basic_calculator():
    global MATH_STR
    print("\n--- Basic Calculator ---")
    try:
        num1 = float(input("Enter first number: "))
    except Exception as e:
        print(e)
        return
    try:
        op = input("Enter operation (+, -, *, /): ").strip()
        if op not in MATH_STR:
            raise ValueError 
    except:
        print("Wrong symbol")
        return  

    try:
        num2 = float(input("Enter second number: "))
    except ValueError:
        print ('Wrong symbol')
        return
    
    try:
        if op == '+':
            result = num1 + num2
        elif op == '-':
            result = num1 - num2
        elif op == '*':
            result = num1 * num2
        elif op == '/':
            result = num1 / num2
        else:
            print("Invalid operation")
            show_menu()
    except Exception as e:
        print(e)



    print(f"Result: {result}")


def find_matching_bracket(s, start):
        #Finds matching closing  bracket
        print ('hello from find_matching_bracket')
        print (s, start)
        count = 1
        for i in range(start + 1, len(s)):
            print (i, s[i])
            if s[i] == '(':
                count += 1
            elif s[i] == ')':
                count -= 1
            if count == 0:
                return i
        return -1  # No matching closing  bracket

def tokenize (s):
    print (s)
    global MATH_STR
    i=0
    tokenized = []
    while i < len(s):
        if s[i].isdigit() or s[i] == '.':
            j = i
            while j < len(s) and (s[j].isdigit() or s[j] == '.'):
                j += 1
            operand = float(s[i:j])
            i = j
            tokenized.append(operand)    
        elif s[i] in MATH_STR:
            operand = str(s[i])
            tokenized.append(operand) 
            i += 1
        else:
            i += 1
    print (tokenized)
    return tokenized

def solve_brackerts(s):
    print ('hello from solve_brackerts')
    i = 0
    j = 0
    list = s
    while i < len(s):
        ind = 0
        print (s[i])
        if s[i] == '(':
            ind = i
            j = find_matching_bracket(s, i)
            print (f'hello from solve_brackerts j = {j}')
            
            if j == -1:
                print ("Wrong brackets order")
                return
            print (f'From solve_brackets - part in bracets {s[(i+1):j]}')
            operand = calculate(s[i + 1:j])
            print (f'hello from solve_brackerts {list}, {operand}, {j}')
            list[i:j+1] = [operand]
            print (f'From solve_brackets - part in bracets {operand}')
            print (list)
            i = j + 1
        else:
            i+=1
    return(list)



def calculate(s):
        print (f'hello from calculate {s}')
        # To calculate expression
        global PRIOR_MATH
        i = 0
        res_list = []
        result = 0
        operand = 0
        print('-'* 40)
        print (len(s))
        while i < len(s):
            if s[i] in PRIOR_MATH:
                print (f'hello from calculate PRIOR {s[i]}')
                try:
                    if s[i] == '*':
                        operand = s[i-1]*s[i+1]
                    elif s[i] == '/':
                        operand = s[i-1]/s[i+1]
                    print (f'hello from calculate {operand}')
                    return operand
                except:
                    print ('Wrong string structure')
                    return
            i +=1
        print ('Test 2')
        i=0              
        while i < len(s):
            print (f'hello from calculate NON_PRIOR {s[i]}')
            try:
                if s[i] == '+':
                    operand = s[i-1]+s[i+1]
                elif s[i] == '-':
                    operand = s[i-1]-s[i+1]
                    print (f'hello from calculate_ZZZZZZZ {s[i-1]-s[i+1]}.  = {operand}')
                return operand
            except:
                print ('Wrong string structure')
                return
            i +=1

            

def smart_calculator():
    smart_result = 0
    expression = []
    print("\n--- Smart Calculator ---")
    expression = input("Enter your expression like  2 + 3 * (4 - 1): ")
    expression = tokenize(expression)
    expression = solve_brackerts (expression)
    smart_result = calculate(expression)
    print(f"Result: {smart_result}")

show_menu()
