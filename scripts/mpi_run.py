# -*- coding: utf-8 -*-
"""
Created on Fri Jul 20 14:12:55 2018

@author: Shekar
"""

from mpi4py import MPI
from network_snapshot import SumoSim
import sumolib
import time
import os

comm = MPI.COMM_WORLD
rank = comm.Get_rank()

network = sumolib.net.readNet('../network/SF_combined.net.xml')
edges = network.getEdges()
edgeIDs = [edge.getID() for edge in edges]
time_intervals = [(0,28800), (28800, 57600), (57600, 86400)]
#lmbd_list = [1, 2, 3 ,4, 5, 6, 7, 8, 9, 10, 11, 12, 100]
lmbd_list = [100]

offset = 66

for edge in edgeIDs:
    if rank+1 == int(edge.split('_')[0])-offset:
        for start_time, end_time in time_intervals:
            network_size = 0
            for lmbd in lmbd_list:
                if start_time == end_time:
                    filename = "../output/net_dump/lmbd{}/traveltime_{}_{}_{}_{}_{}.json".format(lmbd, edge, start_time, end_time, lmbd, True)
                else:
                    filename = "../output/net_dump/lmbd{}/traveltime_{}_{}_{}_{}_{}.json".format(lmbd, edge, start_time, end_time, lmbd, False)
                ss = SumoSim(edge, lmbd, start_time, end_time, network_size, filename, rank)
                #if not os.path.isfile(filename) and network_size != len(ss.subnetwork_edges):
                if not os.path.isfile(filename):
                    print('Running sim <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')
                    f = open(filename, 'w')
                    f.close()
                    ss.run()
                network_size = len(ss.subnetwork_edges)
