dict1 = {
    "age": "Dor",
    "height": 1.65,
    "teacher": None,
    "nums": [100.5,99.3,8.7,56.3],
}
dict2 = {
    "age": "Dor",
    "height": 6.85,
    "teacher": None,
    "nums": [100.5,99.3,8.7,56.3],
}
dict3 = {
    "age": "dwdwdwd",
    "height": 1.65,
    "teacher": None,
    "nums": [100.5,99.3,8.7,56.3],
}
MAX_LOOPS = 50
 
def change_dict(_abc, a):
    global MAX_LOOPS
    for key, val in _abc.items():
        if (a == 0):
            return
        if(type(val) == str):
            _abc[key] = val.upper()
        elif(type(val) == float):
            _abc[key] = int(val)
        a -=1
        return a, _abc
        print(a)
       
change_dict(dict1.copy())
print(dict1)
change_dict(a, dict2 )
print(dict2)
change_dict(dict3)
print(dict3)
print(a)
 