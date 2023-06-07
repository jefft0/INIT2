########################################################################################
# This agent makes the robot circle around an echo object or a territory delimited by a line
########################################################################################

import numpy as np
from . Action import ACTION_FORWARD, ACTION_SCAN
from . Interaction import Interaction, OUTCOME_DEFAULT
from . CompositeInteraction import CompositeInteraction
from . PredefinedInteractions import create_interactions, OUTCOME_LOST_FOCUS, OUTCOME_CLOSE_FRONT, \
    OUTCOME_FAR_FRONT, OUTCOME_FAR_LEFT, OUTCOME_LEFT, OUTCOME_RIGHT, OUTCOME_FAR_RIGHT, OUTCOME_FLOOR_LEFT, \
    OUTCOME_FLOOR_FRONT, OUTCOME_FLOOR_RIGHT, OUTCOME_IMPACT
from ..Robot.Enaction import Enaction


class DeciderCircle:
    def __init__(self, workspace):
        """ Creating our agent """
        self.workspace = workspace
        self.anticipated_outcome = None
        self.previous_interaction = None
        self.last_interaction = None

        # Load the predefined behavior
        self.procedural_memory = create_interactions(self.workspace.actions)
        self._action = self.workspace.actions[ACTION_FORWARD]

    def activation_level(self):
        """Return the activation level of this decider/ 1: default; 3 if focus object """
        activation_level = 1

        if self.workspace.memory.egocentric_memory.focus_point is not None:
            if np.linalg.norm(self.workspace.memory.egocentric_memory.focus_point) < 500:
                activation_level = 3
        return activation_level

    def propose_intended_enaction(self, enacted_interaction):
        """Propose the next intended enaction from the previous enacted interaction.
        This is the main method of the agent"""
        # Compute a specific outcome suited for this agent
        outcome = self.outcome(enacted_interaction)
        # Compute the intended enaction
        return self.intended_enaction(outcome)

    def intended_enaction(self, outcome):
        """Learning from the previous outcome and selecting the next enaction"""

        # Recording previous experience
        self.previous_interaction = self.last_interaction
        self.last_interaction = Interaction.create_or_retrieve(self._action, outcome)

        # Tracing the last interaction
        if self._action is not None:
            print("Action: " + str(self._action) +
                  ", Anticipation: " + str(self.anticipated_outcome) +
                  ", Outcome: " + str(outcome) +
                  ", Satisfaction: (anticipation: " + str(self.anticipated_outcome == outcome) +
                  ", valence: " + str(self.last_interaction.valence) + ")")

        # Learning or reinforcing the last composite interaction
        if self.previous_interaction is not None:
            composite_interaction = CompositeInteraction.create_or_reinforce(self.previous_interaction,
                                                                             self.last_interaction)
            self.procedural_memory.append(composite_interaction)

        # Selecting the next action to enact
        self._action = self.workspace.actions[ACTION_SCAN]  # Good for circling around object behavior
        # proclivity_dict = {}  # dict.fromkeys(ACTION_LIST, 0)
        # proclivity_dict = {ACTION_FORWARD: 0, ACTION_TURN_LEFT: 0, ACTION_TURN_RIGHT: 0} good for exploring terrain
        proclivity_dict = {self.workspace.actions[ACTION_FORWARD]: 0}  # Good for touring terrain
        if self.procedural_memory:
            activated_interactions = [ci for ci in self.procedural_memory if ci.pre_interaction == self.last_interaction]
            for ai in activated_interactions:
                if ai.post_interaction.action in proclivity_dict:
                    proclivity_dict[ai.post_interaction.action] += ai.weight * ai.post_interaction.valence
                else:
                    proclivity_dict[ai.post_interaction.action] = ai.weight * ai.post_interaction.valence

        # print("Proclivity dictionary:", proclivity_dict)
        # Select the action that has the highest proclivity value
        if proclivity_dict:
            # See https://pythonguides.com/python-find-max-value-in-a-dictionary/
            self._action = max(proclivity_dict, key=proclivity_dict.get)

        """ Computing the anticipation """
        # TODO compute the anticipated outcome
        self.anticipated_outcome = OUTCOME_DEFAULT

        # The intended enaction
        ii = Interaction.create_or_retrieve(self._action, self.anticipated_outcome)
        return Enaction(ii, self.workspace.clock, self.workspace.memory.egocentric_memory.focus_point, None)

    def outcome(self, enacted_interaction):
        """ Convert the enacted interaction into an outcome adapted to the circle behavior """
        outcome = OUTCOME_DEFAULT

        # If there is an echo, compute the echo outcome
        if 'echo_xy' in enacted_interaction:
            if enacted_interaction['echo_xy'][0] < 200:  # From the center of the robot
                outcome = OUTCOME_CLOSE_FRONT
            elif enacted_interaction['echo_xy'][0] > 500:  # Must be farther than the forward speed
                outcome = OUTCOME_FAR_FRONT
            elif enacted_interaction['echo_xy'][1] > 150:
                outcome = OUTCOME_FAR_LEFT  # More that 150 to the left
            elif enacted_interaction['echo_xy'][1] > 0:
                outcome = OUTCOME_LEFT      # between 0 and 150 to the left
            elif enacted_interaction['echo_xy'][1] > -150:
                outcome = OUTCOME_RIGHT     # Between 0 and -150 to the right
            else:
                outcome = OUTCOME_FAR_RIGHT  # More that -150 to the right

        if 'lost_focus' in enacted_interaction:
            outcome = OUTCOME_LOST_FOCUS

        # If impact then override the echo and focus outcome
        if 'impact' in enacted_interaction:
            if enacted_interaction['impact'] > 0:
                outcome = OUTCOME_IMPACT
        if 'blocked' in enacted_interaction:
            if enacted_interaction['blocked']:
                outcome = OUTCOME_IMPACT

        # If floor then override the echo and focus and impact outcome
        if 'floor' in enacted_interaction:
            if enacted_interaction['floor'] == 0b10:
                outcome = OUTCOME_FLOOR_LEFT
            if enacted_interaction['floor'] == 0b11:
                outcome = OUTCOME_FLOOR_FRONT
            if enacted_interaction['floor'] == 0b01:
                outcome = OUTCOME_FLOOR_RIGHT

        return outcome


# Testing AgentCircle
# py -m autocat.Decider.AgentCircle
if __name__ == "__main__":
    a = DeciderCircle()
    _outcome = OUTCOME_LOST_FOCUS

    for i in range(20):
        _intended_interaction = a.intended_interaction(_outcome)
        print("Action: ", _intended_interaction)
        _outcome = input("Enter outcome: ").upper()
        print(" Outcome: ", _outcome)
