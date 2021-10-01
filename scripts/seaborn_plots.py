import seaborn as sns
import matplotlib.pyplot as plt


def rank_corr(data):
    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(1, 3, figsize=(18,5))
    
    for i, lmbd in enumerate(data):
        y = data[lmbd]['y']
        x = data[lmbd]['x']
        sns.scatterplot(ax=axes[i],x=x, y=y)
        sns.lineplot(ax=axes[i], x=range(len(x)), y=range(len(y)), lw=2, color='purple')

        axes[i].tick_params(axis = 'both', which = 'major', labelsize = 20)
        
        axes[i].set_xlim(0, len(x))
        axes[i].set_ylim(0, len(y))
        if i != 1:
            axes[i].set_xlabel(f'$\lambda = {lmbd}$', fontsize=20)
        else:
            axes[i].set_xlabel(f'$\lambda = {lmbd}$\nSubnetwork vulnerability ranking', fontsize=20)
        

        if i == 0:
            axes[i].set_ylabel('Full network\nvulnerability ranking', fontsize=20)
        
        #plt.xlabel('Subnetwork vulnerability ranking', fontsize=20)
    

def ga_plot(min_vul, avg_vul):
    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(1, 1, figsize=(12,8))
    sns.lineplot(ax=axes, x=range(len(min_vul)), y=min_vul, lw=2, label='$B = 10$ for $\lambda = 3$')
    sns.lineplot(ax=axes, x=range(len(avg_vul)), y=avg_vul, lw=2, label='$B = 15$ for $\lambda = 3$')
    #plt.hlines(y=1.357, xmin=0, xmax=40, label='Full network vulnerability\nwithout VMS', color='red')
    #plt.hlines(y=2.334, xmin=0, xmax=40, label='Network vulnerability w/o\n VMS for $\lambda = 3$', color='red')
    #plt.hlines(y=1.097, xmin=0, xmax=40, label='Full network vulnerability with best VMS configuration')
    
    axes.tick_params(axis = 'both', which = 'major', labelsize = 20)
    axes.set_xlabel('Generation', fontsize=20)
    axes.set_ylabel('Vulnerability', fontsize=20)
    plt.legend(prop={"size":20})
    fig.show()
