import math
import numpy as np
from pyrr import Quaternion, Vector3
from ..Robot.RobotDefine import ROBOT_SETTINGS, ROBOT_CHASSIS_X, ROBOT_OUTSIDE_Y
from ..Utils import quaternion_to_azimuth, quaternion_to_direction_rad
from . import EMOTION_PLEASURE, EMOTION_VIGILANCE, EMOTION_CONTENT

ENERGY_TIRED = 80  # 88  # 90  # 92  # Level of energy below which the agent wants to go to color patch
EXCITATION_LOW = 90  # 95  # 60  # 75  # Level of excitation below witch Robot just wants to watch if it is not tired
DOPAMINE = 0
SEROTONIN = 1
NORADRENALINE = 2


class BodyMemory:
    """Memory of body position"""
    def __init__(self, robot_id):
        """Initialize the body position and speed variables"""
        self.robot_id = robot_id
        self.head_direction_rad = .0  # [-pi/2, pi/2] Radian relative to the robot's x axis
        self.body_quaternion = Quaternion([0., 0., 0., 1.])  # The direction of the body initialized to x axis
        self.compass_offset = np.array(ROBOT_SETTINGS[robot_id]["compass_offset"], dtype=int)
        self.retreat_yaw = ROBOT_SETTINGS[robot_id]["retreat_yaw"]
        # TODO Return to color patch based on neurotransmitters
        self.neurotransmitters = np.array([50, 50, 50], dtype=int)  # DA, 5-HT, NA
        self.energy = 100  # [0,100] The level of energy of the robot
        self.excitation = 100  # [0, 100] The level of excitation
        self.simulation_rotation_deg = 0
        self.simulation_translate = np.array([0., 0., 0.])

    def update(self, enaction):
        """Update the body state variables: energy and excitation, head, body direction"""
        # Update the head
        self.set_head_direction_degree(enaction.outcome.head_angle)
        # Body direction
        self.body_quaternion[:] = enaction.trajectory.body_quaternion

        # Update energy level
        if enaction.outcome.color_index > 0 and enaction.outcome.floor > 0:
            # Fully recharge when color floor
            self.energy = 100
        else:
            # Decrease energy when not color floor
            self.energy = max(0, self.energy - 1)
        # Decrease excitation level
        self.excitation = max(0, self.excitation - 1)

    def set_head_direction_degree(self, head_direction_degree: int):
        """Set the head direction from degree measured relative to the robot within [-90,90]"""
        self.head_direction_rad = math.radians(max(-90, min(head_direction_degree, 90)))

    def head_direction_degree(self):
        """Return the robot's head direction relative to the robot in degrees [-90,90]"""
        return round(math.degrees(self.head_direction_rad))

    def body_azimuth(self):
        """Return the azimuth in degree relative to north [0,360["""
        return quaternion_to_azimuth(self.body_quaternion)

    def get_body_direction_rad(self):
        """Return the body direction in rad in polar-egocentric coordinates"""
        return quaternion_to_direction_rad(self.body_quaternion)

    def get_body_direction_normalized(self):
        """Return a normalized vector indicating the body direction"""
        return self.body_quaternion * Vector3([1., 0., 0.])

    def head_absolute_direction(self):
        """The head's direction in polar-egocentric reference"""
        return self.get_body_direction_rad() + self.head_direction_rad

    def outline(self):
        """The rectangle occupied by the robot's body in polar-egocentric reference"""
        return np.array([
            self.body_quaternion * Vector3([ROBOT_CHASSIS_X, ROBOT_OUTSIDE_Y, 0]),
            self.body_quaternion * Vector3([-ROBOT_CHASSIS_X, ROBOT_OUTSIDE_Y, 0]),
            self.body_quaternion * Vector3([-ROBOT_CHASSIS_X, -ROBOT_OUTSIDE_Y, 0]),
            self.body_quaternion * Vector3([ROBOT_CHASSIS_X, -ROBOT_OUTSIDE_Y, 0])])

    def emotion_code(self):
        """Return the code to display the emotion"""
        return [EMOTION_PLEASURE, EMOTION_CONTENT, EMOTION_VIGILANCE][np.argmax(self.neurotransmitters)]

    def save(self):
        """Return a clone of bodymemory to save a snapshot of memory"""
        saved_body_memory = BodyMemory(self.robot_id)
        saved_body_memory.head_direction_rad = self.head_direction_rad
        saved_body_memory.body_quaternion = self.body_quaternion.copy()
        saved_body_memory.compass_offset = self.compass_offset.copy()
        saved_body_memory.retreat_yaw = self.retreat_yaw
        saved_body_memory.energy = self.energy
        saved_body_memory.excitation = self.excitation
        saved_body_memory.neurotransmitters[:] = self.neurotransmitters
        saved_body_memory.simulation_rotation_deg = self.simulation_rotation_deg  # Perhaps not needed
        saved_body_memory.simulation_translate[:] = self.simulation_translate
        return saved_body_memory
