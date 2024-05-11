import json
import pyglet
from .Proposer.Action import create_actions, ACTION_FORWARD, ACTIONS, ACTION_TURN, ACTION_BACKWARD
from .Memory.Memory import Memory
from .Memory.PhenomenonMemory import TERRAIN_ORIGIN_CONFIDENCE
from .Robot.Enaction import Enaction
from .Robot.Command import DIRECTION_BACK
from .Robot.Message import Message
from .Enaction.Enacter import Enacter
from .Enaction.Simulator import Simulator
from .Robot.CtrlRobot import ENACTION_STEP_IDLE, ENACTION_STEP_RENDERING
from .Enaction.CompositeEnaction import CompositeEnaction
from .Integrator.PredictionError import PredictionError
from .Integrator.Calibrator import Calibrator
from .Enaction import KEY_ENGAGEMENT_ROBOT, KEY_CONTROL_DECIDER, KEY_ENGAGEMENT_IMAGINARY

# KEY_CONTROL_DECIDER = "A"  # Automatic mode: controlled by the deciders
KEY_CONTROL_USER = "M"  # Manual mode : controlled by the user
# KEY_ENGAGEMENT_ROBOT = "R"  # The robot actually enacts the interaction
# KEY_ENGAGEMENT_IMAGINARY = "I"  # The application imagines the interaction but the robot does not enact them
KEY_DECREASE = "D"
KEY_INCREASE = "P"
KEY_CLEAR = "C"  # Clear the stack of interactions to enact next
KEY_PREDICTION_ERROR = "E"
KEY_ENCLOSE = "N"


