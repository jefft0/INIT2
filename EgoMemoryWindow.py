import pyglet
from pyglet.gl import *
from pyglet import shapes
import math
from OsoyooCar import OsoyooCar

ZOOM_IN_FACTOR = 1.2


class EgoMemoryWindow(pyglet.window.Window):
    def __init__(self, width=400, height=400, *args, **kwargs):
        super().__init__(width, height, resizable=True, *args, **kwargs)
        self.set_caption("Egocentric Memory")
        self.set_minimum_size(150, 150)
        glClearColor(1.0, 1.0, 1.0, 1.0)

        self.batch = pyglet.graphics.Batch()
        self.zoom_level = 1

        self.origin = shapes.Rectangle(0, 0, 60, 40, color=(150, 150, 225))
        self.origin.anchor_position = 30, 20
        self.environment_matrix = (GLfloat * 16)(1, 0, 0, 0,
                                                 0, 1, 0, 0,
                                                 0, 0, 1, 0,
                                                 0, 0, 0, 1)
        self.mouse_press_x = 0
        self.mouse_press_y = 0
        self.mouse_press_angle = 0

    def on_draw(self):
        """ Drawing the window """
        glClear(GL_COLOR_BUFFER_BIT)
        glLoadIdentity()

        # The transformations are stacked, and applied backward to the vertices

        # Stack the projection matrix. Centered on (0,0). Fit the window size and zoom factor
        glOrtho(-self.width * self.zoom_level, self.width * self.zoom_level, -self.height * self.zoom_level,
                self.height * self.zoom_level, 1, -1)

        # Stack the rotation of the world so the robot's front is up
        # glRotatef(90, 0.0, 0.0, 1.0)

        # Draw the robot and the phenomena
        self.batch.draw()

        # Stack the environment's displacement and draw the origin just to check
        glMultMatrixf(self.environment_matrix)
        self.origin.draw()  # Draw the origin of the robot

    def on_resize(self, width, height):
        """ Adjusting the viewport when resizing the window """
        # Always display in the whole window
        glViewport(0, 0, width, height)

    def on_mouse_press(self, x, y, button, modifiers):
        """ Computing the position of the mouse click relative to the robot in mm and degrees """
        self.mouse_press_x = int((x - self.width/2)*self.zoom_level*2)
        self.mouse_press_y = int((y - self.height/2)*self.zoom_level*2)
        print(self.mouse_press_x, self.mouse_press_y)
        self.mouse_press_angle = int(math.degrees(math.atan2(self.mouse_press_y, self.mouse_press_x)))

    def on_mouse_scroll(self, x, y, dx, dy):
        """ Zooming the window """
        # Inspired by https://www.py4u.net/discuss/148957
        f = ZOOM_IN_FACTOR if dy > 0 else 1/ZOOM_IN_FACTOR if dy < 0 else 1
        if .4 < self.zoom_level * f < 5:
            self.zoom_level *= f

    def update_environment_matrix(self, translation, rotation):
        """ Updating the environment matrix used to keep track of the origin """
        glLoadIdentity()
        glTranslatef(-translation[0], -translation[1], 0)
        glRotatef(-rotation, 0, 0, 1.0)
        glMultMatrixf(self.environment_matrix)
        glGetFloatv(GL_MODELVIEW_MATRIX, self.environment_matrix)


# Testing the egocentric memory window by moving the environment with the keyboard
if __name__ == "__main__":
    emw = EgoMemoryWindow()
    robot = OsoyooCar(emw.batch)

    @emw.event
    def on_text(text):
        """ Receiving the action from the window and updating the position of the environment """
        if text == "8":  # Move forward
            emw.update_environment_matrix([180, 0], 0)
        if text == "2":  # Move forward
            emw.update_environment_matrix([-180, 0], 0)
        if text == "1":  # Move forward
            emw.update_environment_matrix([0, 0], 45)
        if text == "3":  # Move forward
            emw.update_environment_matrix([0, 0], -45)

    pyglet.app.run()
