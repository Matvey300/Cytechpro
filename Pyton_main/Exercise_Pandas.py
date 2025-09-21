import numpy as np
import pandas as pd

# data = {
#     'names': ['Dor', 'sasi', 'moshe'],
#     'scores': [100, 95, 78],
#     'more_data': ['aaaaa', 'bbbb', 'cccc']}

# my_panda = pd.DataFrame(data)
# print(my_panda)
# print ('-'*60)
# my_new_panda = my_panda.loc[my_panda['scores'] > 85]
# print (my_new_panda)
# print ('-'*60)
# my_list = [1,2,3,4,5]
# my_series = pd.Series(my_list)
# print(my_series)
# print ('-'*60)

my_panda = pd.DataFrame(np.random.randint(1, 10, size=(5, 3)), columns=["A", "B", "C"])
print(my_panda)

# print ('-'*80)

# my_panda = pd.DataFrame(np.random.randint(2,5, size=(5,3)), columns = ['Nina', 'Vera', 'Sara'])
# print(my_panda)

# print ('-'*80)

# my_panda = pd.DataFrame(np.random.randint(2,5, size=(5,3)), columns = ['Nina', 'Vera', 'Sara'], index = ['Geo', 'Phi', 'Math', 'Lit', 'Che'])
# print(my_panda)

# print ('-'*80)

# my_new_panda = my_panda.loc[my_panda['Vera'] > 3, 'Vera']
# print(my_new_panda)
# print ('-'*80)

# my_new_panda =  my_panda.loc[my_panda.gt(3).any(axis=1)]
# print(my_new_panda)
# print ('-'*80)

# my_new_panda =  my_panda.loc[my_panda.gt(2).all(axis=1)]

# # Дальше 3 варианта того же самого от преподавателя. Третий вариант совпадает с моим.
# # new_df=table.loc[(table['a']>80) & (table['b']>80) & (table['c']>80)]
# # new_df=table.loc[((table[['a','b','c']] >80).all(axis=1)),['a','b','c']]
# # df_high_score = table.loc[table.gt(80).all(axis = 1)]

# print(my_new_panda)
# print ('-'*80)

sales_data = pd.DataFrame({"Product": ["A", "B", "C", "A", "B"], "Price": [10, 20, 15, 12, 18]})

rev = sales_data["Price"].sum()
print(rev)

sales_data.to_csv("sales_data.csv", index=1)
