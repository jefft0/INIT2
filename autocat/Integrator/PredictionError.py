import math
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import os
from pyrr import Quaternion
from ..Decider.Action import ACTION_FORWARD
from ..Utils import short_angle, point_to_head_direction_distance
from ..Integrator.OutcomeCode import CONFIDENCE_CONFIRMED_FOCUS

PREDICTION_ERROR_WINDOW = 100


def plot(data_dict, caption, file_name):
    """Plot the values in this dictionary"""
    point_x = list(data_dict.keys())
    point_y = list(data_dict.values())

    # Create the figure
    plt.figure(figsize=(6, 3))
    # Set plot properties
    plt.title(caption)
    plt.xlabel('Clock')
    plt.ylabel('Prediction error')
    plt.axhline(0, color='black', linewidth=0.5)
    # plt.axvline(0, color='black', linewidth=0.5)
    plt.grid(color='gray', linestyle='--', linewidth=0.5)
    # plt.legend()
    # plt.axis('equal')  # Ensure equal scaling of axes

    # The points
    plt.plot(point_x, point_y, marker='o', linestyle='-', color='b', label=None)

    # Show the plot
    # plt.ion()
    # plt.draw()
    # plt.show()
    # plt.pause(1)
    plt.savefig("log/" + file_name + ".pdf")
    plt.close()


