from timeit import default_timer
from time import asctime
from numpy import amin
from solution import Solution
from dataprocess import obtain_input_data


# tiny instance
input_file="instances\\tiny_2d_3s_5c.txt"


class NoMoreCombosError(Exception):
    """Exception used to indicate no more possible combinations."""
    pass


def evaluate(individual):
    """Obtain fitness values of individual."""
    a = individual.first_echelon_cost()
    b = individual.second_echelon_cost()
    c = individual.nr_vehicles_used()
    d = individual.total_emissions()
    return a,b,c,d


def exhaustive_search(max_pd_values,min_pd_values, t0):
    """Exhaustively search through all possible solutions.

    Does all the work and updates the Pareto set approximation.
    Keyword arguments:
        max_pd_values -- list of maximum product delivery values
        min_pd_values -- list of minimum product delivery values
        t0 -- time of execution initiation
    """
    # current product delivery matrix
    current_pd = min_pd_values[:]
    max_sp_values,min_sp_values = compute_sp_values(current_pd)
    # current starting point matrix
    current_sp = min_sp_values[:]
    # current solution in list form
    current = current_sp + current_pd
    sol = make_solution(current)
    front = []
    need_next_combo = False
    counter = 0
    while True:
        # iterate through product delivery matrix combinations
        while not no_overflow(sol) or need_next_combo:
            need_next_combo = False
            try:
                next_combo(current_pd,max_pd_values,min_pd_values)
            except NoMoreCombosError:
                # generate Pareto front and return
                return front, counter
            current = current_sp + current_pd
            sol = make_solution(current)
        # obtain ranges for starting point values according to valid product delivery matrix
        max_sp_values, min_sp_values = compute_sp_values(current_pd)
        current_sp = min_sp_values[:]
        # iterate through starting point array combinations
        while not need_next_combo:
            counter += 1
            if counter % 10000 == 0:
                tx = default_timer()
                sols = [ind[1] for ind in front]
                mins = amin(sols,0)
                print "{:>10d}\t{:>5d}\t{:>10.3f} s\t{:>15.5f}\t{:>15.5f}\t{:>5d}\t{:>15.5f}".format(
                    counter,len(front),(tx-t0),
                    mins[0],mins[1],int(mins[2]),mins[3])
            # generate new current solution
            current = current_sp + current_pd
            sol = make_solution(current)
            # list of clients served by each vehicle
            clients_served = [[cl for cl in range(Solution.client_nr) if ve + 1 in sol.product_delivery[cl]]
                              for ve in range(Solution.vehicle_nr)]
            # deterministic client order
            sol.order_client_visits(clients_served)
            # update front with new solution
            update_front(front,sol)
            try:
                next_combo(current_sp,max_sp_values,min_sp_values)
            except NoMoreCombosError:
                need_next_combo = True


def next_combo(current, max_values, min_values):
    """Compute next permutation given current combination and range of values.

    Keyword arguments:
        current -- current permutation, modified in-place
        max_values -- list of maximum values for each position in current
        min_values -- list of minimum values for each position in current
    """
    for pos in range(len(current) - 1, -1, -1):
        if current[pos] < max_values[pos]:
            current[pos] += 1
            if pos < len(current) - 1:
                for i in range(pos + 1, len(current)):
                    current[i] = min_values[i]
            return
    raise NoMoreCombosError


def compute_sp_values(current_pd):
    """Return lists of starting point value ranges.

    Keyword arguments:
        current_pd -- current product delivery matrix in list form
    """
    max_sp_values = [Solution.satellite_nr] * Solution.vehicle_nr
    min_sp_values = [0] * Solution.vehicle_nr
    # produce product delivery matrix
    product_delivery = [current_pd[i:i + Solution.product_nr]
                        for i in range(0, len(current_pd), Solution.product_nr)]
    # determine clients served by each vehicle
    clients_served = [[cl for cl in range(Solution.client_nr) if ve + 1 in product_delivery[cl]]
                      for ve in range(Solution.vehicle_nr)]
    # iterate through vehicles
    for vehicle in range(Solution.vehicle_nr):
        # if a client is served, there must be a satellite (range: [1,3])
        if len(clients_served[vehicle]) > 0:
            min_sp_values[vehicle] = 1
        # else, there may be no satellite (range: [0,0)
        elif len(clients_served[vehicle]) == 0:
            max_sp_values[vehicle] = 0
    return max_sp_values,min_sp_values


