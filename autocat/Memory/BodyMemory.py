import math


class BodyMemory:
    """Memory of body position"""
    def __init__(self, ):
        self.head_direction_rad = .0  # Radian relative to the robot's x axis [-pi/2, pi/2]
        self.body_direction_rad = .0  # Radian relative to horizontal x axis (west-east) [-pi, pi]

    def set_head_direction_degree(self, head_direction_degree: int):
        """Set the head direction from degree measured relative to x axis [-90,90]"""
        assert(-90 <= head_direction_degree <= 90)
        self.head_direction_rad = math.radians(head_direction_degree)

    def head_direction_degree(self):
        """Return the robot's head direction in degrees [-90,90]"""
        return int(math.degrees(self.head_direction_rad))

    def set_body_direction_from_azimuth(self, azimuth_degree: int):
        """Set the body direction from azimuth measure relative to north [0,360[ degree"""
        # assert(0 <= azimuth_degree <= 361)  #
        deg_trig = 90 - azimuth_degree  # Degree relative to x axis in trigonometric direction
        while deg_trig < -180:  # Keep within [-180, 180]
            deg_trig += 360
        self.body_direction_rad = math.pi / 2 - math.radians(azimuth_degree)

    def body_azimuth(self):
        """Return the azimuth in degree relative to north [0,360["""
        deg_north = 90 - math.degrees(self.body_direction_rad)
        while deg_north < 0:  # Keep within [0, 360]
            deg_north += 360
        return int(deg_north)

    def body_direction_degree(self):
        """Return the body direction in degree relative to the x axis [-180,180["""
        return int(math.degrees(self.body_direction_rad))

    def rotate_degree(self, yaw_degree: int, azimuth_degree: int):
        """Rotate the robot's body by the yaw or prevent drift using azimuth."""
        new_azimuth = self.body_azimuth() - yaw_degree  # Yaw is counterclockwise
        # Keep it within [0, 360[
        while new_azimuth < 0:
            new_azimuth += 360
        new_azimuth = new_azimuth % 360

        # If the direction is too far from the azimuth then use the azimuth
        # https://stackoverflow.com/questions/1878907/how-can-i-find-the-difference-between-two-angles
        if 10 < azimuth_degree < 350:  # Don't apply if imu has no compass information
            if abs(new_azimuth - azimuth_degree) > 10:
                new_azimuth = azimuth_degree

        self.set_body_direction_from_azimuth(new_azimuth)
