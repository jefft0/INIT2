from . Interaction import Interaction, OUTCOME_DEFAULT
from . CompositeInteraction import CompositeInteraction
from . Action import ACTION_FORWARD, ACTION_BACKWARD, ACTION_SWIPE, ACTION_RIGHTWARD, ACTION_TURN, \
    ACTION_TURN_RIGHT, ACTION_SCAN, ACTION_WATCH

# Circle object outcome

OUTCOME_LOST_FOCUS = 'L'
OUTCOME_FAR_FRONT = 'F'
OUTCOME_CLOSE_FRONT = 'C'
OUTCOME_LEFT = '4'
OUTCOME_RIGHT = '6'
OUTCOME_NEARBY = 'N'
OUTCOME_FAR_LEFT = '1'
OUTCOME_FAR_RIGHT = '3'

OUTCOME_LIST = [OUTCOME_LOST_FOCUS, OUTCOME_FAR_FRONT, OUTCOME_CLOSE_FRONT, OUTCOME_LEFT, OUTCOME_RIGHT,
                OUTCOME_FAR_LEFT, OUTCOME_FAR_RIGHT, OUTCOME_NEARBY]

OUTCOME_FLOOR_LEFT = '10'
OUTCOME_FLOOR_FRONT = '11'
OUTCOME_FLOOR_RIGHT = '01'


