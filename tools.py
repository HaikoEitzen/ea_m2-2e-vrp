from random import randint, choice
from math import sqrt


def generate_points(num=10, lwr_limit=0, uppr_limit=100):
    """Generate list of random cartesian points within limits.

    Keyword arguments:
        num -- number of points to be generated
        lwr_limit -- lower limit
        uppr_limit -- upper limit
    """
    return [(randint(lwr_limit,uppr_limit), randint(lwr_limit,uppr_limit)) for i in range(num)]


def compute_distance(a,b):
    """Return distance between two cartesian points.

    Keyword arguments:
        a -- first point
        b -- second point
    """
    return sqrt(distance_sqrd(a,b))


def distance_sqrd(a,b):
    """Return distance squared between two cartesian points.

    Applies the distance formula without the square root.
    Keyword arguments:
        a -- first point
        b -- second point
    """
    return pow(a[0]-b[0],2)+pow(a[1]-b[1],2)


def compute_distance_matrix(points):
    """Return distance matrix for given list of cartesian points.

    Keyword arguments:
        points -- list of cartesian points
    """
    distance_matrix = [[0 for a in points] for b in points]
    for i in range(len(points)-1):
        distance_matrix[i][i] = float('inf')
        for j in range(i+1, len(points)):
            dist = compute_distance(points[i], points[j])
            distance_matrix[i][j] = dist
            distance_matrix[j][i] = dist
    distance_matrix[len(points)-1][len(points)-1] = float('inf')
    return distance_matrix


def isclose(a, b, rel_tol=1e-09, abs_tol=0.0):
    """Return True if two float values are reasonably close, or sufficiently equal, otherwise False.

    Keyword arguments:
        a -- first float value
        b -- second float value
        rel_tol -- relative tolerance (default 1e-09)
        abs_tol -- minimum absolute tolerance (default 0.0)
    """
    return abs(a-b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)


def make_submatrix(matrix, indices):
    """Return indicated submatrix.

    Keyword arguments:
        matrix -- starting matrix
        indices -- indices of submatrix within matrix to be returned
    """
    return [[matrix[row][column] for column in indices] for row in indices]


def generate_demand(nr_depots, nr_clients, prod_max, min_dmd, max_dmd, intrval):
    """Generate random demand matrix.

    Keyword arguments:
        nr_depots -- number of depots (products)
        nr_clients -- number of clients
        prod_max -- maximum combined demand for a single product
        min_dmd -- minimum demand if demand non-zero
        max_dmd -- maximum demand by a client for a product
        intrval -- step between demand values
    """
    demand = [[0] * nr_depots for i in range(nr_clients)]
    for product in range(nr_depots):
        capacity = prod_max
        while capacity > 0:
            client = choice(range(nr_clients))
            if demand[client][product] == 0 and capacity >= min_dmd:
                demand[client][product] = min_dmd
                capacity -= min_dmd
            elif demand[client][product] < max_dmd:
                if capacity >= intrval:
                    demand[client][product] += intrval
                    capacity -= intrval
                else:
                    demand[client][product] += capacity
                    capacity = 0
    for row in demand:
        line = str()
        for elem in row:
            line += str(elem) + "\t\t"
        print line