class Workspace:
    """The Workspace supervises the interaction cycle. It produces the intended_interaction
    and processes the enacted interaction """

    def __init__(self, arena_id, robot_id):
        self.arena_id = arena_id
        self.robot_id = robot_id
        self.actions = create_actions(robot_id)
        self.memory = Memory(arena_id, robot_id)
        self.enacter = Enacter(self)
        self.simulator = Simulator(self)
        self.prediction_error = PredictionError(self)
        self.calibrator = Calibrator(self)

        self.composite_enaction = None  # The composite enaction to enact
        self.enaction = None  # The primitive enaction to enact

        self.decider_id = "Manual"
        self.control_mode = KEY_CONTROL_USER
        self.engagement_mode = KEY_ENGAGEMENT_ROBOT

        # Controls which phenomenon to display
        self.ctrl_phenomenon_view = None

        # Message from other robot
        self.message = None

        # Try to load sounds (it may not work on all platforms)
        try:
            self.startup_sound = pyglet.media.load('autocat/Assets/R5.wav', streaming=False)
            self.clear_sound = pyglet.media.load('autocat/Assets/R3.wav', streaming=False)
            self.near_home_sound = pyglet.media.load('autocat/Assets/R4.wav', streaming=False)
            self.push_sound = pyglet.media.load('autocat/Assets/tiny_cute.wav', streaming=False)
            self.message_sound = pyglet.media.load('autocat/Assets/chirp.wav', streaming=False)
            self.floor_sound = pyglet.media.load('autocat/Assets/cyberpunk3.wav', streaming=False)
            self.impact_sound = pyglet.media.load('autocat/Assets/cute_beep1.wav', streaming=False)
            self.surprise_sound = pyglet.media.load('autocat/Assets/chirp3.mp3', streaming=False)
            self.startup_sound.play()
        except pyglet.media.codecs.wave.WAVEDecodeException as e:
            print("Error loading sound files", e)

    def main(self, dt):
        """The main handler of the interaction cycle:
        organize the generation of the intended_interaction and the processing of the enacted_interaction."""
        self.enacter.main(dt)

    def process_user_key(self, user_key):
        """Process the keypress on the view windows (called by the views)"""
        if user_key.upper() in [KEY_CONTROL_DECIDER, KEY_CONTROL_USER]:
            self.control_mode = user_key.upper()
        elif user_key.upper() in [KEY_ENGAGEMENT_ROBOT, KEY_ENGAGEMENT_IMAGINARY]:
            self.engagement_mode = user_key.upper()
        elif user_key.upper() in ACTIONS:
            # Only process actions when the robot is IDLE
            if self.enacter.interaction_step == ENACTION_STEP_IDLE:
                # self.memory.appraise_emotion()
                self.composite_enaction = Enaction(self.actions[user_key.upper()], self.memory.save(), span=10)
        elif user_key.upper() == "/":
            # If key ALIGN then turn and move forward to the prompt
            if self.enacter.interaction_step == ENACTION_STEP_IDLE:
                # The first enaction: turn to the prompt
                e0 = Enaction(self.actions[ACTION_TURN], self.memory.save())
                # Second enaction: move forward to the prompt
                e1 = Enaction(self.actions[ACTION_FORWARD], e0.predicted_memory.save())
                self.composite_enaction = CompositeEnaction([e0, e1])
        elif user_key.upper() == ":" and self.memory.egocentric_memory.focus_point is not None:
            # If key ALIGN BACK then turn back and move backward to the prompt
            if self.enacter.interaction_step == ENACTION_STEP_IDLE:
                # The first enaction: turn the back to the prompt
                e0 = Enaction(self.actions[ACTION_TURN], self.memory.save(), direction=DIRECTION_BACK)
                # Second enaction: move forward to the prompt
                e1 = Enaction(self.actions[ACTION_BACKWARD], e0.predicted_memory.save())
                self.composite_enaction = CompositeEnaction([e0, e1])
        elif user_key.upper() == "P" and self.memory.egocentric_memory.focus_point is not None:
            # If key PUSH and has focus then create the push sequence
            if self.enacter.interaction_step == ENACTION_STEP_IDLE:
                # First enaction: turn to the prompt
                e0 = Enaction(self.actions[ACTION_TURN], self.memory.save())
                # Second enaction: move forward to the prompt
                e1 = Enaction(self.actions[ACTION_FORWARD], e0.predicted_memory.save())
                # Third enaction: turn to the prompt which is copied from the focus because it may be cleared
                e2_memory = e1.predicted_memory.save()
                e2_memory.egocentric_memory.prompt_point = e1.predicted_memory.egocentric_memory.focus_point.copy()
                e2 = Enaction(self.actions[ACTION_TURN], e2_memory)
                # Fourth enaction: move forward to the new prompt
                e3 = Enaction(self.actions[ACTION_FORWARD], e2.predicted_memory.save())
                self.composite_enaction = CompositeEnaction([e0, e1, e2, e3])
        elif user_key.upper() == KEY_CLEAR:
            # Clear the stack of enactions
            self.clear_sound.play()
            self.composite_enaction = None
            # Restore memory
            serotonin = self.memory.body_memory.serotonin  # Handel user change  TODO improve
            dopamine = self.memory.body_memory.dopamine  # Handel user change
            noradrenaline = self.memory.body_memory.noradrenaline  # Handel user change
            confidence = self.memory.phenomenon_memory.terrain_confidence()
            self.memory = self.enacter.memory_snapshot
            self.memory.body_memory.serotonin = serotonin
            self.memory.body_memory.dopamine = dopamine
            self.memory.body_memory.noradrenaline = noradrenaline
            if self.memory.phenomenon_memory.terrain() is not None:
                self.memory.phenomenon_memory.terrain().confidence = confidence
            self.enacter.interaction_step = ENACTION_STEP_RENDERING
            # TODO: prevent a crash when the enaction has been cleared and then an outcome is received after
        elif user_key.upper() == KEY_PREDICTION_ERROR:
            self.prediction_error.plot()

    def emit_message(self):
        """Return the message to answer to another robot"""

        message = {"robot": self.robot_id, "clock": self.memory.clock,
                   "azimuth": self.memory.body_memory.body_azimuth(), "emotion": self.memory.emotion_code}

        # If the terrain has been found then send the position relative to the terrain origin
        if self.memory.phenomenon_memory.terrain_confidence() > TERRAIN_ORIGIN_CONFIDENCE:  # TERRAIN_INITIAL_CONFIDENCE:
            robot_point = self.memory.terrain_centric_robot_point()
            message['position'] = robot_point.astype(int).tolist()

        # Add information about the current enaction only once
        if self.enaction is not None and not self.enaction.is_message_sent:
            # The destination position in polar-egocentric
            # TODO handle destination
            # destination_point = quaternion.apply_to_vector(self.enaction.body_quaternion,
            #                                                self.enaction.command.anticipated_translation)
            # message['destination'] = destination_point.astype(int).tolist()

            # The focus point
            if self.enaction.trajectory.focus_point is not None:
                focus_point = self.memory.egocentric_to_polar_egocentric(self.enaction.trajectory.focus_point)
                message['focus'] = focus_point.astype(int).tolist()

            # Mark the message for this enaction sent
            self.enaction.is_message_sent = True

        return json.dumps(message)

    def receive_message(self, message_string):
        """Store the latest message received from other robots in the Workspace. It will be used during INTEGRATING"""
        # If no message then keep the previous one
        if message_string is not None:
            self.message = Message(message_string)

