import re
from solution import Solution
from time import strftime, asctime


def obtain_input_data(filename):
    """Return distance, demand, and vehicle data matrices.

    Returns four matrices: first-echelon distance, second-echelon distance, demand, and vehicle data.
    Keyword arguments:
        filename -- path of input file
    """
    # opens file and extracts data
    with open(filename) as file:
        lines = file.readlines()
    # separate all data by [any combination of] tabs [using regular expressions]
    data = [re.split(r'\t+',line.rstrip('\t')) for line in lines]
    # the first line contains the number of depots, satellites, and clients
    nr_depots, nr_satellites, nr_clients = int(data[0][0]), int(data[0][1]), int(data[0][2])
    # set the dimensions of the distance matrices
    e1_nr = nr_depots + nr_satellites
    e2_nr = nr_satellites + nr_clients
    # build the echelon 1 and echelon 2 distance matrices
    e1 = [[float(data[x][y]) for y in range(1,e1_nr + 1)] for x in range(1,e1_nr + 1)]
    e2 = [[float(data[x][y]) for y in range(1,e2_nr + 1)] for x in range(1 + e1_nr, e1_nr + e2_nr + 1)]
    # build demand matrix
    dmd_start = 1 + e1_nr + e2_nr
    dmd_end = dmd_start + nr_clients
    demand = [[int(data[x][y]) for y in range(nr_depots)] for x in range(dmd_start,dmd_end)]
    # build vehicle data matrix
    l1_cpk, l1_emissions = float(data[dmd_end][2]), int(data[dmd_end][3])
    l2_capacity, l2_cpk, l2_emissions = [],[],[]
    for line in data[dmd_end+1:]:
        quantity = int(line[4])
        l2_capacity += [int(line[1])] * quantity
        l2_cpk += [float(line[2])] * quantity
        l2_emissions += [int(line[3])] * quantity
    vehicles = [l2_capacity,l2_cpk,l2_emissions,l1_cpk,l1_emissions]
    return e1,e2,demand,vehicles


def generate_dump(nr_pop,gen,total_time,exec_time,front):
    """Generate dump files during algorithm execution.

    Generates two dump files on a determined generation. The first has a lot of data, the second only fitness values.
    Keyword arguments:
        nr_pop -- size N of [initial] population
        gen -- generation number
        total_time -- total elapsed time since initiating execution
        exec_time -- elapsed execution time
        front -- set of solutions corresponding to Pareto set approximation
    """
    # create file name
    filename = "dumps\\{nr_d}d_{nr_s}s_{nr_c}c\\dump_{nr_d}d_{nr_s}s_{nr_c}c_{n_i}i_gen{n_g}_{td}.txt".format(
        nr_d=Solution.product_nr, nr_s=Solution.satellite_nr,
        nr_c=Solution.client_nr, n_i=nr_pop, n_g=gen, td=strftime("%Y%m%d%H%M%S"))
    # open dump file to write
    with open(filename, 'w') as dump_file:
        # header: date and time, details of instance, generation number, computation time
        dump_file.write("{}\n".format(asctime()))
        dump_file.write("{} depots\n{} satellites\n{} clients\n".format(Solution.product_nr,
                                                                        Solution.satellite_nr,
                                                                        Solution.client_nr))
        dump_file.write("Population size: {} individuals\n".format(nr_pop))
        dump_file.write("Generation {}\n".format(gen))
        # obtain total time in hours, minutes, seconds
        minutes, seconds = divmod(int(round(total_time)), 60)
        hours, minutes = divmod(minutes, 60)
        dump_file.write("Total elapsed time: {:0d}:{:02d}:{:02d}\n".format(hours, minutes, seconds))
        # obtain execution time in hours, minutes, seconds
        minutes, seconds = divmod(int(round(exec_time)), 60)
        hours, minutes = divmod(minutes, 60)
        dump_file.write("Elapsed execution time: {:0d}:{:02d}:{:02d}\n".format(hours, minutes, seconds))
        # Pareto Front
        dump_file.write("Pareto Front ({} individuals)\n".format(len(front)))
        dump_file.write("Solutions\n")
        # sort solutions
        for i in range(4):
            front = sorted(front, key=lambda ind: ind.fitness.values[3 - i])
        # write all solutions in front including log
        for ind in front:
            dump_file.write("{}\n{}\n{}\n".format(repr(ind), ind.fitness.values, ind.log))
        # write all fitness in same order as solution above
        dump_file.write("Objective functions\n"
                        "f0 - First-echelon cost (Guaranies)\n"
                        "f1 - Second-echelon cost (Guaranies)\n"
                        "f2 - Total vehicles used\n"
                        "f3 - Total emissions produced (grams)\n")
        for ind in front:
            dump_file.write("{:>20.5f}\t{:>20.5f}\t{:>5d}\t{:>20.5f}\n".format(
                ind.fitness.values[0],
                ind.fitness.values[1],
                int(ind.fitness.values[2]),
                ind.fitness.values[3]))
        # write best solutions for each OF
        dump_file.write("Best solutions for each OF\n")
        best = [min(front, key=lambda ind: ind.fitness.values[i]) for i in range(4)]
        for obj_func, ind in enumerate(best):
            dump_file.write("Function {}\n".format(obj_func))
            dump_file.write("{}\n".format(repr(ind)))
            dump_file.write("{:>15.5f}\t{:>15.5f}\t{:>5d}\t{:>15.5f}\n{}\n".format(
                ind.fitness.values[0],
                ind.fitness.values[1],
                int(ind.fitness.values[2]),
                ind.fitness.values[3],
                ind.log))
    # dump file just with fitness values (equal to objective function values by design)
    fitness_dump_filename = "dumps\\{nr_d}d_{nr_s}s_{nr_c}c" \
                            "\\fitness_dump_{nr_d}d_{nr_s}s_{nr_c}c_{n_i}i_gen{n_g}_{td}.txt".format(
                            nr_d=Solution.product_nr, nr_s=Solution.satellite_nr,
                            nr_c=Solution.client_nr, n_i=nr_pop, n_g=gen, td=strftime("%Y%m%d%H%M%S"))
    with open(fitness_dump_filename,'w') as dump_file:
        for ind in front:
            dump_file.write("{:>15.5f}\t{:>15.5f}\t{:>5d}\t{:>15.5f}\n".format(
                ind.fitness.values[0],
                ind.fitness.values[1],
                int(ind.fitness.values[2]),
                ind.fitness.values[3]))