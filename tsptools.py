from tools import compute_distance_matrix


def tsp(distance_matrix):
    """Solve symmetrical TSP instance.

    Keyword arguments:
        distance_matrix -- matrix of distances between points
    """
    # obtain number of points
    n = len(distance_matrix)
    # establish simple order and infinite cost as upper bound
    uppr_bnd_tour = [i for i in range(n)]
    uppr_bnd_cost = float('inf')
    # determine lower bound by minimum edge
    min_edge, lwr_bnd_cost = compute_lower_bound(distance_matrix,n)
    # recursively search
    best_tour, best_cost = tsp_search(distance_matrix, n, [0], 0,
                                      min_edge, lwr_bnd_cost,
                                      uppr_bnd_tour, uppr_bnd_cost)
    return best_tour, best_cost


def tsp_with_points(points):
    """Solve symmetrical TSP instance given list of points.

    Keyword arguments:
        points -- list of cartesian points
    """
    distance = compute_distance_matrix(points)
    return tsp(distance)


def tsp_search(distance, n, tour, curr_cost, min_edge, curr_bnd, best_tour, best_cost):
    """Return optimal tour and cost for TSP instance using branch-and-bound algorithm.

    Keyword arguments:
        distance -- distance matrix
        n -- total number of vertices
        tour -- current tour
        curr_cost -- current cost
        min_edge -- list of minimum edges for each vertex
        curr_bnd -- current bound
        best_tour -- current best tour
        best_cost -- current best cost
    """
    lcl_best_tour = best_tour[:]
    lcl_best_cost = best_cost
    # if tour isn't finished yet
    if len(tour) < n:
        last_vertex = tour[-1]
        # create list of remaining vertices
        vertices = [i for i in range(n) if i not in tour]
        # order according to minimum distance to last vertex
        vertices.sort(key=lambda vertex: distance[last_vertex][vertex])
        for v in vertices:
            # potential cost = current cost + current edge + current bound
            # current bound is updated locally at every step
            lcl_curr_bnd = curr_bnd
            if len(tour) == 1:
                lcl_curr_bnd -= (min_edge[last_vertex][1] + min_edge[v][1])/2
            else:
                lcl_curr_bnd -= (min_edge[last_vertex][0] + min_edge[v][1])/2
            # if potential cost of next vertex is less than upper bound, try
            if curr_cost + distance[last_vertex][v] + lcl_curr_bnd < lcl_best_cost:
                v_tour, v_cost = tsp_search(distance, n, tour + [v],
                                            curr_cost + distance[last_vertex][v],
                                            min_edge, lcl_curr_bnd,
                                            lcl_best_tour, lcl_best_cost)
                if v_cost < lcl_best_cost:
                    lcl_best_cost = v_cost
                    lcl_best_tour = v_tour
            # if potential cost is greater, no need to continue as vertices are
            # sorted according to distance to current vertex
            else:
                break
    # if tour is finished and there are more than 1 points
    # return current tour and the cost, including the return to first vertex
    elif n > 1:
        return tour, curr_cost + distance[tour[-1]][tour[0]]
    return lcl_best_tour, lcl_best_cost


def compute_lower_bound(distance, n):
    """Return list of minimum edges for vertices and initial lower bound cost.

    Computes initial lower bound based on minimum edge.
    Keyword arguments:
        distance -- distance matrix
        n -- total number of vertices
    """
    # determine minimum edge costs for each point
    min_edge = []
    min_cost = 0
    for v in range(n):
        # create a list of possible edges
        edges = [distance[v][i] for i in range(n) if i != v]
        # sort according to minimum distance
        edges.sort()
        # add the two smallest edges to minimum edge list
        min_edge.append((edges[0], edges[1]))
        min_cost += edges[0] + edges[1]
    min_cost /= 2
    return min_edge, min_cost