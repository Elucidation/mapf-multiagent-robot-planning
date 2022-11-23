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
        # return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1]) # manhatten distance
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


if __name__ == '__main__':
    import numpy as np
    maingrid = np.array([
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 1],
        [1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]])

    print(astar(maingrid, (1, 1), (5, 8)))
