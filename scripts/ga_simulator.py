import pandas as pd
import traci
import time
import dask

import sumolib

import pickle
#import networkx
import xml.etree.ElementTree as ET
import json
import time
from collections import defaultdict
import os.path
import multiprocessing as mp
from result_utils import calc_vul
from pathlib import Path
import random
#from scoop import worker
#import scoop
from dask.distributed import get_worker


BUDGET = 10

class SumoSim():
    
    SUMOBIN = 'sumo'
    snapshot_data = {}

    def __init__(self, disrupted, lmbd, 
                 start_time, end_time, 
                 filename, rank, gene=[], meso=False):
        #try:
        #    rank = mp.current_process()._identity[0]
        #except:
        #    rank = 0
        self.vehroutes_path = "../output/net_dump/vehroutes{}.xml".format(rank)
        self.rank = rank

        self.SUMOCMD = [self.SUMOBIN, "-c", "../config/generated_configs/config_{}.sumocfg".format(rank),
                    "--time-to-teleport", "900", "--vehroute-output", self.vehroutes_path,
                    "--vehroute-output.exit-times", "true", "--ignore-route-errors", 
                    "-v", "false", "-W", "true", "--no-step-log"]
        if meso:
            self.SUMOCMD = self.SUMOCMD + ['--mesosim']
        print("Simulation Details: \n Disrupted link: {} \n Lambda: {} \n Start - End time: {} - {}".format(disrupted, lmbd, start_time, end_time))
        print("Initializing")
        self.filename = filename
        
        self.network = sumolib.net.readNet('../network/SF_combined.net.xml')
        self.edges = self.network.getEdges()
        self.edgeIDs = [edge.getID() for edge in self.edges]

        self.disrupted = disrupted

        self.start_time = start_time
        self.end_time = end_time
        
        #if isinstance(gene, (np.ndarray, np.generic)):
        #    self.gene = gene.tolist()
        #else:
        self.gene = gene
        print("*********************************************************")
        if start_time == 0 and end_time ==0:
            self.nominal = True
        else:
            self.nominal = False

        self.lmbd = lmbd
        
        print("Searching network")
        self.convert_network(lmbd=self.lmbd)
        self.setup_additional_file()
        
        print("Setting up simulation")
        self.setup_sim()
        print("Total number of trips: {}".format(len(self.new_demand_route)))
        

    def setup_additional_file(self):
        #config_with_TLS_combined_no_trips.sumocfg
        tree = ET.parse('../config/base_configs/config_with_TLS_combined_no_trips.sumocfg')
        add_files = list(tree.iter(tag='additional-files'))[0]
        add_files.set('value', 'additional_{}.xml'.format(self.rank))
        tree.write('../config/generated_configs/config_{}.sumocfg'.format(self.rank), encoding='UTF-8', xml_declaration=True)
        tree = ET.parse('../config/base_configs/additional.xml')
        xmlRoot = tree.getroot()
        rerouter = ET.Element("rerouter")
        interval = ET.Element("interval")
        closing_reroute = ET.Element("closingReroute")

        closing_reroute.set('id', str(self.disrupted))
        closing_reroute.set('disallow', 'passenger')
        interval.set('begin', str(self.start_time))
        interval.set('end', str(self.end_time))
        rerouter.set('id', '1')
        
        disruptedEdge = self.network.getEdge(self.disrupted)
        to_node = disruptedEdge.getToNode()
        from_node = disruptedEdge.getFromNode()

        if self.gene is None:
            dests = [edge.getID() for edge in list(to_node.getIncoming())] + \
                            [edge.getID() for edge in list(to_node.getOutgoing())]
            sources = [edge.getID() for edge in list(from_node.getIncoming())] + \
                            [edge.getID() for edge in list(from_node.getOutgoing())]
        else:
            sources = [disruptedEdge.getID()]
            if isinstance(self.gene[0], int):
                print(len(self.gene), len(self.subnetwork_edges))

                # If gene is a series of numbers, then its a regular gene
                dests = [edge for i, edge in enumerate(self.subnetwork_edges) if self.gene[i]]
            elif isinstance(self.gene[0], str):
                # If gene is a series of strings, then these are edge names
                dests = [edge for edge in self.gene]

        rerouter.set('edges', ' '.join(sources + dests))
        #rerouter.set('edges', '1_1')
        interval.append(closing_reroute)
        rerouter.append(interval)
        xmlRoot.append(rerouter)

        tree.write('../config/generated_configs/additional_{}.xml'.format(self.rank))


    def run(self):
        print("Running Simulation")
        self.sim_start = time.time()
        self.run_sim()
        self.sim_end = time.time()
        print("Writing to file")
        self.write_to_file()

    def setup_sim(self):
        f = open('../output/net_dump/vehroutes.json', 'r')
        jsondata = json.load(f)
        f.close()

        #Vehicles considered will hold names of vehicles that pass through the subnetwork
        vehicles_considered = []
        for vehicle in jsondata:
            #if len(set(jsondata[vehicle]['edges']) & set(self.subnetwork_edges)) > 0:
            if len(set(jsondata[vehicle]['edges']).intersection(set(self.subnetwork_edges))) > 0:
                vehicles_considered.append(vehicle)

        #Calculate new demand and the depart time
        self.new_demand_route = {}
        self.new_demand_depart = {}
        self.new_demand_depart_lane = {}
        self.new_demand_depart_pos = {}
        self.new_demand_depart_speed = {}
        self.new_demand_depart_vehicles = defaultdict(list)


        for vehicle in vehicles_considered:
            start = False
            for i, edge in enumerate(jsondata[vehicle]['edges']):
                if edge in self.subnetwork_edges and not start:
                    self.new_demand_route[vehicle] = [edge]
                    self.new_demand_depart[vehicle] = int(float(jsondata[vehicle]['exitTimes'][i]))
                    self.new_demand_depart_vehicles[int(float(jsondata[vehicle]['exitTimes'][i]))].append(vehicle)
                    start = True
                    if i == 0:
                        self.new_demand_depart_lane[vehicle] = int(jsondata[vehicle]['departLane'])
                        self.new_demand_depart_pos[vehicle] = float(jsondata[vehicle]['departPos'])
                        self.new_demand_depart_speed[vehicle] = float(jsondata[vehicle]['departSpeed'])
                    else:
                        self.new_demand_depart_lane[vehicle] = 0
                        self.new_demand_depart_pos[vehicle] = 0.0
                        self.new_demand_depart_speed[vehicle] = 0.0
                elif (edge in self.subnetwork_edges and start) and i < len(jsondata[vehicle]['edges']):
                    self.new_demand_route[vehicle].append(edge)
                elif (edge not in self.subnetwork_edges and start):
                    break

    def close_edges(self):
        # Close appropriate edges in network for subnetwork
        for edgeID in self.edgeIDs:
            if edgeID not in set(self.subnetwork_edges):
                lanes = self.network.getEdge(edgeID).getLanes()
                for lane in lanes:
                    laneID = lane.getID()
                    traci.lane.setDisallowed(laneID, ['passenger'])


    def setup_trips(self):
        for vehicle in self.new_demand_route:
            if self.new_demand_route[vehicle][0] == self.disrupted:
                if self.start_time <= self.new_demand_depart[vehicle] and self.new_demand_depart[vehicle] <= self.end_time:
                    self.new_demand_depart[vehicle] = self.end_time+1
            
            traci.route.add(vehicle + '_route', self.new_demand_route[vehicle])
            
            try:
                traci.vehicle.add(vehicle, vehicle+'_route', depart= str(self.new_demand_depart[vehicle]),
                              departPos=str(self.new_demand_depart_pos[vehicle]), departSpeed='0',
                              typeID="passenger")
            except traci.exceptions.TraCIException as e:
                print(e.getCommand())
                print(e.getType())
                print("Vehicle : " + vehicle)
                print( "Depart : {}".format(self.new_demand_depart[vehicle]))
                print("Pos : {}".format(self.new_demand_depart_pos[vehicle]))
                print(" Route : {}".format(self.new_demand_route[vehicle]))
                print("Traci Route : {}".format(traci.route.getEdges(vehicle + "_route")))


    def run_sim(self):
        traci.start(self.SUMOCMD)
        dask.distributed.get_worker().log_event("start_sim", 'Started simulation')
        time.sleep(15.0)
        while True:
            try:
                self.close_edges()
                self.setup_trips()
                break
            except Exception as e:
                print(f'Exception {e}')
                dask.distributed.get_worker().log_event("exception", e)
                continue

        self.arrived = 0
        self.step = 0

        while self.arrived < len(self.new_demand_route):
            traci.simulationStep()
            self.step += 1
            self.arrived += traci.simulation.getArrivedNumber()
            if self.step  in [self.end_time+30, self.start_time+30, 30, 28830, 57630, 86430]:
                for edge in self.subnetwork_edges:
                    for veh in traci.edge.getLastStepVehicleIDs(edge):
                        traci.vehicle.rerouteTraveltime(veh)
        traci.close()


    def convert_network(self, lmbd = 1):
        tree = ET.parse('../network/SF_combined.edg.xml')
        root = tree.getroot()
        self.network_rep = Graph()
        for edge in root:
            self.network_rep.add_edge(edge.attrib['from'], edge.attrib['to'],edge.attrib['id'])
        self.subnetwork_edges = self.network_rep.get_subnetwork(self.disrupted, lmbd, disrupted= not self.nominal)
        print("Size of subnetwork : {}".format(len(self.subnetwork_edges)))

    def write_to_file(self):
        data = {}
        tree = ET.parse(self.vehroutes_path)
        root = tree.getroot()
        for vehicle in root:
            data[vehicle.attrib['id']] = float(vehicle.attrib['arrival']) - float(vehicle.attrib['depart'])
            
        data['sim_time'] = self.sim_end - self.sim_start
        
        with open(self.filename, 'w') as outfile:
            json.dump(data, outfile)
        tree.write(self.filename+'.xml')


