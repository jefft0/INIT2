from ..Robot.CtrlRobot import ENACTION_STEP_IDLE, ENACTION_STEP_INTENDING, ENACTION_STEP_ENACTING, \
    ENACTION_STEP_INTEGRATING, ENACTION_STEP_REFRESHING


class Enacter:
    def __init__(self, workspace):
        self.workspace = workspace
        self.interaction_step = ENACTION_STEP_IDLE
        self.memory_snapshot = None

    def main(self, dt):
        """Controls the enaction."""
        if self.interaction_step == ENACTION_STEP_IDLE:
            # When the next enaction is in the stack, prepare the enaction
            # if self.workspace.clock in self.workspace.enactions:
            if self.workspace.composite_enaction is not None:
                # Take the current enaction from the composite interaction
                self.workspace.enaction = self.workspace.composite_enaction.current_enaction()
                # self.workspace.enaction.clock = self.workspace.clock
                # Take a memory stapshot to restore at the end of the enaction
                self.memory_snapshot = self.workspace.memory.save()
                # Begin the enaction and attribute the clock
                self.workspace.enaction.begin(self.workspace.clock)
                if self.workspace.is_imagining:
                    # If imagining then proceed to simulating the enaction
                    self.interaction_step = ENACTION_STEP_ENACTING
                else:
                    # Take a snapshot for the simulation and proceed to INTENDING
                    self.interaction_step = ENACTION_STEP_INTENDING

        # INTENDING: is handled by CtrlRobot

        # ENACTING: Simulate the enaction in memory
        if self.interaction_step == ENACTION_STEP_ENACTING:
            outcome = self.workspace.memory.simulate(self.workspace.enaction, dt)
            # If imagining then use the imagined outcome when the simulation is finished
            if self.workspace.is_imagining and outcome is not None:
                self.workspace.enaction.terminate(outcome)
                if not self.workspace.composite_enaction.increment(outcome):
                    self.workspace.composite_enaction = None
                self.interaction_step = ENACTION_STEP_INTEGRATING
            # If not imagining then CtrlRobot will return the outcome and proceed to INTEGRATING

        # INTEGRATING: the new enacted interaction
        if self.interaction_step == ENACTION_STEP_INTEGRATING:
            # Restore the memory from the snapshot and integrate the experiences
            self.workspace.memory = self.memory_snapshot
            # Retrieve possible message from other robot
            self.workspace.enaction.message = self.workspace.message
            self.workspace.message = None
            # Update body memory and egocentric memory
            self.workspace.memory.update_and_add_experiences(self.workspace.enaction)

            # Call the integrator to create and update the phenomena
            # Currently we don't create phenomena in imaginary mode
            self.workspace.integrator.integrate()

            # Update allocentric memory: robot, phenomena, focus
            self.workspace.memory.update_allocentric(self.workspace.clock)

            # Increment the clock if the enacted interaction was properly received
            if self.workspace.enaction.clock >= self.workspace.clock:  # don't increment if the robot is behind
                # Remove the enaction from the stack (ok if it has already been removed)
                # self.workspace.enactions.pop(self.workspace.clock, None)
                # Increment the clock
                self.workspace.clock += 1

            self.interaction_step = ENACTION_STEP_REFRESHING

        # REFRESHING: Will be reset to IDLE in the next cycle