def make_solution(sol_in_list_form):
    """Return solution object given solution in list form.

    Keyword arguments:
        sol_in_list_form -- solution in list form
    """
    # extract the starting points
    starting_points = sol_in_list_form[:Solution.vehicle_nr]
    # extract the product delivery list and make a matrix
    product_delivery_list = sol_in_list_form[Solution.vehicle_nr:]
    product_delivery = [product_delivery_list[i:i+Solution.product_nr]
                        for i in range(0,len(product_delivery_list),Solution.product_nr)]
    # set client order to zero as it will be corrected elsewhere
    client_order = [[0] * Solution.vehicle_nr for i in range(Solution.client_nr)]
    sol = Solution(starting_points,client_order,product_delivery)
    return sol


def no_overflow(sol):
    """Return True if no second-echelon exceeds capacity, otherwise False.

    Keyword arguments:
        sol -- solution object
    """
    remaining_capacity = sol.determine_overflow()
    for i in range(Solution.vehicle_nr):
        if remaining_capacity[i] < 0:
            return False
    return True


def update_front(front, new_sol):
    """Update Pareto set approximation given a new solution.

    Keyword arguments:
        front -- current Pareto set approximation
        new_sol -- new solution object to be tested against current set
    """
    new_sol_fitness = evaluate(new_sol)
    new_sol_tuple = (new_sol,new_sol_fitness)
    for sol_tuple in front:
        if dominates(sol_tuple[1],new_sol_fitness):
            return
        elif dominates(new_sol_fitness,sol_tuple[1]):
            front.remove(sol_tuple)
    front.append(new_sol_tuple)


def dominates(sol_fitness_1, sol_fitness_2):
    """Return True if first solution dominates second, False otherwise.

    Fitness must be less in a minimization context.
    Keyword arguments:
        sol_fitness_2 -- fitness values of first solution
        sol_fitness_2 -- fitness values of second solution
    """
    not_equal = False
    for fitness_1, fitness_2 in zip(sol_fitness_1, sol_fitness_2):
        if fitness_1 > fitness_2:
            return False
        elif fitness_1 < fitness_2:
            not_equal = True
    return not_equal


def main(filename=input_file):
    """Obtain and dump Pareto set approximation, given instance file.

    Keyword arguments:
        filename -- path of input file (default tiny_instance)
    """
    # obtain parameters
    e1, e2, dmd, veh = obtain_input_data(filename)
    # set environment parameters
    Solution.set_environment(veh, dmd, e1, e2)
    # set timer
    t0 = default_timer()
    # make list with maximum values for each gene
    max_pd_values = [Solution.vehicle_nr] * (Solution.client_nr * Solution.product_nr)
    # make list of minimum values
    min_pd_values = [0] * len(max_pd_values)
    # set product_delivery maximum values to zero if no demand
    for client in range(Solution.client_nr):
        for product in range(Solution.product_nr):
            if Solution.demand[client][product] == 0:
                max_pd_values[client * Solution.product_nr + product] = 0
            else:
                min_pd_values[client * Solution.product_nr + product] = 1
    # obtain real Pareto front
    front, counter = exhaustive_search(max_pd_values, min_pd_values, t0)
    # end timer
    tf = default_timer()
    # sort solutions
    for i in range(4):
        front = sorted(front, key=lambda ind: ind[1][3 - i])
    # file with overhead data and solutions
    solution_filename = "exhaustive_solutions.txt"
    solution_file = open(solution_filename, 'w')
    # write time and date at beginning of solution file
    solution_file.write("{}\n".format(asctime()))
    # write down total number of counted solutions
    solution_file.write("{} solutions tried\n".format(counter))
    # write down size of Pareto front
    solution_file.write("{} solutions in Pareto front\n".format(len(front)))
    # obtain total time in hours, minutes, seconds
    minutes, seconds = divmod(int(round(tf-t0)), 60)
    hours, minutes = divmod(minutes, 60)
    solution_file.write("Total elapsed time: {:0d}:{:02d}:{:02d}\n".format(hours, minutes, seconds))
    # file with fitness
    fitness_filename = "exhaustive_fitness.txt"
    fitness_file = open(fitness_filename, 'w')
    # write down all solutions and fitness
    for ind in front:
        solution_file.write("{}\n".format(repr(ind)))
        fitness_file.write("{:>15.5f}\t{:>15.5f}\t{:>5d}\t{:>15.5f}\n".format(
            ind[1][0], ind[1][1], int(ind[1][2]), ind[1][3]))
    # close files
    solution_file.close()
    fitness_file.close()


if __name__ == "__main__":
    main(input_file)