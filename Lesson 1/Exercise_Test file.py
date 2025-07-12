def find_matching_bracket(s, start):
        #Finds matching closing  bracket
        count = 1
        for i in range(start + 1, len(s)):
            if s[i] == '(':
                count += 1
            elif s[i] == ')':
                count -= 1
            if count == 0:
                return i
        return -1  # No matching closing  bracket



def calculate(s):
        # To calculate expression
        i = 0
        result = 0
        current_op = '+'
        priority_op = ''
        priority_res = 0

        while i < len(s):
            if s[i] == '(':
                j = find_matching_bracket(s, i)
                if j == -1:
                    print ("Wrong brackets order")
                    break
                operand = calculate(s[i + 1:j])
                i = j + 1
            elif s[i].isdigit() or s[i] == '.':
                j = i
                while j < len(s) and (s[j].isdigit() or s[j] == '.'):
                    j += 1
                operand = float(s[i:j])
                i = j
            elif s[i] in '*/' and priority_res == 0:
                 priority_op = s[i]    
                 priority_res = operand
            elif s[i] in '+-' and priority_op == '':
                if current_op == '+':
                    result += operand
                elif current_op == '-':
                    result -= operand
                current_op = s[i]
                i += 1
            elif s[i] in '+-' and priority_op != '':
                if priority_op == "*":
                    result = priority_res*operand
                elif priority_op == '/':
                    result = priority_res/operand
                priority_op = ''
                priority_res = 0
            elif s[i] in '*/' and priority_op != '':
                if priority_op == "*":
                    operand = priority_res*operand
                elif priority_op == '/':
                    operand = priority_res/operand
                priority_op = s[i]
                priority_res = operand

            elif s[i] == ' ':
                i += 1
            else:
               print(f"Worng symbol: {s[i]}")
               break


        if current_op == '+' and priority_op == '':
            result += operand
        elif current_op == '-' and priority_op == '':
            result -= operand
        elif priority_op == '*':
            result = result*operand
        elif priority_op == '/':
            result = result/operand
        return result