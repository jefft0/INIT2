import numpy as np

from .Decider.AgentCircle import AgentCircle
from .Decider.Action import create_actions
from .Memory.Memory import Memory
from .Integrator.Integrator import Integrator
from .Utils import rotate_vector_z

DECIDER_KEY_CIRCLE = "A"  # Automatic mode: controlled by AgentCircle
DECIDER_KEY_USER = "M"  # Manual mode : controlled by the user

ENGAGEMENT_KEY_ROBOT = "R"  # The application controls the robot
ENGAGEMENT_KEY_IMAGINARY = "I"  # The application imagines the interaction

INTERACTION_STEP_IDLE = 0
INTERACTION_STEP_INTENDING = 1
INTERACTION_STEP_ENACTING = 2
INTERACTION_STEP_INTEGRATING = 3
INTERACTION_STEP_REFRESHING = 4


class Workspace:
    """The Workspace supervises the interaction cycle. It produces the intended_interaction
    and processes the enacted interaction """
    def __init__(self):
        self.actions = create_actions()

        self.memory = Memory()
        self.decider = AgentCircle(self)
        self.integrator = Integrator(self)

        self.intended_interaction = None
        self.enacted_interaction = {}

        self.decider_mode = DECIDER_KEY_USER
        self.engagement_mode = ENGAGEMENT_KEY_ROBOT
        self.interaction_step = INTERACTION_STEP_IDLE

        self.focus_xy = None
        self.prompt_xy = None

        # Controls which phenomenon to display
        self.ctrl_phenomenon_view = None

        self.clock = 0
        self.initial_body_direction_rad = 0.  # Memorize the initial body direction before enaction
        self.initial_robot_point = np.array([0, 0, 0], dtype=float)

    def main(self, dt):
        """The main handler of the interaction cycle:
        organize the generation of the intended_interaction and the processing of the enacted_interaction."""
        # IDLE: If ready and automatic, ask the decider for a new intended interaction
        if self.interaction_step == INTERACTION_STEP_IDLE:
            if self.decider_mode == DECIDER_KEY_CIRCLE:
                self.intended_interaction = self.decider.propose_intended_interaction(self.enacted_interaction)
                self.interaction_step = INTERACTION_STEP_INTENDING
            # Case DECIDER_KEY_USER is handled by self.process_user_key()

        # INTENDING: is handled by CtrlRobot

        # ENACTING: update body memory until CtrlRobot returns the outcome
        if self.interaction_step == INTERACTION_STEP_ENACTING:
            if self.actions[self.intended_interaction['action']].is_simulating:
                self.actions[self.intended_interaction['action']].simulate(self.memory, dt)
            # self.memory.body_memory.body_direction_rad += \
            #     self.actions[self.intended_interaction['action']].rotation_speed_rad * dt * SIMULATION_TURN_RATIO
            # self.memory.allocentric_memory.robot_point += \
            #     rotate_vector_z(self.actions[self.intended_interaction['action']].translation_speed * dt
            #                     * SIMULATION_SPEED_RATIO, self.memory.body_memory.body_direction_rad)

        # INTEGRATING: the new enacted interaction
        if self.interaction_step == INTERACTION_STEP_INTEGRATING:
            self.memory.body_memory.body_direction_rad = self.initial_body_direction_rad  # Retrieve the direction
            self.memory.allocentric_memory.robot_point = self.initial_robot_point
            # Update body memory and egocentric memory
            self.memory.update_and_add_experiences(self.enacted_interaction)
            self.memory.decay(self.clock)

            # Call the integrator to create and update the phenomena.
            self.integrator.integrate()

            # Update allocentric memory: robot, phénomena
            self.memory.update_allocentric(self.integrator.phenomena)

            self.interaction_step = INTERACTION_STEP_REFRESHING

        # REFRESHING: is handle by views and reset by CtrlPhenomenonDisplay

    def get_intended_interaction(self):
        """If the workspace has a new intended interaction then return it, otherwise return None
        Reset the intended_interaction. (Called by CtrlRobot)
        """
        if self.interaction_step == INTERACTION_STEP_INTENDING:
            self.interaction_step = INTERACTION_STEP_ENACTING
            self.actions[self.intended_interaction['action']].is_simulating = True
            self.initial_body_direction_rad = self.memory.body_memory.body_direction_rad  # Memorize the direction
            self.initial_robot_point = self.memory.allocentric_memory.robot_point.copy()
            self.intended_interaction["clock"] = self.clock
            return self.intended_interaction

        return None

    def update_enacted_interaction(self, enacted_interaction):
        """Update the enacted interaction (called by CtrlRobot)"""
        # enacted_interaction["clock"] = self.clock  # sent by the robot

        if "status" in enacted_interaction and enacted_interaction["status"] == "T":
            print("The workspace received an empty enacted interaction")
            self.memory.body_memory.body_direction_rad = self.initial_body_direction_rad  # Retrieve the direction
            self.memory.allocentric_memory.robot_point = self.initial_robot_point.copy()

            # Reset the interaction step
            if self.decider_mode == DECIDER_KEY_CIRCLE:
                # If automatic mode then resend the same intended interaction unless the user has set another one
                self.interaction_step = INTERACTION_STEP_INTENDING
            else:
                # If user mode then abort the enaction and wait for a new action but don't increment the clock
                self.interaction_step = INTERACTION_STEP_IDLE
            return

        # Increment the clock if the enacted interaction was properly received
        self.clock += 1

        # Manage focus catch and lost
        if self.focus_xy is not None:
            # If the focus was kept then update it
            if 'focus' in enacted_interaction:
                if 'echo_xy' in enacted_interaction:  # Not sure why this is necessary
                    self.focus_xy = enacted_interaction['echo_xy']
            # If the focus was lost then reset it
            if 'focus' not in enacted_interaction:
                # The focus was lost, override the echo outcome
                self.focus_xy = None
                print("LOST FOCUS")
        else:
            if self.intended_interaction['action'] in ["-", "8"]:
                # Catch focus
                if 'echo_xy' in enacted_interaction:
                    print("CATCH FOCUS")
                    self.focus_xy = enacted_interaction['echo_xy']

        self.enacted_interaction = enacted_interaction
        self.intended_interaction = None
        self.interaction_step = INTERACTION_STEP_INTEGRATING

    def process_user_key(self, user_key):
        """Process the keypress on the view windows (called by the views)"""
        if user_key.upper() in [DECIDER_KEY_CIRCLE, DECIDER_KEY_USER]:
            self.decider_mode = user_key.upper()
        elif user_key.upper() in [ENGAGEMENT_KEY_ROBOT, ENGAGEMENT_KEY_IMAGINARY]:
            self.engagement_mode = user_key.upper()
        else:
            # Other keys are considered actions and sent to the robot
            if self.interaction_step == INTERACTION_STEP_IDLE:
                self.intended_interaction = {"action": user_key}
                if self.focus_xy is not None:
                    self.intended_interaction['focus_x'] = int(self.focus_xy[0])
                    self.intended_interaction['focus_y'] = int(self.focus_xy[1])
                self.interaction_step = INTERACTION_STEP_INTENDING
