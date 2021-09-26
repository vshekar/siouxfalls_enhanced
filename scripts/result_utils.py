from collections import defaultdict
import numpy as np
import xml.etree.ElementTree as ET
from pathlib import Path
import json
from network_snapshot import Graph

def calc_vul(vul_data, nom_data, extra_data):
    vehicles = set(vul_data.keys()).intersection(set(nom_data.keys()))
    vehicles.discard('sim_time')

    full_vul_list = []
    full_nom_list = []
    for veh in vehicles:
        full_nom_list.append(nom_data[veh])
        full_vul_list.append(vul_data[veh])

    nom_list = np.array(full_nom_list)
    vul_list = np.array(full_vul_list)

    try:
        vul = np.sum(vul_list - nom_list)/np.sum(nom_list)
    except Exception as e:
        print(f'Calc vul exception: {e} {extra_data}')
        vul = None
    return vul


def get_sub_vuls(link, interval, lmbd, sub_nom_data):
    filename = "../output/net_dump/lmbd{}/traveltime_{}_1_{}_{}_{}_{}.json".format(lmbd, link, interval[0], interval[1], lmbd, False)
    filepath = Path(filename)
    sub_vul = None
    #filename_nom = "../output/net_dump/old_data/lmbd{}/traveltime_{}_1_{}_{}_{}_{}.json".format(lmbd, link, 0, 0, lmbd, True)
    
    if filepath.is_file():
        try:
            sub_vul_data = json.load(filepath.open())
        except Exception as e:
            print(f'Sub vul exception: {filepath}, {e}')
        sub_vul = calc_vul(sub_vul_data, sub_nom_data, (link, interval, lmbd))
    return sub_vul


def get_full_vuls(link, interval, full_nom_data):
    lambdas = [100]
    #filename_nom = "../output/net_dump/lmbd{}/traveltime_{}_1_{}_{}_{}_{}.json".format(lmbd, link, 0, 0, lmbd, True)
    
    full_vul = None
    for lmbd in lambdas:
        try:
            filename = "../output/net_dump/old_data/lmbd{}/traveltime_{}_1_{}_{}_{}_{}.json".format(lmbd, link, interval[0], interval[1], lmbd, False)
            vul_filepath = Path(filename)
            if vul_filepath.is_file():
                full_vul_data = json.load(vul_filepath.open())
                full_vul = calc_vul(full_vul_data, full_nom_data, (link, interval, lmbd))
        except Exception as e:
            print(f'Full vul exception: {link}, {interval}, {lmbd}: {e}')
    return full_vul


def get_sorted_in_interval(vuls, selected_interval, rank=False):
    sorted_vuls = {}
    for i, (link, interval) in enumerate(vuls):
        if interval == selected_interval:
            if not rank:
                sorted_vuls[link] = vuls[(link, interval)]
            else:
                sorted_vuls[link] = i
    return sorted_vuls


def get_subnetwork_tt(jsondata, subnetwork_edges):
    #Vehicles considered will hold names of vehicles that pass through the subnetwork
    #travel_data = defaultdict(list)
    travel_times = defaultdict(float)
    subnetwork_edges = set([edge.split('_')[0] for edge in subnetwork_edges])

    for vehicle in jsondata:
        tts = jsondata[vehicle]
        vehicle_edges = set(tts.keys())
        sub_veh_edges = vehicle_edges.intersection(subnetwork_edges)
        
        for edge in sub_veh_edges:
            travel_times[vehicle] += tts[edge]
        """
        if len(set(jsondata[vehicle]['edges']) & set(subnetwork_edges)) > 0:
            start = False
            for i, edge in enumerate(jsondata[vehicle]['edges']):
                exit_time = int(float(jsondata[vehicle]['exitTimes'][i]))
                if edge in subnetwork_edges and not start:
                    travel_data[vehicle].append(exit_time)
                    start = True
                elif (edge in subnetwork_edges and start) and i < len(jsondata[vehicle]['edges']):
                    travel_data[vehicle].append(exit_time)
                elif (edge not in subnetwork_edges and start):
                    travel_data[vehicle].append(exit_time)
                    break
    for veh, tt_vector in travel_data.items():
        if len(tt_vector) == 1:
            travel_times[veh] = 1
        else:
            travel_times[veh] = tt_vector[-1] - tt_vector[0]
    
        """
   
    return travel_times


def get_subnet_edges(lmbd, disrupted_edge, nominal=True, get_nodes=False):
    tree = ET.parse('../network/SF_combined.edg.xml')
    root = tree.getroot()
    network_rep = Graph()
    for edge in root:
        network_rep.add_edge(edge.attrib['from'], edge.attrib['to'],edge.attrib['id'])
    subnetwork_edges = network_rep.get_subnetwork(disrupted_edge, lmbd, disrupted= not nominal, get_nodes=get_nodes)
    #print("Size of subnetwork : {}".format(len(subnetwork_edges)))
    return subnetwork_edges