class PredictionError:
    def __init__(self, workspace):
        """Initialize the prediction error arrays"""
        self.workspace = workspace
        self.forward_duration1 = {}  # (s)
        self.yaw = {}  # (degree)
        self.compass = {}  # (degree)
        self.echo_direction = {}  # (degree)
        self.echo_distance = {}  # (mm)
        self.focus_direction = {}  # (degree)
        self.focus_distance = {}  # (mm)

    def log(self, enaction):
        """Compute the prediction errors: computed - actual"""
        computed_outcome = enaction.predicted_outcome
        actual_outcome = enaction.outcome

        # Translation FORWARD duration1

        if enaction.action.action_code in [ACTION_FORWARD] and actual_outcome.duration1 != 0:
            pe = (computed_outcome.duration1 - actual_outcome.duration1) / 1000  # / actual_outcome.duration1
            self.forward_duration1[enaction.clock] = pe
            self.forward_duration1.pop(actual_outcome.clock - PREDICTION_ERROR_WINDOW, None)
            print("Prediction Error Translate duration1 (simulation - measured)=", round(pe),
                  "Average:", round(float(np.mean(list(self.forward_duration1.values())))),
                  "std:", round(float(np.std(list(self.forward_duration1.values())))))
        # yaw

        # pe = math.degrees(-short_angle(enaction.command.intended_yaw_quaternion, enaction.yaw_quaternion))
        pe = math.degrees(-short_angle(Quaternion.from_z_rotation(math.radians(computed_outcome.yaw)),
                                       enaction.trajectory.yaw_quaternion))
        self.yaw[enaction.clock] = pe
        self.yaw.pop(enaction.clock - PREDICTION_ERROR_WINDOW, None)
        print("Prediction Error Yaw (command - measure)=", round(pe, 1),
              "Average:", round(float(np.mean(list(self.yaw.values()))), 1),
              "std:", round(float(np.std(list(self.yaw.values()))), 1))

        # Compass prediction error

        self.compass[enaction.clock] = math.degrees(enaction.trajectory.body_direction_delta)
        self.compass.pop(actual_outcome.clock - PREDICTION_ERROR_WINDOW, None)
        print("Prediction Error Compass (integrated direction - compass measure)=",
              round(self.compass[enaction.clock], 2), "Average:",
              round(float(np.mean(list(self.compass.values()))), 2), "std:",
              round(float(np.std(list(self.compass.values()))), 2))

        # The echo prediction error when focus is confident

        # if enaction.trajectory.focus_confidence >= CONFIDENCE_CONFIRMED_FOCUS:
        pe = computed_outcome.head_angle - actual_outcome.head_angle
        self.echo_direction[actual_outcome.clock] = pe
        self.echo_direction.pop(actual_outcome.clock - PREDICTION_ERROR_WINDOW, None)
        print("Prediction Error Head Direction (prediction - measure)=", pe,
              # enaction.trajectory.focus_direction_prediction_error,
              "Average:", round(float(np.mean(list(self.echo_direction.values())))),
              "std:", round(float(np.std(list(self.echo_direction.values())))))

        if computed_outcome.echo_distance < 10000 and actual_outcome.echo_distance < 10000:
            pe = computed_outcome.echo_distance - actual_outcome.echo_distance
            self.echo_distance[enaction.clock] = pe
            self.echo_distance.pop(enaction.clock - PREDICTION_ERROR_WINDOW, None)
            print("Prediction Error Echo Distance (prediction - measure)=", pe,
                  # enaction.trajectory.focus_distance_prediction_error,
                  "Average:", round(float(np.mean(list(self.echo_distance.values())))),
                  "std:", round(float(np.std(list(self.echo_distance.values())))))

        # The focus prediction error

        if enaction.predicted_memory.egocentric_memory.focus_point is not None and enaction.trajectory.focus_point is not None:
            pa, pd = point_to_head_direction_distance(enaction.predicted_memory.egocentric_memory.focus_point)
            ma, md = point_to_head_direction_distance(enaction.trajectory.focus_point)
            self.focus_direction[actual_outcome.clock] = round(pa - ma)
            self.focus_direction.pop(actual_outcome.clock - PREDICTION_ERROR_WINDOW, None)
            print("Prediction Error Focus Direction (prediction - measure)=", round(pa - ma),
                  "Average:", round(float(np.mean(list(self.focus_direction.values())))),
                  "std:", round(float(np.std(list(self.focus_direction.values())))))
            self.focus_distance[enaction.clock] = round(pd - md)
            self.focus_distance.pop(enaction.clock - PREDICTION_ERROR_WINDOW, None)
            print("Prediction Error Focus Distance (prediction - measure)=", round(pd - md),
                  "Average:", round(float(np.mean(list(self.focus_distance.values())))),
                  "std:", round(float(np.std(list(self.focus_distance.values())))))

        # The terrain origin prediction error

        terrain = self.workspace.memory.phenomenon_memory.terrain()
        if terrain is not None:
            terrain.origin_prediction_error.pop(enaction.clock - PREDICTION_ERROR_WINDOW, None)
            if enaction.clock in terrain.origin_prediction_error:
                print("Prediction Error Terrain origin (integration - measure)=",
                      round(terrain.origin_prediction_error[enaction.clock]),
                      "Average:", round(float(np.mean(list(terrain.origin_prediction_error.values())))),
                      "std:", round(float(np.std(list(terrain.origin_prediction_error.values())))))

    def plot(self):
        """Show the prediction error plots"""
        # The agg backend avoids interfering with pyglet windows
        # https://matplotlib.org/stable/users/explain/figure/backends.html
        matplotlib.use('agg')
        # Create the log directory if it does not exist because it is not included in git
        if not os.path.exists("log"):
            os.makedirs("log")
        # Generate the plots
        plot(self.forward_duration1, "Forward duration (s)", "Forward_duration")
        plot(self.yaw, "Yaw (degrees)", "yaw")
        plot(self.compass, "Compass (degree)", "Compass")
        plot(self.echo_direction, "Head direction (degree)", "Head_direction")
        plot(self.echo_distance, "Echo distance (mm)", "Echo_distance")
        plot(self.focus_direction, "Focus direction (degree)", "Focus_direction")
        plot(self.focus_distance, "Focus distance (mm)", "Focus_distance")
        terrain = self.workspace.memory.phenomenon_memory.terrain()
        if terrain is not None:
            plot(terrain.origin_prediction_error, "Terrain origin (mm)", "Origin")


# Test plot
if __name__ == "__main__":
    test_dict = {0: 1, 1: 2, 2: 2, 3: 1, 4: 0}
    matplotlib.use('agg')
    plot(test_dict, "Test", "test")
