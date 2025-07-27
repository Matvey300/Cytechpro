
import rumpy
import time 
import sys
import numpy as np 
import pandas as pd

purchases = [
    {'product': 'Laptop', 'price': 1200, 'quantity': 2},
    {'product': 'Mouse', 'price': 25, 'quantity': 5},
    {'product': 'Headphones', 'price': 120, 'quantity': 3},
    {'product': 'Keyboard', 'price': 50, 'quantity': 2},
    {'product': 'Laptop', 'price': 1100, 'quantity': 1},
    {'product': 'Headphones', 'price': 200, 'quantity': 1}
]
DF = pd.DataFrame(purchases)

def QA1(df):
    df['revenue'] = df['price']*df['quantity']
    total_revenue = df['revenue'].sum()
    print(total_revenue)

def QB1(df):
    df_1 = df[df['quantity']>2]['product'].tolist()
    print(df_1)

def Q1C(df):
    df['revenue'] = df['price']*df['quantity']
    highest_revenue = df.loc[df['revenue'].idxmax()]
    print(highest_revenue)


def Q1D(df):
    df_1 = df.groupby('product')['price'].mean().reset_index()
    print(df_1)
    i = int(input ('Input product name index from list: '))
    print(df_1.loc[i, 'price'])

def Q1E(df):
    df_1 = df.groupby('product')['price'].mean().reset_index()
    print(df_1)
    i = int(input ('Input your budget: '))
    print(df_1.loc[df['price']<=i])

def Q2():
    n = int(input('Input number of Catalans: '))
    if n <= 0:
        return np.array([], dtype=int)
    
    catalan = np.zeros(n, dtype=int)
    catalan[0] = 1  # C0 = 1

    for i in range(1, n):
        catalan[i] = sum(catalan[j] * catalan[i - 1 - j] for j in range(i))
    
    print(catalan)

def Q3():
    my_str = (input('Input string: '))
    if len(list(my_str)) ==0:
        return 
    
    my_np = np.array(list(my_str))
    print (my_np)
    for i in my_np:
        if np.count_nonzero(my_np == i) < 2:
            print(f'The symbol is: {i}')
            break

def Q4():
    my_list = list(input('Input set of numbers: '))
    my_num = int(input('Input number: '))
    if len(list(my_list)) ==0:
        return 
    
    my_np = np.array(my_list)
    print (my_np)
    for i in range(len(my_np)):
        if int(my_np[i]) == my_num:
            print(f'{my_np[i]} equal to {my_num}')
            continue
        for j in range(i+1, len(my_np)):
            if (int(my_np[i])+int(my_np[j])) == my_num:
                print(f'Combination {my_np[i]}+{my_np[j]} gives {my_num}')


 

Q4()


      