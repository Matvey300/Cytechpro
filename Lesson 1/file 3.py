def main():
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
        elif choice == 'exit':
            print("Goodbye!")
            break
        else:
            print("Invalid selection. Please choose 1, 2, or exit.")

def basic_calculator():
    print("\n--- Basic Calculator ---")
    try:
        num1 = float(input("Enter first number: "))
        op = input("Enter operation (+, -, *, /): ").strip()
        num2 = float(input("Enter second number: "))
        
        if op == '+':
            result = num1 + num2
        elif op == '-':
            result = num1 - num2
        elif op == '*':
            result = num1 * num2
        elif op == '/':
            result = num1 / num2
        else:
            print("Invalid operation. Using + as default.")
            result = num1 + num2
            
        print(f"Result: {result}")
    except ValueError:
        print("Invalid number input")
    except ZeroDivisionError:
        print("Error: Division by zero")

def smart_calculator():
    print("\n--- Smart Calculator ---")
    expression = input("Enter a math expression: ").strip()
    tokens = tokenize(expression)
    result = evaluate_expression(tokens)
    print(f"Result: {result}")

def tokenize(expression):
    tokens = []
    current_token = ''
    
    for char in expression:
        if char.isspace():
            if current_token:
                tokens.append(current_token)
                current_token = ''
        elif char in '()+-*/':
            if current_token:
                tokens.append(current_token)
                current_token = ''
            tokens.append(char)
        else:
            current_token += char
    
    if current_token:
        tokens.append(current_token)
    
    return tokens

def evaluate_expression(tokens):
    # Convert tokens to numbers and operators
    parsed_tokens = []
    for token in tokens:
        if token in '()+-*/':
            parsed_tokens.append(token)
        else:
            try:
                parsed_tokens.append(float(token))
            except ValueError:
                parsed_tokens.append(token)
    
    # Handle parentheses recursively
    while '(' in parsed_tokens:
        start = None
        end = None
        depth = 0
        
        # Find innermost parentheses
        for i, token in enumerate(parsed_tokens):
            if token == '(':
                start = i
                depth = 1
            elif token == ')':
                if depth == 1 and start is not None:
                    end = i
                    break
                depth -= 1
        
        if start is None or end is None:
            break
            
        # Evaluate expression inside parentheses
        sub_expression = parsed_tokens[start+1:end]
        sub_result = evaluate_expression(sub_expression)
        
        # Replace parentheses with result
        parsed_tokens = parsed_tokens[:start] + [sub_result] + parsed_tokens[end+1:]
    
    # Handle multiplication and division
    i = 0
    while i < len(parsed_tokens):
        token = parsed_tokens[i]
        if token == '*':
            left = parsed_tokens[i-1]
            right = parsed_tokens[i+1]
            result = left * right
            parsed_tokens = parsed_tokens[:i-1] + [result] + parsed_tokens[i+2:]
            i -= 1  # Stay at current position after removal
        elif token == '/':
            left = parsed_tokens[i-1]
            right = parsed_tokens[i+1]
            result = left / right
            parsed_tokens = parsed_tokens[:i-1] + [result] + parsed_tokens[i+2:]
            i -= 1  # Stay at current position after removal
        else:
            i += 1
    
    # Handle addition and subtraction
    i = 0
    while i < len(parsed_tokens):
        token = parsed_tokens[i]
        if token == '+':
            left = parsed_tokens[i-1]
            right = parsed_tokens[i+1]
            result = left + right
            parsed_tokens = parsed_tokens[:i-1] + [result] + parsed_tokens[i+2:]
            i -= 1
        elif token == '-':
            left = parsed_tokens[i-1]
            right = parsed_tokens[i+1]
            result = left - right
            parsed_tokens = parsed_tokens[:i-1] + [result] + parsed_tokens[i+2:]
            i -= 1
        else:
            i += 1
    
    return parsed_tokens[0]

if __name__ == "__main__":
    main()