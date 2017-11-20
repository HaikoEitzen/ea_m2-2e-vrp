from solution import Solution
from algorithm import nsga2
from dataprocess import obtain_input_data
from exhaustive import make_solution, dominates
from deap import tools
from deap import creator
from deap import base

pareto_file = "exhaustive_individuals.txt"
fitness_file = "exhaustive_fitness.txt"
instance_file = "instances\\tiny_2d_3s_5c.txt"


def evaluate(individual):
    a = individual.first_echelon_cost()
    b = individual.second_echelon_cost()
    c = individual.nr_vehicles_used()
    d = individual.total_emissions()
    return a,b,c,d


creator.create("FitnessMin", base.Fitness, weights=(-1.0,-1.0,-1.0,-1.0))
creator.create("Individual", Solution, fitness=creator.FitnessMin)


def obtain_pareto_front(pareto_file):
    with open(pareto_file) as file:
        lines = file.readlines()
    data = [line.split() for line in lines]
    data = [[int(elem) for elem in row] for row in data]
    front = []
    for i in range(0,(52*6),6):
        sp = data[i]
        pd = []
        for j in range(1,6):
            pd += data[i+j]
        sollf = sp + pd
        sol = make_solution(sollf)
        ind = creator.Individual(sol.starting_points,sol.client_order,sol.product_delivery,'Pareto')
        ind.correct()
        ind.fitness.values = evaluate(ind)
        front.append(ind)
    return front


if __name__ == "__main__":
    first_echelon, second_echelon, demand, vehicles = obtain_input_data(instance_file)
    Solution.set_environment(vehicles, demand, first_echelon, second_echelon)
    pareto_front = obtain_pareto_front(pareto_file)
    pop = []
    for i in range(10):
        print "Run " + str(i)
        pop.append(nsga2(NGEN=200, MU=200, dump_intrval=50))
    pop_final = []
    for i in range(10):
        pop_final += pop[i]
    pop_final = set(pop_final)
    pop_fronts = tools.sortNondominated(pop_final,len(pop_final),first_front_only=True)
    pop_front = pop_fronts[0]
    for i in range(4):
        pop_front = sorted(pop_front, key=lambda ind: ind.fitness.values[3 - i])
    dom_count = 0
    pareto_error = 0
    for sol in pop_front:
        if sol not in pareto_front:
            dom_count += 1
            for par_sol in pareto_front:
                if dominates(sol.fitness.values,par_sol.fitness.values):
                    pareto_error += 1
    with open("tiny_comparison_test.txt",'w') as file:
        file.write("pop front\n")
        for ind in pop_front:
            file.write("{}\n{}\n".format(repr(ind),ind.fitness.values))
        for ind in pop_front:
            file.write("{:>20.5f}\t{:>20.5f}\t{:>5d}\t{:>20.5f}\n".format(
                ind.fitness.values[0],
                ind.fitness.values[1],
                int(ind.fitness.values[2]),
                ind.fitness.values[3]))
        file.write("\n")
        file.write("pareto front\n")
        for ind in pareto_front:
            file.write("{}\n{}\n".format(repr(ind), ind.fitness.values))
        for ind in pareto_front:
            file.write("{:>20.5f}\t{:>20.5f}\t{:>5d}\t{:>20.5f}\n".format(
                ind.fitness.values[0],
                ind.fitness.values[1],
                int(ind.fitness.values[2]),
                ind.fitness.values[3]))
        file.write("dominated solutions in pop front: {}\n".format(dom_count))
        file.write("dominated solutions in pareto front: {}\n".format(pareto_error))