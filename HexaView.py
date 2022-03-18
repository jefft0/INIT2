import pyglet
from pyglet.gl import *
from pyglet import shapes
import math
import time
from Utils import hexaMemory_to_pyglet
ZOOM_IN_FACTOR = 1.2
from HexaMemory import HexaMemory

NB_CELL_WIDTH = 30
NB_CELL_HEIGHT = 100
CELL_RADIUS = 50

class HexaView(pyglet.window.Window):
    def __init__(self, width=400, height=400, shapesList = None, *args, **kwargs):
        super().__init__(width, height, resizable=True, *args, **kwargs)
        self.set_caption("Hexa Memory")
        self.set_minimum_size(150, 150)
        glClearColor(1.0, 1.0, 1.0, 1.0)
        self.batch = pyglet.graphics.Batch()
        self.zoom_level = 1
        self.azimuth = 0
        self.shapesList = shapesList
        # self.mouse_press_x = 0
        # self.mouse_press_y = 0
        self.mouse_press_angle = 0
        self.window = None

    def set_ShapesList(self,s):
        self.shapesList = s

    def refresh(self,memory):
        @self.event
        def on_close():
            self.close()
            #@self.window.event
            #def on_key_press(key, mod):
            #    # ...do stuff on key press
        pyglet.clock.tick()
        self.clear()
        self.dispatch_events()
        self.extract_and_convert_phenomenons(memory)
        self.on_draw()
        # ...transform, update, create all objects that need to be rendered
        self.flip()

    def extract_and_convert_interactions(self, memory):
        self.shapesList = hexaMemory_to_pyglet(memory, self.batch)


    def on_draw(self):
        """ Drawing the window """
        glClear(GL_COLOR_BUFFER_BIT)
        glLoadIdentity()
        # The transformations are stacked, and applied backward to the vertices
        # Stack the projection matrix. Centered on (0,0). Fit the window size and zoom factor  # DEBUG TODO ALED decentrer le bordel, ou plutot le centrer sur le milieu de la grid
        # glOrtho(1 * self.zoom_level, self.width * self.zoom_level , 1* self.zoom_level,
        #         self.height * self.zoom_level, 1, -1)
        grid_width = NB_CELL_WIDTH * CELL_RADIUS * 3.3 # 36*50
        grid_height = NB_CELL_HEIGHT * CELL_RADIUS  # 5000 36*50
        left = -CELL_RADIUS  # -grid_width / 2  * self.zoom_level # * self.width
        right = grid_width * self.zoom_level  # * self.width
        bottom = -CELL_RADIUS # -center_y  * self.zoom_level  # * self.height
        top = grid_height * self.zoom_level  # * self.height

        glOrtho(left, right, bottom, top, 1, 0)
        # Draw the robot and the phenomena
        shapesListo = self.shapesList
        self.batch.draw()

    def on_resize(self, width, height):
        """ Adjusting the viewport when resizing the window """
        # Always display in the whole window
        glViewport(0, 0, width, height)

    def on_mouse_scroll(self, x, y, dx, dy):
        """ Zooming the window """
        # Inspired by https://www.py4u.net/discuss/148957
        f = ZOOM_IN_FACTOR if dy > 0 else 1/ZOOM_IN_FACTOR if dy < 0 else 1
        # if .4 < self.zoom_level * f < 5:  # Olivier
        self.zoom_level *= f

        def set_batch(self, batch):
            self.batch = batch


# Testing by displaying HexaView with HexaMemory
if __name__ == "__main__":
    hexaview = HexaView()
    hexa_memory = HexaMemory(width=NB_CELL_WIDTH, height=NB_CELL_HEIGHT, cells_radius=CELL_RADIUS)
    hexaview.extract_and_convert_phenomenons(hexa_memory)

    pyglet.app.run()
