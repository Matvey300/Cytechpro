import os

MATH_STR = ['(', ')', '+', '-', '*', '/']
PRIOR_MATH = ['*', '/']
RESULTS_FILE = "results.txt"

def show_menu():
    while True:
        print("\n===== Calculator Menu =====")
        print("[1] Basic Calculator")
        print("[2] Smart Calculator")
        if os.path.exists(RESULTS_FILE):
            print("[3] Recall Previous Results")
        print("[exit] Exit Program")

        choice = input("Select an option: ").strip().lower()

        if choice == '1' or choice == 'basic':
            basic_calculator()
        elif choice == '2' or choice == 'smart':
            smart_calculator()
        elif choice == '3' and os.path.exists(RESULTS_FILE):
            recall_previous_results()
        elif choice == 'exit':
            print("Goodbye!")
            return
        else:
            print("Invalid selection. Please choose a valid option.")

def write_result_to_file(expression, result):
    """
    Appends a successfully computed expression and its result to RESULTS_FILE.
    """
    try:
        with open(RESULTS_FILE, "a") as f:
            f.write(f"{expression} = {result}\n")
    except Exception as e:
        print(f"Error writing to results file: {e}")

def recall_previous_results():
    """
    Displays the contents of the results file if it exists.
    """
    print("\n--- Previous Results ---")
    try:
        with open(RESULTS_FILE, "r") as f:
            content = f.read()
            if content.strip() == "":
                print("No previous results found.")
            else:
                print(content.strip())
    except Exception as e:
        print(f"Error reading results file: {e}")

def basic_calculator():
    print("\n--- Basic Calculator ---")
    try:
        num1 = float(input("Enter first number: "))
        op = input("Enter operation (+, -, *, /): ").strip()
        if op not in ['+', '-', '*', '/']:
            print("Invalid operator.")
            return
        num2 = float(input("Enter second number: "))

        if op == '+':
            result = num1 + num2
        elif op == '-':
            result = num1 - num2
        elif op == '*':
            result = num1 * num2
        elif op == '/':
            if num2 == 0:
                print("Error: Division by zero.")
                return
            result = num1 / num2
        else:
            print("Invalid operation.")
            return

        print(f"Result: {result}")
        write_result_to_file(f"{num1} {op} {num2}", result)

    except ValueError:
        print("Invalid input. Please enter numeric values.")
    except Exception as e:
        print(f"Unexpected error: {e}")

def find_matching_bracket(tokens, start):
    count = 1
    for i in range(start + 1, len(tokens)):
        if tokens[i] == '(':
            count += 1
        elif tokens[i] == ')':
            count -= 1
        if count == 0:
            return i
    return -1

def tokenize(s):
    tokens = []
    i = 0
    while i < len(s):
        if s[i].isdigit() or s[i] == '.':
            j = i
            while j < len(s) and (s[j].isdigit() or s[j] == '.'):
                j += 1
            try:
                tokens.append(float(s[i:j]))
            except ValueError:
                print(f"Invalid number: {s[i:j]}")
                return None
            i = j
        elif s[i] in MATH_STR:
            tokens.append(s[i])
            i += 1
        elif s[i] == ' ':
            i += 1
        else:
            print(f"Invalid character encountered: {s[i]}")
            return None
    return tokens

def solve_brackets(tokens):
    i = 0
    while i < len(tokens):
        if tokens[i] == '(':
            j = find_matching_bracket(tokens, i)
            if j == -1:
                print("Error: Unmatched parentheses.")
                return None
            inner_tokens = tokens[i + 1:j]
            solved_value = calculate(solve_brackets(inner_tokens))
            if solved_value is None:
                return None
            tokens = tokens[:i] + [solved_value] + tokens[j + 1:]
            i = 0
        else:
            i += 1
    return tokens

def calculate(tokens):
    if tokens is None:
        return None
    try:
        i = 0
        while i < len(tokens):
            if tokens[i] in PRIOR_MATH:
                op = tokens[i]
                a = tokens[i - 1]
                b = tokens[i + 1]
                if op == '*':
                    result = a * b
                elif op == '/':
                    if b == 0:
                        print("Error: Division by zero.")
                        return None
                    result = a / b
                tokens = tokens[:i - 1] + [result] + tokens[i + 2:]
                i = 0
            else:
                i += 1

        i = 0
        while i < len(tokens):
            if tokens[i] in ['+', '-']:
                op = tokens[i]
                a = tokens[i - 1]
                b = tokens[i + 1]
                if op == '+':
                    result = a + b
                elif op == '-':
                    result = a - b
                tokens = tokens[:i - 1] + [result] + tokens[i + 2:]
                i = 0
            else:
                i += 1

        if len(tokens) == 1:
            return tokens[0]
        else:
            print("Error: Could not fully evaluate the expression.")
            return None

    except (IndexError, TypeError) as e:
        print(f"Error during calculation: {e}")
        return None

def smart_calculator():
    print("\n--- Smart Calculator ---")
    try:
        raw_expression = input("Enter your expression (e.g., 2 + 3 * (4 - 1)): ")
        if not raw_expression.strip():
            print("Empty input, please enter a valid expression.")
            return

        tokens = tokenize(raw_expression)
        if tokens is None:
            print("Error during tokenization.")
            return

        tokens = solve_brackets(tokens)
        if tokens is None:
            print("Error while resolving brackets.")
            return

        result = calculate(tokens)
        if result is not None:
            print(f"Result: {result}")
            write_result_to_file(raw_expression, result)
        else:
            print("Calculation failed due to input errors.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

show_menu()
