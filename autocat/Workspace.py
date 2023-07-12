import json
import numpy as np
from pyrr import quaternion
from playsound import playsound
from .Decider.DeciderCircle import DeciderCircle
from .Decider.DeciderExplore import DeciderExplore
from .Decider.DeciderWatch import DeciderWatch
from .Decider.Action import create_actions, ACTION_FORWARD, ACTIONS, ACTION_TURN
from .Memory.Memory import Memory
from .Integrator.Integrator import Integrator
from .Robot.Enaction import Enaction
from .Robot.CtrlRobot import INTERACTION_STEP_IDLE, INTERACTION_STEP_INTENDING, INTERACTION_STEP_ENACTING, \
    INTERACTION_STEP_INTEGRATING, INTERACTION_STEP_REFRESHING
from .Robot.RobotDefine import ROBOT_FRONT_X
from .Enaction.SpatialModifier import SpatialModifier

KEY_DECIDER_CIRCLE = "A"  # Automatic mode: controlled by the deciders
KEY_DECIDER_USER = "M"  # Manual mode : controlled by the user
KEY_ENGAGEMENT_ROBOT = "R"  # The robot actually enacts the interaction
KEY_ENGAGEMENT_IMAGINARY = "I"  # The application imagines the interaction but the robot does not enact them
KEY_DECREASE_CONFIDENCE = "D"
KEY_INCREASE_CONFIDENCE = "P"
KEY_CLEAR = "C"  # Clear the stack of interactions to enact next


