from random import shuffle, randint, choice
from operator import itemgetter
from copy import deepcopy as dcpy
from numpy import ndindex as nrange
from tsptools import tsp
from tools import make_submatrix


class Solution(object):

    """Represent solutions for the Multi-Objective Multi-Commodity 2E-VRP with heterogeneous vehicle fleets.

    Attributes:
        capacity -- list of capacities of second-echelon vehicles
        cost_per_km -- list of cost per kilometer values for second-echelon vehicles
        emissions -- list of carbon emissions per kilometer produced by second-echelon vehicles
        l1_cpk -- cost per kilometer of first-echelon vehicle type
        l1_emissions -- carbon emissions per kilometer produced by first-echelon vehicle type
        demand -- client demand matrix
        first_echelon -- matrix of distances between depots and satellites
        second_echelon -- matrix of distances between satellites and clients
        vehicle_nr -- number of second-echelon vehicles available
        client_nr -- number of clients
        satellite_nr -- number of satellites
        product_nr -- number of products (depots)

    """

    # These MUST be correctly established before any instantiation
    capacity = []
    cost_per_km = []
    emissions = []
    l1_cpk = 0
    l1_emissions = 0
    demand = []
    first_echelon = []
    second_echelon = []
    vehicle_nr = 0
    client_nr = 0
    satellite_nr = 0
    product_nr = 0

    def __init__(self, starting_points, client_order, product_delivery, initial_log="initiated"):
        """Initialize Solution object.

        Keyword arguments:
            starting_points -- list of satellites where second-echelon vehicles start and end their routes
            client_order -- the order in which vehicles visit clients
            product_delivery -- matrix that indicates which vehicles deliver which products to which clients
            initial_log -- initial string for object log of modifications
        """
        self.starting_points = starting_points
        self.client_order = client_order
        self.product_delivery = product_delivery
        # placeholder, computed by first_echelon_distances, used for fitness functions
        self.l1_distance = 0
        # placeholder, computed by first_echelon_distances, used for string representation
        self.l1_routes = []
        # placeholder, computed by second_echelon_distances, used for fitness functions
        self.l2_distance = []
        # placeholder, lists of clients served by each L2 vehicle
        # used to determine if it's necessary to recalculate second_echelon distance
        self.l2_clients = [[] for i in range(Solution.vehicle_nr)]
        # placeholder, computed by first_echelon_distances, used for fitness functions
        self.sat_demand = [False]
        self.log = [initial_log]

    def __eq__(self, other):
        """Override equality (==) method."""
        if isinstance(other, Solution):
            return self.starting_points == other.starting_points \
                and self.product_delivery == other.product_delivery
        return NotImplemented

    def __ne__(self, other):
        """Override non-equality (!=) method."""
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __str__(self):
        """Override to-string ( str() ) method.

        Only prints starting points and product delivery matrix.
        """
        strng = str()
        for veh in range(Solution.vehicle_nr):
            strng += str(self.starting_points[veh]) + '\t'
        strng += '\n'
        for product in range(Solution.product_nr):
            for client in range(Solution.client_nr):
                strng += str(self.product_delivery[client][product]) + '\t'
            if product < Solution.product_nr - 1:
                strng += '\n'
        return strng

    def __repr__(self):
        """Override to-representation ( repr() ) method.

        Includes first-echelon and second-echelon routes in addition to starting points and product delivery.
        """
        if not self.l1_routes:
            dist = self.first_echelon_distances()
        strng = str()
        strng += "< "
        for route in self.l1_routes:
            for pos,index in enumerate(route,1):
                if pos == 1:
                    strng += "depot " + str(index) + " | "
                else:
                    strng += str(index) + ' '
            strng += " ||\t"
        strng += '\n'
        for veh in range(Solution.vehicle_nr):
            strng += str(self.starting_points[veh]) + '\t'
        strng += '\n'
        for client in range(Solution.client_nr):
            for veh in range(Solution.vehicle_nr):
                strng += str(self.client_order[client][veh]) + '\t'
            strng += "| "
            for product in range(Solution.product_nr):
                strng += str(self.product_delivery[client][product]) + ' '
            if client < Solution.client_nr - 1:
                strng += '\n'
        strng += '>'
        return strng

    def __hash__(self):
        """Override hash method."""
        return hash(str(self))

    @classmethod
    def set_environment(cls, vehicles, demand, first_echelon, second_echelon):
        """Set the problem environment variables.

        Needs to be invoked before any object instantiation.
        Keyword arguments:
            vehicles -- array of data on vehicles from both echelons
            demand -- client demand matrix
            first_echelon -- matrix of distances between depots and satellites
            second_echelon -- matrix of distances between satellites and clients
        """
        cls.capacity, cls.cost_per_km, cls.emissions, cls.l1_cpk, cls.l1_emissions = vehicles
        cls.vehicle_nr = len(cls.capacity)
        cls.demand = demand
        # the number of clients is equal to number of rows in demand
        cls.client_nr = len(demand)
        cls.second_echelon = second_echelon
        # the number of satellites is equal to number of rows in the L2 distance matrix
        # minus the number of clients
        cls.satellite_nr = len(second_echelon) - cls.client_nr
        cls.first_echelon = first_echelon
        # the number of products or depots is equal to the number of rows in the L1 distance matrix
        # minus the number of satellites
        cls.product_nr = len(first_echelon) - cls.satellite_nr

    @classmethod
    def empty_solution(cls, i_log):
        """Generate empty solution object."""
        starting_points = [0] * cls.vehicle_nr
        client_order = [[0] * cls.vehicle_nr for i in range(cls.client_nr)]
        product_delivery = [[0] * cls.product_nr for i in range (cls.client_nr)]
        return Solution(starting_points,client_order,product_delivery,i_log)

    @classmethod
    def generate_order(cls):
        """Generate solution object with ordered strategy.

        Generates a random solution with a greedy strategy, seeking clients to be served
        by only one truck for all products wherever possible, and then fills out the
        remaining clients with remaining trucks.
        """
        sol = cls.empty_solution("Order")
        # make list of clients served to be filled out by another method
        clients_served = [[] for i in range(cls.vehicle_nr)]
        # assign clients to vehicles
        try:
            sol.assign_clients_to_vehicles(clients_served)
        # if not possible, retry
        except UnsatisfiedDemandError:
            return cls.generate_order()
        # order vehicle routes using TSP strategy for vehicles with more than two assigned clients
        sol.order_client_visits(clients_served)
        return sol

    def assign_clients_to_vehicles(self, clients_served):
        """Assign clients to vehicles with greedy strategy.

        Keyword arguments:
            clients_served -- list of lists, indicating clients served by each vehicle
        """
        # keep records of remaining capacity of each vehicle,
        remaining_capacity = Solution.capacity[:]
        # whether each demand (client, product combination) has been satisfied
        demand_satisfied = [[False if Solution.demand[i][j] > 0 else True
                                for j in range(Solution.product_nr)]
                                for i in range(Solution.client_nr)]
        # first attempt to satisfy all demand by a client with one vehicle visit
        all_clients_satisfied = self.satisfy_demand_1vpc(remaining_capacity, clients_served, demand_satisfied)
        # if not all clients satisfied, proceed to select individual client, product combinations
        # to be served by vehicles
        if not all_clients_satisfied:
            # attempt to satisfy demand with multiple vehicles per client
            self.satisfy_demand_mvpc(remaining_capacity, clients_served, demand_satisfied)

    def satisfy_demand_1vpc(self, remaining_capacity, clients_served, demand_satisfied):
        """Attempt to satisfy demand with one vehicle per client.

        Keyword arguments:
            remaining_capacity -- list of remaining capacity values for each vehicle
            clients_served -- list of lists, indicating clients served by each vehicle
            demand_satisfied -- matrix indicating client-product intersections effectively served
        """
        # assume all clients satisfied with current method
        all_clients_satisfied = True
        # make list of clients
        clients = range(Solution.client_nr)
        # if there's a client remaining
        while clients:
            # random client chosen and demand computed
            client = choice(clients)
            client_demand = sum(Solution.demand[client])
            # determine available vehicles according to remaining capacity
            # due to time constraints on the TSP resolution, limit maximum
            # number of clients per vehicle to 12
            available = [veh for veh in range(Solution.vehicle_nr)
                         if remaining_capacity[veh] >= client_demand
                         and len(clients_served[veh]) < 12]
            # proceed to select a vehicle if available
            if available:
                # vehicle randomly chosen
                vehicle = choice(available)
                # all demand of chosen client satisfied
                for product in range(Solution.product_nr):
                    if Solution.demand[client][product] > 0:
                        # product delivery updated
                        self.product_delivery[client][product] = vehicle + 1
                        # demand satisifed matrix updated
                        demand_satisfied[client][product] = True
                # remaining_capacity updated
                remaining_capacity[vehicle] -= client_demand
                # client added to vehicle's served clients
                clients_served[vehicle].append(client)
            # at least one client could not be satisfied
            else:
                all_clients_satisfied = False
            # chosen client removed from list of clients
            clients.remove(client)
        return all_clients_satisfied

    def satisfy_demand_mvpc(self, remaining_capacity, clients_served, demand_satisfied):
        """Attempt to satisfy demand with multiple vehicles per client.

        Keyword arguments:
            remaining_capacity -- list of remaining capacity values for each vehicle
            clients_served -- list of lists, indicating clients served by each vehicle
            demand_satisfied -- matrix indicating client-product intersections effectively served
        """
        # make list of all non-satisfied client-product combinations using nrange
        client_products = [(c, p) for c, p in nrange((Solution.client_nr, Solution.product_nr))
                           if demand_satisfied[c][p] == False]
        while client_products:
            # select random client-product combo
            client, product = choice(client_products)
            # make list of available vehicles according to capacity
            # due to time constraints on the TSP resolution, limit maximum
            # number of clients per vehicle to 12
            available = [veh for veh in range(Solution.vehicle_nr)
                         if remaining_capacity[veh] >= Solution.demand[client][product]
                         and (len(clients_served[veh]) < 12
                              or client in clients_served[veh])]
            # if none is available, demand cannot be satisfied, raise an exception
            if not available:
                raise UnsatisfiedDemandError
            # random vehicle selected
            vehicle = choice(available)
            # product delivery updated
            self.product_delivery[client][product] = vehicle + 1
            # remaining capacity updated
            remaining_capacity[vehicle] -= Solution.demand[client][product]
            # client added to vehicle's served clients
            if client not in clients_served[vehicle]:
                clients_served[vehicle].append(client)
            # client-product combo removed from list
            client_products.remove((client, product))

    @classmethod
    def generate_chaos(cls):
        """Generate solution with simple random strategy and then repair."""
        sol = cls.empty_solution("Chaos")
        # auxiliary array of clients served per vehicle
        clients_served = [[] for i in range(cls.vehicle_nr)]
        # auxiliary array to determine available vehicles
        available = []
        # randomly assign satellites, 0 meaning vehicle not used
        for veh in range(cls.vehicle_nr):
            # no more than a 25% chance of not being used
            prob = randint(0, max(4, cls.vehicle_nr))
            if prob > 0:
                sol.starting_points[veh] = randint(1, cls.satellite_nr)
                available.append(veh)
            else:
                sol.starting_points[veh] = 0
        # if, due to probability, available ends up empty, fill
        if not available:
            available = range(cls.vehicle_nr)
        # randomly assign clients and products served
        for client in range(cls.client_nr):
            for product in range(cls.product_nr):
                if cls.demand[client][product] > 0:
                    # if list of available vehicles is empty
                    # and there are vehicles without starting points but also some with
                    # meaning available was not already reset, add a random remaining vehicle
                    if not available and 0 in sol.starting_points and sum(sol.starting_points) > 0:
                        remaining_vehicles = [ve for ve in range(cls.vehicle_nr)
                                              if sol.starting_points[ve] == 0]
                        next_vehicle = choice(remaining_vehicles)
                        sol.starting_points[next_vehicle] = randint(1, cls.satellite_nr)
                        available.append(next_vehicle)
                    # otherwise all eligible vehicles have been used up, attempt new generation
                    elif not available:
                        return cls.generate_chaos()
                    # select random vehicle and update product delivery
                    veh = choice(available)
                    sol.product_delivery[client][product] = veh + 1
                    # add client to clients served by vehicle if not already included
                    if client not in clients_served[veh]:
                        clients_served[veh].append(client)
                    # prevent vehicles from serving more than 12 clients
                    if len(clients_served[veh]) == 12:
                        available.remove(veh)
        # correct vehicle capacity overflow, client order will be determined here
        sol.correct()
        return sol

    def correct(self):
        """Repair solution object."""
        # auxiliary array of clients served per vehicle
        clients_served = [[cl for cl in range(Solution.client_nr) if ve + 1 in self.product_delivery[cl]]
                           for ve in range(Solution.vehicle_nr)]
        # make certain that no L2 vehicles have more than 12 clients
        self.limit_clients(clients_served)
        # determine remaining vehicle capacities
        remaining_capacity = self.determine_overflow()
        # correct vehicle capacity overflow
        self.correct_overflow(remaining_capacity, clients_served)
        # correct client vehicle order
        self.order_client_visits(clients_served)

    def limit_clients(self, clients_served, max_nr=12):
        """Verify all second-echelon vehicles have no more than the client limit, correct if necessary.

        Keyword arguments:
            clients_served -- list of lists, indicating clients served by each vehicle
            max_nr -- maximum number of clients to be served by each vehicle
        """
        # make list of vehicles with more than 12 clients
        too_many_clients = [ve for ve in range(Solution.vehicle_nr) if len(clients_served[ve]) > max_nr]
        # iterate over list of vehicles with too many clients
        for veh in too_many_clients:
            # as long as vehicle has too many clients
            while len(clients_served[veh]) > max_nr:
                # randomly select from clients served
                client_to_remove = choice(clients_served[veh])
                # make list of available replacement vehicles
                available = [ve for ve in range(Solution.vehicle_nr) if ve != veh
                             and (len(clients_served[ve]) < max_nr
                                  or client_to_remove in clients_served[ve])]
                # replace all vehicle service from client
                for product in range(Solution.product_nr):
                    if self.product_delivery[client_to_remove][product] == veh + 1:
                        # select new vehicle
                        new_veh = choice(available)
                        # update delivery of product with new vehicle
                        self.product_delivery[client_to_remove][product] = new_veh + 1
                        # add client to new vehicle if not already served
                        if client_to_remove not in clients_served[new_veh]:
                            clients_served[new_veh].append(client_to_remove)
                # remove client from clients served of current vehicle
                clients_served[veh].remove(client_to_remove)

    def determine_overflow(self):
        """Return list of remaining capacity values for each vehicle.

        Capacity overflow will have occurred wherever the remaining capacity value is negative.
        """
        remaining_capacity = Solution.capacity[:]
        for client in range(Solution.client_nr):
            for product in range(Solution.product_nr):
                veh = self.product_delivery[client][product]
                if veh != 0:
                    remaining_capacity[veh-1] -= Solution.demand[client][product]
        return remaining_capacity

    def correct_overflow(self, remaining_capacity, clients_served):
        """Correct vehicle capacity overflow.

        Keyword arguments:
            remaining_capacity -- list of remaining capacity values for each vehicle
            clients_served -- list of lists, indicating clients served by each vehicle
        """
        # determine number of vehicles with capacity overflow
        overflow = 0
        for i in range(len(remaining_capacity)):
            if remaining_capacity[i] < 0:
                overflow += 1
        # auxiliary counter for while loop
        i = 0
        # overflow correction procedure
        while overflow > 0:
            rc_old = remaining_capacity[:]
            client_list = range(Solution.client_nr)
            shuffle(client_list)
            # randomly iterate through the list of clients
            for client in client_list:
                product_list = range(Solution.product_nr)
                shuffle(product_list)
                # randomly iterate through the list of products
                for product in product_list:
                    veh = self.product_delivery[client][product]
                    # if product is delivered by a vehicle and the vehicle capacity is overflowed
                    if veh != 0 and remaining_capacity[veh - 1] < 0:
                        # create list of eligible vehicles
                        vehicle_list = [ve for ve in range(Solution.vehicle_nr)
                                        if remaining_capacity[ve] >= Solution.demand[client][product]
                                        and (len(clients_served[ve]) < 12
                                             or client in clients_served[ve])]
                        shuffle(vehicle_list)
                        # randomly iterate through list of remaining vehicles
                        for k in vehicle_list:
                            # if vehicle is already being used or if it's already past
                            # the first two iterations, choose vehicle
                            if self.starting_points[k] > 0 or i >= 2:
                                # assign product delivery to chosen vehicle
                                self.product_delivery[client][product] = k + 1
                                # add client to list of clients served by chosen vehicle
                                if client not in clients_served[k]:
                                    clients_served[k].append(client)
                                # remove client from list of clients served by former vehicle if necessary
                                if veh not in self.product_delivery[client]:
                                    clients_served[veh-1].remove(client)
                                # update remaining capacity numbers
                                remaining_capacity[veh - 1] += Solution.demand[client][product]
                                remaining_capacity[k] -= Solution.demand[client][product]
                                # update number of vehicles with overflow
                                if remaining_capacity[veh - 1] >= 0:
                                    overflow -= 1
                                break
            # auxiliary to avoid standby vehicles in first two iterations
            i += 1
            # couldn't be solved, replace with random solution
            if i > 2 and remaining_capacity == rc_old:
                sol = Solution.generate_chaos()
                self.starting_points = sol.starting_points
                self.client_order = sol.client_order
                self.product_delivery = sol.product_delivery
                self.l1_distance = 0
                self.l2_clients = sol.l2_clients
                self.l2_distance = []
                self.sat_demand = [False]
                self.log.append("Regenerated")
                # update clients_served before returning
                for veh in range(Solution.vehicle_nr):
                    clients_served[veh] = []
                    for client in range(Solution.client_nr):
                        if veh + 1 in self.product_delivery[client]:
                            clients_served[veh].append(client)
                return

    def order_client_visits(self, clients_served):
        """Set routing for second-echelon vehicles.

        Sets the order of client visits.
        Keyword arguments:
            clients_served -- list of lists, indicating clients served by each vehicle
        """
        # manage client order for each vehicle
        for veh, veh_clients in enumerate(clients_served):
            # check if clients changed, or set to empty elsewhere
            # if not, pass on to next vehicle
            if (veh_clients == self.l2_clients[veh] and len(veh_clients) > 0
                    and self.starting_points[veh] > 0):
                continue
            # if so, make client order zero for this vehicle
            for client in range(Solution.client_nr):
                self.client_order[client][veh] = 0
            # check number of clients vehicle serves
            nr_clients_served = len(veh_clients)
            # no clients served
            if nr_clients_served == 0:
                # set initial satellite to zero and order to empty array
                sat, order = 0, []
            # one or two clients served
            elif nr_clients_served <= 2:
                # if no starting point selected
                if self.starting_points[veh] == 0:
                    # select satellite with minimum combined distance
                    sat = Solution.find_nearest_satellite(veh_clients)
                # if starting point selected
                else:
                    # satellite remains
                    sat = self.starting_points[veh]
                # copy clients_served into order array
                order = veh_clients[:]
                # cost for one or two clients will always be the same, sort for uniformity
                order.sort()
            # more than two clients served
            elif nr_clients_served > 2:
                # obtain minimum distance tour for vehicle
                # if satellite already selected, the same will be returned to sat
                # otherwise, the optimal satellite will be returned to sat
                sat, order = Solution.min_distance_tour(self.starting_points[veh], veh_clients)
            # selected satellite established as starting point
            self.starting_points[veh] = sat
            # client_order filled out
            for count, client in enumerate(order, 1):
                self.client_order[client][veh] = count

    @classmethod
    def find_nearest_satellite(cls, clients_served):
        """Find nearest satellite to one or two clients.

        Keyword arguments:
            clients_served -- list of one or two clients
        """
        min_dist = float('inf')
        # if only one client
        if len(clients_served) == 1:
            # compute client index
            client_index = clients_served[0] + cls.satellite_nr
            # iterate through satellites
            for sat_index in range(cls.satellite_nr):
                # obtain distance from distance matrix
                dist = cls.second_echelon[client_index][sat_index]
                # update minimum distance and satellite if necessary
                if dist < min_dist:
                    min_dist, sat = dist, sat_index + 1
        # if two clients
        else:
            # compute client indices
            client_index_1 = clients_served[0] + cls.satellite_nr
            client_index_2 = clients_served[1] + cls.satellite_nr
            # iterate through satellites
            for sat_index in range(cls.satellite_nr):
                # obtain distance from distance matrix
                dist = (cls.second_echelon[client_index_1][sat_index]
                        + cls.second_echelon[client_index_2][sat_index])
                # update minimum distance and satellite if necessary
                if dist < min_dist:
                    min_dist, sat = dist, sat_index + 1
        return sat

    @classmethod
    def min_distance_tour(cls, starting_point, clients_served):
        """Return optimal route for clients and satellite given.

        Returns best satellite if no satellite given. Otherwise returns same satellite.
        Keyword arguments:
            starting_point -- initial satellite
            clients_served -- list of clients to be visited
        """
        # compute the client indices in the second-echelon distance matrix
        client_indices = [client + cls.satellite_nr for client in clients_served]
        # if satellite already selected
        if starting_point > 0:
            # indices of points for TSP (selected satellite and served clients)
            point_indices = [starting_point - 1] + client_indices
            # compute the distance_matrix to be used as a submatrix of the second-echelon distance matrix
            # with only the relevant clients and satellite
            distance_matrix = make_submatrix(cls.second_echelon, point_indices)
            # find TSP route
            tour, cost = tsp(distance_matrix)
            # order is equal to tour with client indices without initial satellite
            order = [clients_served[i - 1] for i in tour if i > 0]
            # the same satellite will be returned
            sat = starting_point
        # if no satellite yet selected
        else:
            min_cost = float('inf')
            # iterate through satellites
            for sat_index in range(cls.satellite_nr):
                # indices of points for TSP (selected satellite and served clients)
                point_indices = [sat_index] + client_indices
                # compute the distance_matrix to be used as a submatrix of the second-echelon distance matrix
                # with only the relevant clients and satellite
                distance_matrix = make_submatrix(cls.second_echelon, point_indices)
                # find TSP route
                tour, cost = tsp(distance_matrix)
                # update minimal tour found if necessary
                if cost < min_cost:
                    min_cost, min_tour, sat = cost, tour, sat_index + 1
            # order is equal to min_tour with client indices without initial satellite
            order = [clients_served[i - 1] for i in min_tour if i > 0]
        return sat, order

    @classmethod
    def crossover(cls, parent_1, parent_2):
        """Return a pair of child solutions from parent crossover.

        Method based on swapping random client data.
        """
        child_1 = dcpy(parent_1)
        child_2 = dcpy(parent_2)
        for client in range(Solution.client_nr):
            # product delivery data swapped with 50% probability
            # client order will be corrected later
            if randint(1, 2) == 2:
                child_1.product_delivery[client] = parent_2.product_delivery[client][:]
                child_2.product_delivery[client] = parent_1.product_delivery[client][:]
        return child_1, child_2

    @classmethod
    def cx_wrapper(cls, parent_1, parent_2):
        """Perform crossover and repair solutions."""
        child_1, child_2 = cls.crossover(parent_1, parent_2)
        # product delivery updated, starting points remain the same, client order corrected later
        parent_1.product_delivery = child_1.product_delivery
        parent_2.product_delivery = child_2.product_delivery
        # correct
        parent_1.correct()
        parent_2.correct()
        # update log
        parent_1.log.append("Crossover")
        parent_2.log.append("Crossover")

    def mut_switch_trucks(self):  # mutation method 1: truck swap
        """Mutate solution by swapping all data between two trucks."""
        veh_choices = range(Solution.vehicle_nr)
        a = choice(veh_choices)
        veh_choices.remove(a)
        b = choice(veh_choices)
        # swap the satellites
        self.starting_points[a], self.starting_points[b] = self.starting_points[b], self.starting_points[a]
        # swap the clients product delivery, client order corrected later
        for client in range(Solution.client_nr):
            # swap the delivery of products
            for product in range(Solution.product_nr):
                if self.product_delivery[client][product] == a + 1:
                    self.product_delivery[client][product] = b + 1
                elif self.product_delivery[client][product] == b + 1:
                    self.product_delivery[client][product] = a + 1
        # reset L2 clients to ensure recalculation of client order and distance
        self.l2_clients[a] = []
        self.l2_clients[b] = []
        # update log
        self.log.append("Switch trucks")

    def mut_switch_satellites(self):  # mutation method 2: satellite swap
        """Mutate solution by swapping satellite origin between any two trucks or randomizing if same origin."""
        veh_choices = [i for i in range(Solution.vehicle_nr) if self.starting_points[i] > 0]
        a = choice(veh_choices)
        veh_choices.remove(a)
        b = choice(veh_choices)
        # if the satellites are the same
        if self.starting_points[a] == self.starting_points[b]:
            # select new random satellites for both
            self.starting_points[a] = randint(1, Solution.satellite_nr)
            self.starting_points[b] = randint(1, Solution.satellite_nr)
        # else, swap
        else:
            self.starting_points[a], self.starting_points[b] = self.starting_points[b], self.starting_points[a]
        # reset L2 clients to ensure recalculation of client order and distance
        self.l2_clients[a] = []
        self.l2_clients[b] = []
        # update log
        self.log.append("Switch satellites")

    def mut_switch_products(self):  # mutation method 3: delivery switch
        """Mutate solution by having another truck serve a certain product for a certain client."""
        # two-dimensional range (nrange)
        cp_choices = [(c,p) for c,p in nrange((Solution.client_nr, Solution.product_nr))
                      if Solution.demand[c][p] > 0]
        # select a client-product combo
        client, product = choice(cp_choices)
        # make list of other vehicles
        veh_choices = [ve+1 for ve in range(Solution.vehicle_nr)
                       if ve+1 != self.product_delivery[client][product]]
        # select vehicle and update product delivery
        veh = choice(veh_choices)
        self.product_delivery[client][product] = veh
        # update
        self.log.append("Switch products")

    def mut_swap_clients(self):  # mutation method 4: client swap
        """Mutate solution by swapping two clients between two trucks."""
        # select a random vehicle 'a'
        a = randint(1, Solution.vehicle_nr)
        # a list of clients vehicle 'a' serves
        client_choices = [cl for cl in range(Solution.client_nr)
                          if a in self.product_delivery[cl]]
        # verify if vehicle 'a' serves any clients; if not, choose again
        while len(client_choices) == 0:
            a = randint(1, Solution.vehicle_nr)
            # the clients vehicle 'a' serves
            client_choices = [cl for cl in range(Solution.client_nr)
                              if a in self.product_delivery[cl]]
        # choose 'b' from remaining vehicles
        remaining_choices = range(1, Solution.vehicle_nr + 1)
        remaining_choices.remove(a)
        b = choice(remaining_choices)
        # client in first vehicle chosen must be served
        client_1 = choice(client_choices)
        # client for second vehicle chosen can be any, even empty
        client_2 = randint(0, Solution.client_nr - 1)
        # swap vehicles 'a' and 'b' in chosen clients
        for product in range(Solution.product_nr):
            if self.product_delivery[client_1][product] == a:
                self.product_delivery[client_1][product] = b
            if self.product_delivery[client_2][product] == b:
                self.product_delivery[client_2][product] = a
        # update log
        self.log.append("Swap clients")

    def mut_centralize_client(self):  # mutation method 5: consolidate service
        """Mutate solution by having one truck serve all products for a certain client."""
        client = randint(0, Solution.client_nr - 1)
        veh = randint(1, Solution.vehicle_nr)
        for product in range(Solution.product_nr):
            if Solution.demand[client][product] > 0:
                self.product_delivery[client][product] = veh
        # update log
        self.log.append("Centralize client")

    def mutation_wrapper(self, mut_nr):
        """Perform indicated mutation method.

        Keyword arguments:
            mut_nr -- numerical identifier of mutation method
        """
        if mut_nr == 1:
            self.mut_switch_trucks()
        elif mut_nr == 2:
            self.mut_switch_satellites()
        elif mut_nr == 3:
            self.mut_switch_products()
        elif mut_nr == 4:
            self.mut_swap_clients()
        elif mut_nr == 5:
            self.mut_centralize_client()
        else:
            raise ValueError("argument needs to be between 1 and 5")

    def mut_with_correction(self, mut_nr):
        """Perform indicated mutation method and repair resulting solution.

        Keyword arguments:
            mut_nr -- numerical identifier of mutation method
        """
        self.mutation_wrapper(mut_nr)
        self.correct()

    def mutation(self):
        """Perform mutation on solution by applying all or several mutation methods in random order."""
        # randomly order possible mutations (1 to 5)
        muts = range(1, 6)
        shuffle(muts)
        # save original self
        original = dcpy(self)
        # apply first mutation
        self.mutation_wrapper(muts[0])
        # if no mutation returned, iterate until mutation returned
        i = 1
        while self == original:
            self.mutation_wrapper(muts[i])
            i += 1
        # apply remaining mutations with 50% probability
        for j in range(i, 5):
            k = randint(1, 2)
            if k == 1:
                self.mutation_wrapper(muts[j])
        # correct after sequential mutations
        self.correct()

    def first_echelon_distances(self):
        """Compute routing and return list of combined distance covered by first-echelon vehicles."""
        # determine satellite demand
        curr_sat_demand = self.satellite_demand()
        # if satellite demand hasn't changed, first-echelon distances also haven't
        if self.sat_demand == curr_sat_demand:
            return self.l1_distance
        dist = 0
        # create list of indices for every depot/product
        indices = Solution.compute_first_echelon_indices(curr_sat_demand)
        # solve TSP for each depot/product
        routes = []
        for i in range(Solution.product_nr):
            # if two satellites, no TSP required
            if len(indices[i]) == 2:
                tour = [0, 1]
                # obtain distance from first-echelon distance matrix
                tspdist = Solution.first_echelon[indices[i][0]][indices[i][1]] * 2
            # if three satellites, no TSP required
            elif len(indices[i]) == 3:
                tour = [0, 1, 2]
                # obtain distances from first-echelon distance matrices
                tspdist = (Solution.first_echelon[indices[i][0]][indices[i][1]]
                            + Solution.first_echelon[indices[i][1]][indices[i][2]]
                            + Solution.first_echelon[indices[i][2]][indices[i][0]])
            # if more than three satellites, TSP required
            elif len(indices[i]) > 3:
                # compute the distance_matrix to be used as a submatrix of the first-echelon distance matrix
                # with only the relevant satellites and depot
                distance_matrix = make_submatrix(Solution.first_echelon, indices[i])
                tour, tspdist = tsp(distance_matrix)
            # no satellites to serve
            else:
                routes.append([i])
                continue
            route = [indices[i][k] - Solution.product_nr + 1 for k in tour]
            route[0] = i
            routes.append(route)
            # add up distances
            dist += tspdist
        # replace self.sat_demand
        self.sat_demand = curr_sat_demand
        # save routes
        self.l1_routes = routes
        # save new distance
        self.l1_distance = dist
        return dist

    def satellite_demand(self):
        """Return boolean matrix indicating products required by each satellite."""
        # boolean matrix of satellites x products
        # as only a TSP is solved on L1, it's only necessary to know *if* a provider needs to serve
        # a satellite, not *how much*.
        sat_demand = [[False for i in range(Solution.product_nr)] for j in range(Solution.satellite_nr)]
        for client in range(Solution.client_nr):
            for product in range(Solution.product_nr):
                veh = self.product_delivery[client][product] - 1
                if veh >= 0:
                    sat = self.starting_points[veh] - 1
                    sat_demand[sat][product] = True
        return sat_demand

    @classmethod
    def compute_first_echelon_indices(cls, sat_demand):
        """Return list of depot and satellite indices required for first-echelon distance computation."""
        # list of lists, one list for each depot/product
        indices = [[i] for i in range(cls.product_nr)]
        # if a satellite serves demand for a certain product, add to list of corresponding depot
        for product in range(cls.product_nr):
            for sat in range(cls.satellite_nr):
                if sat_demand[sat][product]:
                    indices[product].append(cls.product_nr + sat)
        return indices

    def second_echelon_distances(self):
        """Return list of distances covered by each second-echelon vehicle."""
        # distance variable for every vehicle
        dist = [0] * Solution.vehicle_nr
        # compute clients served per vehicle to check against saved record
        clients_served = [[cl for cl in range(Solution.client_nr) if ve + 1 in self.product_delivery[cl]]
                          for ve in range(Solution.vehicle_nr)]
        # compute distances for each vehicle
        for veh in range(Solution.vehicle_nr):
            # check if any changes to clients or set to empty elsewhere
            # if not, add saved distance and continue to next vehicle
            if (clients_served[veh] == self.l2_clients[veh] and len(clients_served[veh]) > 0
                    and self.starting_points > 0):
                dist[veh] = self.l2_distance[veh]
                continue
            # verify vehicle is used
            if self.starting_points[veh] > 0:
                # create list of served clients and their order for every vehicle
                serve_order = []
                for client in clients_served[veh]:
                    order = self.client_order[client][veh]
                    serve_order.append((client, order))
                # sort the clients served
                serve_order.sort(key=itemgetter(1))
                # satellite to first client computed separately
                origin_index = self.starting_points[veh] - 1
                first_client_index = serve_order[0][0] + Solution.satellite_nr
                # obtain distance from second-echelon distance matrix
                dist[veh] += Solution.second_echelon[origin_index][first_client_index]
                # movement between clients computed
                for client in range(len(serve_order) - 1):
                    # compute indices for pair of clients
                    a = serve_order[client][0] + Solution.satellite_nr
                    b = serve_order[client + 1][0] + Solution.satellite_nr
                    # obtain distance from second-echelon distance matrix
                    dist[veh] += Solution.second_echelon[a][b]
                # last client back to satellite computed separately
                last_client_index = serve_order[-1][0] + Solution.satellite_nr
                # obtain distance from second-echelon distance matrix
                dist[veh] += Solution.second_echelon[last_client_index][origin_index]
        # save new distances
        self.l2_distance = dist
        # reset L2 clients
        self.l2_clients = clients_served
        return dist

    def first_echelon_cost(self):  # fitness method for objective function 1
        """Return first-echelon transportation cost."""
        # obtain distances
        dist = self.first_echelon_distances()
        # calculate cost
        cost = dist * Solution.l1_cpk
        return cost

    def second_echelon_cost(self):  # fitness method for objective function 2
        """Return second-echelon transportation cost."""
        cost = 0
        # obtain distances
        vehicle_distances = self.second_echelon_distances()
        # calculate and add up costs for each vehicle
        for veh in range(Solution.vehicle_nr):
            cost += vehicle_distances[veh] * Solution.cost_per_km[veh]
        return cost

    def nr_vehicles_used(self):  # fitness method for objective function 3
        """Return total number of vehicles used."""
        # number of L1 vehicles is used is equal to number of providers,
        # as each provider only has one vehicle in this model.
        nr = Solution.product_nr
        # add L2 vehicles
        for veh in range(Solution.vehicle_nr):
            if self.starting_points[veh] > 0:
                nr += 1
        return nr

    def total_emissions(self):  # fitness method for objective function 4
        """Return total emissions produced."""
        # begin with L1 emissions
        emis = self.first_echelon_distances() * Solution.l1_emissions
        # obtain L2 distances
        vehicle_distances = self.second_echelon_distances()
        # calculate and add up L2 emissions
        for veh in range(Solution.vehicle_nr):
            emis += vehicle_distances[veh] * Solution.emissions[veh]
        return emis


# used by satfisy_demand_mvpc
class UnsatisfiedDemandError(Exception):
    pass