class Graph():
    graph = {}
    edge_names = {}
    node_names = {}

    def add_edge(self, source, dest, name):
        if source in self.graph.keys():
            self.graph[source].append(dest)
        else:
            self.graph[source] = [dest]

        self.edge_names[(source, dest)] = name
        self.node_names[name] = (source, dest)

    def get_subnetwork(self, name, depth, disrupted=True, get_nodes=False):
        nodes = set()
        source, dest = self.node_names[name]
        visited = set()
        #visited.add(source)

        visited = self.bfs_search(source, depth, visited)
        visited2 = set()
        visited = visited.union(self.bfs_search(dest, depth, visited2)) 

        edge_names = set()
        #self.subnetwork = Graph()

        for source in visited:
            for dest in self.graph[source]:
                e_name = self.edge_names[(source, dest)]
                edge_names.add(e_name)
                if (dest, source) in self.edge_names:
                    e_name = self.edge_names[(dest, source)]
                    edge_names.add(e_name)
                    nodes.add(source)
                    nodes.add(dest)
                #self.subnetwork.add_edge(source, dest, e_name)

        edge_names = sorted(list(edge_names))
        #edge_names.remove(name)
        if get_nodes:
            return edge_names, visited
        else:
            return edge_names

    def get_path_edges(self, start_edge, end_edge):
        a, start = self.node_names[start_edge]
        b, end = self.node_names[end_edge]
        path = [a] + self.find_path(start, end)
        edges = []
        for i,node in enumerate(path[:-1]):
            edges.append(self.edge_names[(node, path[i+1])])
        return edges

    def find_path(self, start, end, path=[]):
        path += [start]
        if start == end:
            return path
        if start not in self.graph.keys():
            return None
        shortest = None
        for node in self.graph[start]:
            if node not in path:
                newpath = self.find_path(node, end, path)
                if newpath:
                    if not shortest or len(newpath) < len(shortest):
                        shortest = newpath
        return shortest


    def bfs_search(self, start_node, depth, visited=set()):
        depth -= 1
        visited.add(start_node)
        for child in self.graph[start_node]:
            if depth > 0 and child not in visited:
                self.bfs_search(child, depth, visited)

        return visited

