import math
import matplotlib.path as mpath
import time
import numpy as np
from pyrr import quaternion
from . Hexagonal_geometry import point_to_cell, get_neighbors
from . GridCell import GridCell, CELL_UNKNOWN
from ..EgocentricMemory.Experience import EXPERIENCE_FLOOR, EXPERIENCE_PLACE, EXPERIENCE_FOCUS, EXPERIENCE_PROMPT, \
    EXPERIENCE_ALIGNED_ECHO, EXPERIENCE_IMPACT
from ..AllocentricMemory.GridCell import CELL_NO_ECHO
from ...Robot.RobotDefine import ROBOT_CHASSIS_X, ROBOT_OUTSIDE_Y, CHECK_OUTSIDE
from ...Memory.PhenomenonMemory.PhenomenonMemory import TER, ROBOT1
from ...Memory.PhenomenonMemory.PhenomenonTerrain import TERRAIN_ORIGIN_CONFIDENCE
from ..PhenomenonMemory import PHENOMENON_RECOGNIZE_CONFIDENCE


class AllocentricMemory:
    """The agent's allocentric memory made with an hexagonal grid."""

    def __init__(self, width, height, cell_radius):
        """Construct the allocentric memory of the robot, child class of HexaGrid
        with the addition of the robot at the center of the grid and a link between the
        software and the real word, cell_radius representing the radius of a cell in the real world (in millimeters)
        """
        # The grid of cells
        self.width = width  # Nb cells width
        self.height = height  # Nb cells height
        self.min_i = -width // 2 + 1
        self.max_i = width // 2
        self.min_j = -height // 2 + 1
        self.max_j = height // 2
        self.cell_radius = cell_radius

        # Allocentric memory is initialized with the robot at its center
        self.robot_point = np.array([0, 0, 0], dtype=float)

        self.focus_i = None
        self.focus_j = None
        self.prompt_i = None
        self.prompt_j = None

        # The affordances
        self.affordances = []

        # Fill the grid with cells
        self.grid = list()
        # Use negative grid index for negative positions
        for i in range(self.width):
            self.grid.append(list())
            if i <= self.width // 2:
                cell_i = i
            else:
                cell_i = -self.width + i
            for j in range(self.height):
                if j <= self.height // 2:
                    cell_j = j
                else:
                    cell_j = -self.height + j
                self.grid[i].append(GridCell(cell_i, cell_j, self.cell_radius))

        self.user_added_echos = []  # List of mutable tuples to be easily copied

    def __str__(self):
        output = ""
        for j in range(self.max_j, self.min_j - 1, -1):
            if j % 2 == 1:
                output += "-----"
            for i in range(self.min_i, self.max_i + 1):
                output += str(self.grid[i][j]) + "-----"
                # output += "-----"
            output += "\n"
        return output

    def update_affordances(self, phenomenon_memory, clock):
        """Allocate the phenomena to the cells of allocentric memory"""
        # start_time = time.time()
        # Clear the previous phenomena
        self.clear_grid_status()
        # Place the phenomena again
        for p_id, p in phenomenon_memory.phenomena.items():
            # Mark the cells outside the terrain (for BICA 2023 paper)
            if CHECK_OUTSIDE == 1:
                if p_id == TER and p.confidence >= PHENOMENON_RECOGNIZE_CONFIDENCE and p.path is not None:
                    for c in [c for line in self.grid for c in line if not p.is_inside(c.point())]:
                        c.status[0] = EXPERIENCE_FLOOR
                        c.phenomenon_id = TER
                        c.clock_place = clock
            # If terrain category has been recognised
            if p_id == TER and p.confidence >= TERRAIN_ORIGIN_CONFIDENCE:
                # Draw the terrain from its shape
                for point in p.shape:
                    cell_x, cell_y = point_to_cell(point + p.point)
                    self.apply_status_to_cell(cell_x, cell_y, EXPERIENCE_FLOOR, p.last_origin_clock, 0)
                    # Attribute this phenomenon to this cell
                    if (self.min_i <= cell_x <= self.max_i) and (self.min_j <= cell_y <= self.max_j):
                        self.grid[cell_x][cell_y].phenomenon_id = p_id
            if p_id == ROBOT1:
                # Draw the other robot from its shape
                for point in p.shape:
                    cell_x, cell_y = point_to_cell(point + p.point)
                    self.apply_status_to_cell(cell_x, cell_y, EXPERIENCE_ALIGNED_ECHO, p.last_origin_clock, 0)
                    self.apply_status_to_cell(cell_x, cell_y, EXPERIENCE_IMPACT, p.last_origin_clock, 0)
                    # Attribute this phenomenon to this cell
                    if (self.min_i <= cell_x <= self.max_i) and (self.min_j <= cell_y <= self.max_j):
                        self.grid[cell_x][cell_y].phenomenon_id = p_id
            # Mark the affordances of this phenomenon
            for a in p.affordances.values():
                if (p_id != TER or p.confidence < PHENOMENON_RECOGNIZE_CONFIDENCE or a.color_index != 0
                    or CHECK_OUTSIDE == 0) and a.type != EXPERIENCE_PLACE:
                    # Attribute the status of the affordance
                    cell_x, cell_y = point_to_cell(a.point+p.point)
                    self.apply_status_to_cell(cell_x, cell_y, a.type, a.clock, a.color_index)
                    # Attribute this phenomenon to this cell
                    if (self.min_i <= cell_x <= self.max_i) and (self.min_j <= cell_y <= self.max_j):
                        self.grid[cell_x][cell_y].phenomenon_id = p_id

        # Place the affordances that are not attached to phenomena
        for a in self.affordances:
            cell_x, cell_y = point_to_cell(a.point)
            self.apply_status_to_cell(cell_x, cell_y, a.type, clock, a.color_index)

        # print("Update allocentric time:", time.time() - start_time, "seconds")

    def move(self, direction_quaternion, translation, clock):
        """Move the robot in allocentric memory. Mark the traversed cells Free. Returns the new position
        If body_quaternion is identity then the translation is allocentric"""

        # Move the robot along its body direction
        destination_point = self.robot_point + quaternion.apply_to_vector(direction_quaternion, translation)
        # Mark the cells traversed by the robot
        if translation[0] > 0:  # Move back
            p1 = quaternion.apply_to_vector(direction_quaternion, [ROBOT_CHASSIS_X, ROBOT_OUTSIDE_Y, 0]) + self.robot_point
            p2 = quaternion.apply_to_vector(direction_quaternion, [-ROBOT_CHASSIS_X, ROBOT_OUTSIDE_Y, 0]) + destination_point
            p3 = quaternion.apply_to_vector(direction_quaternion, [-ROBOT_CHASSIS_X, -ROBOT_OUTSIDE_Y, 0]) + destination_point
            p4 = quaternion.apply_to_vector(direction_quaternion, [ROBOT_CHASSIS_X, -ROBOT_OUTSIDE_Y, 0]) + self.robot_point
        elif translation[1] > 0:  # Swipe left
            p1 = quaternion.apply_to_vector(direction_quaternion, [ROBOT_CHASSIS_X, ROBOT_OUTSIDE_Y, 0]) + destination_point
            p2 = quaternion.apply_to_vector(direction_quaternion, [-ROBOT_CHASSIS_X, ROBOT_OUTSIDE_Y, 0]) + destination_point
            p3 = quaternion.apply_to_vector(direction_quaternion, [-ROBOT_CHASSIS_X, -ROBOT_OUTSIDE_Y, 0]) + self.robot_point
            p4 = quaternion.apply_to_vector(direction_quaternion, [ROBOT_CHASSIS_X, -ROBOT_OUTSIDE_Y, 0]) + self.robot_point
        elif translation[1] < 0:  # Swipe right
            p1 = quaternion.apply_to_vector(direction_quaternion, [ROBOT_CHASSIS_X, ROBOT_OUTSIDE_Y, 0]) + self.robot_point
            p2 = quaternion.apply_to_vector(direction_quaternion, [-ROBOT_CHASSIS_X, ROBOT_OUTSIDE_Y, 0]) + self.robot_point
            p3 = quaternion.apply_to_vector(direction_quaternion, [-ROBOT_CHASSIS_X, -ROBOT_OUTSIDE_Y, 0]) + destination_point
            p4 = quaternion.apply_to_vector(direction_quaternion, [ROBOT_CHASSIS_X, -ROBOT_OUTSIDE_Y, 0]) + destination_point
        else:  # Move forward
            p1 = quaternion.apply_to_vector(direction_quaternion, [ROBOT_CHASSIS_X, ROBOT_OUTSIDE_Y, 0]) + destination_point
            p2 = quaternion.apply_to_vector(direction_quaternion, [-ROBOT_CHASSIS_X, ROBOT_OUTSIDE_Y, 0]) + self.robot_point
            p3 = quaternion.apply_to_vector(direction_quaternion, [-ROBOT_CHASSIS_X, -ROBOT_OUTSIDE_Y, 0]) + self.robot_point
            p4 = quaternion.apply_to_vector(direction_quaternion, [ROBOT_CHASSIS_X, -ROBOT_OUTSIDE_Y, 0]) + destination_point

        path = mpath.Path([p[0:2] for p in [p1, p2, p3, p4]])
        for c in [c for line in self.grid for c in line if c.is_inside(path)]:
            c.status[0] = EXPERIENCE_PLACE
            c.clock_place = clock

        # The new position of the robot
        self.robot_point = destination_point
        return np.round(destination_point)

    def place_robot(self, body_memory, clock):
        """Apply the PLACE status to the cells at the position of the robot"""
        # start_time = time.time()
        outline = body_memory.outline() + self.robot_point
        path = mpath.Path([p[0:2] for p in outline])
        for c in [c for line in self.grid for c in line if c.is_inside(path)]:
            c.status[0] = EXPERIENCE_PLACE
            c.clock_place = clock
        # print("Place robot time:", time.time() - start_time, "seconds")

    def clear_grid_status(self):
        """Reset the status of all cells except PLACE status"""
        for c in [c for line in self.grid for c in line if c.phenomenon_id is not None]:
            if c.status[0] != EXPERIENCE_PLACE:  # The place experiences are not moved with phenomena
                c.status[0] = CELL_UNKNOWN
            c.status[1] = CELL_UNKNOWN
            c.clock_phenomenon = 0
            c.phenomenon_id = None

    def apply_status_to_cell(self, i, j, status, clock, color_index):
        """Change the cell status. Keep the max clock"""
        if (self.min_i <= i <= self.max_i) and (self.min_j <= j <= self.max_j):
            if status in [EXPERIENCE_FLOOR, EXPERIENCE_PLACE]:
                self.grid[i][j].status[0] = status
                self.grid[i][j].clock_place = max(clock, self.grid[i][j].clock_place)
                self.grid[i][j].color_index = color_index
            else:
                self.grid[i][j].status[1] = status
                self.grid[i][j].clock_interaction = max(clock, self.grid[i][j].clock_interaction)
        else:
            pass
            # print("Error: cell out of grid, i:", i, "j:", j, "Status:", status)

    def clear_cell(self, i, j, clock):
        """Reset status0 and color of that cell"""
        if (self.min_i <= i <= self.max_i) and (self.min_j <= j <= self.max_j):
            self.grid[i][j].status[0] = CELL_UNKNOWN
            self.grid[i][j].clock_place = clock
            self.grid[i][j].color_index = 0
            self.grid[i][j].phenomenon_id = None

    def mark_echo_area(self, affordance):
        """Mark the area covered by the echolocalization sensor in allocentric memory"""
        # start_time = time.time()
        points = affordance.sensor_triangle()
        triangle = [p[0:2] for p in points]
        path = mpath.Path(triangle)
        for c in [c for line in self.grid for c in line if c.is_inside(path)]:
            c.status[2] = CELL_NO_ECHO
            c.clock_no_echo = affordance.clock
        # print("Place echo time:", time.time() - start_time, "seconds")

    def update_focus(self, allo_focus, clock):
        """Update the focus in allocentric memory"""
        # Clear the previous focus cell
        if self.focus_i is not None:
            if (self.min_i <= self.focus_i <= self.max_i) and (self.min_j <= self.focus_j <= self.max_j):
                self.grid[self.focus_i][self.focus_j].status[3] = CELL_UNKNOWN
        # Add the new focus cell
        if allo_focus is not None:
            self.focus_i, self.focus_j = point_to_cell(allo_focus, self.cell_radius)
            if (self.min_i <= self.focus_i <= self.max_i) and (self.min_j <= self.focus_j <= self.max_j):
                self.grid[self.focus_i][self.focus_j].status[3] = EXPERIENCE_FOCUS
                self.grid[self.focus_i][self.focus_j].clock_focus = clock

    def update_prompt(self, allo_prompt, clock):
        """Update the prompt in allocentric memory"""
        # Clear the previous prompt cell
        if self.prompt_i is not None:
            if (self.min_i <= self.prompt_i <= self.max_i) and (self.min_j <= self.prompt_j <= self.max_j):
                self.grid[self.prompt_i][self.prompt_j].status[4] = CELL_UNKNOWN
        # Add the new prompt cell
        if allo_prompt is not None:
            self.prompt_i, self.prompt_j = point_to_cell(allo_prompt, self.cell_radius)
            if (self.min_i <= self.prompt_i <= self.max_i) and (self.min_j <= self.prompt_j <= self.max_j):
                self.grid[self.prompt_i][self.prompt_j].status[4] = EXPERIENCE_PROMPT
                self.grid[self.prompt_i][self.prompt_j].clock_prompt = clock
                # print("Prompt in cell", self.prompt_i, ", ", self.prompt_j)

    def save(self):
        """Retun a clone of allocentric memory for memory snapshot"""
        saved_allocentric_memory = AllocentricMemory(self.width, self.height, self.cell_radius)
        saved_allocentric_memory.robot_point = self.robot_point.copy()
        saved_allocentric_memory.focus_i = self.focus_i
        saved_allocentric_memory.focus_j = self.focus_j
        saved_allocentric_memory.prompt_i = self.prompt_i
        saved_allocentric_memory.prompt_j = self.prompt_j
        saved_allocentric_memory.affordances = [a.save() for a in self.affordances]
        saved_allocentric_memory.grid = [[c.save() for c in line] for line in self.grid]
        saved_allocentric_memory.user_added_echos = [e for e in self.user_added_echos]

        return saved_allocentric_memory

    def most_interesting_pool(self, clock):
        """Return the coordinates of the cell that has the most interesting pool value"""
        interests = []
        coords = []

        # for n in range(-2, 2):
        #     for m in range(-2, 2):
        # 3 tours counterclockwise:
        visit = [(2, 0), (-1, 4), (-2, -4), (2, -2), (0, 4), (-2, -2), (2, -4), (1, 4), (-2, 0), (1, -4), (2, 4), (-2, 2),
                 (0, -4), (2, 2), (-2, 4), (-1, -4)]
        visit = [(2, 0), (-1, 4), (-2, -4), (2, -2), (0, 4), (-2, -2), (2, -4), (1, 4), (-2, 0), (1, -4), (2, 4), (-2, 2),
                 (0, -4), (2, 2), (-2, 4), (-1, -4)]
        for i in visit:
            i_even = 3 * i[0] + i[1]
            j_even = -2 * i[0] + 4 * i[1]
            coords.append([i_even, j_even])
            interests.append(self.pool_interest(i_even, j_even, clock))
            # i_odd = i_even - 2
            # j_odd = j_even + 1
            # cells.append([i_odd, j_odd])
            # interests.append(self.pool_interest(i_odd, j_odd, clock))
        max_interest = max(interests)
        coord = coords[interests.index(max_interest)]
        # Update the prompt
        if self.prompt_i is not None:
            self.grid[self.prompt_i][self.prompt_j].status[3] = CELL_UNKNOWN
        self.prompt_i, self.prompt_j = coord[0], coord[1]
        self.grid[self.prompt_i][self.prompt_j].status[3] = EXPERIENCE_PROMPT
        self.grid[self.prompt_i][self.prompt_j].clock_prompt = clock
        print("Most interesting pool:", coord, "with interest", max_interest)
        return self.grid[self.prompt_i][self.prompt_j].point()

    def pool_interest(self, i, j, clock):
        """Return the sum of interest of neighbors plus this cell"""
        if (self.min_i + 1 <= i <= self.max_i - 1) and (self.min_j + 1 <= j <= self.max_j - 1):
            interest = self.grid[i][j].interest_value(clock)
            for n in get_neighbors(i, j).values():
                interest += self.grid[n[0]][n[1]].interest_value(clock)
            return interest
        else:
            # If not in the grid
            return -20
