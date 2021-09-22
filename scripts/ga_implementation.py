import array
import random

import numpy

from deap import algorithms
from deap import base
from deap import creator
from deap import tools
from ga_simulator import evalOneMax, get_subnet, run_sim


import os
import json
import multiprocessing as mp
import pickle
from itertools import combinations

import numpy as np

from traci import start

creator.create("FitnessMax", base.Fitness, weights=(1.0,))
creator.create("Individual", array.array, typecode='b', fitness=creator.FitnessMax)

LAMBDA = 3
SIZE = len(get_subnet('18_1', LAMBDA))
BUDGET = 10
CXPB = 1.0
MUTPB = 1.0

toolbox = base.Toolbox()

# Attribute generator
toolbox.register("attr_bool", random.randint, 0, 1)

def create_indv(container, budget, size):
    indv = np.random.binomial(1, budget/size, size=size).tolist()
    return container(i for i in indv)

# Structure initializers
#toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.attr_bool, SIZE)
toolbox.register("individual", create_indv, creator.Individual, BUDGET, SIZE)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)
#toolbox.register("population_guess", init_population, list, toolbox.individual)


poolSize = mp.cpu_count() - 2
p = mp.Pool(poolSize)
toolbox.register("map", p.map)

toolbox.register("evaluate", evalOneMax, lmbd=LAMBDA)
toolbox.register("mate", tools.cxTwoPoint)
toolbox.register("mutate", tools.mutFlipBit, indpb=0.05)
toolbox.register("select", tools.selTournament, tournsize=3)

def main():
    random.seed(64)
    
    pop = toolbox.population(n=100)
    #pop = toolbox.population_guess(n=100)
    hof = tools.HallOfFame(1)
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", numpy.mean)
    stats.register("std", numpy.std)
    stats.register("min", numpy.min)
    stats.register("max", numpy.max)
    
    pop, log = algorithms.eaSimple(pop, toolbox, cxpb=CXPB, mutpb=MUTPB, ngen=40, 
                                   stats=stats, halloffame=hof, verbose=True)
    
    return pop, log, hof

if __name__ == "__main__":
    pop, log, hof = main()
    pickle.dump(pop, open(f'./final_results/pop_lmbd{LAMBDA}_cxpb{CXPB}_mutpb{MUTPB}.pkl', 'wb'))
    pickle.dump(log, open(f'./final_results/log_lmbd{LAMBDA}_cxpb{CXPB}_mutpb{MUTPB}.pkl', 'wb'))
    pickle.dump(hof, open(f'./final_results/hof_lmbd{LAMBDA}_cxpb{CXPB}_mutpb{MUTPB}.pkl', 'wb'))
    
    
    #lmbd = 9
    #edge = '18_1'
    #start_time = 57600
    #end_time = 86400
    #rank = 0

    #hof_lmbd3 = pickle.load(open('hof_lmbd3.pkl', 'rb'))
    #subnet_edges = get_subnet(edge, 3)
    #individual = [subnet_edge for i, subnet_edge in enumerate(subnet_edges) if hof_lmbd3[0][i]]
    #print(f'HOF 3. lambda 3: {evalOneMax(hof_lmbd3[0], lmbd=3)}\n Gene: {individual}')

    #vulnerability = run_sim(lmbd, edge, start_time, end_time, rank, individual)
    #print(f'HOF 3. lambda 9: {vulnerability}\n Gene: {individual}')

    #hof_lmbd2 = pickle.load(open('hof_lmbd2.pkl', 'rb'))
    #subnet_edges = get_subnet(edge, 2)
    #individual = [subnet_edge for i, subnet_edge in enumerate(subnet_edges) if hof_lmbd2[0][i]]
    #print(f'HOF 2. lambda 2: {evalOneMax(hof_lmbd2[0], lmbd=2)}\n Gene: {individual}')
    #print(set(['12_1', '19_1', '20_1', '26_1', '29_1', '32_1', '43_1', '49_1', '52_1', '54_1']).difference(set(subnet_edges)))

    #vulnerability = run_sim(lmbd, edge, start_time, end_time, rank, individual)
    #print(f'HOF 2. lambda 9: {vulnerability}\n Gene: {individual}')

    #subnet_edges = get_subnet(edge, 9)
    #individual = [subnet_edge for subnet_edge in subnet_edges]
    #vulnerability = run_sim(lmbd, edge, start_time, end_time, rank, individual)
    #print(f'All links with rerouters. lambda 9: {vulnerability}')
    
    #hof_lmbd2 = pickle.load(open('hof_lmbd2.pkl', 'rb'))
    #print(f'HOF 2. lambda 2: {evalOneMax(hof_lmbd2[0], lmbd=2)}')
    #print(f'HOF 2. lambda 9: {evalOneMax(hof_lmbd2[0], lmbd=9)}')