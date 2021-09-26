import pandas as pd
import traci
import sumolib
from collections import namedtuple
import pickle
#import networkx
import xml.etree.ElementTree as ET
import json
import time
from collections import defaultdict
import os.path

vehicleData = namedtuple('vehicleData', ['lane', 'pos', 'speed', 'accel', 'route'])


class SumoSim():
    
    SUMOBIN = 'sumo'

    snapshot_data = {}

    def __init__(self, disrupted, lmbd, start_time, end_time, prev_network_size, filename, rank):
        self.vehroutes_path = "../output/net_dump/vehroutes{}.xml".format(rank)
        self.rank = rank
        self.rerouting_options = ['--device.rerouting.probability', '0.1', 
                                  '--device.rerouting.period', '300', 
                                  '--device.rerouting.threads', '3', "--no-step-log"]

        self.SUMOCMD = [self.SUMOBIN, "-c", "../config/generated_configs/config_{}.sumocfg".format(rank),
                    "--time-to-teleport", "400", "--vehroute-output", self.vehroutes_path,
                    "--vehroute-output.exit-times", "true", "--ignore-route-errors", "-v", "false", "-W", "true"]
        self.SUMOCMD = self.SUMOCMD+self.rerouting_options
        print("*********************************************************")
        print("Simulation Details: \n Disrupted link: {} \n Lambda: {} \n Start - End time: {} - {}".format(disrupted, lmbd, start_time, end_time))
        print("Initializing")
        self.filename = filename
        self.prev_network = prev_network_size
        self.network = sumolib.net.readNet('../network/SF_combined.net.xml')
        self.edges = self.network.getEdges()
        self.edgeIDs = [edge.getID() for edge in self.edges]

        self.disrupted = disrupted

        self.start_time = start_time
        self.end_time = end_time
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
        #sources = [edge.getID() for edge in list(disruptedEdge.getIncoming().keys())]
        #dests = [edge.getID() for edge in list(disruptedEdge.getOutgoing().keys())]
        to_node = disruptedEdge.getToNode()
        from_node = disruptedEdge.getFromNode()
        dests = [edge.getID() for edge in list(to_node.getIncoming())] + \
                        [edge.getID() for edge in list(to_node.getOutgoing())]
        sources = [edge.getID() for edge in list(from_node.getIncoming())] + \
                        [edge.getID() for edge in list(from_node.getOutgoing())]

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


    def disrupt_links(self):
        if self.nominal ==False and (self.start_time == self.step):
            #If nominal is true to not disrupt link
            lanes = self.network.getEdge(self.disrupted).getLanes()
            for lane in lanes:
                laneID = lane.getID()
                traci.lane.setDisallowed(laneID, ['passenger'])
        if self.nominal ==False and self.step == self.end_time:
            lanes = self.network.getEdge(self.disrupted).getLanes()
            for lane in lanes:
                laneID = lane.getID()
                traci.lane.setDisallowed(laneID, [])


    def setup_trips(self):
        for vehicle in self.new_demand_route:
            """
            if len(self.new_demand_route[vehicle]) > 1 and self.disrupted in self.new_demand_route[vehicle]:
                if self.disrupted != self.new_demand_route[vehicle][0] and self.disrupted != self.new_demand_route[vehicle][-1]:
                    traci.route.add(vehicle+'_route', [self.new_demand_route[vehicle][0], self.new_demand_route[vehicle][-1]])
                    #traci.route.add(vehicle + '_route', self.new_demand_route[vehicle])
                else:
                    if self.new_demand_route[vehicle][0] == self.disrupted:
                        traci.route.add(vehicle + '_route',
                                        [self.new_demand_route[vehicle][1], self.new_demand_route[vehicle][-1]])
                    else:
                        traci.route.add(vehicle + '_route',
                                        [self.new_demand_route[vehicle][0], self.new_demand_route[vehicle][-2]])
            elif self.new_demand_route[vehicle][0] == self.disrupted:
                disruptedEdge = self.network.getEdge(self.disrupted)
                source = list(disruptedEdge.getIncoming().keys())[0].getID()
                dest = list(disruptedEdge.getOutgoing().keys())[0].getID()
                traci.route.add(vehicle + '_route', [source, dest])
            else:
                traci.route.add(vehicle + '_route', self.new_demand_route[vehicle])
            """
            if self.new_demand_route[vehicle][0] == self.disrupted:
                #disruptedEdge = self.network.getEdge(self.disrupted)
                #source = list(disruptedEdge.getIncoming().keys())[0].getID()
                #dest = list(disruptedEdge.getOutgoing().keys())[0].getID()
                #traci.route.add(vehicle + '_route', [source, dest])
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
        self.close_edges()
        self.setup_trips()
        self.arrived = 0
        self.step = 0

        while self.arrived < len(self.new_demand_route):
            #self.disrupt_links()
            """
            if self.step in self.new_demand_depart_vehicles.keys():
                vehicles = self.new_demand_depart_vehicles[self.step]
                for vehicle in vehicles:
                    self.setup_trips(vehicle)
            """
            traci.simulationStep()
            self.step += 1
            self.arrived += traci.simulation.getArrivedNumber()
            if self.step  in [self.end_time+30, self.start_time+30, 30, 28830, 57630, 86430]:
                for edge in self.subnetwork_edges:
                    for veh in traci.edge.getLastStepVehicleIDs(edge):
                        traci.vehicle.rerouteTraveltime(veh)


        traci.close()


    def take_snapshot(self):

        for edgeID in self.edgeIDs:
            vehIDs = traci.edge.getLastStepVehicleIDs(edgeID)
            for vehID in vehIDs:
                lane = traci.vehicle.getLaneID(vehID)
                pos = traci.vehicle.getLanePosition(vehID)
                speed = traci.vehicle.getSpeed(vehID)
                accel = traci.vehicle.getAccel(vehID)
                route = traci.vehicle.getRoute(vehID)
                vehData = vehicleData(lane, pos, speed, accel, route)
                self.snapshot_data[vehID] = vehData

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
            """
            for route in vehicle:
                if route.tag == 'routeDistribution':
                    for r in route:
                        get_route(r)
                else:
                    get_route(route)
            """
            
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




if __name__=="__main__":
    network = sumolib.net.readNet('../network/SF_combined.net.xml')
    edges = network.getEdges()
    #edgeIDs = [edge.getID() for edge in edges]
    edgeIDs = ['50_1']
    #time_intervals = [(0,28800), (28800, 57600), (57600, 86400), (0,0)]
    time_intervals = [(start_time, start_time+3600) for start_time in range(0, 86400, 3600)]
    #lmbd_list = [1, 2, 3 ,4, 5, 6, 7, 8 , 9 , 10, 100]
    lmbd_list = [100]
    for edge in edgeIDs:
        for start_time, end_time in time_intervals:
            network_size = 0
            for lmbd in lmbd_list:
                if start_time == end_time:
                    filename = "../output/hourly/lmbd{}/traveltime_{}_{}_{}_{}_{}.json".format(lmbd, edge, start_time, end_time, lmbd, True)
                else:
                    filename = "../output/hourly/lmbd{}/traveltime_{}_{}_{}_{}_{}.json".format(lmbd, edge, start_time, end_time, lmbd, False)
                
                ss = SumoSim(edge, lmbd, start_time, end_time, network_size, filename, 0)
                #if not os.path.isfile(filename) and network_size != len(ss.subnetwork_edges):
                f = open(filename, 'w')
                f.close()
                ss.run()
                network_size = len(ss.subnetwork_edges)
