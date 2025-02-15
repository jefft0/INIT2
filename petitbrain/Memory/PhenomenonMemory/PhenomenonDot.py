import math
import numpy as np
from pyrr import Quaternion
from . import PHENOMENON_INITIAL_CONFIDENCE, PHENOMENON_ENCLOSED_CONFIDENCE, PHENOMENON_RECOGNIZABLE_CONFIDENCE
from ...Utils import short_angle
from .Phenomenon import PHENOMENON_DELTA
from ...Memory.BodyMemory import SEROTONIN
from ...Robot.RobotDefine import ROBOT_FLOOR_SENSOR_X
from ...Proposer.Action import ACTION_TURN, ACTION_FORWARD, ACTION_SWIPE
from ...Proposer.Interaction import OUTCOME_FLOOR, OUTCOME_FOCUS_FRONT


class PhenomenonDot:
    """A point that affords the same type of affordance from any direction"""
    def __init__(self, affordance):
        """Initialize the phenomenon using the first affordance"""
        self.confidence = PHENOMENON_INITIAL_CONFIDENCE
        self.phenomenon_type = affordance.type
        self.category = None  # Required because tested for push
        self.affordance_id = 0
        self.point = affordance.point.copy()
        affordance.point[:] = 0  # Array-wise reset in place
        self.affordances = {0: affordance}
        self.color = affordance.color_index

        self.position_pe = {}  # (mm) The distance between predicted position and measured position

    def __str__(self):
        return f"(Phenomenon type:{self.phenomenon_type})"

    def update(self, affordance):
        """Add a new affordance to this phenomenon and move the phenomenon to the position of this affordance"""
        if affordance.type == self.phenomenon_type and np.linalg.norm(self.point - affordance.point) < PHENOMENON_DELTA:
            offset = affordance.point - self.point
            # Shift the phenomenon to the point of the new affordance
            # self.shift(offset)  # Comment to assume that the dot is fixed
            # Add the new affordance
            affordance.point[:] = 0
            self.affordance_id += 1
            self.affordances[self.affordance_id] = affordance
            # Return the robot's position correction
            self.position_pe[affordance.clock] = np.linalg.norm(offset)
            return -offset  # Correct the robot's position based on the fixed dot
        else:
            return None

    def shift(self, offset):
        """Shift the phenomenon's point by the offset. Shift the affordances by the opposite"""
        self.point += offset
        print("Phenomenon offset", offset)
        for a in self.affordances.values():
            a.point -= offset

    def check(self):
        """If an affordances in every pi/2 then increase confidence to PHENOMENON_ENCLOSED_CONFIDENCE"""
        n = 4  # Number of quadrants
        affordances = {}
        for theta in np.linspace(0, 2 * math.pi, n):
            q = Quaternion.from_z_rotation(theta)
            for k, a in self.affordances.items():
                if abs(short_angle(Quaternion.from_z_rotation(math.atan2(a.point[1], a.point[0])), q)) < math.pi/n:
                    affordances[k] = a
                    # Keep only one affordance per quadrant
                    break
        if len(affordances) >= n:
            self.confidence = min(self.confidence, PHENOMENON_ENCLOSED_CONFIDENCE)
            self.affordances = affordances

    def category_clue(self):
        """If RECOGNIZABLE confidence then return the phenomenon type else return None"""
        if self.confidence >= PHENOMENON_RECOGNIZABLE_CONFIDENCE:
            return self.phenomenon_type
        else:
            return None

    def outline(self):
        """Return the terrain outline 2D points as list of integers"""
        # The affordance points must be integers
        return np.array([a.point[0:2] for a in self.affordances.values()]).flatten().tolist()

    def propose_interaction_code(self, memory, outcome_code):
        """Return the interaction code and updates the memory"""
        # If very playful and the dot is forward
        if memory.body_memory.neurotransmitters[SEROTONIN] > 55 and memory.egocentric_memory.focus_point[0] > \
                ROBOT_FLOOR_SENSOR_X:
            if abs(memory.egocentric_memory.focus_point[1]) < 20:
                # If in front then go to the dot
                return ACTION_FORWARD, OUTCOME_FLOOR
            elif abs(math.degrees(math.atan2(memory.egocentric_memory.focus_point[1],
                                             memory.egocentric_memory.focus_point[0]))) < 15:
                # If slightly in front then swipe
                return ACTION_SWIPE, OUTCOME_FOCUS_FRONT
            else:
                # If not in front then turn
                return ACTION_TURN, OUTCOME_FOCUS_FRONT

        # If mildly playful then turn around the dot
        if memory.egocentric_memory.focus_point[0] > ROBOT_FLOOR_SENSOR_X:
            # First enaction SWIPE in the direction of the focus
            if memory.egocentric_memory.focus_point[1] > 0:
                memory.egocentric_memory.prompt_point = None
            else:
                memory.egocentric_memory.prompt_point = np.array([0, -200, 0])
            return "STF"
        else:
            return "TF"

    def save(self):
        """Return a clone of the phenomenon for memory snapshot"""
        saved_phenomenon = PhenomenonDot(self.affordances[min(self.affordances)].save())
        saved_phenomenon.confidence = self.confidence
        saved_phenomenon.phenomenon_type = self.phenomenon_type
        saved_phenomenon.point[:] = self.point
        saved_phenomenon.affordances = {key: a.save() for key, a in self.affordances.items()}
        saved_phenomenon.affordance_id = self.affordance_id
        saved_phenomenon.color = self.color
        return saved_phenomenon
