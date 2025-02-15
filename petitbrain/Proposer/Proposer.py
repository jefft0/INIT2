########################################################################################
# This proposer proposes the default behavior which makes the robot circle around objects
# Activation 2:
# EMOTION_PLEASURE: Dopamine
########################################################################################

import numpy as np
from . Action import ACTION_SCAN, ACTION_TURN, ACTION_SWIPE, ACTION_FORWARD
from . PredefinedInteractions import create_composite_interactions, create_or_reinforce_composite
from . Interaction import OUTCOME_FOCUS_TOO_FAR, OUTCOME_LOST_FOCUS
from ..Robot.Enaction import Enaction
from ..Enaction.CompositeEnaction import CompositeEnaction
from ..Proposer.Interaction import OUTCOME_PROMPT


class Proposer:
    """The parent class Decider generates the circle behavior"""
    def __init__(self, workspace):
        self.workspace = workspace
        self.previous_interaction = None
        self.last_interaction = None

        # Load the predefined behavior
        # self.primitive_interactions = create_primitive_interactions(self.workspace.actions)
        self.composite_interactions = create_composite_interactions(self.workspace.primitive_interactions)

        # The direction of translation
        self.direction = 1

    def propose_enaction(self):
        """Return a proposed interaction"""
        if self.workspace.enaction is None:
            i0 = self.workspace.primitive_interactions[(ACTION_FORWARD, OUTCOME_PROMPT)]
            e = Enaction(i0, self.workspace.memory.save())
            return CompositeEnaction([e], 'Default', np.array([0.5, 0, 0]))
        return self.select_enaction(self.workspace.enaction)

    def select_enaction(self, enaction):
        """Add the next enaction to the stack based on sequence learning and spatial modifiers"""

        # Call the sequence learning mechanism to select the next action
        action = self.select_action(enaction)
        e_memory = self.workspace.memory.save()
        # e_memory.emotion_code = EMOTION_PLEASURE
        span = 40

        # Set the spatial modifiers
        if action.action_code in [ACTION_TURN]:
            # Turn to the direction of the focus
            if enaction.outcome_code == OUTCOME_FOCUS_TOO_FAR or e_memory.egocentric_memory.focus_point is None:
                # If focus TOO FAR or None then turn around
                e_memory.egocentric_memory.prompt_point = np.array([-100, 0, 0], dtype=int)
            else:
                e_memory.egocentric_memory.prompt_point = self.workspace.memory.egocentric_memory.focus_point.copy()
        elif action.action_code in [ACTION_SWIPE]:
            # Swipe in the predefined direction
            e_memory.egocentric_memory.prompt_point = self.direction * action.translation_speed
        # If lost focus then scan carefully
        elif action.action_code in [ACTION_SCAN] and enaction.outcome_code == OUTCOME_LOST_FOCUS:
            span = 10
        else:
            e_memory.egocentric_memory.prompt_point = None

        # Add the enaction to the stack
        i0 = self.workspace.primitive_interactions[(action.action_code, OUTCOME_PROMPT)]
        e = Enaction(i0, e_memory, span=span)
        return CompositeEnaction([e], 'Default', np.array([0.5, 0, 0]))

    def select_action(self, enaction):
        """The sequence learning mechanism that proposes the next action"""
        # Recording previous interaction (call this decider every cycle to record every interaction
        self.previous_interaction = self.last_interaction
        self.last_interaction = self.workspace.primitive_interactions[(enaction.action.action_code, enaction.outcome_code)]

        # Tracing the last interaction
        print("Action: " + str(enaction.action) +
              ", Anticipation: " + str(enaction.predicted_outcome_code) +
              ", Outcome: " + str(enaction.outcome_code) +
              ", Satisfaction: (anticipation: " + str(enaction.predicted_outcome_code == enaction.outcome_code) +
              ", valence: " + str(self.last_interaction.valence) + ")")

        # Learning or reinforcing the last composite interaction
        if self.previous_interaction is not None:
            create_or_reinforce_composite(self.composite_interactions, self.previous_interaction, self.last_interaction)

        # Selecting the next action to enact
        # Initialize with the first action to select by default
        proclivity_dict = {self.workspace.actions[ACTION_FORWARD]: 1}  # Favors exploration
        # proclivity_dict = {self.workspace.actions[ACTION_SCAN]: 0}  # Favors staying in place
        if self.composite_interactions:
            activated_interactions = [ci for ci in self.composite_interactions if
                                      ci.pre_interaction == self.last_interaction]
            for ai in activated_interactions:
                # print("activated interaction", ai)
                if ai.post_interaction.action in proclivity_dict:
                    proclivity_dict[ai.post_interaction.action] += ai.weight * ai.post_interaction.valence
                else:
                    proclivity_dict[ai.post_interaction.action] = ai.weight * ai.post_interaction.valence
        # for k, v in proclivity_dict.items():
        #     print(k.__str__(), "proclivity", v)

        # Select the action that has the highest proclivity value
        return max(proclivity_dict, key=proclivity_dict.get)
