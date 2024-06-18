# A place cell is defined by a point and contains the cues to recognize it

import numpy as np
from pyrr import Matrix44
from ..EgocentricMemory.EgocentricMemory import EXPERIENCE_FLOOR


class PlaceCell:
    def __init__(self, point, cues):
        """initialize the place cell from its point and its dictionary of cues"""
        self.point = point.copy()
        self.key = round(self.point[0]), round(self.point[1])
        self.cues = cues  # Dictionary of cues

    def __str__(self):
        """Return the string of the tuple of the place cell coordinates"""
        return self.key.__str__()

    def __hash__(self):
        """Return the hash to use place cells as nodes in networkx"""
        return hash(self.key)

    def recognize_vector(self, cues):
        """Return the vector of the position defined by previous cues minus the position by the new cues"""
        vector = np.array([0, 0, 0])
        # Assume FLOOR experiences come from a single point
        for new_cue in [cue for cue in cues.values() if cue.type == EXPERIENCE_FLOOR]:
            for previous_cue in [cue for cue in self.cues.values() if cue.type == EXPERIENCE_FLOOR]:
                vector = previous_cue.point() - new_cue.point()
        return vector

    # def add_cues(self, cues):
    #     """Compute a position correction, add the cues, and return the position correction"""
    #     position_correction = np.array([0, 0, 0])
    #     # Assume FLOOR experiences come from a single point
    #     for new_cue in [cue for cue in cues.values() if cue.type == EXPERIENCE_FLOOR]:
    #         for old_cue in [cue for cue in self.cues.values() if cue.type == EXPERIENCE_FLOOR]:
    #             position_correction = old_cue.point() - new_cue.point()
    #     position_correction_matrix = Matrix44.from_translation(position_correction)
    #     # shift the new cues
    #     for cue in cues.values():
    #         cue.pose_matrix @= position_correction_matrix
    #     self.cues.update(cues)
    #     return position_correction

    def save(self):
        """Return a cloned place cell for memory snapshot"""
        return PlaceCell(self.point, {key: c.save() for key, c in self.cues.items()})
