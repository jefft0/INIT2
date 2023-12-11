import math
import numpy as np
import time
from pyrr import matrix44, quaternion, Quaternion
from . import EMOTION_HAPPY, EMOTION_RELAXED, EMOTION_SAD, EMOTION_ANGRY, EMOTION_UPSET
from .EgocentricMemory.EgocentricMemory import EgocentricMemory
from .AllocentricMemory.AllocentricMemory import AllocentricMemory
from .BodyMemory import BodyMemory, EXCITATION_LOW, ENERGY_TIRED, point_to_echo_direction_distance
from .PhenomenonMemory.PhenomenonMemory import PhenomenonMemory, TER
from .PhenomenonMemory.PhenomenonTerrain import TERRAIN_INITIAL_CONFIDENCE, TERRAIN_ORIGIN_CONFIDENCE
from .AllocentricMemory.Hexagonal_geometry import CELL_RADIUS
from ..Decider.Action import ACTION_SWIPE
from ..Decider.Decider import FOCUS_TOO_FAR_DISTANCE, CONFIDENCE_CONFIRMED_FOCUS
from ..Robot.Outcome import Outcome

GRID_WIDTH = 20  # 15   # 100 Number of cells wide
GRID_HEIGHT = 60  # 45  # 200 Number of cells high
NEAR_HOME = 300    # (mm) Max distance to consider near home
SIMULATION_TIME_RATIO = 1  # 0.5   # The simulation speed is slower than the real speed because ...
# EMOTION_RELAXED = 1  # White
# EMOTION_HAPPY = 2  # Green
# EMOTION_SAD = 3  # Bleu
# EMOTION_ANGRY = 4  # Red
# EMOTION_UPSET = 5  # Orange (Can't arrange an object from where the robot is)
ARRANGE_MIN_RADIUS = 100
ARRANGE_MAX_RADIUS = 400