class Workspace:
    """The Workspace supervises the interaction cycle. It produces the intended_interaction
    and processes the enacted interaction """
    def __init__(self, arena_id, robot_id):
        self.arena_id = arena_id
        self.robot_id = robot_id
        self.actions = create_actions(robot_id)
        self.memory = Memory(robot_id)
        if self.robot_id == '3':
            self.deciders = {'Explore': DeciderExplore(self), 'Circle': DeciderCircle(self), 'Watch': DeciderWatch(self)}
        else:
            self.deciders = {'Explore': DeciderExplore(self), 'Circle': DeciderCircle(self)}
        self.integrator = Integrator(self)

        self.enactions = {}  # The stack of enactions to enact next
        self.enaction = None
        # self.enacted_enaction = None

        self.decider_mode = KEY_DECIDER_USER
        self.engagement_mode = KEY_ENGAGEMENT_ROBOT
        self.interaction_step = INTERACTION_STEP_IDLE

        # Controls which phenomenon to display
        self.ctrl_phenomenon_view = None

        self.clock = 0
        self.memory_snapshot = None
        self.is_imagining = False

    def main(self, dt):
        """The main handler of the interaction cycle:
        organize the generation of the intended_interaction and the processing of the enacted_interaction."""
        # REFRESHING: last only one cycle
        if self.interaction_step == INTERACTION_STEP_REFRESHING:
            self.interaction_step = INTERACTION_STEP_IDLE

        # IDLE: Ready to choose the next intended interaction
        if self.interaction_step == INTERACTION_STEP_IDLE:
            # Manage the memory snapshot
            if self.is_imagining:
                # If stop imagining then restore memory from the snapshot
                if self.engagement_mode == KEY_ENGAGEMENT_ROBOT:
                    self.memory = self.memory_snapshot.save()  # Keep the snapshot saved
                    self.is_imagining = False
                    self.interaction_step = INTERACTION_STEP_REFRESHING
                # (If continue imagining then keep the previous snapshot)
            else:
                # If was not previously imagining then take a new memory snapshot
                if self.engagement_mode == KEY_ENGAGEMENT_IMAGINARY:
                    # Start imagining
                    self.memory_snapshot = self.memory.save()  # Fail when trying to save an affordance created during imaginary
                    self.is_imagining = True
            # Next automatic decision
            if self.clock not in self.enactions:
                if self.decider_mode == KEY_DECIDER_CIRCLE:
                    # The most activated decider processes the previous enaction and chooses the next enaction
                    decider = max(self.deciders, key=lambda k: self.deciders[k].activation_level())
                    print("Decider:", decider)
                    self.deciders[decider].stack_enaction()
                    # TODO Manage the enacted_interaction after imagining

                # Case DECIDER_KEY_USER is handled by self.process_user_key()

            # When the next enaction is in the stack
            if self.clock in self.enactions:
                # Take the next enaction from the stack
                self.enaction = self.enactions[self.clock]
                # Adjust the spatial modifiers
                self.enaction.body_quaternion = self.memory.body_memory.body_quaternion.copy()
                if self.memory.egocentric_memory.prompt_point is not None:
                    self.enaction.prompt_point = self.memory.egocentric_memory.prompt_point.copy()
                if self.memory.egocentric_memory.focus_point is not None:
                    self.enaction.focus_point = self.memory.egocentric_memory.focus_point.copy()
                # self.enaction.adjust_and_begin(self.memory)
                self.enaction.begin()
                print("Emit", self.emit_message())
                if self.is_imagining:
                    # If imagining then proceed to simulating the enaction
                    self.interaction_step = INTERACTION_STEP_ENACTING
                else:
                    # Take a snapshot for the simulation and proceed to INTENDING
                    self.memory_snapshot = self.memory.save()  # Fail when trying to save an affordance created during imaginary
                    self.interaction_step = INTERACTION_STEP_INTENDING

        # INTENDING: is handled by CtrlRobot

        # ENACTING: update body memory during the robot enaction or the imaginary simulation
        if self.interaction_step == INTERACTION_STEP_ENACTING:
            if not self.memory.simulate(self.enaction, dt):
                # End of the simulation
                if self.is_imagining:
                    # Skip INTEGRATING for now
                    del self.enactions[self.clock]
                    self.clock += 1  # Perhaps not necessary
                    self.interaction_step = INTERACTION_STEP_REFRESHING

        # INTEGRATING: the new enacted interaction (if not imagining)
        if self.interaction_step == INTERACTION_STEP_INTEGRATING:
            # Restore the memory from the snapshot and integrate the experiences
            self.memory = self.memory_snapshot
            # Update body memory and egocentric memory
            self.memory.update_and_add_experiences(self.enaction)

            # Call the integrator to create and update the phenomena
            # Currently we don't create phenomena in imaginary mode
            self.integrator.integrate()

            # Update allocentric memory: robot, phenomena, focus
            self.memory.update_allocentric(self.clock)

            # Increment the clock if the enacted interaction was properly received
            if self.enaction.clock >= self.clock:  # don't increment if the robot is behind
                # Remove the enaction from the stack (ok if it has already been removed)
                self.enactions.pop(self.clock, None)
                # Increment the clock
                self.clock += 1

            self.interaction_step = INTERACTION_STEP_REFRESHING

        # REFRESHING: Will be reset to IDLE in the next cycle

    def process_user_key(self, user_key):
        """Process the keypress on the view windows (called by the views)"""
        if user_key.upper() in [KEY_DECIDER_CIRCLE, KEY_DECIDER_USER]:
            self.decider_mode = user_key.upper()
        elif user_key.upper() in [KEY_ENGAGEMENT_ROBOT, KEY_ENGAGEMENT_IMAGINARY]:
            self.engagement_mode = user_key.upper()
        elif user_key.upper() in ACTIONS:
            # Only process actions when the robot is IDLE
            if self.interaction_step == INTERACTION_STEP_IDLE:
                self.enactions[self.clock] = Enaction(self.actions[user_key.upper()], self.clock)
        elif user_key.upper() == "/":
            # If key ALIGN then turn and move forward to the prompt
            if self.interaction_step == INTERACTION_STEP_IDLE:
                self.enactions[self.clock] = Enaction(self.actions[ACTION_TURN], self.clock)
                self.enactions[self.clock + 1] = Enaction(self.actions[ACTION_FORWARD], self.clock + 1)
        elif user_key.upper() == KEY_CLEAR:
            # Clear the stack of enactions
            playsound('autocat/Assets/R3.wav', False)
            self.enactions = {}

    def emit_message(self):
        """Return the message to answer to another robot"""
        message = {"azimuth": self.memory.body_memory.body_azimuth()}

        # If focus then send polar-egocentric information
        focus_point = self.memory.egocentric_to_polar_egocentric(self.enaction.focus_point)
        if focus_point is not None:
            # The position of the focus
            # p = p * (np.linalg.norm(p) + ROBOT_FRONT_X / 2) / np.linalg.norm(p)
            # p = Vector3(p)
            # p = p.normalize() * (p.length() + ROBOT_FRONT_X / 2)
            message['focus_x'] = round(focus_point[0])
            message['focus_y'] = round(focus_point[1])

            # The destination position in polar-egocentric
            destination_point = quaternion.apply_to_vector(self.enaction.body_quaternion,
                                                           self.enaction.command.anticipated_translation)
            message['destination_x'] = round(destination_point[0])
            message['destination_y'] = round(destination_point[1])

            return json.dumps(message)
