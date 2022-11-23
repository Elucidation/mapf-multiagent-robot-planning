import numpy as np
import heapq
from collections import defaultdict
from multiagent_utils import get_scenario, flip_tuple_lists


def astar(graph, a, b, flip_row_col=False):
    # graph is NxN int array, obstacles are non-zero
    # a and b are tuple positions (r,c) in graph
    if flip_row_col:
        a = (a[1], a[0])
        b = (b[1], b[0])

    if graph[a[0], a[1]] > 0 or graph[b[0], b[1]] > 0:
        raise Exception('Start/End locations in walls')

    def heuristic(p1, p2):
        # return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1]) # manhattan distance
        return (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2  # squared distance

    def check_valid(n):
        R, C = graph.shape
        if n[0] < 0 or n[0] >= R:
            return False
        elif n[1] < 0 or n[1] >= C:
            return False
        elif graph[n[0], n[1]] > 0:
            return False
        return True

    closeSet = set()
    pathTrack = dict()  # coord -> parent
    pathTrack[a] = None
    closeSet.add(a)

    path = []

    # priority queue via heapq
    # heuristc_score, parent, pos
    pq = [(heuristic(a, b), None, a)]

    i = 0
    while(pq or i < 100):
        h, parent, curr = heapq.heappop(pq)
        # print(h, parent, curr)
        if (curr == b):
            # print('Found it!')
            break

        r, c = curr

        neighbors = [(r-1, c), (r+1, c), (r, c-1), (r, c+1)]
        for neighbor in neighbors:
            if neighbor not in closeSet and check_valid(neighbor):
                heapq.heappush(pq, (heuristic(neighbor, b), curr, neighbor))
                closeSet.add(neighbor)
                pathTrack[neighbor] = curr
        i += 1

    def get_path(c):
        path = []
        while c:
            if flip_row_col:
                path.append((c[1], c[0]))
            else:
                path.append(c)
            c = pathTrack[c]

        return list(reversed(path))

    # If path was found
    if curr == b:
        return get_path(curr)
    # No path found
    return []


def st_astar(graph, a, b, dynamic_obstacles=dict(), T=20, flip_row_col=False, maxiters=10000):
    # space-time astar
    # graph is NxN int array, obstacles are non-zero
    # dynamic_obstacles is a dict of (r,c,t) obstacles to avoid
    # each tile is position
    # convert to NxNxT loaf (where T = time) with cells as position at a time
    # a and b are tuple positions (r,c) in graph
    if flip_row_col:
        a = (a[1], a[0])
        b = (b[1], b[0])

    if graph[a[0], a[1]] > 0 or graph[b[0], b[1]] > 0:
        raise Exception('Start/End locations in walls')

    def heuristic(p1, p2):
        return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])  # manhattan distance
        # return (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2  # squared distance
        # todo, use true-distance heuristic via backwards search

    def check_valid(n):
        (r, c, t) = n
        R, C = graph.shape
        if(t > T):
            return False
        elif r < 0 or r >= R:
            return False
        elif c < 0 or c >= C:
            return False
        elif graph[r, c] > 0:
            return False
        elif n in dynamic_obstacles:
            return False
        return True

    closeSet = set()
    pathTrack = dict()  # coord -> parent
    curr = (a[0], a[1], 0)
    pathTrack[curr] = None
    closeSet.add(curr)

    # priority queue via heapq
    # heuristc_score, parent, pos, time
    pq = [(heuristic(a, b), None, (a[0], a[1], 0))]

    i = 0
    while(pq or i < maxiters):
        # print(pq)
        h, parent, curr = heapq.heappop(pq)
        closeSet.add(curr)
        # print(h, parent, curr)
        if (curr == (b[0], b[1], T)):
            # print('Found it!')
            break

        r, c, t = curr

        # next cell one time step forward
        neighbors = [(r, c, t+1),
                     (r-1, c, t+1),
                     (r+1, c, t+1),
                     (r, c-1, t+1),
                     (r, c+1, t+1)]
        for neighbor in neighbors:
            if neighbor not in closeSet and check_valid(neighbor):
                heapq.heappush(
                    pq, (heuristic(neighbor[:2], b), curr, neighbor))
                # closeSet.add(neighbor)
                pathTrack[neighbor] = curr
        i += 1

    def get_path(c):
        path = []
        while c:
            if flip_row_col:
                path.append((c[1], c[0]))
            else:
                path.append(c[:2])  # remove time from path
                # path.append(c)
            c = pathTrack[c]

        return list(reversed(path))

    # If path was found
    if curr[:2] == b:
        return get_path(curr)
    # No path found
    return []


def find_all_collisions(paths):
    collisions = []
    for i in range(len(paths)):
        for j in range(i+1, len(paths)):
            collisions.extend(find_collisions(paths[i], paths[j], i, j))
    return collisions


