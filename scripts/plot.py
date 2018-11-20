import json
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.mlab as mlab
from scipy.stats import *
import scipy
import chartify
import numbers

with open('../output/net_dump/lmbd8/traveltime_55_1_28800_57600_8_False.json') as f:
    high_vul_tt = json.load(f)

with open('../output/net_dump/lmbd100/traveltime_1_1_0_0_100_True.json') as f:
    nom_tt = json.load(f)

df1 = pd.DataFrame.from_dict(data=nom_tt, orient="index")
df2 = pd.DataFrame.from_dict(data=high_vul_tt, orient="index")
result = pd.concat([df1, df2], axis=1, join='inner')
result.columns = ['nom', '55_1_t2']
#plt.hist(result['nom'], bins=10000, histtype='step', linewidth=2.0, normed=True )
#plt.hist(result['55_1_t2'], bins=10000, histtype='step', linewidth=2.0, normed=True)

bins = [i for i in range(10000)]

def matplotlib_plotting():
    mu_nom, sigma_nom = norm.fit(result['nom'])
    y = mlab.normpdf(bins, mu_nom, sigma_nom)
    l = plt.plot(bins, y, 'r--', linewidth=2)

    mu_vul, sigma_vul = norm.fit(result['55_1_t2'])
    y2 = mlab.normpdf(bins, mu_vul, sigma_vul)
    l2 = plt.plot(bins, y2, 'b', linewidth=2)

    plt.xlabel('Travel Time')

    plt.show()

def chartify_plotting():
    ch = chartify.Chart(blank_labels=True, y_axis_type='density')
    ch.plot.kde(
        data_frame=result,
        values_column='nom'
    )
    ch.plot.kde(
        data_frame=result,
        values_column='55_1_t2'
    )
    ch.show()

def all_dists(col_name):
    dist_list = [cls.__name__[:-4] for cls in rv_continuous.__subclasses__() if getattr(cls,"fit", False)]
    all_params = {}
    dist_results = {}
    for dist_name in dist_list:
        if dist_name not in [""]:
            try:
                dist = getattr(scipy.stats, dist_name)
                print(dist_name + " : ")
                param = dist.fit(result[col_name])
                print("{}".format(param))
                all_params[dist_name] = param
                D, p = kstest(result[col_name], dist_name, args=param)
                if isinstance(p, numbers.Number):
                    dist_results[dist_name] = p
            except:
                print("Model fitting error")
                pass
    
    p = max(dist_results.items(), key=lambda item:item[1])
    print(dist_results)
    return dist_results
#chartify_plotting()
#all_dists()
"""
x = [i for i in range(4000)]

rv = johnsonsu.pdf(x, -0.77719917904683722, 1.1760612707804805, 385.21950369138796, 253.22462820468638)
fig, ax = plt.subplots(1, 1)
ax.plot(x, rv, label='Nominal PDF')
plt.show()
"""

#results = all_dists('55_1_t2')

x = [i for i in range(4000)]
rv = johnsonsu.pdf(x, -0.77719917904683722, 1.1760612707804805, 385.21950369138796, 253.22462820468638)
#rv2 = johnsonsu.pdf(x, -0.63028674610689217, 0.90080091121644701, 424.14762590931252, 182.90581566389028)
fig, ax = plt.subplots(1, 1)
#ax.plot(x, rv, label="Nominal")
ax.hist(rv, alpha=0.5, label="Fitted")
#ax.hist(result['nom'], alpha=0.5, label="Actual")
#ax.plot(x, rv2, label='55_1')
plt.show()