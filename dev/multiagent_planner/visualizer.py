"""Visualizer class for showing animated multiagent plans."""
import math
import numpy as np
import matplotlib.pyplot as plt  # type: ignore
from matplotlib import animation  # type: ignore
from matplotlib.patches import Circle, Rectangle  # type: ignore


class Visualizer():
    """System for visualizing and animating env + robot paths."""
    Colors = ['red', 'cyan', 'green', 'orange', 'yellow', 'blue', 'gray']

    # pylint: disable=redefined-outer-name,too-many-locals
    def __init__(self, grid, starts, goals, paths, fps=15):
        self.grid = grid
        self.starts = starts
        self.goals = goals
        self.paths = paths
        self.fps = fps

        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111, aspect='equal')
        self.fig.subplots_adjust(
            left=0, right=1, bottom=0, top=1, wspace=None, hspace=None)

        self.patches = []
        self.artists = []
        self.robots = dict()
        self.robot_names = dict()
        self.robot_paths = dict()

        x_min = -0.5
        y_min = -0.5
        y_max = len(self.grid) - 0.5
        x_max = len(self.grid[0]) - 0.5
        plt.xlim(x_min, x_max)
        plt.ylim(y_min, y_max)

        # Create background grid with gray walls
        self.patches.append(Rectangle((x_min, y_min), x_max - x_min,
                                      y_max - y_min, facecolor='none', edgecolor='gray'))

        for i, j in np.argwhere(self.grid):
            self.patches.append(
                Rectangle((j - 0.5, i - 0.5), 1, 1, facecolor='gray', edgecolor='gray'))

        # Draw starts
        for i, start in enumerate(self.starts):
            size = 0.06
            color = self.Colors[i % len(self.Colors)]
            self.patches.append(Rectangle(
                (start[1] - size/2, start[0] - size/2), size, size, facecolor=color, edgecolor='black', alpha=0.5))
        # Draw goals
        for i, goal in enumerate(self.goals):
            size = 0.25
            color = self.Colors[i % len(self.Colors)]
            self.patches.append(Rectangle(
                (goal[1] - size/2, goal[0] - size/2), size, size, facecolor=color, edgecolor='black', alpha=0.5))

        # Draw paths
        # for i, path in enumerate(self.paths):
        #     if not path:
        #         continue
        #     path = np.array(path)
        #     color = self.Colors[i % len(self.Colors)]
        #     self.robot_paths[i] = self.ax.plot(path[:,1], path[:,0],'-', color=color, alpha=0.1, lw=1)

        # Draw robots
        self.t = 0  # Total steps/time is based on longest path
        for i, path in enumerate(self.paths):
            name = str(i)
            start = starts[i]
            color = self.Colors[i % len(self.Colors)]
            self.robots[i] = Circle(
                (start[1], start[0]), 0.3, facecolor=color, edgecolor='black')
            self.robots[i].original_face_color = color
            self.patches.append(self.robots[i])
            self.t = max(self.t, len(path) - 1)
            self.robot_names[i] = self.ax.text(
                start[1], start[0], name, color='black')
            self.robot_names[i].set_horizontalalignment('center')
            self.robot_names[i].set_verticalalignment('center')
            self.artists.append(self.robot_names[i])

        # Create animation

        self.animation = animation.FuncAnimation(self.fig, self.animate,
                                                 init_func=self.init,
                                                 frames=self.fps *
                                                 (self.t + 1),
                                                 interval=10,  # speed
                                                 blit=True)

    def init(self):
        # Initialize fig with grid and artists
        for p in self.patches:
            self.ax.add_patch(p)
        for a in self.artists:
            self.ax.add_artist(a)
        return self.patches + self.artists

    def animate(self, frame_number):
        # Animate paths
        for i, path in enumerate(self.paths):
            if not path:
                continue
            pos = self.interp_pos(frame_number / self.fps, path)
            # Converting from r,c to x,y for drawing
            pos = (pos[1], pos[0])
            self.robots[i].center = pos
            self.robot_names[i].set_position(pos)

        return self.patches + self.artists

    def save(self, file_name, rate=1):
        self.animation.save(
            file_name,
            fps=self.fps * rate,
            dpi=200,
            savefig_kwargs={"pad_inches": 0})

    @staticmethod
    def show():
        plt.show()

    @staticmethod
    def interp_pos(i, path):
        # interpolate position along path based on index
        # Clamp to bounds of path
        # i = np.clip(i, 0, len(path)-1)
        # int truncates
        if i <= 0:
            return path[0]
        elif int(i) + 1 >= len(path):
            return path[-1]

        a = np.array(path[math.floor(i)])
        b = np.array(path[math.ceil(i)])
        return (b-a) * (i-int(i)) + a
        # return path[int(i)] # for now just closest point


if __name__ == '__main__':
    grid = np.array([
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 1, 1, 0, 1, 1, 0, 0, 1],
        [1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 1],
        [1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 1],
        [1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 1],
        [1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    ])

    starts = [(1, 1), (2, 1), (4, 9)]
    goals = [(5, 8), (4, 5), (3, 2)]
    paths = [[(1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (2, 5), (2, 6), (2, 7), (2, 8), (3, 8), (4, 8), (5, 8)],
             [(2, 1), (2, 2), (2, 3), (2, 4), (2, 5), (3, 5), (4, 5)],
             [(4, 9), (4, 8), (3, 8), (2, 8), (2, 7), (2, 6), (2, 5), (2, 4), (2, 3), (2, 2), (3, 2)]]

    visualizer = Visualizer(grid, starts, goals, paths)
    # visualizer.save('mapf0.gif')
    visualizer.show()
