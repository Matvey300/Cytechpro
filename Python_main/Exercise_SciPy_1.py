import numpy as np
import pandas as pd
import scipy as sc

df = pd.read_csv("/Users/Matvej1/Downloads/penguins.csv")
print(df.head())
ALPHA = 0.05

# adelie_mass = df.loc[df.species == 'Adelie', 'body-mass_g'].values
# gentoo_mass = df.loc[df.species == 'Gentoo', 'body-mass_g'].values

# t_stat, p_val = sc.stats.ttest_ind(adelie_mass, gentoo_mass, equla_var = False)

# if p_val < ALPHA:
#     print ('Gentoo and Adelie mass is not hte same')
# else:
#     print('We dont know')

# bill_length = df.bill_length_mm.dropna()
# bill_depth = df.bill_depth_mm.drop()


# t_stat, p_val = sc.stats.pearsonr(bill_depth, bill_length, )
# if p_val < ALPHA:
#     print("Reject the H0, bill length and the bill depth are significantly correlated")
# else:
#     print("I dont have enough evidence to say the t")


# TEST 4 Is species distribution independent of *island*? (Chi-square)

contingency_table = pd.crosstab(df["species"], df["island"])
chi2_stat, p_value, dof, expected = sc.stats.chi2_contingency(contingency_table)

print(contingency_table)


print(p_value)
print(dof)
print(expected)


def carmers_v(chi2, n, k, r):
    return np.sqrt(chi2 / (n * (min(k, r) - 1)))


v = carmers_v(chi2_stat, df.shape[0], *contingency_table.shape)

print(f"Cramer's V: {v}")

if p_value < ALPHA:
    print("Reject the H0, species distribution is depends ds on the island")
else:
    print("I dont have enough evidence to say the there is or isnt a linear correlation")
