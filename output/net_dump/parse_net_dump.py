import xml.etree.ElementTree as ET
import json
import sumolib
import pandas as pd
import math

def write_routes():
	tree = ET.parse('vehroutes1000.xml')
	root = tree.getroot()

	routes = {}

	for r in root:
		for rt in r[0]:
			if 'exitTimes' in rt.attrib.keys():
				route = {}
				route['edges'] = rt.attrib['edges'].split()
				route['exitTimes'] = [int(float(r.attrib['depart']))] + [int(float(x)) for x in rt.attrib['exitTimes'].split()[:-1]]
				#route['departLane'] = r.attrib['departLane']
				#route['departPos'] = r.attrib['departPos']
				#route['departSpeed'] = r.attrib['departSpeed']
				routes[r.attrib['id']] = route

	jsondata = json.dumps(routes)
	f = open('vehroutes1000.json', 'w')
	f.write(jsondata)
	f.close()
            

def matrixitize():
	f = open('vehroutes.json', 'r')
	jsondata = json.load(f)
	f.close()
	network = sumolib.net.readNet('../../network/SF_with_TLS_combined.net.xml')
	edges = network.getEdges()
	edgeIDs = [edge.getID() for edge in edges]
	rows = [i for i in range(76733)]
	data = pd.DataFrame(index=rows, columns=edgeIDs)
	#data.fillna([])
	populate(data, jsondata)
	


def populate(data, jsondata):
	#Populate the pandas data
	for vehicle in jsondata.keys():
		for i in range(len(jsondata[vehicle]['edges'])):
			veh_locs = data.loc[int(jsondata[vehicle]['exitTimes'][i][:-3]), jsondata[vehicle]['edges'][i]]
			if type(veh_locs) != list:
				veh_locs = [vehicle]
			else:
				veh_locs.append(vehicle)




write_routes()
#matrixitize()

