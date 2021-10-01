#%%
import multiprocessing as mp

from network_snapshot import SumoSim
import sumolib
import time
import os
from pathlib import Path
import result_utils as ru

#%%
network = sumolib.net.readNet('../network/SF_combined.net.xml')
edges = network.getEdges()
edgeIDs = [edge.getID() for edge in edges]
time_intervals = [(0,10), (0,28800), (28800, 57600), (57600, 86400)]
lmbd_list = [1, 2, 3 ,4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
#lmbd_list = [100]
#%%
def generate_args():
    args = []
    for lmbd in lmbd_list:
        for edge in edgeIDs:
            for start_time, end_time in time_intervals:
                args.append((edge, start_time, end_time, lmbd))
    return args

#%%

def test_run():
    edge, start_time, end_time, lmbd = '23_1',28800, 57600, 5
    filename = "../output/net_dump/lmbd{}/traveltime_{}_{}_{}_{}_{}.json".format(lmbd, edge, start_time, end_time, lmbd, False)
    ss = SumoSim(edge, lmbd, start_time, end_time, 0, filename, 101)
    if not os.path.isfile(filename):
        print('Running sim <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')
        f = open(filename, 'w')
        f.close()
    ss.run()

#test_run()

#%%
import json
with open('../output/net_dump/vehroutes_new.json', 'r') as f:
    jsondata = json.load(f)
nom_tt = ru.get_subnetwork_tt(jsondata, ru.get_subnet_edges(1, f'1_1', nominal=True))
nom_tt


#%%
def generate_nominal_args():
    args = []
    lmbd_list = [15,20,100]
    for lmbd in lmbd_list:
        args.append(('1_1', 0, 0, lmbd))
        args.append(('76_1', 0, 0, lmbd))
    return args

#%%
generate_nominal_args()
#%%
#generate_args()[:10]
#%%
def myPID():
	# Returns relative PID of a pool process
	return mp.current_process()._identity[0]
            
def process(args):   
    edge, start_time, end_time, lmbd = args
    folder = Path(f'../output/net_dump/lmbd{lmbd}')
    folder.mkdir(parents=True, exist_ok=True)
    if start_time == end_time:
        filename = "../output/net_dump/lmbd{}/traveltime_{}_{}_{}_{}_{}.json".format(lmbd, edge, start_time, end_time, lmbd, True)
    else:
        filename = "../output/net_dump/lmbd{}/traveltime_{}_{}_{}_{}_{}.json".format(lmbd, edge, start_time, end_time, lmbd, False)
    ss = SumoSim(edge, lmbd, start_time, end_time, 0, filename, myPID())
    #if not os.path.isfile(filename) and network_size != len(ss.subnetwork_edges):
    if not os.path.isfile(filename):
        print('Running sim <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')
        f = open(filename, 'w')
        f.close()
        ss.run()
    #network_size = len(ss.subnetwork_edges)

if __name__=='__main__':
    poolSize = mp.cpu_count() - 2
    p = mp.Pool(poolSize)
    p.imap(process, generate_args(), 5)
    #p.map(process, generate_nominal_args(), 1)
    p.close()
    p.join()
    #process(('67_1', 0, 28800, 100))
# %%
