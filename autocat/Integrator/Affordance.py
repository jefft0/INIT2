import math
from pyrr import matrix44
from ..Memory.EgocentricMemory.Experience import EXPERIENCE_ALIGNED_ECHO
from ..Utils import assert_almost_equal_angles

AFFORDANCE_MAX_DISTANCE = 300  # (mm) Max distance within which affordances are similar
AFFORDANCE_MAX_DIRECTION = 15  # (degrees) Max angle within which affordances are similar


class Affordance:
    """An affordance is an experience localized relative to a phenomenon"""
    def __init__(self, point, experience):
        """Position should be integer to facilitate search"""
        self.point = point
        print("Phenomenon point: ", self.point)
        self.position_matrix = matrix44.create_from_translation(self.point).astype('float64')
        self.experience = experience

    def similar_to(self, other_affordance):
        """Affordances are similar if they have similar point and their experience have similar absolute direction"""
        if math.dist(self.point, other_affordance.point) < AFFORDANCE_MAX_DISTANCE:
            if assert_almost_equal_angles(self.experience.absolute_direction_rad,
                                          other_affordance.experience.absolute_direction_rad,
                                          AFFORDANCE_MAX_DIRECTION):
                print("Near affordance: point 1:", self.point, ", point 2:", other_affordance.point,
                      ", direction 1: ", int(math.degrees(self.experience.absolute_direction_rad)),
                      "°, direction 2: ", int(math.degrees(other_affordance.experience.absolute_direction_rad)), "°")
                return True
        return False

    def sensor_triangle(self):
        """The set of points to display the sensor in phenomenon view"""
        points = None
        if self.experience.type == EXPERIENCE_ALIGNED_ECHO:
            # The position of the sensor
            # sensor_position_matrix = matrix44.multiply(self.experience.sensor_matrix, self.position_matrix)
            # p1x, p1y, _ = matrix44.apply_to_vector(sensor_position_matrix, [0, 0, 0]) + self.position_point
            p1x, p1y, _ = matrix44.apply_to_vector(self.experience.sensor_matrix, [0, 0, 0]) + self.point
            # Second point of the triangle
            orthogonal_rotation = matrix44.create_from_z_rotation(math.pi/2)
            p2_matrix = matrix44.multiply(self.experience.sensor_matrix, orthogonal_rotation)
            p2_matrix[3, 0] /= 3
            p2_matrix[3, 1] /= 3
            # p2_matrix = matrix44.multiply(p2_matrix, self.position_matrix)
            p2x, p2y, _ = matrix44.apply_to_vector(p2_matrix, [0, 0, 0]) + self.point
            # Third point of the triangle
            p3_matrix = matrix44.multiply(self.experience.sensor_matrix, orthogonal_rotation)
            p3_matrix[3, 0] /= -3
            p3_matrix[3, 1] /= -3
            # p3_matrix = matrix44.multiply(p3_matrix, self.position_matrix)
            p3x, p3y, _ = matrix44.apply_to_vector(p3_matrix, [0, 0, 0]) + self.point

            points = [int(p1x), int(p1y), int(p2x), int(p2y), int(p3x), int(p3y)]
        return points
