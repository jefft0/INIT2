import pyglet
from pyglet.gl import *
# from .Utils import hexaMemory_to_pyglet
# from .Utils import translate_indecisive_cell_to_pyglet
from .Utils import recently_changed_to_pyglet
from ..EgocentricDisplay.OsoyooCar import OsoyooCar
import math
from .Cell import Cell


NB_CELL_WIDTH = 30
NB_CELL_HEIGHT = 100
CELL_RADIUS = 50
ZOOM_IN_FACTOR = 1.2


class AllocentricView(pyglet.window.Window):
    """Create the allocentric view"""
    def __init__(self, memory, width=400, height=400, *args, **kwargs):
        super().__init__(width, height, resizable=True, *args, **kwargs)
        self.set_caption("Allocentric Memory")
        self.set_minimum_size(150, 150)
        # glClearColor(0.2, 0.2, 0.7, 1.0)  # Make it look like hippocampus imaging
        glClearColor(1.0, 1.0, 1.0, 1.0)
        self.batch = pyglet.graphics.Batch()
        self.background = pyglet.graphics.OrderedGroup(0)
        self.foreground = pyglet.graphics.OrderedGroup(1)

        self.robot_batch = pyglet.graphics.Batch()
        self.robot = OsoyooCar(self.robot_batch, self.foreground)

        # self.test_cell = Cell(0, 100, self.robot_batch, self.foreground, 50, 'Free')

        self.zoom_level = 4
        self.shapesList = []
        self.mouse_press_angle = 0
        self.window = None

        self.nb_cell_x = memory.allocentric_memory.width
        self.nb_cell_y = memory.allocentric_memory.height
        self.cell_radius = memory.allocentric_memory.cell_radius

        self.mouse_press_x = 0
        self.mouse_press_y = 0
        self.label = pyglet.text.Label('', font_name='Arial', font_size=15, x=10, y=10)
        self.label.color = (0, 0, 0, 255)
        self.memory = memory

        self.projections_for_context = []

    def extract_and_convert_interactions(self):
        """Create the shapes from hexagonal memory"""
        grid = self.memory.allocentric_memory.grid
        radius = self.memory.allocentric_memory.cell_radius
        height = math.sqrt((2 * radius) ** 2 - radius ** 2)
        shape_list = []

        for i in range(0, len(grid)):
            for j in range(0, len(grid[0])):
                # robot = False
                cell = grid[i][j]
                if cell.status != "Unknown":
                    if j % 2 == 0:
                        x = i * 3 * radius
                        y = height * (j / 2)
                    else:
                        x = (1.5 * radius) + i * 3 * radius
                        y = (height / 2) + (j - 1) / 2 * height
                    hexagon = Cell(x, y, self.batch, None, radius, cell.status).shape
                    shape_list.append(hexagon)
        self.shapesList = shape_list
        # self.indecisive_cell_shape = []
        # self.shapesList = hexaMemory_to_pyglet(memory, self.batch)
        # self.nb_cell_x = memory.allocentric_memory.width
        # self.nb_cell_y = memory.allocentric_memory.height
        # self.cell_radius = memory.allocentric_memory.cell_radius

    def extract_and_convert_recently_changed_cells(self, memory, to_reset=[], projections=[]):
        tmp = recently_changed_to_pyglet(memory, self.batch, projections=projections)
        self.shapesList.append(tmp)

    # def show_indecisive_cell(self, indecisive_cell): #(indecisive_cell,hexaMemory,batch)
    #     self.indecisive_cell_shape = []
    #     self.indecisive_cell_shape = translate_indecisive_cell_to_pyglet(indecisive_cell, self.hexa_memory, self.batch)
        
    def on_draw(self):
        """ Drawing the window """
        glClear(GL_COLOR_BUFFER_BIT)

        # The transformations are stacked, and applied backward to the vertices
        glLoadIdentity()

        # Stack the projection matrix. Centered on (0,0). Fit the window size and zoom factor
        glOrtho(-self.width * self.zoom_level, self.width * self.zoom_level, -self.height * self.zoom_level,
                self.height * self.zoom_level, 1, -1)

        # Stack the translation to center the grid in the widow
        tx = -self.nb_cell_x * 30 * self.cell_radius / 20
        ty = -self.nb_cell_y * 8.66 * self.cell_radius / 20
        glTranslatef(tx, ty, 0)

        # Draw the grid
        self.batch.draw()

        # Stack the transformation to position the robot
        glTranslatef(-tx + self.memory.allocentric_memory.robot_pos_x, -ty + self.memory.allocentric_memory.robot_pos_y, 0)
        # glTranslatef(-tx + 100, -ty + self.memory.allocentric_memory.robot_pos_y, 0)
        glRotatef(90 - self.memory.body_memory.body_azimuth_degree(), 0.0, 0.0, 1.0)
        # Draw the robot
        self.robot.rotate_head(self.memory.body_memory.head_direction_degree())
        self.robot_batch.draw()

        # Draw the text in the bottom left corner
        glLoadIdentity()
        glOrtho(0, self.width, 0, self.height, -1, 1)
        self.label.draw()

    def on_resize(self, width, height):
        """ Adjusting the viewport when resizing the window """
        # Always display in the whole window
        glViewport(0, 0, width, height)        # For standard screen
        # glViewport(0, 0, width * 2, height * 2)  # For retina screen on Mac

    def on_mouse_scroll(self, x, y, dx, dy):
        """ Zooming the window """
        # Inspired by https://www.py4u.net/discuss/148957
        f = ZOOM_IN_FACTOR if dy > 0 else 1/ZOOM_IN_FACTOR if dy < 0 else 1
        # if .4 < self.zoom_level * f < 5:  # Olivier
        self.zoom_level *= f

    def on_mouse_motion(self, x, y, dx, dy):
        # mouse_x = int((x - self.width/2) * self.zoom_level * 2)
        # mouse_y = int((y - self.height/2) * self.zoom_level * 2)
        # Find the cell
        cell_x, cell_y = self.cell_from_screen_coordinate(x, y)
        self.label.text = "Cell: " + str(cell_x) + ", " + str(cell_y)

    def cell_from_screen_coordinate(self, x, y):
        """ Computes the cell coordinates from the screen coordinates """
        mouse_x = int((x - self.width/2) * self.zoom_level * 2)
        mouse_y = int((y - self.height/2) * self.zoom_level * 2)
        cell_x, cell_y = self.memory.allocentric_memory.convert_pos_in_cell(mouse_x, mouse_y)
        self.label.text = "Cell: " + str(cell_x) + ", " + str(cell_y)
        return cell_x, cell_y
