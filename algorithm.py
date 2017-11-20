import random
from timeit import default_timer
from deap import base
from deap import creator
from deap import tools
from solution import Solution
from dataprocess import generate_dump


def generation(order_prob, rand_func, gen_order, gen_chaos):
    x = rand_func()
    if x < order_prob:
        ind = gen_order()
    else:
        ind = gen_chaos()
    return ind


def generation_wrapper(container, generation_func):
    ind = generation_func()
    return container(ind.starting_points, ind.client_order, ind.product_delivery, ind.log[0])


def crossover_wrapper(child_1, child_2):
    Solution.cx_wrapper(child_1, child_2)


def mutation_wrapper(individual):
    individual.mutation()


def evaluate(individual):
    a = individual.first_echelon_cost()
    b = individual.second_echelon_cost()
    c = individual.nr_vehicles_used()
    d = individual.total_emissions()
    return a,b,c,d

# ordered generation probability
ORPB = 0.3


creator.create("FitnessMin", base.Fitness, weights=(-1.0,-1.0,-1.0,-1.0))
creator.create("Individual", Solution, fitness=creator.FitnessMin)

toolbox = base.Toolbox()

toolbox.register("rand_func", random.random)
toolbox.register("gen_order", Solution.generate_order)
toolbox.register("gen_chaos", Solution.generate_chaos)
toolbox.register("generation", generation, ORPB,
                 toolbox.rand_func, toolbox.gen_order, toolbox.gen_chaos)
toolbox.register("individual", generation_wrapper, creator.Individual, toolbox.generation)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)
toolbox.register("evaluate", evaluate)
toolbox.register("mate", crossover_wrapper)
toolbox.register("mutate", mutation_wrapper)
toolbox.register("select", tools.selNSGA2)


def nsga2(seed=None, NGEN=100, MU=100, CXPB=0.5, dump_intrval=0):
    """Execute NSGA-II-based algorithm for the M2-2E-VRP.

    Taken and adapted from DEAP example.
    Keyword arguments:
        seed -- seed for randomness
        NGEN -- number of generations (default 100)
        MU -- size of [initial] population (default 100)
        CXPB -- crossover probability (default 0.5)
        dump_intrval -- interval at which dump files are generated (default 0)
    """
    random.seed(seed)

    # begin recording time
    t0 = default_timer()

    # file io time to be subtracted
    file_time = 0

    # initial population generation
    pop = toolbox.population(n=MU)

    # Evaluate the individuals with an invalid fitness
    invalid_ind = [ind for ind in pop if not ind.fitness.valid]
    fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
    for ind, fit in zip(invalid_ind, fitnesses):
        ind.fitness.values = fit

    # This is just to assign the crowding distance to the individuals
    pop = toolbox.select(pop,MU)

    # Begin the generational process
    for gen in range(1, NGEN+1):

        # print during each Generation in order to follow execution flow
        print "Generation " + str(gen)

        # Vary the population
        offspring = tools.selTournamentDCD(pop, len(pop))
        offspring = [toolbox.clone(ind) for ind in offspring]

        for ind1, ind2 in zip(offspring[::2], offspring[1::2]):
            if random.random() <= CXPB:
                toolbox.mate(ind1, ind2)

            toolbox.mutate(ind1)
            toolbox.mutate(ind2)
            del ind1.fitness.values, ind2.fitness.values

        # Evaluate the individuals with an invalid fitness
        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
        for ind, fit in zip(invalid_ind, fitnesses):
            ind.fitness.values = fit

        # Select the next generation population
        pop = toolbox.select(pop + offspring, MU)

        # dump every 'intrval' (usually 50) generations
        if dump_intrval > 0 and gen % dump_intrval == 0:
            # determine execution time
            tx = default_timer()
            total_time = (tx-t0)
            exec_time = total_time - file_time
            # obtain pareto front
            fronts = tools.sortNondominated(pop, len(pop), first_front_only=True)
            front = fronts[0]
            # generate dump
            generate_dump(MU,gen,total_time,exec_time,front)
            ty = default_timer()
            file_time += (ty-tx)

    return pop


def main():
    pop = nsga2(NGEN=10)
    # to double check it's actually a set
    for i in range(4):
        pop = sorted(pop, key=lambda ind: ind.fitness.values[3-i])
    for ind in pop:
        print ind.fitness.values
    print len(pop)
    # select individuals with minimum value for each objective function
    sol = [min(pop, key=lambda ind: ind.fitness.values[i]) for i in range(4)]
    for ind in sol:
        print repr(ind)
        print "{:.5f}\t{:.5f}\t{:d}\t{:.5f}\t{}".format(
            ind.fitness.values[0],
            ind.fitness.values[1],
            int(ind.fitness.values[2]),
            ind.fitness.values[3],
            ind.log)


if __name__ == "__main__":
    main()