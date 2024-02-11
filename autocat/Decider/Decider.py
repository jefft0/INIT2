import math
import numpy as np
from . Action import ACTION_FORWARD, ACTION_SCAN
from . PredefinedInteractions import create_or_retrieve_primitive, create_primitive_interactions, \
    create_composite_interactions, create_or_reinforce_composite
from . Interaction import OUTCOME_NO_FOCUS, OUTCOME_FOCUS_TOO_FAR
from ..Integrator.OutcomeCode import outcome_code
from . Action import ACTION_TURN
from ..Robot.Enaction import Enaction
from ..Memory.Memory import EMOTION_HAPPY

# FOCUS_TOO_CLOSE_DISTANCE = 200   # (mm) Distance below which OUTCOME_FOCUS_TOO_CLOSE. From robot center
# FOCUS_FAR_DISTANCE = 400         # (mm) Distance beyond which OUTCOME_FOCUS_FAR. Must be farther than forward speed
# FOCUS_TOO_FAR_DISTANCE = 600     # (mm) Distance beyond which OUTCOME_FOCUS_TOO_FAR (The robot will get closer
# # FOCUS_TOO_TOO_FAR_DISTANCE = 1600   # (mm) Distance beyond which OUTCOME_FOCUS_TOO_FAR for Watch behavior
#                                  # Must detect something within too_too_far for touring the terrain
# FOCUS_SIDE_ANGLE = 3.14159 / 6.  # (rad) Angle beyond which OUTCOME_SIDE
# CONFIDENCE_NO_FOCUS = 0
# CONFIDENCE_NEW_FOCUS = 1
# CONFIDENCE_TOUCHED_FOCUS = 2
# CONFIDENCE_CAREFUL_SCAN = 3
# CONFIDENCE_CONFIRMED_FOCUS = 4


