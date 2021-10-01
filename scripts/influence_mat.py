import json
import sumolib
import numpy as np
import h5py
from collections import defaultdict
import pandas as pd

f = open('../output/net_dump/vehroutes.json')
data = json.load(f)
f.close()

mat_data = {key:[0 for i in range(24)] for key in range(24)}
matrix = pd.DataFrame(data=mat_data)
#matrix = np.array([[0 for i in range(24)] for x in range(24)])
network = sumolib.net.readNet('../network/SF_combined.net.xml')
edge2node = {}
for edge in network.getEdges():
    edgeID = edge.getID()
    fromNode = int(edge.getFromNode().getID()) - 1
    toNode = int(edge.getToNode().getID()) - 1
    edge2node[edgeID] = (fromNode, toNode)

time_steps_set = set()
#for veh in data:
#    time_steps_set = set.union(set(data[veh]["exitTimes"]), time_steps_set)

time_series = defaultdict(str)
#for time in time_steps_set:
#    time_series[time] = np.array([[0 for i in range(24)] for x in range(24)])

for veh in data:
    edgelist = data[veh]['edges']
    if len(edgelist) == 1:
        fromNode, toNode = edge2node[edgelist[0]]
    else:
        fromNode = edge2node[edgelist[0]][0]
        toNode = edge2node[edgelist[-1]][0]
    
    if fromNode == toNode:
        fromNode = edge2node[edgelist[0]][0]
        toNode = edge2node[edgelist[-1]][1]
    
    if fromNode == toNode:
        print(edgelist[0], edgelist[-1])
        
    matrix.iloc[fromNode, toNode] += 1


    """
    for i, edgeID in enumerate(data[veh]['edges']):
        fromNode, toNode = edge2node[edgeID]
        time = data[veh]['exitTimes'][i]
        if time not in time_series:
            time_series[time] = np.array([[0 for i in range(24)] for x in range(24)])
        
        #time_series[time][fromNode, toNode] += 1
        #time_series[time] = ",".join([time_series[time], "({}, {})".format(fromNode, toNode)])
        edge = network.getEdge(edgeID)
        fromNode = int(edge.getFromNode().getID()) - 1
        toNode = int(edge.getToNode().getID()) - 1
        matrix.iloc[fromNode, toNode] += 1
    """
#print(time_series[23088])
matrix.to_csv('sources_and_sinks.csv')
#matrix.to_hdf('time_series.h5', 'all')
#f = h5py.File('time_series.h5', 'w')

#for time in time_series:
    #f.create_dataset(str(time), data=time_series[time])
#f.create_dataset('all', data=matrix)
#f.close()
#f = open('time_series.txt', 'w')
#for time in time_series:
#    f.write("{} : {}\n".format(time, time_series[time]))
#f.close()