class Memory:
    """The Memory serves as the general container of the three memories:
        body memory, egocentric memory, and allocentric memory
    """

    def __init__(self, arena_id, robot_id):
        self.arena_id = arena_id
        self.robot_id = robot_id
        self.body_memory = BodyMemory(robot_id)
        self.egocentric_memory = EgocentricMemory()
        self.allocentric_memory = AllocentricMemory(GRID_WIDTH, GRID_HEIGHT, cell_radius=CELL_RADIUS)
        self.phenomenon_memory = PhenomenonMemory(arena_id)
        self.compass_prediction_error = {}  # Used to calibrate GYRO_COEF
        self.focus_direction_prediction_error = {}
        self.focus_distance_prediction_error = {}
        self.emotion_code = EMOTION_RELAXED

    def __str__(self):
        return "Memory Robot position (" + str(round(self.allocentric_memory.robot_point[0])) + "," +\
                                           str(round(self.allocentric_memory.robot_point[1])) + ")"

    def appraise_emotion(self):
        """Update the emotional state code"""
        # Search terrain origin: Robot HAPPY DeciderCircle
        if self.phenomenon_memory.terrain_confidence() < TERRAIN_ORIGIN_CONFIDENCE:
            self.emotion_code = EMOTION_HAPPY
        # Terrain origin has been found
        else:
            # High energy then must circle, explore, watch or arrange
            if self.body_memory.energy >= ENERGY_TIRED:
                # High excitation then must circle or explore
                if self.body_memory.excitation > EXCITATION_LOW:
                    # Focus inside terrain or not too far: HAPPY DeciderCircle
                    if self.egocentric_memory.focus_point is not None and \
                            np.linalg.norm(self.egocentric_memory.focus_point) < FOCUS_TOO_FAR_DISTANCE and \
                            not self.is_outside_terrain(self.egocentric_memory.focus_point):
                        self.emotion_code = EMOTION_HAPPY
                    # No interesting focus: RELAXED, DeciderExplore
                    else:
                        self.emotion_code = EMOTION_RELAXED
                else:
                    # High energy with low excitation, must watch or arrange
                    # if self.is_outside_terrain(self.egocentric_memory.focus_point):
                    if self.egocentric_memory.focus_point is None:
                        # Focus outside terrain or None then SAD, DeciderWatch
                        # No focus then SAD, DeciderWatch
                        self.emotion_code = EMOTION_SAD
                    # Focus is inside terrain
                    else:
                        # If object inside terrain and closer than target: ANGRY, DeciderPush
                        ego_target = self.terrain_centric_to_egocentric(self.phenomenon_memory.arrange_point())
                        is_to_arrange = self.is_to_arrange(self.egocentric_memory.focus_point)
                        # print("Ego focus", self.egocentric_memory.focus_point)
                        is_closer = self.egocentric_memory.focus_point[0] < ego_target[0] - ARRANGE_MIN_RADIUS
                        print("Focus near terrain center:", is_to_arrange, "Before terrain center:", is_closer,
                              "Other robot angry:", self.phenomenon_memory.other_robot_is_angry())
                        if is_to_arrange:
                            if is_closer and not self.phenomenon_memory.other_robot_is_angry():
                                # Object before center: ANGRY DeciderArrange
                                self.emotion_code = EMOTION_ANGRY
                            else:
                                # Object behind center: UPSET DeciderArrange
                                self.emotion_code = EMOTION_UPSET
                        else:
                            # Object too far from center: SAD DeciderWatch
                            self.emotion_code = EMOTION_SAD
            else:
                # Tired: Robot RELAXED, DeciderExplore to go home
                self.emotion_code = EMOTION_RELAXED

    def update_and_add_experiences(self, enaction):
        """ Process the enacted interaction to update the memory
        - Move the robot in body memory
        - Move the previous experiences in egocentric_memory
        - Add new experiences in egocentric_memory
        - Move the robot in allocentric_memory
        """
        self.egocentric_memory.focus_point = enaction.focus_point
        self.egocentric_memory.prompt_point = enaction.prompt_point

        # self.body_memory.set_head_direction_degree(enaction.outcome.head_angle)
        # TODO Keep the simulation and adjust the robot position
        # Translate the robot before applying the yaw
        # print("Robot relative translation", enaction.translation)
        self.allocentric_memory.move(self.body_memory.body_quaternion, enaction.translation, enaction.clock)
        # self.body_memory.body_quaternion = enaction.body_quaternion
        self.body_memory.update(enaction)

        # Track compass prediction error to calibrate gyro_coef is correct
        self.compass_prediction_error[enaction.clock] = enaction.body_direction_delta
        self.compass_prediction_error = {key: d for key, d in self.compass_prediction_error.items()
                                         if key > enaction.clock - 10}
        print("Prediction Error Compass (integrated azimuth - compass)=",
              round(math.degrees(enaction.body_direction_delta), 2), "Average:",
              round(math.degrees(np.mean(list(self.compass_prediction_error.values()))), 2), "std:",
              round(math.degrees(np.std(list(self.compass_prediction_error.values()))), 2))

        # If focus is confident then track its prediction error
        if enaction.focus_confidence >= CONFIDENCE_CONFIRMED_FOCUS:
            self.focus_direction_prediction_error[enaction.clock] = enaction.focus_direction_prediction_error
            self.focus_direction_prediction_error = {key: d for key, d in self.focus_direction_prediction_error.items()
                                                     if key > enaction.clock - 10}
            print("Prediction Error Focus (predicted - new direction)=", enaction.focus_direction_prediction_error,
                  "Average:", round(np.mean(list(self.focus_direction_prediction_error.values()))),
                  "std:", round(np.std(list(self.focus_direction_prediction_error.values()))))
            self.focus_distance_prediction_error[enaction.clock] = enaction.focus_distance_prediction_error
            self.focus_distance_prediction_error = {key: d for key, d in self.focus_distance_prediction_error.items()
                                                    if key > enaction.clock - 10}
            print("Prediction Error Focus (predicted - new distance)=", enaction.focus_distance_prediction_error,
                  "Average:", round(np.mean(list(self.focus_distance_prediction_error.values()))),
                  "std:", round(np.std(list(self.focus_distance_prediction_error.values()))))

        self.egocentric_memory.update_and_add_experiences(enaction)

        # The integrator may again update the robot's position

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

    def egocentric_to_polar_egocentric(self, point):
        """Convert the position of a point from egocentric to polar-egocentric reference"""
        if point is None:
            return None
        return quaternion.apply_to_vector(self.body_memory.body_quaternion, point)

    def egocentric_to_allocentric(self, point):
        """Return the point in allocentric from the point in egocentric reference"""
        if point is None:
            return None
        # convert to polar-egocentric and then add the position in allocentric memory
        return self.egocentric_to_polar_egocentric(point) + self.allocentric_memory.robot_point

    def polar_egocentric_to_egocentric(self, point):
        """Convert from polar-egocentric to egocentric references"""
        if point is None:
            return None
        # Rotate the point by the opposite body direction using the inverse body quaternion
        return quaternion.apply_to_vector(self.body_memory.body_quaternion.inverse, point)

    def allocentric_to_egocentric(self, point):
        """Return the point in egocentric coordinates from the point in allocentric coordinates"""
        if point is None:
            return None
        return self.polar_egocentric_to_egocentric(point - self.allocentric_memory.robot_point)

    def terrain_centric_to_egocentric(self, point):
        """Return the point in egocentric coordinates from the point in terrain-centric coordinates"""
        if point is None:
            return None
        if self.phenomenon_memory.terrain_confidence() >= TERRAIN_ORIGIN_CONFIDENCE:
            return self.allocentric_to_egocentric(point + self.phenomenon_memory.phenomena[TER].point)
        return self.allocentric_to_egocentric(point)

    def egocentric_to_terrain_centric(self, point):
        """Return the point in terrain egocentric coordinates from the point in egocentric coordinates"""
        if point is None:
            return None
        if self.phenomenon_memory.terrain_confidence() >= TERRAIN_ORIGIN_CONFIDENCE:
            return self.egocentric_to_allocentric(point) - self.phenomenon_memory.phenomena[TER].point
        return self.egocentric_to_allocentric(point)

    def terrain_centric_to_allocentric(self, point):
        """Return the point in allocentric coordinates from the point in terrain_centric"""
        if point is None:
            return None
        elif self.phenomenon_memory.terrain_confidence() >= TERRAIN_ORIGIN_CONFIDENCE:
            return point + self.phenomenon_memory.phenomena[TER].point
        else:
            return point

    def terrain_centric_robot_point(self):
        """Return the position of the robot relative to the terrain point"""
        if self.phenomenon_memory.terrain_confidence() >= TERRAIN_ORIGIN_CONFIDENCE:
            return self.allocentric_memory.robot_point - self.phenomenon_memory.phenomena[TER].point
        else:
            return self.allocentric_memory.robot_point

    def save(self):
        """Return a clone of memory for memory snapshot"""
        # start_time = time.time()
        saved_memory = Memory(self.phenomenon_memory.arena_id, self.robot_id)
        saved_memory.emotion_code = self.emotion_code
        # Clone body memory
        saved_memory.body_memory = self.body_memory.save()
        # Clone egocentric memory
        saved_memory.egocentric_memory = self.egocentric_memory.save()
        # Clone allocentric memory
        saved_memory.allocentric_memory = self.allocentric_memory.save()
        # Clone phenomenon memory
        saved_memory.phenomenon_memory = self.phenomenon_memory.save()
        saved_memory.compass_prediction_error = {key: d for key, d in self.compass_prediction_error.items()}
        saved_memory.focus_direction_prediction_error = {key: d for key, d in self.focus_direction_prediction_error.items()}
        saved_memory.focus_distance_prediction_error = {key: d for key, d in self.focus_distance_prediction_error.items()}
        # print("Save memory duration:", time.time() - start_time, "seconds")

        return saved_memory

    def is_to_arrange(self, ego_point):
        """Return True if the focus within 400mm of the terrain center"""
        # If no terrain origin then don't arrange object
        if self.phenomenon_memory.terrain_confidence() <= TERRAIN_INITIAL_CONFIDENCE:
            return False
        # If there is a terrain origin, check if the focus is around the terrain center
        else:
            terrain_point = self.egocentric_to_terrain_centric(ego_point)
            print("Focus in terrain-centric coordinates", terrain_point)
            return np.linalg.norm(terrain_point) < ARRANGE_MAX_RADIUS

    def is_outside_terrain(self, ego_point):
        """Return True if ego_point is not None and there is a terrain and ego_point is outside"""
        allo_point = self.egocentric_to_allocentric(ego_point)
        return self.phenomenon_memory.is_outside_terrain(allo_point)

    def is_near_terrain_origin(self):
        """Return True if the robot is near the origin of the terrain"""
        if TER in self.phenomenon_memory.phenomena:
            delta = self.phenomenon_memory.phenomena[TER].origin_point() - self.allocentric_memory.robot_point
            return np.linalg.norm(delta) < NEAR_HOME
        else:
            return False

    def simulate(self, enaction, dt):
        """Simulate the enaction in memory. Return True during the simulation, and False when it ends"""

        if enaction.is_simulating:

            # Check the target time
            enaction.simulation_time += dt
            if enaction.simulation_time >= enaction.simulation_duration:
                dt += enaction.simulation_duration - enaction.simulation_time  # Adjust to the exact duration
                enaction.is_simulating = False

            # The intermediate displacement
            yaw_quaternion = Quaternion.from_z_rotation((enaction.simulation_rotation_speed * dt))
            way = 1
            if enaction.action.action_code == ACTION_SWIPE and enaction.command.speed is not None and enaction.command.speed < 0:
                way = -1
            translation = enaction.action.translation_speed * dt * SIMULATION_TIME_RATIO * way
            yaw_matrix = matrix44.create_from_quaternion(yaw_quaternion)
            translation_matrix = matrix44.create_from_translation(-translation)
            displacement_matrix = matrix44.multiply(yaw_matrix, translation_matrix)

            # Simulate the displacement of experiences
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
            self.body_memory.body_quaternion = self.body_memory.body_quaternion.cross(yaw_quaternion)
            if self.egocentric_memory.focus_point is not None:
                # Simulate the head to focus alignment
                head_direction_degree, _ = point_to_echo_direction_distance(self.egocentric_memory.focus_point)
                self.body_memory.set_head_direction_degree(head_direction_degree)

            # Update allocentric memory
            self.allocentric_memory.robot_point += quaternion.apply_to_vector(self.body_memory.body_quaternion, translation)
            self.allocentric_memory.place_robot(self.body_memory, enaction.clock)

        # When the simulation is over, return the simulated outcome
        if enaction.is_simulating:
            return None
        else:
            if enaction.command.duration is None:
                duration1 = enaction.action.target_duration * 1000
            else:
                duration1 = enaction.command.duration
            # The yaw will be computed as if the robot had no imu
            return Outcome({"action": enaction.action.action_code, "clock": enaction.clock, "floor": 0,
                            "duration1": duration1, 'status': "I", 'head_angle': 0, 'echo_distance': 300})
