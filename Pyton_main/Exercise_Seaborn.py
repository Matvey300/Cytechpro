import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

y_arr_1 = [1, 4, 5, 6]
x_arr_1 = [6, 7, 8, 9]
# plt.subplot(2,2,1)
# plt.xlabel("nums X 1")
# plt.ylabel("nums Y 1")
# plt.plot(x_arr_1,y_arr_1)

# y_arr_2 = [1,2,3,4,5,6]
# x_arr_2 = [60,70,80,90,77,55]
# plt.subplot(2,2,2)
# plt.xlabel("nums X 2")
# plt.ylabel("nums Y 2")

# plt.plot(x_arr_2,y_arr_2)
# y_arr_3 = [11,41,51,61]
# x_arr_3 = [-6,-7,-8,-9]
# plt.subplot(2,2,3)
# plt.xlabel("nums X 3")
# plt.ylabel("nums Y 3")


# plt.subplot(2,2,4)
# plt.xlabel("nums X 4")
# plt.ylabel("nums Y 4")
# plt.plot(x_arr_3,y_arr_3)

# plt.tight_layout()

# plt.show()

df = pd.DataFrame({"x": x_arr_1, "y": y_arr_1})
sns.histplot(df["y"])
plt.show()
