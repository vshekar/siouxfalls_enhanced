import os
import math
import sys
import time

import multiprocessing.popen_spawn_posix  # Python 3.9 workaround for Dask.  See https://github.com/dask/distributed/issues/4168
from distributed import Client
from dask.utils import format_bytes
import toolz

from leap_ec import context, test_env_var
from leap_ec import ops
from leap_ec.decoder import IdentityDecoder
from leap_ec.binary_rep.initializers import create_binary_sequence
from leap_ec.binary_rep.ops import mutate_bitflip
from leap_ec.binary_rep.problems import MaxOnes
from leap_ec.distrib import DistributedIndividual
from leap_ec.distrib import synchronous
from leap_ec.probe import AttributesCSVProbe

from dask_jobqueue import lsf, JobQueueCluster

import pandas as pd

from leap_ec.problem import ScalarProblem
import numpy as np
from ga_simulator import get_subnet, run_sim
from dask.distributed import get_worker

LAMBDA = 3
SIZE = len(get_subnet('18_1', LAMBDA))
BUDGET = 5
WORKERS = 4
GENERATIONS = 2
CORES = 4
MEMORY = CORES*2
MESO = True

def evalOneMax(individual, lmbd=LAMBDA, budget=BUDGET):
    #lmbd = 3
    edge = '18_1'
    start_time = 57600
    end_time = 86400
    
    #end_time = 10
    try:
        rank = get_worker().id
    except:
        rank = 0
    
    if np.sum(individual) > budget:
        penalty = -10*(np.sum(individual) - budget)
    else:
        penalty = 0
    vul = run_sim(lmbd, edge, start_time, end_time, rank, individual, meso=MESO)
    return vul+penalty 

class EvalSumo(ScalarProblem):
    def __init__(self, lmbd, budget, maximize=True):
        self.lmbd = lmbd
        self.budget = budget
        super().__init__(maximize)

    def evaluate(self, phenome):
        if not isinstance(phenome, np.ndarray):
            raise ValueError(("Expected phenome to be a numpy array. "
                              f"Got {type(phenome)}."))
        phenome = phenome.tolist()
        return evalOneMax(phenome, lmbd=self.lmbd, budget=self.budget)


def create_indv_func(budget=BUDGET, size=SIZE):
    def create_indv():
        indv = np.random.binomial(1, budget/size, size=size)
        return indv
    return create_indv


class LSFJob(lsf.LSFJob):
    @property
    def worker_process_threads(self):
        return 1

    @property
    def worker_process_memory(self):
        mem = format_bytes(self.worker_memory/self.worker_cores)
        mem = mem.replace(" ", "")
        return mem


class LSFCluster(JobQueueCluster):
    job_cls = LSFJob



if __name__ == '__main__':
    if len(sys.argv) == 5:
        BUDGET, WORKERS, CORES, GENERATIONS = (int(arg) for arg in sys.argv[1:])
        MEMORY = CORES*2
        
    cluster = LSFCluster(name='sumo_ga', 
               interface='ib0', queue='short', #n_workers=WORKERS,
               cores=CORES, memory=f'{MEMORY}GB', job_extra=['-R select[rh=8]'],
               walltime='4:00', ncpus=CORES, processes=CORES,
               header_skip=['span']
               )
    scale = math.ceil((WORKERS*1.0)/CORES)
    #cluster.scale(jobs=scale)
    cluster.scale(jobs=1)
    print(cluster.job_script())
    result_data = {'Population':[], 'Max':[], 'Min':[], 'Average':[], 'Best':[]}

    # We've added some additional state to the probe for DistributedIndividual,
    # so we want to capture that.
    probe = AttributesCSVProbe(attributes=['hostname',
                                           'pid',
                                           'uuid',
                                           'birth_id',
                                           'start_eval_time',
                                           'stop_eval_time'],
                               do_fitness=True,
                               do_genome=True,
                               stream=open('simple_sync_distributed.csv', 'w'))

    # Just to demonstrate multiple outputs, we'll have a separate probe that
    # will take snapshots of the offspring before culling.  That way we can
    # compare the before and after to see what specific individuals were culled.
    offspring_probe = AttributesCSVProbe(attributes=['hostname',
                                           'pid',
                                           'uuid',
                                           'birth_id',
                                           'start_eval_time',
                                           'stop_eval_time'],
                               do_fitness=True,
                               stream=open('simple_sync_distributed_offspring.csv', 'w'))

    #with Client(n_workers=WORKERS, threads_per_worker=1) as client:
    with Client(cluster) as client:
        # create an initial population of 5 parents of 4 bits each for the
        # MAX ONES problem
        parents = DistributedIndividual.create_population(100, # make five individuals
                                                          initialize=create_indv_func(
                                                              budget=BUDGET,
                                                              size=SIZE
                                                          ), 
                                                          decoder=IdentityDecoder(),
                                                          problem=EvalSumo(LAMBDA, BUDGET))

        # Scatter the initial parents to dask workers for evaluation
        parents = synchronous.eval_population(parents, client=client)

        # probes rely on this information for printing CSV 'step' column
        context['leap']['generation'] = 0

        probe(parents) # generation 0 is initial population
        offspring_probe(parents) # generation 0 is initial population

        # When running the test harness, just run for two generations
        # (we use this to quickly ensure our examples don't get bitrot)
        if os.environ.get(test_env_var, False) == 'True':
            generations = 2
        else:
            generations = GENERATIONS

        for current_generation in range(generations):
            context['leap']['generation'] += 1

            offspring = toolz.pipe(parents,
                                   ops.tournament_selection,
                                   ops.clone,
                                   mutate_bitflip(probability=0.05),
                                   ops.uniform_crossover,
                                   # Scatter offspring to be evaluated
                                   synchronous.eval_pool(client=client,
                                                         size=len(parents)),
                                   offspring_probe, # snapshot before culling
                                   ops.elitist_survival(parents=parents),
                                   # snapshot of population after culling
                                   # in separate CSV file
                                   probe)

            print('generation:', current_generation)
            with open('output.txt', 'w') as f:
                [print(x.genome, x.fitness, file=f) for x in offspring]
            fitness = [x.fitness for x in offspring]
            genomes = [x.genome for x in offspring]

            result_data['Average'].append(np.mean(fitness))
            result_data['Max'].append(np.max(fitness))
            result_data['Min'].append(np.min(fitness))
            result_data['Population'].append(len(fitness))
            result_data['Best'].append(genomes[np.argmax(fitness)])
            pd.DataFrame.from_dict(result_data).to_csv(f'ga_results_{LAMBDA}_{BUDGET}_{GENERATIONS}.csv')

            parents = offspring
    cluster.close()
    print('Final population:')
    with open('output.txt', 'w') as f:
        [print(x.genome, x.fitness, file=f) for x in parents]
    
    