class Decider:
    def __init__(self, workspace):
        self.workspace = workspace
        self.action = self.workspace.actions[ACTION_FORWARD]
        self.anticipated_outcome = OUTCOME_NO_FOCUS
        self.previous_interaction = None
        self.last_interaction = None

        # Load the predefined behavior
        self.primitive_interactions = create_primitive_interactions(self.workspace.actions)
        self.composite_interactions = create_composite_interactions(self.workspace.actions, self.primitive_interactions)

    def activation_level(self):
        """Return the activation level of this decider/ 1: default; 3 if focus not too far and excited"""
        activation_level = 1  # Is the decider by default
        if self.workspace.memory.emotion_code == EMOTION_HAPPY:
            activation_level = 2
        return activation_level

    def stack_enaction(self):
        """Propose the next intended enaction from the previous enacted interaction.
        This is the main method of the agent"""
        # Compute a specific outcome suited for this agent from the previous enaction
        # outcome = self.outcome(self.workspace.enaction)
        outcome = outcome_code(self.workspace.memory, self.workspace.enaction)
        print("OUTCOME", outcome)
        # Compute the next enaction or composite enaction
        self.workspace.composite_enaction = self.select_enaction(outcome)

    def select_enaction(self, outcome):
        """Add the next enaction to the stack based on sequence learning and spatial modifiers"""

        # Call the sequence learning mechanism to select the next action
        self.select_action(outcome)

        # Set the spatial modifiers
        if self.action.action_code in [ACTION_TURN]:
            # Turn to the direction of the focus
            if outcome == OUTCOME_FOCUS_TOO_FAR or self.workspace.memory.egocentric_memory.focus_point is None:
                # If focus TOO FAR or None then turn around
                self.workspace.memory.egocentric_memory.prompt_point = np.array([-100, 0, 0], dtype=int)
            else:
                self.workspace.memory.egocentric_memory.prompt_point = \
                    self.workspace.memory.egocentric_memory.focus_point.copy()
        else:
            self.workspace.memory.egocentric_memory.prompt_point = None

        # Add the enaction to the stack
        return Enaction(self.action, self.workspace.memory)

    # def outcome(self, enaction):
    #     """ Convert the enacted interaction into an outcome adapted to the circle behavior """
    #     outcome = OUTCOME_NO_FOCUS
    #
    #     # On startup return NO_FOCUS
    #     if enaction is None:
    #         return outcome
    #
    #     # If there is a focus point, compute the focus outcome (focus may come from echo or from impact)
    #     if enaction.trajectory.focus_point is not None:
    #         focus_radius = np.linalg.norm(enaction.trajectory.focus_point)  # From the center of the robot
    #         # If focus is TOO FAR then DeciderCircle won't go after it
    #         if focus_radius > FOCUS_TOO_FAR_DISTANCE:  # self.too_far:  # Different for DeciderCircle or DeciderWatch
    #             outcome = OUTCOME_FOCUS_TOO_FAR
    #         # If the terrain is confident and the focus is outside then it is considered TOO FAR
    #         elif self.workspace.memory.is_outside_terrain(enaction.trajectory.focus_point):
    #             outcome = OUTCOME_FOCUS_TOO_FAR
    #         # Focus FAR: DeciderCircle will move closer
    #         elif focus_radius > FOCUS_FAR_DISTANCE:
    #             outcome = OUTCOME_FOCUS_FAR
    #         # Not TOO CLOSE and not TOO FAR: check if its on the SIDE
    #         elif focus_radius > FOCUS_TOO_CLOSE_DISTANCE:
    #             focus_theta = math.atan2(enaction.trajectory.focus_point[1], enaction.trajectory.focus_point[0])
    #             if math.fabs(focus_theta) < FOCUS_SIDE_ANGLE:
    #                 outcome = OUTCOME_FOCUS_FRONT
    #             else:
    #                 outcome = OUTCOME_FOCUS_SIDE
    #         # Focus TOO CLOSE: DeciderCircle and DeciderWatch will move backward
    #         else:
    #             outcome = OUTCOME_FOCUS_TOO_CLOSE
    #
    #     # LOST FOCUS: DeciderCircle and DeciderArrange will scan again
    #     if enaction.trajectory.focus_confidence <= CONFIDENCE_NEW_FOCUS:  # enaction.lost_focus:
    #         outcome = OUTCOME_LOST_FOCUS
    #
    #     # If TOUCH then override the focus outcome
    #     if enaction.outcome.touch:
    #         outcome = OUTCOME_TOUCH
    #
    #     # If FLOOR then override other outcome
    #     if enaction.outcome.floor > 0 or enaction.outcome.impact > 0:  # TODO Test impact
    #         outcome = OUTCOME_FLOOR
    #
    #     return outcome

    def select_action(self, outcome):
        """The sequence learning mechanism that proposes the next action"""
        # Recording previous interaction
        self.previous_interaction = self.last_interaction
        self.last_interaction = create_or_retrieve_primitive(self.primitive_interactions, self.action, outcome)

        # Tracing the last interaction
        if self.action is not None:
            print("Action: " + str(self.action) +
                  ", Anticipation: " + str(self.anticipated_outcome) +
                  ", Outcome: " + str(outcome) +
                  ", Satisfaction: (anticipation: " + str(self.anticipated_outcome == outcome) +
                  ", valence: " + str(self.last_interaction.valence) + ")")

        # Learning or reinforcing the last composite interaction
        if self.previous_interaction is not None:
            create_or_reinforce_composite(self.composite_interactions, self.previous_interaction, self.last_interaction)

        # Selecting the next action to enact
        # Initialize with the first action to select by default
        proclivity_dict = {self.workspace.actions[ACTION_SCAN]: 0}
        if self.composite_interactions:
            activated_interactions = [ci for ci in self.composite_interactions if ci.pre_interaction == self.last_interaction]
            for ai in activated_interactions:
                # print("activated interaction", ai)
                if ai.post_interaction.action in proclivity_dict:
                    proclivity_dict[ai.post_interaction.action] += ai.weight * ai.post_interaction.valence
                else:
                    proclivity_dict[ai.post_interaction.action] = ai.weight * ai.post_interaction.valence
        # for k, v in proclivity_dict.items():
        #     print(k.__str__(), "proclivity", v)

        # Select the action that has the highest proclivity value
        if proclivity_dict:
            # See https://pythonguides.com/python-find-max-value-in-a-dictionary/
            self.action = max(proclivity_dict, key=proclivity_dict.get)
