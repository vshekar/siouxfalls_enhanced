import os

import multiprocessing.popen_spawn_posix  # Python 3.9 workaround for Dask.  See https://github.com/dask/distributed/issues/4168
from distributed import Client
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

from dask_jobqueue import LSFCluster

from leap_ec.problem import ScalarProblem
import numpy as np
from ga_simulator import evalOneMax, get_subnet

LAMBDA = 1
SIZE = len(get_subnet('18_1', LAMBDA))
BUDGET = 1
CXPB = .5
MUTPB = .5
WORKERS = 5

class EvalSumo(ScalarProblem):
    def __init__(self, maximize=True):
        super().__init__(maximize)

    def evaluate(self, phenome):
        if not isinstance(phenome, np.ndarray):
            raise ValueError(("Expected phenome to be a numpy array. "
                              f"Got {type(phenome)}."))
        phenome = phenome.tolist()
        return evalOneMax(phenome)


def create_indv(budget=BUDGET, size=SIZE):
    indv = np.random.binomial(1, budget/size, size=size)
    return indv


if __name__ == '__main__':
    cluster = LSFCluster(name='sumo_ga', 
               interface='ib0', queue='short', 
               cores=WORKERS, memory='8GB', job_extra=['-R select[rh=8]'],
               walltime='04:00:00',
               )

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
        parents = DistributedIndividual.create_population(5, # make five individuals
                                                          initialize=create_indv, 
                                                          decoder=IdentityDecoder(),
                                                          problem=EvalSumo())

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
            generations = 5

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
            [print(x.genome, x.fitness) for x in offspring]

            parents = offspring

    print('Final population:')
    [print(x.genome, x.fitness) for x in parents]