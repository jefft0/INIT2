import numpy as np
import circle_fit as cf
from pyrr import Matrix44, Vector3, vector3
from ..Memory.EgocentricMemory.Experience import EXPERIENCE_NORTH, EXPERIENCE_COMPASS
from ..Proposer.Action import ACTION_FORWARD

RUNNING_WINDOW_AZIMUTH = 100
MAX_OFFSET_DISTANCE = 100
MIN_OFFSET_RADIUS = 130
MAX_OFFSET_RADIUS = 550  # 400
CALIBRATION_SPEED_WEIGHT = 10


def compass_calibration(points):
    """Return the tuple that represents the offset of the center of the circle defined by the points"""
    if points.shape[0] > 2:
        # Find the center of the circle made by the compass points
        try:
            xc, yc, r, sigma = cf.taubinSVD(points)
            # If the circle is in bounds and not too far off
            if MIN_OFFSET_RADIUS < r < MAX_OFFSET_RADIUS and np.linalg.norm([xc, yc]) < MAX_OFFSET_DISTANCE:
                print(f"Fit circle offset=({xc:.0f}, {yc:.0f}), radius= {r:.0f}, sigma= {sigma:.2f}")
                return round(xc), round(yc)
            else:
                print(f"Compass calibration failed. Radius out of bound: {r:.0f}, or too off-center")
        except ValueError as e:
            # All the points are at the same position
            print("Unable to compute circle:", e)
        except OverflowError as e:
            # All the points are aligned
            print("Unable to compute circle:", e)
    else:
        print(f"Compass calibration failed. Not enough points: {points.shape[0]}")
    return None


class Calibrator:
    def __init__(self, workspace):
        self.workspace = workspace

    def calibrate(self):
        """Run all the automatic calibration procedures"""
        self.calibrate_compass()
        self.calibrate_retreat()
        self.calibrate_forward_speed()

    def calibrate_compass(self):
        """Update the compass offset and the compass experiences"""
        points = np.array([e.point()[0: 2] for e in self.workspace.memory.egocentric_memory.experiences.values()
                           if e.clock >= self.workspace.memory.clock - RUNNING_WINDOW_AZIMUTH and
                           e.type == EXPERIENCE_NORTH])
        offset_2d = compass_calibration(points)
        if offset_2d is not None:
            print("Calibrate compass by", offset_2d, f"distance: {np.linalg.norm(offset_2d):.1f}")
            offset_point = np.array([*offset_2d, 0], dtype=int)
            self.workspace.memory.body_memory.compass_offset += offset_point
            offset_matrix = Matrix44.from_translation(-offset_point).astype('float64')
            for e in self.workspace.memory.egocentric_memory.experiences.values():
                if e.type in [EXPERIENCE_COMPASS, EXPERIENCE_NORTH]:
                    e.displace(offset_matrix)

    def calibrate_retreat(self):
        """Calibrate the retreat yaw """
        # Negative retreat yaw
        if self.workspace.enaction.outcome.floor in [1, 2]:
            # Right floor, negative retreat yaw
            if self.workspace.enaction.outcome.floor == 0b01:
                dif = self.workspace.enaction.outcome.yaw + self.workspace.memory.body_memory.retreat_yaw
                av = (- 0.3 * self.workspace.enaction.outcome.yaw + 0.7 * self.workspace.memory.body_memory.retreat_yaw)  #/2
            # Left floor, positive retreat yaw
            else:
                dif = self.workspace.enaction.outcome.yaw - self.workspace.memory.body_memory.retreat_yaw
                av = (0.3 * self.workspace.enaction.outcome.yaw + 0.7 * self.workspace.memory.body_memory.retreat_yaw)  # /2
            self.workspace.memory.body_memory.retreat_yaw = round(av)
            print(f"Calibrate withdraw yaw to: {av:.0f}, difference {dif:.1f}")

    def calibrate_forward_speed(self):
        """Calibrate the forward speed by adding the forward prediction error / 2"""
        # Assume that the translation lasted 1s
        self.workspace.actions[ACTION_FORWARD].translation_speed[0] += \
            self.workspace.memory.place_memory.forward_pe / CALIBRATION_SPEED_WEIGHT
        # print("Calibrate forward speed to", round(self.workspace.actions[ACTION_FORWARD].translation_speed[0]))
