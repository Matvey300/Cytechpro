
import rumpy
import time 
import sys
import numpy as np 


def Q1():
    arr = ([i for i in range(1,5)])
    print (arr)

# Q1()

def Q2():
    arr = np.zeros((3, 4))
    print (arr)

# Q2()

# def Q3():
#     arr1 = np.array([1,2,3])
#     arr2 = np.array([4,5,6])
#     arr = arr1+arr2
#     print (arr)

# Q3()

def Q5():
    arr1 = np.array([1,2,3,6])
    av = np.mean(arr1)
    print (av)

# Q5()

def Q6():
    arr1 = np.array([1,1,2,3,6,12,18])
    av = np.mean(arr1)
    arr = arr1[arr1>av]
    print (arr)

# Q6()

def Q7():
    arr1 = np.array([1,1,2,3,6,12,18])
    max = np.max(arr1)
    arr = max-arr1
    print (arr)

# Q7()

def Q8():
    arr1 = np.random.randint(-200, 200, size=10) 
    my_unique = np.unique(arr1)
    print(arr1)
    print (my_unique)

# Q8()

def Q91():
    arr1 = [[2, 5, 7], [1, 8, 11]]
    arr2 = [[3, 8, 4], [10, 2, 6]]
    arr = np.concatenate((arr1, arr2))
    print (arr)
    arr = np.vstack((arr1, arr2))
    print (arr)
    arr = np.hstack((arr1, arr2))
    print (arr)

# Q91()

def Q92():
    arr1 = np.array([[2, 5, 7], [1, 8, 11], [3, 8, 4], [10, 2, 6]])
    arr2 = np.array([[[2, 5, 7], [1, 8, 11]], [[3, 8, 4], [10, 2, 6]]])
    arr3 = np.array([[2, 5, 7, 3, 8, 4], [1, 8, 11, 10, 2, 6]])
    arr4 = np.array([[[2, 5, 7], [3, 8, 4]], [[1, 8, 11], [10, 2, 6]]])

    # arr = np.concatenate(arr1, arr2)
    # print (arr)

    arr = np.stack((arr2, arr4), axis=0)
    print (arr)
    print ('-'*40)
    arr = np.stack((arr2, arr4), axis=1)
    print (arr)

Q92()
