########################################################################################
# This decider makes the robot explore the parts of the terrain that are not yet known
# Activation 0: default. 2: the terrain has an absolute reference
########################################################################################

import math
import numpy as np
from pyrr import quaternion, matrix44, Quaternion
from playsound import playsound
from . Action import ACTION_TURN, ACTION_FORWARD, ACTION_SWIPE, ACTION_RIGHTWARD
from . Interaction import OUTCOME_NO_FOCUS
from . Decider import Decider
from ..Robot.Enaction import Enaction
from ..Memory.BodyMemory import ENERGY_TIRED, EXCITATION_LOW
from ..Memory.PhenomenonMemory.PhenomenonMemory import TER
from ..Memory.PhenomenonMemory.PhenomenonTerrain import TERRAIN_ORIGIN_CONFIDENCE
from ..Enaction.CompositeEnaction import CompositeEnaction

CLOCK_TO_GO_HOME = 8  # Number of interactions before going home
OUTCOME_ORIGIN = "O"
OUTCOME_LEFT = "LO"
OUTCOME_RIGHT = "RO"
OUTCOME_FAR_LEFT = "FL"
OUTCOME_FAR_RIGHT = "FR"
OUTCOME_COLOR = "CL"


class DeciderExplore(Decider):
    def __init__(self, workspace):
        super().__init__(workspace)

        # point = np.array([-2000, 2000, 0])  # Begin with North West
        # point = np.array([-920, 770, 0])  # Begin with North West
        # self.prompt_points = [point]
        # # Visit 6 points from North West to south East every pi/6
        # self.nb_points = 6
        # rotation_matrix = matrix44.create_from_z_rotation(-math.pi/6)
        # for i in range(1, self.nb_points):
        #     point = matrix44.apply_to_vector(rotation_matrix, point)
        #     self.prompt_points.append(point)
        self.prompt_index = 0
        self.ter_prompt = None
        self.explore_angle_quaternion = Quaternion.from_z_rotation(math.pi / 3)
        self.action = "-"

    def activation_level(self):
        """The level of activation is 2 if the terrain has confidence and the robot is excited or low energy"""
        activation_level = 0
        # Activate when the terrain phenomenon has an absolute point
        if TER in self.workspace.memory.phenomenon_memory.phenomena:
            # if self.workspace.memory.phenomenon_memory.phenomena[TER].origin_point() is not None:
            if self.workspace.memory.phenomenon_memory.phenomena[TER].confidence >= TERRAIN_ORIGIN_CONFIDENCE:
                if self.workspace.memory.body_memory.energy < ENERGY_TIRED:
                    activation_level = 2
                if self.workspace.memory.body_memory.excitation >= EXCITATION_LOW:
                    activation_level = 2
        return activation_level

    def outcome(self, enaction):
        """ Convert the enacted interaction into an outcome adapted to the explore behavior """
        outcome = OUTCOME_NO_FOCUS

        # On startup return DEFAULT
        if enaction is None or enaction.outcome is None:
            return outcome

        # If color outcome
        if enaction.outcome.color_index > 0:
            outcome = OUTCOME_COLOR
            print("Outcome color")
            # The energy level is decreased by CtrlRobot
            # self.workspace.memory.body_memory.energy -= 10

        # Look for the floor experience
        if enaction.outcome.floor > 0 and enaction.outcome.color_index == 0:
            # If the floor is not colored then figure out if the robot is on the right or on the left
            if self.workspace.memory.phenomenon_memory.phenomena[TER].absolute_affordance() is not None:
                relative_quaternion = quaternion.cross(self.workspace.memory.body_memory.body_quaternion,
                                      quaternion.inverse(self.workspace.memory.phenomenon_memory.phenomena[TER].absolute_affordance().experience.body_direction_quaternion()))
                print("Relative quaternion", repr(relative_quaternion))
                if quaternion.rotation_angle(relative_quaternion) > math.pi:
                    relative_quaternion = - relative_quaternion  # The quaternion representing the short angle
                rot = quaternion.rotation_angle(relative_quaternion)
                print("Rotation from origin", round(math.degrees(rot)))
                if quaternion.rotation_axis(relative_quaternion)[2] > 0:  # Positive z axis rotation
                    if rot < math.pi/3:
                        print("OUTCOME Left of origin")
                        outcome = OUTCOME_LEFT
                    elif rot < math.pi:
                        print("OUTCOME Far Left of origin")
                        outcome = OUTCOME_FAR_LEFT
                else:
                    if rot < math.pi/3:
                        print("OUTCOME Right of origin")
                        outcome = OUTCOME_RIGHT
                    elif rot < math.pi:
                        print("OUTCOME Far Right of origin")
                        outcome = OUTCOME_FAR_RIGHT
        return outcome

    def select_enaction(self, outcome):
        """Return the next intended interaction"""
        # Tracing the last interaction
        if self.action is not None:
            print("Action: " + str(self.action) + ", Anticipation: " + str(self.anticipated_outcome) +
                  ", Outcome: " + str(outcome))

        # Compute the next prompt point

        # It is assumed that the terrain has been found if this decider is activated

        e1, e2 = None, None

        # If time to go home
        if self.workspace.memory.body_memory.energy < ENERGY_TIRED:
            # If right or left then swipe to home
            if outcome in [OUTCOME_LEFT, OUTCOME_RIGHT]:
                if outcome == OUTCOME_RIGHT:
                    ego_confirmation = np.array([0, 280, 0], dtype=int)  # Swipe to the right
                else:
                    ego_confirmation = np.array([0, -280, 0], dtype=int)
                print("Swiping to confirmation by:", ego_confirmation)
                self.action = self.workspace.actions[ACTION_SWIPE]
                self.workspace.memory.egocentric_memory.prompt_point = ego_confirmation
                e1 = Enaction(self.action, self.workspace.memory)
                playsound('autocat/Assets/R5.wav', False)
            # If not left or right we need to manoeuvre
            else:
                # If near home then go to confirmation prompt
                if self.workspace.memory.is_near_terrain_origin() or outcome == OUTCOME_COLOR:
                    polar_confirmation = self.workspace.memory.phenomenon_memory.phenomena[TER].confirmation_prompt()
                    print("Enacting confirmation sequence to", polar_confirmation)
                    ego_confirmation = self.workspace.memory.polar_egocentric_to_egocentric(polar_confirmation)
                    self.workspace.memory.egocentric_memory.prompt_point = ego_confirmation
                    playsound('autocat/Assets/R4.wav', False)
                else:
                    # If not near home then go to origin prompt
                    allo_origin = self.workspace.memory.phenomenon_memory.phenomena[TER].origin_point()
                    print("Going from", self.workspace.memory.allocentric_memory.robot_point, "to origin sensor point", allo_origin)
                    ego_origin = self.workspace.memory.allocentric_to_egocentric(allo_origin)
                    self.workspace.memory.egocentric_memory.prompt_point = ego_origin
                    playsound('autocat/Assets/R3.wav', False)
                self.workspace.memory.egocentric_memory.focus_point = None  # Prevent unnatural head movement
                self.action = self.workspace.actions[ACTION_TURN]
                e1 = Enaction(self.action, self.workspace.memory)
                e2 = Enaction(self.workspace.actions[ACTION_FORWARD], e1.post_memory)
        else:
            # Go to the most interesting pool point
            # mip = self.workspace.memory.allocentric_memory.most_interesting_pool(self.workspace.clock)
            # self.workspace.memory.egocentric_memory.prompt_point = self.workspace.memory.allocentric_to_egocentric(mip)

            # Go successively to the predefined prompt points relative to the terrain center
            if self.prompt_index == 0:
                self.ter_prompt = self.workspace.memory.phenomenon_memory.phenomena[TER].affordances[self.workspace.memory.phenomenon_memory.phenomena[TER].absolute_affordance_key].point * 1.2
            self.ter_prompt = quaternion.apply_to_vector(self.explore_angle_quaternion, self.ter_prompt)
            allo_prompt = self.ter_prompt + self.workspace.memory.phenomenon_memory.phenomena[TER].point
            ego_prompt = self.workspace.memory.allocentric_to_egocentric(allo_prompt)
            self.workspace.memory.egocentric_memory.prompt_point = ego_prompt
            self.workspace.memory.egocentric_memory.focus_point = None  # Prevent unnatural head movement
            self.prompt_index += 1
            # if self.prompt_index >= self.nb_points:
            #     self.prompt_index = 0
            self.action = self.workspace.actions[ACTION_TURN]
            e1 = Enaction(self.action, self.workspace.memory)
            e2 = Enaction(self.workspace.actions[ACTION_FORWARD], e1.post_memory)

        # Add the enactions to the stack
        enaction_sequence = [e1]
        if e2 is not None:
            enaction_sequence.append(e2)
        return CompositeEnaction(enaction_sequence)
