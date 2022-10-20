from pyglet import shapes, gl
from webcolors import name_to_rgb
from autocat.Memory.EgocentricMemory.Experience import *

# Points of interest that only exist in Egocentric Display
# (points of interest attached to an interaction have the same type as their interactions)
POINT_COMPASS = 'Compass'
POINT_AZIMUTH = 'Azimuth'


class PointOfInterest:
    def __init__(self, x, y, batch, group, point_type, experience=None):
        self.experience = experience
        self.x, self.y = 0, 0  # will be displaced
        self.batch = batch
        self.group = group
        self.type = point_type
        self.points = []
        self.opacity = 255
        self.color = name_to_rgb("gray")

        self.is_selected = False

        if self.type == EXPERIENCE_PLACE:
            # Place: LightGreen triangle
            self.points = [30, 0, -20, -20, -20, 20]
            self.color = name_to_rgb("LightGreen")
            self.shape = self.batch.add_indexed(3, gl.GL_TRIANGLES, self.group, [0, 1, 2], ('v2i', self.points),
                                                ('c4B', 3 * (*self.color, self.opacity)))
        if self.type == EXPERIENCE_ALIGNED_ECHO:
            self.color = name_to_rgb("orange")
            self.shape = shapes.Circle(0, 0, 20, color=self.color, batch=self.batch)
            self.shape.group = group
        if self.type == EXPERIENCE_LOCAL_ECHO:
            self.color = name_to_rgb("sienna")
            self.shape = shapes.Circle(0, 0, 7, color=self.color, batch=self.batch)
        if self.type == EXPERIENCE_CENTRAL_ECHO:
            self.color = name_to_rgb("sienna")
            self.shape = shapes.Circle(0, 0, 20, color=self.color, batch=self.batch)
            self.shape.group = group
        if self.type == EXPERIENCE_FLOOR:
            self.color = name_to_rgb("black")
            self.points = [-5, -30, -5, 30, 5, 30, 5, -30]
            self.shape = self.batch.add_indexed(4, gl.GL_TRIANGLES, self.group, [0, 1, 2, 0, 2, 3],
                                        ('v2i', self.points), ('c4B', 4 * (*self.color, self.opacity)))
        if self.type == EXPERIENCE_IMPACT:
            self.color = name_to_rgb("red")
            self.points = [0, 0, 40, -30, 40, 30]
            self.shape = self.batch.add_indexed(3, gl.GL_TRIANGLES, self.group, [0, 1, 2], ('v2i', self.points),
                                                ('c4B', 3 * (*self.color, self.opacity)))
        if self.type == EXPERIENCE_BLOCK:
            self.color = name_to_rgb("salmon")
            self.points = [0, 0, 40, -30, 40, 30]
            self.shape = self.batch.add_indexed(3, gl.GL_TRIANGLES, self.group, [0, 1, 2], ('v2i', self.points),
                                                ('c4B', 3 * (*self.color, self.opacity)))
        if self.type == EXPERIENCE_FOCUS:
            self.color = name_to_rgb("fireBrick")
            self.points = [40, 0, 20, 34, -20, 34, -40, 0, -20, -34, 20, -34]
            self.shape = self.batch.add_indexed(6, gl.GL_TRIANGLES, group, [0, 1, 2, 0, 2, 3, 0, 3, 4, 0, 4, 5],
                                                ('v2i', self.points), ('c4B', 6 * (*self.color, self.opacity)))
        if self.type == POINT_COMPASS:
            self.color = name_to_rgb("RoyalBlue")
            self.points = [10, 0, 0, -10, 0, 10, -10, 0]
            self.shape = self.batch.add_indexed(4, gl.GL_TRIANGLES, self.group, [0, 1, 2, 1, 2, 3],
                                                ('v2i', self.points), ('c4B', 4 * (*self.color, self.opacity)))
        if self.type == POINT_AZIMUTH:
            self.color = name_to_rgb("SteelBlue")
            # self.shape = shapes.Circle(0, 0, 20, color=self.color, batch=self.batch)
            self.points = [20, 0, 0, -20, 0, 20, -20, 0]
            self.shape = self.batch.add_indexed(4, gl.GL_TRIANGLES, self.group, [0, 1, 2, 1, 2, 3],
                                                ('v2i', self.points), ('c4B', 4 * (*self.color, self.opacity)))

        # Move the point of interest to its position
        position_matrix = matrix44.create_from_translation([x, y, 0]).astype('float64')
        self.displace(position_matrix)

    def set_color(self, color_name=None):
        """ Set the color or reset it to its default value """
        if color_name is None:
            if hasattr(self.shape, 'vertices'):
                nb_points = int(len(self.shape.vertices) / 2)
                self.shape.colors[0: nb_points*4] = nb_points * (*self.color, self.opacity)
            else:
                self.shape.color = self.color
            # if self.type == [EXPERIENCE_PLACE, EXPERIENCE_IMPACT, EXPERIENCE_BLOCK]:
            #     self.shape.colors[0:12] = 3 * (*self.color, self.opacity)
            # if self.type == [EXPERIENCE_FLOOR, POINT_COMPASS]:
            #     self.shape.colors[0:16] = 4 * (*self.color, self.opacity)
            # if self.type == EXPERIENCE_FOCUS:
            #     self.shape.colors[0:24] = 6 * (*self.color, self.opacity)
        else:
            if hasattr(self.shape, 'vertices'):
                nb_points = int(len(self.shape.vertices) / 2)
                self.shape.colors[0: nb_points*4] = nb_points * (*name_to_rgb(color_name), self.opacity)
            else:
                self.shape.color = name_to_rgb(color_name)
            # if self.type in [EXPERIENCE_PLACE, EXPERIENCE_IMPACT, EXPERIENCE_BLOCK]:
            #     self.shape.colors[0:12] = 3 * (*name_to_rgb(color_name), self.opacity)
            # if self.type in [EXPERIENCE_FLOOR, POINT_COMPASS]:
            #     self.shape.colors[0:16] = 4 * (*name_to_rgb(color_name), self.opacity)
            # elif self.type == EXPERIENCE_FOCUS:
            #     self.shape.colors[0:24] = 6 * (*name_to_rgb(color_name), self.opacity)

    def reset_position(self):
        """ Reset the position of the point of interest """
        self.x, self.y = 0, 0
        # If the shape has a list of vertices then reset it
        if hasattr(self.shape, 'vertices'):
            self.shape.vertices = self.points
        else:
            self.shape.x, self.shape.y = 0, 0  # Circle

    def displace(self, displacement_matrix):
        """ Applying the displacement matrix to the point of interest """
        #  Rotate and translate the position
        v = matrix44.apply_to_vector(displacement_matrix, [self.x, self.y, 0])
        self.x, self.y = v[0], v[1]

        # If the shape has a list of vertices (POINT PLACE)
        if hasattr(self.shape, 'vertices'):
            for i in range(0, len(self.shape.vertices)-1, 2):
                v = matrix44.apply_to_vector(displacement_matrix, [self.shape.vertices[i], self.shape.vertices[i+1], 0])
                self.shape.vertices[i], self.shape.vertices[i+1] = int(v[0]), int(v[1])
            return

        # Other points of interest have x and y (Circles)
        self.shape.x, self.shape.y = self.x, self.y

        # Rotate the shapes
        if self.type == EXPERIENCE_FLOOR:  # Rotate the rectangle
            q = Quaternion(displacement_matrix)
            if q.axis[2] > 0:  # Rotate around z axis upwards
                self.shape.rotation += math.degrees(q.angle)
            else:  # Rotate around z axis downward
                self.shape.rotation += math.degrees(-q.angle)
        if self.type == EXPERIENCE_BLOCK or self.type == EXPERIENCE_IMPACT:
            # Rotate and translate the other points of the triangle
            v = matrix44.apply_to_vector(displacement_matrix, [self.shape.x2, self.shape.y2, 0])
            self.shape.x2, self.shape.y2 = v[0], v[1]
            v = matrix44.apply_to_vector(displacement_matrix, [self.shape.x3, self.shape.y3, 0])
            self.shape.x3, self.shape.y3 = v[0], v[1]

    def delete(self):
        """ Delete the shape to remove it from the batch """
        self.shape.delete()  # Not sure whether it is necessary or not

    def select_if_near(self, x, y):
        """ If the point is near the x y coordinate, select this point and return True """
        # is_near = math.dist([x, y], [self.x, self.y]) < 20
        if math.dist([x, y], [self.x, self.y]) < 20:
            self.set_color('red')
            self.is_selected = True
        else:
            self.set_color()
            self.is_selected = False

    def update(self, displacement_matrix):
        """ Displace the point of interest to the position of its experience
        or by the displacement_matrix provided as an argument"""

        # If this point of interest has an experience, the displacement matrix comes from this experience
        if self.experience is not None:
            self.reset_position()
            displacement_matrix = self.experience.position_matrix

        # if displacement_matrix is not None:
        self.displace(displacement_matrix)

    def fade(self):
        """Decrease the opacity of this point of interest"""
        if self.experience is None:
            self.opacity = max(self.opacity - 10, 0)
        else:
            self.opacity = int(min(self.experience.actual_durability * (255 / self.experience.durability), 255))
        if hasattr(self.shape, 'vertices'):
            # Update the opacity
            self.set_color(None)
        else:
            self.shape.opacity = self.opacity

    def __str__(self):
        return "POI of type " + self.type + " at x=" + str(int(self.x)) + ", y=" + str(int(self.y)) + \
               ", interaction: " + self.experience.__str__()
