# A place cell is defined by a point and contains the cues to recognize it
import math
import numpy as np
import time
from pyrr import Quaternion, Matrix44
from . import ANGULAR_RESOLUTION
from ..EgocentricMemory.EgocentricMemory import EXPERIENCE_FLOOR, EXPERIENCE_ALIGNED_ECHO, EXPERIENCE_CENTRAL_ECHO, \
    EXPERIENCE_LOCAL_ECHO
from ...Utils import quaternion_translation_to_matrix, polar_to_cartesian, quaternion_to_direction_rad
from .PlaceGeometry import transform_estimation_cue_to_cue, point_to_polar_array, resample_by_diff
from .Cue import Cue


class PlaceCell:
    def __init__(self, point, cues):
        """initialize the place cell from its point and list of cues"""
        self.point = point.copy()
        self.key = round(self.point[0]), round(self.point[1])
        self.cues = cues  # List of cues
        self.polar_echo_curve = np.linspace([0, 0], [0, 2 * math.pi], 360 // ANGULAR_RESOLUTION, dtype=float)
        self.cartesian_echo_curve = np.empty((360 // ANGULAR_RESOLUTION, 3), dtype=float)

    def __str__(self):
        """Return the string of the tuple of the place cell coordinates"""
        return self.key.__str__()

    def __hash__(self):
        """Return the hash to use place cells as nodes in networkx"""
        return hash(self.key)

    def translation_estimation(self, cues):
        """Return the vector of the position defined by previous cues minus the position by the new cues"""
        translation = np.array([0, 0, 0])

        # Translation estimation based on echoes
        place_echo_cues = [c.point() for c in self.cues if c.type in [EXPERIENCE_ALIGNED_ECHO, EXPERIENCE_CENTRAL_ECHO]]
        new_echo_cues = [c.point() for c in cues if c.type in [EXPERIENCE_ALIGNED_ECHO, EXPERIENCE_CENTRAL_ECHO]]
        if len(place_echo_cues) > 0 and len(new_echo_cues) > 0:
            transform = transform_estimation_cue_to_cue(place_echo_cues, new_echo_cues)
            translation = -transform[:3, 3]
            r = math.degrees(quaternion_to_direction_rad(Quaternion.from_matrix(transform[:3, :3])))
            print(f"Place cell rotation: {r:.0f} degree")
            # If rotation too high then cancel the position correction
            if abs(r) > 10:
                translation[:] = 0

        # Assume FLOOR experiences come from a single point
        for new_cue in [cue for cue in cues if cue.type == EXPERIENCE_FLOOR]:
            for previous_cue in [cue for cue in self.cues if cue.type == EXPERIENCE_FLOOR]:
                translation = previous_cue.point() - new_cue.point()
        return translation

    def compute_echo_curve(self):
        """Compute the curve of echoes in polar coordinates"""
        start_time = time.time()
        # Takes almost 300ms to compute 360 points
        # echo_cues = [cartesian_to_polar(cue.point()) for cue in self.cues if cue.type
        #              in [EXPERIENCE_ALIGNED_ECHO, EXPERIENCE_CENTRAL_ECHO, EXPERIENCE_LOCAL_ECHO]]
        # for i in range(0, 360 // ANGULAR_RESOLUTION):
        #     r, theta = 0, math.radians(i * ANGULAR_RESOLUTION)
        #     for r_cue, t_cue in echo_cues:
        #         if r_cue > r and assert_almost_equal_angles(t_cue, theta, 25):
        #             r = r_cue
        #     self.polar_echo_curve[i, :] = [r, theta]

        echo_cues = [cue for cue in self.cues if cue.type in [EXPERIENCE_ALIGNED_ECHO, EXPERIENCE_CENTRAL_ECHO,
                                                              EXPERIENCE_LOCAL_ECHO]]
        a = np.empty((360 // ANGULAR_RESOLUTION, len(echo_cues)), dtype=float)
        for i, c in enumerate(echo_cues):
            a[:, i] = point_to_polar_array(c.point())
        self.polar_echo_curve[:, 0] = a.max(axis=1)
        print(f"Cue curve time: {time.time() - start_time:.3f}")

        # Recompute the central echoes
        self.cues = [c for c in self.cues if c.type != EXPERIENCE_CENTRAL_ECHO]
        diff_points = resample_by_diff(self.polar_echo_curve, 50, math.radians(50))
        for r, theta in diff_points:
            pose_matrix = quaternion_translation_to_matrix(Quaternion.from_z_rotation(theta), [r, 0, 0])
            cue = Cue(0, pose_matrix, EXPERIENCE_CENTRAL_ECHO, 0, 0, [0, 0, 0])
            print(f"Central {cue}, r: {r:.0f}, theta {math.degrees(theta):.0f}")
            self.cues.append(cue)

        self.cartesian_echo_curve[:] = polar_to_cartesian(self.polar_echo_curve)

    def save(self):
        """Return a cloned place cell for memory snapshot"""
        saved_place_cell = PlaceCell(self.point, [cue.save() for cue in self.cues])
        saved_place_cell.polar_echo_curve[:] = self.polar_echo_curve
        saved_place_cell.cartesian_echo_curve[:] = self.cartesian_echo_curve
        return saved_place_cell
