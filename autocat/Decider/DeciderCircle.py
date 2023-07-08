########################################################################################
# This decider makes the robot circle around an echo object or a territory delimited by a line
# Activation 1: default. 3: focus
########################################################################################

import numpy as np
from . Action import ACTION_FORWARD, ACTION_TURN_RIGHT, ACTION_TURN
from . Interaction import Interaction, OUTCOME_DEFAULT
from . CompositeInteraction import CompositeInteraction
from . PredefinedInteractions import create_interactions, OUTCOME_LOST_FOCUS, OUTCOME_CLOSE_FRONT, \
    OUTCOME_FAR_FRONT, OUTCOME_FAR_LEFT, OUTCOME_LEFT, OUTCOME_RIGHT, OUTCOME_FAR_RIGHT, OUTCOME_FLOOR_LEFT, \
    OUTCOME_FLOOR_FRONT, OUTCOME_FLOOR_RIGHT
from ..Robot.Enaction import Enaction
from . Decider import Decider


class DeciderCircle(Decider):
    def __init__(self, workspace):
        """ Creating our agent """
        super().__init__(workspace)

        # Load the predefined behavior
        self.procedural_memory = create_interactions(self.workspace.actions)
        self.action = self.workspace.actions[ACTION_FORWARD]

    def activation_level(self):
        """Return the activation level of this decider/ 1: default; 3 if focus object """
        activation_level = 1

        if self.workspace.memory.egocentric_memory.focus_point is not None:
            if np.linalg.norm(self.workspace.memory.egocentric_memory.focus_point) < 500:
                activation_level = 3
        return activation_level

    def intended_enaction(self, outcome):
        """Learning from the previous outcome and selecting the next enaction"""

        self.propose_action(outcome)

        # # Recording previous interaction
        # self.previous_interaction = self.last_interaction
        # self.last_interaction = Interaction.create_or_retrieve(self.action, outcome)
        #
        # # Tracing the last interaction
        # if self.action is not None:
        #     print("Action: " + str(self.action) +
        #           ", Anticipation: " + str(self.anticipated_outcome) +
        #           ", Outcome: " + str(outcome) +
        #           ", Satisfaction: (anticipation: " + str(self.anticipated_outcome == outcome) +
        #           ", valence: " + str(self.last_interaction.valence) + ")")
        #
        # # Learning or reinforcing the last composite interaction
        # if self.previous_interaction is not None:
        #     composite_interaction = CompositeInteraction.create_or_reinforce(self.previous_interaction,
        #                                                                      self.last_interaction)
        #     self.procedural_memory.append(composite_interaction)
        #
        # # Selecting the next action to enact
        # self.action = self.workspace.actions[ACTION_SCAN]  # Good for circling around object behavior
        # # proclivity_dict = {}  # dict.fromkeys(ACTION_LIST, 0)
        # # proclivity_dict = {ACTION_FORWARD: 0, ACTION_TURN_LEFT: 0, ACTION_TURN_RIGHT: 0} good for exploring terrain
        # proclivity_dict = {self.workspace.actions[ACTION_FORWARD]: 0}  # Good for touring terrain
        # if self.procedural_memory:
        #     activated_interactions = [ci for ci in self.procedural_memory if ci.pre_interaction == self.last_interaction]
        #     for ai in activated_interactions:
        #         if ai.post_interaction.action in proclivity_dict:
        #             proclivity_dict[ai.post_interaction.action] += ai.weight * ai.post_interaction.valence
        #         else:
        #             proclivity_dict[ai.post_interaction.action] = ai.weight * ai.post_interaction.valence
        #
        # # print("Proclivity dictionary:", proclivity_dict)
        # # Select the action that has the highest proclivity value
        # if proclivity_dict:
        #     # See https://pythonguides.com/python-find-max-value-in-a-dictionary/
        #     self.action = max(proclivity_dict, key=proclivity_dict.get)
        #
        # # TODO compute the anticipated outcome
        # self.anticipated_outcome = OUTCOME_DEFAULT
        # ii = Interaction.create_or_retrieve(self.action, self.anticipated_outcome)

        # Adjust the spatial attributes
        if self.action.action_code in [ACTION_TURN]:  #, ACTION_TURN_RIGHT]:
            # self.action = self.workspace.actions[ACTION_TURN]
            self.workspace.memory.egocentric_memory.prompt_point = self.workspace.memory.egocentric_memory.focus_point.copy()
        else:
            self.workspace.memory.egocentric_memory.prompt_point = None  # Remove possible prompt set by another decider
        # Add the enaction to the stack
        self.workspace.enactions[self.workspace.clock] = Enaction(self.action, self.workspace.clock)

    def outcome(self, enacted_enaction):
        """ Convert the enacted interaction into an outcome adapted to the circle behavior """
        outcome = OUTCOME_DEFAULT

        # On startup return DEFAULT
        if enacted_enaction is None:
            return outcome

        # If there is a focus point, compute the echo outcome (focus may come from echo or from impact)
        if enacted_enaction.focus_point is not None:
            if np.linalg.norm(enacted_enaction.focus_point) < 200:  # From the center of the robot
                outcome = OUTCOME_CLOSE_FRONT
            elif np.linalg.norm(enacted_enaction.focus_point) > 400:  # Must be farther than the forward speed
                outcome = OUTCOME_FAR_FRONT
            elif enacted_enaction.focus_point[1] > 150:
                outcome = OUTCOME_FAR_LEFT  # More that 150 to the left
            elif enacted_enaction.focus_point[1] > 0:
                outcome = OUTCOME_LEFT      # between 0 and 150 to the left
            elif enacted_enaction.focus_point[1] > -150:
                outcome = OUTCOME_RIGHT     # Between 0 and -150 to the right
            else:
                outcome = OUTCOME_FAR_RIGHT  # More that -150 to the right

        if enacted_enaction.lost_focus:
            outcome = OUTCOME_LOST_FOCUS

        # If floor then override the focus outcome
        if enacted_enaction.outcome.floor > 0:
            if enacted_enaction.outcome.floor == 0b10:
                outcome = OUTCOME_FLOOR_LEFT
            if enacted_enaction.outcome.floor == 0b11:
                outcome = OUTCOME_FLOOR_FRONT
            if enacted_enaction.outcome.floor == 0b01:
                outcome = OUTCOME_FLOOR_RIGHT

        return outcome
