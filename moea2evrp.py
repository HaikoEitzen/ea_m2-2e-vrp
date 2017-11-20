from solution import Solution
from algorithm import nsga2
from dataprocess import obtain_input_data
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="This is a MOEA solver for the Multi-Objective Multi-Depot"
                                                 "Two-Echelon Vehicle Routing Problem with Heterogeneous Fleets")
    parser.add_argument("filename")
    parser.add_argument("ngen",type=int)
    parser.add_argument("npop",type=int)
    parser.add_argument("intrval",type=int)
    args = parser.parse_args()
    first_echelon, second_echelon, demand, vehicles = obtain_input_data(args.filename)
    Solution.set_environment(vehicles, demand, first_echelon, second_echelon)
    pop = nsga2(NGEN=args.ngen, MU=args.npop, dump_intrval=args.intrval)
    sol = [min(pop, key=lambda ind: ind.fitness.values[i]) for i in range(4)]
    for ind in sol:
        print repr(ind)
        print "{:.5f}\t{:.5f}\t{:d}\t{:.5f}\t{}".format(
            ind.fitness.values[0],
            ind.fitness.values[1],
            int(ind.fitness.values[2]),
            ind.fitness.values[3],
            ind.log)