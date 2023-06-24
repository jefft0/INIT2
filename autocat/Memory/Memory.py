import numpy as np
from pyrr import matrix44, quaternion
from .EgocentricMemory.EgocentricMemory import EgocentricMemory
from .AllocentricMemory.AllocentricMemory import AllocentricMemory
from .BodyMemory import BodyMemory
from .PhenomenonMemory.PhenomenonMemory import PhenomenonMemory, TER
from .AllocentricMemory.Hexagonal_geometry import CELL_RADIUS
from ..Utils import rotate_vector_z


GRID_WIDTH = 100   # Number of cells wide
GRID_HEIGHT = 200  # Number of cells high
NEAR_HOME = 300    # (mm) Max distance to consider near home
SIMULATION_TIME_RATIO = 1  # 0.5   # The simulation speed is slower than the real speed because ...
SIMULATION_STEP_OFF = 0
SIMULATION_STEP_ON = 1  # More step will be used to take wifi transmission time into account


class Memory:
    """The Memory serves as the general container of the three memories:
        body memory, egocentric memory, and allocentric memory
    """

    def __init__(self):
        self.body_memory = BodyMemory()
        self.egocentric_memory = EgocentricMemory()
        self.allocentric_memory = AllocentricMemory(GRID_WIDTH, GRID_HEIGHT, cell_radius=CELL_RADIUS)
        self.phenomenon_memory = PhenomenonMemory()

    def __str__(self):
        return "Memory Robot position (" + str(round(self.allocentric_memory.robot_point[0])) + "," +\
                                           str(round(self.allocentric_memory.robot_point[1])) + ")"

    def update_and_add_experiences(self, enacted_enaction):
        """ Process the enacted interaction to update the memory
        - Move the robot in body memory
        - Move the previous experiences in egocentric_memory
        - Add new experiences in egocentric_memory
        - Move the robot in allocentric_memory
        """
        # self.egocentric_memory.maintain_focus(self.egocentric_memory.focus_point, enacted_enaction)
        self.egocentric_memory.focus_point = enacted_enaction.focus_point
        self.egocentric_memory.prompt_point = enacted_enaction.prompt_point
        # self.egocentric_memory.maintain_prompt(enacted_enaction)

        self.body_memory.set_head_direction_degree(enacted_enaction.head_angle)
        # TODO Keep the simulation and adjust the robot position
        # Translate the robot before applying the yaw
        self.allocentric_memory.move(self.body_memory.get_body_direction_rad(), enacted_enaction.translation,
                                     enacted_enaction.clock)
        # self.body_memory.rotate_degree(enacted_enaction.yaw, enacted_enaction.azimuth)
        self.body_memory.body_quaternion = enacted_enaction.body_quaternion

        self.egocentric_memory.update_and_add_experiences(enacted_enaction)

        # # TODO Keep the simulation and adjust the robot position
        # self.allocentric_memory.move(self.body_memory.body_direction_rad, enacted_interaction['translation'],
        #                              enacted_interaction['clock'])

        # The integrator may subsequently update the robot's position

    def update_allocentric(self, clock):
        """Update allocentric memory on the basis of body, phenomenon, and egocentric memory"""
        # Mark the cells where is the robot
        self.allocentric_memory.place_robot(self.body_memory, clock)

        # Mark the affordances
        self.allocentric_memory.update_affordances(self.phenomenon_memory.phenomena, clock)

        # Update the focus in allocentric memory
        allo_focus = self.egocentric_to_allocentric(self.egocentric_memory.focus_point)
        self.allocentric_memory.update_focus(allo_focus, clock)

        # Update the prompt in allocentric memory
        allo_prompt = self.egocentric_to_allocentric(self.egocentric_memory.prompt_point)
        self.allocentric_memory.update_prompt(allo_prompt, clock)

    def egocentric_to_allocentric(self, point):
        """Return the point in allocentric coordinates from the point in egocentric coordinates"""
        # Rotate the point by the body direction and add the body position
        if point is None:
            return None
        return matrix44.apply_to_vector(self.body_memory.body_direction_matrix(), point) \
            + self.allocentric_memory.robot_point

    def allocentric_to_egocentric(self, point):
        """Return the point in egocentric coordinates from the point in allocentric coordinates"""
        if point is None:
            return None
        # Subtract the body position
        ego_point = point - self.allocentric_memory.robot_point
        # Rotate the point by the opposite body direction using the transposed rotation matrix
        return matrix44.apply_to_vector(self.body_memory.body_direction_matrix().T, ego_point)

    def save(self):
        """Return a clone of memory for memory snapshot"""
        saved_memory = Memory()
        # Clone body memory
        saved_memory.body_memory = self.body_memory.save()
        # Clone egocentric memory
        saved_memory.egocentric_memory = self.egocentric_memory.save()
        # Clone allocentric memory
        saved_memory.allocentric_memory = self.allocentric_memory.save(saved_memory.egocentric_memory.experiences)
        # Clone phenomenon memory
        saved_memory.phenomenon_memory = self.phenomenon_memory.save(saved_memory.egocentric_memory.experiences)

        return saved_memory

    def is_near_terrain_origin(self):
        """Return True if the robot is near the origin of the terrain"""
        if TER in self.phenomenon_memory.phenomena:
            delta = self.phenomenon_memory.phenomena[TER].origin_point() - self.allocentric_memory.robot_point
            return np.linalg.norm(delta) < NEAR_HOME
        else:
            return False

    def simulate(self, intended_enaction, dt):
        """Simulate the enaction in memory. Return True during the simulation, and False when it ends"""
        # Check the target time
        intended_enaction.simulation_time += dt
        if intended_enaction.simulation_time > intended_enaction.simulation_duration:
            intended_enaction.simulation_time = 0.
            intended_enaction.simulation_step = SIMULATION_STEP_OFF
            return False

        # Simulate the displacement in egocentric memory
        translation_matrix = matrix44.create_from_translation(-intended_enaction.action.translation_speed * dt *
                                                              SIMULATION_TIME_RATIO)
        rotation_matrix = matrix44.create_from_z_rotation(intended_enaction.simulation_rotation_speed * dt)
        displacement_matrix = matrix44.multiply(rotation_matrix, translation_matrix)
        for experience in self.egocentric_memory.experiences.values():
            experience.displace(displacement_matrix)
        # Simulate the displacement of the focus and prompt
        if self.egocentric_memory.focus_point is not None:
            self.egocentric_memory.focus_point = matrix44.apply_to_vector(displacement_matrix,
                                                                            self.egocentric_memory.focus_point)
        if self.egocentric_memory.prompt_point is not None:
            self.egocentric_memory.prompt_point = matrix44.apply_to_vector(displacement_matrix,
                                                                             self.egocentric_memory.prompt_point)
        # Displacement in body memory
        # self.body_memory.body_direction_rad += intended_enaction.simulation_rotation_speed * dt
        self.body_memory.body_quaternion = quaternion.cross(self.body_memory.body_quaternion,
             quaternion.create_from_z_rotation((intended_enaction.simulation_rotation_speed * dt)))
        # Update allocentric memory
        self.allocentric_memory.robot_point += rotate_vector_z(intended_enaction.action.translation_speed * dt *
                                                                 SIMULATION_TIME_RATIO,
                                                                 self.body_memory.get_body_direction_rad())
        self.allocentric_memory.place_robot(self.body_memory, intended_enaction.clock)

        return True