def find_collisions(path1, path2, path1_name=0, path2_name=1):
    # Find any vertex and edge collisions, and return a list of (path_idx,r,c,t) collisions
    # for edge collisions, obstacles are for path2 to avoid

    # extend shorter path with waits
    # tmax = min(len(path1), len(path2))
    if not path1 or not path2:
        return []
    diff = len(path2) - len(path1)
    if diff > 0:
        # if path 2 longer
        path1.extend(diff*[path1[-1]])
    elif diff < 0:
        path2.extend((-diff)*[path2[-1]])

    tmax = len(path1)
    collisions = []  # (path_name,r,c,t)
    for t in range(tmax):
        # vertex collision
        if path1[t] == path2[t]:
            collisions.append([path2_name, path1[t][0], path1[t][1], t])

        # edge collision, robots swap locations, just add all times
        if (t-1 >= 0):
            if path1[t-1] == path2[t] and path1[t] == path2[t-1]:
                # obstacle for path 2
                collisions.append([path2_name, path2[t][0], path2[t][1], t])

                # todo: add dynamic obstacles with path reference
                # collisions.append([path1[t-1][0], path1[t-1][1], t])
                # collisions.append([path1[t][0], path1[t][1], t])

    return collisions


def MAPF0(grid, starts, goals):
    # For several robots with given start/goal locations and a grid
    # Get paths for all, do all as independent
    #  - independent A-star for each as initial paths
    assert len(starts) == len(goals)
    paths = []
    N = len(starts)
    for i in range(N):
        paths.append(astar(grid, starts[i], goals[i]))
    return paths


def MAPF1(grid, starts, goals, maxiter=5, T=20):
    # For several robots with given start/goal locations and a grid
    # Attempt to find paths for all that don't collide
    # Attempt 1:
    #  - independent A-star for each as initial paths
    #  - check for collisions as dynamic obstacles
    #  - st_astar for paths (priority ordering) that collide until no collisions
    assert len(starts) == len(goals)

    paths = []
    N = len(starts)

    for i in range(N):
        paths.append(astar(grid, starts[i], goals[i]))

    collisions = find_all_collisions(paths)
    # dict of collisions per path
    path_collisions = defaultdict(list)
    for collision in collisions:
        path_idx, r, c, t = collision
        path_collisions[path_idx].append((r, c, t))

    if not collisions:
        return paths

    # list of (path_idx, r, c, t)
    for i in range(maxiter):
        # print(f'{i} | Trying to remove collisions: {collisions}')
        path_idx, r, c, t = collisions[0]

        # Add all collisions associated with this path
        # dynamic_obstacles = {(r,c,t) : True}
        dynamic_obstacles = path_collisions[path_idx]
        # print('Before:')
        # print(paths[path_idx])
        paths[path_idx] = st_astar(
            grid, starts[path_idx], goals[path_idx], dynamic_obstacles, T=T)
        # print('After:')
        # print(paths[path_idx])
        collisions = find_all_collisions(paths)
        if not collisions:
            break

        # Note: Keeps old dynamic obstacles, not optimal
        for collision in collisions:
            path_idx, r, c, t = collision
            path_collisions[path_idx].append((r, c, t))

    return paths


def test_find_collisions():
    p1 = [(0, 0), (0, 1), (0, 1), (0, 2)]
    p2 = [(1, 0), (1, 1), (0, 1), (0, 0)]
    # These collide at vertex at time 2
    collisions = find_collisions(p1, p2)
    assert(collisions == [[1, 0, 1, 2]])


def test_MAPF0():
    grid, goals, starts = get_scenario('scenarios/scenario2.yaml')
    paths = MAPF0(grid, starts, goals)
    collisions = find_all_collisions(paths)
    assert(collisions == [[2, 2, 5, 6]])
    # print(paths)
    # print(collisions)


def test_MAPF1():
    grid, goals, starts = get_scenario('scenarios/scenario3.yaml')
    paths = MAPF1(grid, starts, goals, maxiter=100)
    collisions = find_all_collisions(paths)
    assert(not collisions)
    # print('---')
    # print(f'Paths: {paths}')
    # print('--')
    # print(f'Collisions: {collisions}')
    # print('--')


def test_single_robot_astar():
    grid, goals, starts = get_scenario('scenarios/scenario1.yaml')
    path = astar(grid, starts[0], goals[0])
    expected_path = [(1, 4), (1, 3), (1, 2), (1, 1), (2, 1),
                     (3, 1), (4, 1), (4, 2), (4, 3), (3, 3), (3, 4)]
    assert(path == expected_path)


if __name__ == '__main__':
    # Run tests
    test_find_collisions()
    test_single_robot_astar()
    test_MAPF0()
    test_MAPF1()
