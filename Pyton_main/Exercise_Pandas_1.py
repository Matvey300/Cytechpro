
import sys
import time

import numpy as np
import pandas as pd
import rumpy

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

# my_panda = pd.DataFrame(np.random.randint(1,10, size=(5,3)), columns = ['A', 'B', 'C'])
# print(my_panda)
                       
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
Running_path = '/Users/Matvej1/Downloads/running.csv'
Albums_path = '/Users/Matvej1/Downloads/SellingAlbums (1).csv'
def extract_from_csv(file_to_process):
    dataframe = pd.read_csv(file_to_process)
    return dataframe

def Q1():
    running = extract_from_csv (Running_path)
    print(running)
    new_running = running.loc[running['Calories']>400]
    print (new_running)

def Q2():
    running = extract_from_csv (Running_path)
    new_running = running.loc[(running['Calories']>400) & (running['Duration']>=45) & (running['Average Pulse']>110)]
    print (new_running)


def Q3():
    running = extract_from_csv (Running_path)
    new_running = running.loc[(running['Calories']<300) |
                            (running['Maxpulse']>170)]
    new_running = new_running[['Duration','Maxpulse','Calories']]
    print (new_running)

def Q4():
    albums = extract_from_csv (Albums_path)
    new_albums = albums.set_index('Artist')
    new_albums = new_albums.loc['Michael Jackson']
    print (new_albums)


def Q5():
    albums = extract_from_csv(Albums_path)

    # Removing NAs, setting index to 'Artist', sorting by index
    new_albums = albums.dropna(subset=['Artist']).set_index('Artist').sort_index()

    # Converting Index to Series (in order to be able to use 'between' methode) ensuring all Indexes are strings 
    artist_series = pd.Series(new_albums.index.astype(str), index=new_albums.index)
    print(artist_series)
    print('-'*80)

    # Creating mask of booleans where true stands for M-S entries 
    mask = artist_series.str[0].between('M', 'S')
    print(mask)

    # Apply mask
    filtered = new_albums.loc[mask]
    print(filtered)


def Q6():
    # In SellingAlbums, where Soundtrack is NaN or empty, use .loc to set Soundtrack = 'N'. Where Soundtrack == 'Y', keep as is.

    albums = extract_from_csv(Albums_path)
    mask = albums['Soundtrack'].isna()

    albums.loc[mask, 'Soundtrack'] = 'N'
    print(albums)

def Q7():
# For each DataFrame (SellingAlbums, running), print the count AND percentage of missing values per column.
    albums = extract_from_csv(Albums_path)
    runnings = extract_from_csv(Running_path)
    df = albums.count().to_frame('Count')
    df['Percentage'] = (df['Count']/len(albums))*100
    print(df)
    print('-'*80)
    df = runnings.count().to_frame('Count')
    df['Percentage'] = (df['Count']/len(runnings))*100
    print(df) 

def Q8():
# In running, fill missing Maxpulse with the mean Maxpulse. In SellingAlbums, fill missing Rating with the column median. Show before/after null counts.
    albums = extract_from_csv(Albums_path)
    runnings = extract_from_csv(Running_path)
    print(albums)
    albums.fillna(albums.mean(numeric_only=True), inplace=True)
    print(albums)
    print('-'*80)

    print(runnings)
    runnings.fillna(runnings.mean(numeric_only=True), inplace=True)
    print(runnings)

def Q9():
    # Assume any Duration < 1 minute or > 300 minutes in running is invalid. Replace such values with NaN (use .loc masks), then report how many were replaced.
    runnings = extract_from_csv(Running_path)
    runnings.loc[(runnings['Duration']<1) | (runnings['Duration']>300), 'Duration'] = np.nan
    print(runnings['Duration'].count())


def Q10():
# SellingAlbums Genre strings are messy (e.g., 'pop, rock, R&B'). Create a cleaned Genre column by mapping strings that contain 'rock' to 'Rock', contain 'pop' to 'Pop', else 'Other'. Use vectorized string methods and .loc (or np.where).
    albums = extract_from_csv(Albums_path)

    print(albums['Genre'])

    albums.loc[albums['Genre'].str.upper().str.contains('ROCK', na=False), 'Genre'] = 'Rock'
    albums.loc[albums['Genre'].str.upper().str.contains('POP', na=False), 'Genre']= 'Pop'
    albums.loc[~albums['Genre'].str.contains('Pop|Rock'), 'Genre'] = 'Other'
 
    print(albums['Genre'])

def Q11():
# Convert SellingAlbums 'Released.1' into a proper datetime column. Where conversion fails, leave NaT and report which rows (use .loc to print them).
    albums = extract_from_csv(Albums_path)

    print(albums['Released.1'])
    try:
        albums['Released.1'] = pd.to_datetime(albums['Released.1'])
        print(albums['Released.1'])
    except:
        print('Conversion failed')
        print (albums.loc[albums['Released.1'].count()])


def Q12():
# Compare the integer 'Released' year to the year extracted from the datetime in q11. Use .loc to list rows where they disagree.
    albums = extract_from_csv(Albums_path)
    print(albums[['Released.1','Released']].head())
    albums['Released.1'] = pd.to_datetime(albums['Released.1'])
    albums['Released', 0] = 6789
    new_albums = albums.loc[albums['Released'] == (albums['Released.1'].dt.year)]
    print(new_albums[['Released', 'Released.1']].head())

def Q13():
#Group running by Duration (minutes). Use transform('mean') to compute group mean Calories and create a boolean column 'AboveDurationMean' that is True where each row's Calories > group mean.
    runnings = extract_from_csv(Running_path)
    print (runnings.groupby('Duration').mean())
    runnings.insert(1, 'AboveDurationMean', runnings['Duration']>runnings['Duration'].mean())
    runnings['AboveCaloriesMean'] = runnings['Calories']>runnings['Calories'].mean()
    print (runnings)

def Q14():
    










Q13()