def create_interactions(actions):
    """Create the interactions needed by AgentCircle"""

    # Create all the primitive interactions
    for a in actions.values():
        for o in OUTCOME_LIST:
            Interaction.create_or_retrieve(a, o)

    # Predefined behaviors used by DeciderCircle

    # When lost focus then scan
    i_4 = Interaction.create_or_retrieve(actions[ACTION_SCAN], OUTCOME_LEFT, 1)
    i_l = Interaction.create_or_retrieve(actions[ACTION_SCAN], OUTCOME_LOST_FOCUS, 1)
    for interaction in Interaction.interaction_list:
        if interaction != i_l and interaction.outcome in [OUTCOME_LOST_FOCUS]:
            CompositeInteraction.create_or_retrieve(interaction, i_4)

    # When scan and lost focus then turn left
    i14 = Interaction.create_or_retrieve(actions[ACTION_TURN], OUTCOME_LEFT, 1)
    CompositeInteraction.create_or_retrieve(i_l, i14)

    # When focus is LEFT or RIGHT then swipe right
    i44 = Interaction.create_or_retrieve(actions[ACTION_SWIPE], OUTCOME_LEFT, 1)
    for interaction in Interaction.interaction_list:
        if interaction.outcome in [OUTCOME_LEFT, OUTCOME_RIGHT]:
            CompositeInteraction.create_or_retrieve(interaction, i44)

    # When outcome NEARBY then WATCH
    iw = Interaction.create_or_retrieve(actions[ACTION_WATCH], OUTCOME_NEARBY, 1)
    for interaction in Interaction.interaction_list:
        if interaction.outcome in [OUTCOME_NEARBY]:
            CompositeInteraction.create_or_retrieve(interaction, iw)

    # When FAR FRONT then forward
    i84 = Interaction.create_or_retrieve(actions[ACTION_FORWARD], OUTCOME_LEFT, 1)
    for interaction in Interaction.interaction_list:
        if interaction.outcome == OUTCOME_FAR_FRONT:
            CompositeInteraction.create_or_retrieve(interaction, i84)

    # When close LEFT or RIGHT then backward
    i24 = Interaction.create_or_retrieve(actions[ACTION_BACKWARD], OUTCOME_LEFT, 1)
    for interaction in Interaction.interaction_list:
        if interaction.outcome == OUTCOME_CLOSE_FRONT:
            CompositeInteraction.create_or_retrieve(interaction, i24)

    # When FAR LEFT or RIGHT then turn
    for interaction in Interaction.interaction_list:
        if interaction.outcome in [OUTCOME_FAR_LEFT, OUTCOME_FAR_RIGHT]:
            CompositeInteraction.create_or_retrieve(interaction, i14)

    # When FAR RIGHT then turn right
    # i34 = Interaction.create_or_retrieve(actions[ACTION_TURN_RIGHT], OUTCOME_LEFT, 1)
    # for interaction in Interaction.interaction_list:
    #     if interaction.outcome == OUTCOME_FAR_RIGHT:
    #         CompositeInteraction.create_or_retrieve(interaction, i34)

    # When impact then scan
    # for interaction in Interaction.interaction_list:
    #     if interaction.outcome == OUTCOME_FAR_RIGHT:
    #         CompositeInteraction.create_or_retrieve(interaction, i34)

    ##################################
    # Trespassing outcome

    # Valence of trespassing interactions
    i80 = Interaction.create_or_retrieve(actions[ACTION_FORWARD], OUTCOME_DEFAULT, 4)
    i810 = Interaction.create_or_retrieve(actions[ACTION_FORWARD], OUTCOME_FLOOR_LEFT, -2)
    i811 = Interaction.create_or_retrieve(actions[ACTION_FORWARD], OUTCOME_FLOOR_FRONT, -2)
    i801 = Interaction.create_or_retrieve(actions[ACTION_FORWARD], OUTCOME_FLOOR_RIGHT, -2)

    i40 = Interaction.create_or_retrieve(actions[ACTION_SWIPE], OUTCOME_DEFAULT, 1)
    i410 = Interaction.create_or_retrieve(actions[ACTION_SWIPE], OUTCOME_FLOOR_LEFT, -1)
    i411 = Interaction.create_or_retrieve(actions[ACTION_SWIPE], OUTCOME_FLOOR_FRONT, -1)
    i401 = Interaction.create_or_retrieve(actions[ACTION_SWIPE], OUTCOME_FLOOR_RIGHT, -1)

    i60 = Interaction.create_or_retrieve(actions[ACTION_RIGHTWARD], OUTCOME_DEFAULT, 1)
    i610 = Interaction.create_or_retrieve(actions[ACTION_RIGHTWARD], OUTCOME_FLOOR_LEFT, -1)
    i611 = Interaction.create_or_retrieve(actions[ACTION_RIGHTWARD], OUTCOME_FLOOR_FRONT, -1)
    i601 = Interaction.create_or_retrieve(actions[ACTION_RIGHTWARD], OUTCOME_FLOOR_RIGHT, -1)

    i10 = Interaction.create_or_retrieve(actions[ACTION_TURN], OUTCOME_DEFAULT, -1)
    i110 = Interaction.create_or_retrieve(actions[ACTION_TURN], OUTCOME_FLOOR_LEFT, -1)
    i111 = Interaction.create_or_retrieve(actions[ACTION_TURN], OUTCOME_FLOOR_FRONT, -1)
    i101 = Interaction.create_or_retrieve(actions[ACTION_TURN], OUTCOME_FLOOR_RIGHT, -1)

    # i30 = Interaction.create_or_retrieve(actions[ACTION_TURN_RIGHT], OUTCOME_DEFAULT, -2)
    # i310 = Interaction.create_or_retrieve(actions[ACTION_TURN_RIGHT], OUTCOME_FLOOR_LEFT, -2)
    # i311 = Interaction.create_or_retrieve(actions[ACTION_TURN_RIGHT], OUTCOME_FLOOR_FRONT, -2)
    # i301 = Interaction.create_or_retrieve(actions[ACTION_TURN_RIGHT], OUTCOME_FLOOR_RIGHT, -2)

    # When FLOOR then SWIPE left
    for interaction in Interaction.interaction_list:
        if interaction.outcome in [OUTCOME_FLOOR_LEFT, OUTCOME_FLOOR_FRONT, OUTCOME_FLOOR_RIGHT]:
            CompositeInteraction.create_or_retrieve(interaction, i40)

    return CompositeInteraction.composite_interaction_list
