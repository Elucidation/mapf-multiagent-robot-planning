import numpy as np
import heapq


def astar(graph, a, b, flip_row_col=False):
    # graph is NxN int array, obstacles are non-zero
    # a and b are tuple positions (r,c) in graph
    if flip_row_col:
        a = (a[1], a[0])
        b = (b[1], b[0])

    if graph[a[0], a[1]] > 0 or graph[b[0], b[1]] > 0:
        return False

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


def st_astar(graph, a, b, dynamic_obstacles=dict(), T=20, flip_row_col=False):
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
        (r,c,t) = n
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
    while(pq or i < 10000):
        # print(pq)
        h, parent, curr = heapq.heappop(pq)
        # print(h, parent, curr)
        if (curr[:2] == b):
            # print('Found it!')
            break

        r, c, t = curr

        # next cell one time step forward
        neighbors = [(r-1, c, t+1),
                     (r+1, c, t+1),
                     (r, c-1, t+1),
                     (r, c+1, t+1)]
        for neighbor in neighbors:
            if neighbor not in closeSet and check_valid(neighbor):
                heapq.heappush(pq, (heuristic(neighbor[:2], b), curr, neighbor))
                closeSet.add(neighbor)
                pathTrack[neighbor] = curr
        i += 1

    def get_path(c):
        path = []
        while c:
            if flip_row_col:
                path.append((c[1], c[0]))
            else:
                path.append(c[:2]) # remove time from path
                # path.append(c)
            c = pathTrack[c]

        return list(reversed(path))

    # If path was found
    if curr[:2] == b:
        return get_path(curr)
    # No path found
    return []


def find_collisions(path1, path2):
    # Find any vertex and edge collisions, and return a list of (r,c,t) collisions
    # for edge collisions, obstacles are for path2 to avoid
    tmax = min(len(path1), len(path2))
    collisions = []
    for t in range(tmax):
        # vertex collision
        if path1[t] == path2[t]:
            collisions.append([path1[t][0], path1[t][1], t])

        # edge collision, robots swap locations, just add all times
        if (t-1 >= 0):
            if path1[t-1] == path2[t] and path1[t] == path2[t-1]:
                # obstacle for path 2
                collisions.append([path2[t][0], path2[t][1], t])

                # todo: add dynamic obstacles with path reference
                # collisions.append([path1[t-1][0], path1[t-1][1], t])
                # collisions.append([path1[t][0], path1[t][1], t])


    return collisions


def test_collisions():

    p1 = [(0,0), (0,1), (0,1), (0,2)]
    p2 = [(1,0), (1,1), (0,1), (0,0)]
    # These collide at vertex at time 2
    collisions = find_collisions(p1,p2)
    print(collisions)


    p1 = [(1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (5, 2), (6, 2), (7, 2), (8, 2), (8, 3), (8, 4), (8, 5)]
    p2 = [(1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (5, 3), (5, 4)]
    p3 = [(9, 4), (8, 4), (8, 3), (8, 2), (7, 2), (6, 2), (5, 2), (4, 2), (3, 2), (2, 2), (2, 3)]

    # p1 and p2 don't intersect
    # p1 and p3 cross
    collisions = find_collisions(p1,p3)
    print(collisions)



if __name__ == '__main__':
    # test_collisions()


    maingrid = np.array([
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 1],
        [1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]])

    print(astar(maingrid, (1, 1), (5, 8)))
    print('----')
    # Confirm st_astar same path as astar with no dynamic obstacles
    print(st_astar(maingrid, (1, 1), (5, 8)))
    # Avoid dynamic obstacl at 1,6 at time step 5
    print(st_astar(maingrid, (1, 1), (5, 8), dynamic_obstacles=dict({(1,6,5):True})))

    
