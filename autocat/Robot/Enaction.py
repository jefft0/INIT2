import math
import json
import numpy as np
from pyrr import matrix44
from playsound import playsound
from ..Decider.Action import ACTION_FORWARD, ACTION_BACKWARD, ACTION_SWIPE, ACTION_RIGHTWARD,  ACTION_TURN, \
    ACTION_SCAN, ACTION_WATCH
from ..Decider.Decider import CONFIDENCE_NO_FOCUS, CONFIDENCE_NEW_FOCUS, CONFIDENCE_TOUCHED_FOCUS, \
    CONFIDENCE_CAREFUL_SCAN, CONFIDENCE_CONFIRMED_FOCUS
from ..Memory.Memory import SIMULATION_TIME_RATIO
from ..Memory.BodyMemory import point_to_echo_direction_distance
from ..Utils import short_angle
from .RobotDefine import DEFAULT_YAW, TURN_DURATION, ROBOT_FRONT_X, ROBOT_FRONT_Y, ROBOT_SETTINGS, RETREAT_DISTANCE_Y
from .Command import Command, DIRECTION_FRONT
from .Outcome import echo_point

FOCUS_MAX_DELTA = 200  # 200 (mm) Maximum delta to keep focus


class Enaction:
    """An Enaction object handles the enaction of an interaction by the robot
    1. Workspace instantiates the enaction
    2. CtrlRobot sends the command to the robot
    3. CtrlRobot computes the outcome received from the robot
    4. CtrlRobot call ternminate(outcome)
    """
    def __init__(self, action, memory, direction=DIRECTION_FRONT, span=40):
        """Initialize the enaction upon creation. Will be adjusted before generating the command"""
        # The initial arguments
        self.action = action
        self.robot_id = memory.robot_id

        # the attributes that will be adjusted
        self.clock = None
        self.prompt_point = None
        self.focus_point = None

        # The command to the robot
        self.body_quaternion = memory.body_memory.body_quaternion.copy()
        if memory.egocentric_memory.prompt_point is not None:
            self.prompt_point = memory.egocentric_memory.prompt_point.copy()
            # print("Initialize Enaction clock", self.clock, "prompt", self.prompt_point)
        if memory.egocentric_memory.focus_point is not None:
            self.focus_point = memory.egocentric_memory.focus_point.copy()
        self.command = Command(self.action, self.prompt_point, self.focus_point, direction, span, memory.emotion_code)

        # The anticipated memory
        self.post_memory = memory.save()
        self.post_memory.allocentric_memory.move(self.body_quaternion, self.command.anticipated_translation, self.clock)
        self.post_memory.body_memory.body_quaternion = self.command.anticipated_yaw_quaternion * self.body_quaternion
        if memory.egocentric_memory.prompt_point is not None:
            self.post_memory.egocentric_memory.prompt_point = \
                matrix44.apply_to_vector(self.command.anticipated_displacement_matrix, self.prompt_point).astype(int)
        if memory.egocentric_memory.focus_point is not None:
            self.post_memory.egocentric_memory.focus_point = \
                matrix44.apply_to_vector(self.command.anticipated_displacement_matrix, self.focus_point).astype(int)

        # The simulation of the enaction
        self.is_simulating = False
        self.simulation_duration = 0
        self.simulation_rotation_speed = 0
        self.simulation_time = 0.

        # The outcome
        self.outcome = None
        self.body_direction_delta = 0  # Displayed in BodyView
        self.focus_confidence = CONFIDENCE_NO_FOCUS  # Used by deciders to possibly trigger scan
        self.translation = None  # Used by allocentric memory to move the robot
        self.yaw_matrix = None  # Used by bodyView to rotate compass points
        self.displacement_matrix = None  # Used by EgocentricMemory to rotate experiences

        # The message received from other robot
        self.message = None
        self.message_sent = False  # Message sent to other robots

        self.focus_direction_prediction_error = 0
        self.focus_distance_prediction_error = 0

    def begin(self, clock, body_quaternion):
        """Adjust the spatial modifiers of the enaction.
        Compute the command to send to the robot.
        Initialize the simulation"""

        self.clock = clock
        # Update the body_quaternion to avoid errors in the estimated yaw
        self.body_quaternion = body_quaternion.copy()

        # Initialize the simulation of the intended interaction
        # Compute the duration and the speed depending and the enaction
        self.simulation_duration = self.action.target_duration
        self.simulation_rotation_speed = self.action.rotation_speed_rad
        if self.command.duration is not None:
            self.simulation_duration = self.command.duration / 1000
        if self.command.angle is not None:
            self.simulation_duration = math.fabs(self.command.angle) * TURN_DURATION / DEFAULT_YAW
            if self.command.angle < 0:  # and self.action.action_code != ACTION_TURN_RIGHT:
                self.simulation_rotation_speed = -self.action.rotation_speed_rad
        self.simulation_duration *= SIMULATION_TIME_RATIO
        self.simulation_rotation_speed *= SIMULATION_TIME_RATIO
        self.is_simulating = True
        self.simulation_time = 0.

    def terminate(self, outcome):
        """Computes the azimuth, the yaw, and the displacement. Follow up the focus and the prompt."""
        self.outcome = outcome

        # The displacement --------

        # Translation integrated from the action's speed multiplied by the duration1
        # TODO Take the yaw into account
        # self.translation = self.action.translation_speed * (float(outcome.duration1) / 1000.0)
        # if self.action.action_code == ACTION_SWIPE and self.command.speed is not None and self.command.speed < 0:
        #     self.translation = - self.translation
        self.translation = self.command.anticipated_translation.copy()
        if self.command.duration is None or self.command.duration == 0:
            self.translation *= (self.outcome.duration1/(self.action.target_duration * 1000.))
        else:
            self.translation *= (self.outcome.duration1/self.command.duration)

        if self.outcome.floor > 0:
            # Update the translation
            if self.outcome.floor == 0b01:
                # Black line on the right
                retreat = [-ROBOT_SETTINGS[self.robot_id]["retreat_distance"], RETREAT_DISTANCE_Y, 0]
            elif self.outcome.floor == 0b10:
                # Black line on the left
                retreat = [-ROBOT_SETTINGS[self.robot_id]["retreat_distance"], -RETREAT_DISTANCE_Y, 0]
            else:
                # Black line on the front
                retreat = [-ROBOT_SETTINGS[self.robot_id]["retreat_distance"], 0, 0]
            playsound('autocat/Assets/cyberpunk3.wav', False)
            self.translation += retreat

        if outcome.blocked:
            self.translation = np.array([0, 0, 0], dtype=int)

        # The yaw quaternion
        if outcome.yaw_quaternion is None:
            # yaw_quaternion = Quaternion.from_z_rotation(self.action.target_duration * self.action.rotation_speed_rad)
            yaw_quaternion = self.command.anticipated_yaw_quaternion.copy()
        else:
            yaw_quaternion = outcome.yaw_quaternion
        yaw_integration_quaternion = self.body_quaternion.cross(yaw_quaternion)
        # print("body_quaternion", repr(self.body_quaternion), "cross yaw_quaternion", repr(yaw_quaternion),
        #       "= yaw_integration_quaternion", repr(yaw_integration_quaternion))

        # If the robot returns no compass then the body_quaternion is estimated from yaw
        if outcome.compass_point is None:
            self.body_quaternion = yaw_integration_quaternion
        else:
            if self.clock == 0:
                # On the first interaction, the body_quaternion is given by the compass
                self.body_quaternion = self.outcome.compass_quaternion
            else:
                # After the first interaction, the body_quaternion is averaged of the compass and the yaw integration
                if self.outcome.compass_quaternion.dot(yaw_integration_quaternion) < 0.0:
                    yaw_integration_quaternion = - yaw_integration_quaternion

                # Save the difference to display in BodyView
                self.body_direction_delta = short_angle(self.outcome.compass_quaternion, yaw_integration_quaternion)
                # If positive when turning trigonometric direction then the yaw is measured greater than it is

                # Take the median angle between the compass and the yaw estimate
                # 0 is compass only, 1 is yaw estimate only
                # This is known as a complementary filter
                # https://forum.arduino.cc/t/guide-to-gyro-and-accelerometer-with-arduino-including-kalman-filtering/57971
                new_body_quaternion = self.outcome.compass_quaternion.slerp(yaw_integration_quaternion, 0.75)

                # Recompute the yaw quaternion
                yaw_quaternion = new_body_quaternion.cross(self.body_quaternion.inverse)
                if yaw_quaternion.angle > math.pi:
                    yaw_quaternion = -yaw_quaternion

                # Update the body_quaternion
                self.body_quaternion = new_body_quaternion
                # print("new_body_quaternion", repr(self.body_quaternion))

        # Compute the displacement matrix which represents the displacement of the environment
        # relative to the robot (Translates and turns in the opposite direction)
        self.yaw_matrix = matrix44.create_from_quaternion(yaw_quaternion)
        self.displacement_matrix = matrix44.multiply(matrix44.create_from_translation(-self.translation),
                                                     self.yaw_matrix)

        # The focus --------

        # If careful watch then the focus is the first central_echo
        new_focus = self.outcome.echo_point
        if self.command.span == 10 and len(self.outcome.central_echos) > 0:
            # central_echo = self.outcome.central_echos[0]
            # x = ROBOT_HEAD_X + math.cos(math.radians(central_echo[0])) * central_echo[1]
            # y = math.sin(math.radians(central_echo[0])) * central_echo[1]
            # new_focus = np.array([x, y, 0], dtype=int)
            new_focus = echo_point(*self.outcome.central_echos[0])

        # If the robot is already focussed then adjust the focus and the displacement
        if self.focus_point is not None:
            if new_focus is not None:
                # The error between the expected and the actual position of the echo
                new_focus_direction, new_focus_distance = point_to_echo_direction_distance(new_focus)
                prediction_focus_point = matrix44.apply_to_vector(self.displacement_matrix, self.focus_point)
                prediction_focus_direction, prediction_focus_distance = point_to_echo_direction_distance(prediction_focus_point)
                prediction_error_focus = prediction_focus_point - new_focus
                self.focus_direction_prediction_error = prediction_focus_direction - new_focus_direction
                self.focus_distance_prediction_error = prediction_focus_distance - new_focus_distance
                # If the new focus is near the previous focus or the displacement has been continuous.
                if np.linalg.norm(prediction_error_focus) < FOCUS_MAX_DELTA or self.outcome.status == "continuous":
                    # The focus has been kept
                    print("Focus kept with prediction error", prediction_error_focus, "moved to ", end="")
                    self.focus_confidence = CONFIDENCE_CONFIRMED_FOCUS
                    # If the action has been completed
                    if self.outcome.duration1 >= 1000:
                        # If the head is forward then correct longitudinal displacements
                        if -20 < self.outcome.head_angle < 20:
                            if self.action.action_code in [ACTION_FORWARD, ACTION_BACKWARD]:
                                self.translation[0] = self.translation[0] + prediction_error_focus[0]
                                # Correct the estimated speed of the action
                                if self.command.duration is None:
                                    self.action.adjust_translation_speed(self.translation)
                        # If the head is sideways then correct lateral displacements
                        if self.outcome.head_angle < -60 or 60 < self.outcome.head_angle:
                            if self.action.action_code in [ACTION_SWIPE, ACTION_RIGHTWARD]:
                                self.translation[1] = self.translation[1] + prediction_error_focus[1]
                                # Correct the estimated speed of the action
                                if self.command.duration is None:
                                    self.action.adjust_translation_speed(self.translation)
                        # Update the displacement matrix according to the new translation
                        translation_matrix = matrix44.create_from_translation(-self.translation)
                        self.displacement_matrix = matrix44.multiply(translation_matrix, self.yaw_matrix)
                else:
                    # The focus was lost
                    print("Focus delta:", prediction_error_focus, "New focus:", end="")
                    # Careful scan forces CONFIDENCE_CAREFUL_SCAN
                    if self.command.span == 10:
                        self.focus_confidence = CONFIDENCE_CAREFUL_SCAN
                    else:
                        self.focus_confidence = CONFIDENCE_NEW_FOCUS
                    # playsound('autocat/Assets/R5.wav', False)
            else:
                # The focus was lost
                print("Lost focus due to no echo ", end="")
                self.focus_confidence = CONFIDENCE_NO_FOCUS
                # self.lost_focus = True  # Used by agent_circle
                # playsound('autocat/Assets/R5.wav', False)
        else:
            # If the robot was not focussed then check for catch focus
            if self.action.action_code in [ACTION_SCAN, ACTION_FORWARD, ACTION_TURN, ACTION_WATCH] \
                    and self.outcome.echo_point is not None:
                # Catch focus
                # playsound('autocat/Assets/cute_beep2.wav', False)  # DeciderExplore and DeciderWatch often clear focus
                self.focus_confidence = CONFIDENCE_NEW_FOCUS
                print("New focus ", end="")
        self.focus_point = new_focus
        print(self.focus_point)

        # Impact or block catch focus
        if self.outcome.impact > 0 and self.action.action_code == ACTION_FORWARD:
            # if new_focus is not None and np.linalg.norm(self.outcome.echo_point) < 200:
            #     # Focus on the object "seen"
            if new_focus is None or np.linalg.norm(new_focus) > 200:
                # Focus on the object "felt"
                if self.outcome.impact == 0b01:
                    self.focus_point = np.array([ROBOT_FRONT_X + 10, -ROBOT_FRONT_Y, 0])
                elif self.outcome.impact == 0b10:
                    self.focus_point = np.array([ROBOT_FRONT_X + 10, ROBOT_FRONT_Y, 0])
                else:
                    self.focus_point = np.array([ROBOT_FRONT_X + 10, 0, 0])
            self.focus_confidence = CONFIDENCE_TOUCHED_FOCUS
            print("Catch focus impact", self.focus_point)

        # Move the prompt -----

        if self.prompt_point is not None:
            self.prompt_point = matrix44.apply_to_vector(self.displacement_matrix, self.prompt_point).astype(int)
            # print("Terminate Enaction clock", self.clock, "Prompt", self.prompt_point)

    def current_enaction(self):
        """Useful if the enaction is taken as a composite enaction"""
        return self

    def increment(self, outcome):
        """Useful if the enaction is taken as a composite enaction"""
        return False

    def serialize(self):
        """Return the command string to send to the robot"""
        command_dict = {'clock': self.clock}
        command_dict.update(self.command.command_dict())
        return json.dumps(command_dict)
