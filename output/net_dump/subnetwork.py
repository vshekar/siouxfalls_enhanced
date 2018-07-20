# -*- coding: utf-8 -*-
"""
Created on Fri Jun 29 14:57:37 2018

@author: Shekar
"""

import json

f = open('vehroutes.json', 'r')

routes = json.loads(f.read())

print(routes['0'])
