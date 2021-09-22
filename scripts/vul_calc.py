import json
import os
import scipy.stats


def get_vul(link, interval, lmbd):
    filename = "../output/net_dump/lmbd{}/traveltime_{}_{}_{}_{}_{}.json".format(lmbd, link, interval[0], interval[1], lmbd, False)
    while not os.path.isfile(filename):
        lmbd -=1
        filename = "../output/net_dump/lmbd{}/traveltime_{}_{}_{}_{}_{}.json".format(lmbd, link, interval[0], interval[1], lmbd, False)


    sub_vul_data = json.load(open(filename))
    filename_nom = "../output/net_dump/lmbd{}/traveltime_{}_{}_{}_{}_{}.json".format(lmbd, link, 0, 0, lmbd, True)
    sub_nom_data = json.load(open(filename_nom))
    
    num = 0
    den = 0
    for vehicle in sub_vul_data:
        if vehicle != 'sim_time':
            num += float(sub_vul_data[vehicle]) - float(sub_nom_data[vehicle])
            den += float(sub_nom_data[vehicle])
    #print("Vulnerability of subnetwork: {}".format(num/den))
    sub_vul = num/den

    lambdas = [100]
    for lmbd in lambdas:
        filename = "../output/net_dump/lmbd{}/traveltime_{}_{}_{}_{}_{}.json".format(lmbd, link, interval[0], interval[1], lmbd, False)
        if os.path.isfile(filename):
            full_vul_data = json.load(open(filename))
            filename_nom = "../output/net_dump/lmbd{}/traveltime_{}_{}_{}_{}_{}.json".format(lmbd, link, 0, 0, lmbd, True)
            full_nom_data = json.load(open(filename_nom))
            break

    num_full = 0
    den_full = 0
    for vehicle in full_vul_data:
        if vehicle != 'sim_time':
            num_full += float(full_vul_data[vehicle]) - float(full_nom_data[vehicle])
            den_full += float(full_nom_data[vehicle])
    #print("Vulnerability of full network: {}".format(num_full/den_full))

    #print("Sim time ratio : {}/{} = {}".format(full_vul_data['sim_time'], sub_vul_data['sim_time'],  full_vul_data['sim_time']/sub_vul_data['sim_time']))  
    

    full_vul = num_full/den_full

    return sub_vul, full_vul

if __name__ =="__main__":
    sub_vuls = []
    full_vuls = []
    link_name = []
    for i in range(76):
        link = str(i+1)+'_1'
        link_name.append(link)
        #interval = (0, 28800)
        #interval = (28800, 57600)
        interval = (57600, 86400)
        lmbd = 12
        sub_vul, full_vul = get_vul(link, interval, lmbd)
        sub_vuls.append(sub_vul)
        full_vuls.append(full_vul)
    print(link_name[full_vuls.index(max(full_vuls))], max(full_vuls))
    
    print(scipy.stats.spearmanr(sub_vuls, full_vuls))