def write_results(lmbd, edge, start_time, end_time, individual, result, rank):
    base_path = Path('./ga_results')
    rank_path = base_path / 'rank_{}_results.pkl'.format(rank)
    if rank_path.exists():
        with rank_path.open('rb') as f:
            result_dict = pickle.load(f)
    else:
        result_dict = {}
    
    result_dict[(lmbd, edge, start_time, end_time, tuple(individual))] = result
    with rank_path.open('wb') as f:
        pickle.dump(result_dict, f)
        
def check_results(lmbd, edge, start_time, end_time, individual):
    if isinstance(individual[0], int):
        if sum(individual) <= BUDGET:
            base_path = Path('./ga_results')
            rank_paths = base_path.glob('*.pkl')

            for rank_path in rank_paths:
                with rank_path.open('rb') as f:
                    result_dict = pickle.load(f)
                key = (lmbd, edge, start_time, end_time, tuple(individual))
                if key in result_dict:
                    return result_dict[key]
        else:
            return -100*(sum(individual) - BUDGET)
    return None

def run_sim(lmbd, edge, start_time, end_time, rank, individual, meso=False):
    filename = "../output/net_dump/traveltime_{}_{}_{}_{}_{}.json".format(lmbd, edge, start_time, end_time, rank)

    #result = check_results(lmbd, edge, start_time, end_time, individual)
    result = None
    if result is None:
        ss = SumoSim(edge, lmbd, start_time, 
                     end_time, filename, rank, 
                     gene=individual, meso=meso)
        
        if not os.path.isfile(filename):
            print('Result not found, Running sim <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')
            f = open(filename, 'w')
            f.close()
        ss.run()
        with open(filename) as f:
            sub_tt = json.load(f)
        if meso:
            meso_suffix = '_meso'
        else:
            meso_suffix = ''
        filename = '../output/net_dump/1.high_correlation/lmbd{}/traveltime_{}_0_10_{}_False{}.json'.format(lmbd, edge, lmbd, meso_suffix)
        with open(filename) as f:
            nom_tt = json.load(f)

        result = -1*calc_vul(sub_tt, nom_tt, [lmbd, edge, (start_time, end_time)])
        write_results(lmbd, edge, start_time, end_time, individual, result, rank)
    return result


def evalOneMax(individual, lmbd=3):
    #lmbd = 3
    edge = '18_1'
    start_time = 57600
    end_time = 86400
    try:
        #rank = mp.current_process()._identity[0]
        #rank = scoop.worker.decode("utf-8")
        #rank = rank.replace(".", "")
        #rank = rank.replace(":","")
        #rank = random.randint(0, 100)
        get_worker().id
    except:
        rank = 0

    return run_sim(lmbd, edge, start_time, end_time, rank, individual)

def get_subnet(dis_edge, lmbd):
    tree = ET.parse('../network/SF_combined.edg.xml')
    root = tree.getroot()
    network_rep = Graph()
    for edge in root:
        network_rep.add_edge(edge.attrib['from'], edge.attrib['to'],edge.attrib['id'])
    subnetwork_edges = network_rep.get_subnetwork(dis_edge, lmbd, disrupted=True)
    return subnetwork_edges



if __name__=="__main__":
    #subnetwork_edges = get_subnet('18_1', 3)
    #print(len(subnetwork_edges))
    import numpy as np
    indv = np.random.binomial(1, 15/50, size=50)
    evalOneMax(indv.tolist())
