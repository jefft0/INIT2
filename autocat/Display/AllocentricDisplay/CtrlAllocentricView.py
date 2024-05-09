import time
from pyglet.window import key, mouse
from .AllocentricView import AllocentricView
from ...Memory.AllocentricMemory.Geometry import point_to_cell
from ...Robot.CtrlRobot import ENACTION_STEP_RENDERING, ENACTION_STEP_ENACTING
from ...Memory.EgocentricMemory.Experience import EXPERIENCE_FLOOR, EXPERIENCE_ALIGNED_ECHO
from ...Memory.AllocentricMemory.AllocentricMemory import CELL_UNKNOWN


STATUS_0 = 0
STATUS_1 = 1
STATUS_3 = 6
STATUS_4 = 8
CLOCK_PLACE = 2
COLOR_INDEX = 3
CLOCK_FOCUS = 7
CLOCK_PROMPT = 9
CLOCK_INTERACTION = 4
PHENOMENON_ID = 5
CLOCK_NO_ECHO = 10


class CtrlAllocentricView:
    def __init__(self, workspace):
        """Control the allocentric view"""
        self.workspace = workspace
        self.view = AllocentricView(self.workspace)
        self.next_time_refresh = 0

        # Handlers
        def on_text(text):
            """Send user keypress to the workspace to handle"""
            self.workspace.process_user_key(text)

        self.view.on_text = on_text

        def on_mouse_press(x, y, button, modifiers):
            """Display the label of this cell"""
            click_point = self.view.mouse_coordinates_to_point(x, y)
            cell_x, cell_y = point_to_cell(click_point)
            cell = self.workspace.memory.allocentric_memory.grid[cell_x][cell_y]

            # Change cell status
            if button == mouse.RIGHT:
                # SHIFT clear the cell and the prompts
                if modifiers & key.MOD_SHIFT:
                    self.delete_prompt()
                    # Clear the FLOOR status
                    self.workspace.memory.allocentric_memory.clear_cell(cell_x, cell_y, self.workspace.memory.clock)
                    if (cell_x, cell_y) in self.workspace.memory.allocentric_memory.user_cells:
                        self.workspace.memory.allocentric_memory.user_cells.remove((cell_x, cell_y))
                # CTRL ALT: toggle COLOR FLOOR
                elif modifiers & key.MOD_CTRL and modifiers & key.MOD_ALT:
                    #if cell.status[0] == EXPERIENCE_FLOOR and cell.color_index > 0:
                    if self.workspace.memory.allocentric_memory.grid[cell_x][cell_y][STATUS_0] == EXPERIENCE_FLOOR and self.workspace.memory.allocentric_memory.grid[cell_x][cell_y][COLOR_INDEX] > 0:
                        #cell.status[0] = CELL_UNKNOWN
                        self.workspace.memory.allocentric_memory.grid[cell_x][cell_y][STATUS_0] = CELL_UNKNOWN
                        self.workspace.memory.allocentric_memory.grid[cell_x][cell_y][COLOR_INDEX] = 0
                        #cell.color_index = 0
                        if (cell_x, cell_y) in self.workspace.memory.allocentric_memory.user_cells:
                            self.workspace.memory.allocentric_memory.user_cells.remove((cell_x, cell_y))
                    else:
                        # Mark a green FLOOR cell
                        self.workspace.memory.allocentric_memory.apply_status_to_cell(cell_x, cell_y, EXPERIENCE_FLOOR,
                                                                                      self.workspace.memory.clock, 4)
                        self.workspace.memory.allocentric_memory.user_cells.append((cell_x, cell_y))
                # CTRL: Toggle FLOOR
                elif modifiers & key.MOD_CTRL:
                    #if cell.status[0] == EXPERIENCE_FLOOR and cell.color_index == 0:
                    if self.workspace.memory.allocentric_memory.grid[cell_x][cell_y][STATUS_0] == EXPERIENCE_FLOOR and self.workspace.memory.allocentric_memory.grid[cell_x][cell_y][COLOR_INDEX] == 0:
                        self.workspace.memory.allocentric_memory.grid[cell_x][cell_y][STATUS_0] = CELL_UNKNOWN

                        #cell.status[0] = CELL_UNKNOWN
                        if (cell_x, cell_y) in self.workspace.memory.allocentric_memory.user_cells:
                            self.workspace.memory.allocentric_memory.user_cells.remove((cell_x, cell_y))
                    else:
                        # Mark a FLOOR cell
                        self.workspace.memory.allocentric_memory.apply_status_to_cell(cell_x, cell_y, EXPERIENCE_FLOOR,
                                                                                      self.workspace.memory.clock, 0)
                        self.workspace.memory.allocentric_memory.user_cells.append((cell_x, cell_y))
                # ALT: Toggle ECHO
                elif modifiers & key.MOD_ALT:
                    # if cell.status[1] == EXPERIENCE_ALIGNED_ECHO:
                    #     cell.status[1] = CELL_UNKNOWN
                    #     cell.color_index = 0

                    if self.workspace.memory.allocentric_memory.grid[cell_x][cell_y][STATUS_1] == EXPERIENCE_ALIGNED_ECHO:
                        self.workspace.memory.allocentric_memory.grid[cell_x][cell_y][STATUS_1] = CELL_UNKNOWN
                        self.workspace.memory.allocentric_memory.grid[cell_x][cell_y][COLOR_INDEX] = 0



                        if (cell_x, cell_y) in self.workspace.memory.allocentric_memory.user_cells:
                            self.workspace.memory.allocentric_memory.user_cells.remove((cell_x, cell_y))
                    else:
                        # Mark an echo cell
                        self.workspace.memory.allocentric_memory.apply_status_to_cell(cell_x, cell_y,
                                                                                      EXPERIENCE_ALIGNED_ECHO,
                                                                                      self.workspace.memory.clock, 0)
                        self.workspace.memory.allocentric_memory.user_cells.append((cell_x, cell_y))
                # No modifier: move the prompt
                else:
                    # Mark the prompt
                    self.workspace.memory.allocentric_memory.update_prompt(click_point, self.workspace.memory.clock)
                    # Store the prompt in egocentric memory
                    ego_point = self.workspace.memory.allocentric_to_egocentric(click_point)
                    self.workspace.memory.egocentric_memory.prompt_point = ego_point

                self.update_view()

            # Display this phenomenon in phenomenon window
            if self.workspace.memory.allocentric_memory.grid[cell_x][cell_y][PHENOMENON_ID] != -1:
            # if cell.phenomenon_id is not None:
                self.workspace.ctrl_phenomenon_view.view.set_caption(f"Phenomenon {self.workspace.memory.allocentric_memory.grid[cell_x][cell_y][PHENOMENON_ID]}")
                self.workspace.ctrl_phenomenon_view.phenomenon_id = self.workspace.memory.allocentric_memory.grid[cell_x][cell_y][PHENOMENON_ID]
                self.workspace.ctrl_phenomenon_view.update_body_robot()
                self.workspace.ctrl_phenomenon_view.update_affordance_displays()

            self.view.label_click.text = self.workspace.memory.allocentric_memory.grid[cell_x][cell_y].__str__()

            # """Label of the cell for display on click in allocentricView"""
            # label = str(self.workspace.memory.allocentric_memory.grid[cell_x][cell_y][STATUS_0]) + " Clocks: ["
            # label += str(self.workspace.memory.allocentric_memory.grid[cell_x][cell_y][STATUS_1])
            # label += str(self.workspace.memory.allocentric_memory.grid[cell_x][cell_y][STATUS_3])
            # label += str(self.workspace.memory.allocentric_memory.grid[cell_x][cell_y][STATUS_4])
            # label += str(self.workspace.memory.allocentric_memory.grid[cell_x][cell_y][CLOCK_PLACE]) + ", "
            # label += str(self.workspace.memory.allocentric_memory.grid[cell_x][cell_y][CLOCK_INTERACTION]) + ", "
            # label += str(self.workspace.memory.allocentric_memory.grid[cell_x][cell_y][CLOCK_NO_ECHO]) + ", "
            # label += str(self.workspace.memory.allocentric_memory.grid[cell_x][cell_y][CLOCK_FOCUS]) + ", "
            # label += str(self.workspace.memory.allocentric_memory.grid[cell_x][cell_y][CLOCK_FOCUS]) + "]"
            # # if self.phenomenon_id is not None:
            #     label += " Phenomenon:" + str(self.phenomenon_id)
            #
            #     self.view.label_click.text = label

        self.view.on_mouse_press = on_mouse_press

        def on_key_press(symbol, modifiers):
            """ Deleting the prompt"""
            if symbol == key.DELETE:
                self.delete_prompt()
                self.workspace.memory.allocentric_memory.user_cells = []

        self.view.on_key_press = on_key_press

    def delete_prompt(self):
        """Delete the prompt"""
        self.workspace.memory.egocentric_memory.prompt_point = None
        self.workspace.memory.allocentric_memory.update_prompt(None, self.workspace.memory.clock)
        self.update_view()

    def update_view(self):
        """Update the allocentric view from the status in the allocentric grid cells"""
        # for c in [c for line in self.workspace.memory.allocentric_memory.grid for c in line]:
        #     self.view.update_hexagon(c)
        for i in range(self.workspace.memory.allocentric_memory.min_i, self.workspace.memory.allocentric_memory.max_i):
            for j in range(self.workspace.memory.allocentric_memory.min_j, self.workspace.memory.allocentric_memory.max_j):
                self.view.update_hexagon(i, j, self.workspace.memory.allocentric_memory.grid[i][j][:])
        # Update the other robot
        # if ROBOT1 in self.workspace.memory.phenomenon_memory.phenomena:
        #     self.view.update_robot_poi(self.workspace.memory.phenomenon_memory.phenomena[ROBOT1])

    def main(self, dt):
        """Refresh allocentric view"""
        # Refresh during the enaction and at the end of the interaction cycle
        if self.workspace.enacter.interaction_step in [ENACTION_STEP_ENACTING, ENACTION_STEP_RENDERING]:
            self.update_view()
