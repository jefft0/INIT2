# Testing the Phenomenon View
# py -m autocat.Display.PlaceCellDisplay

import numpy as np
import math
import pyglet
from pyrr import Quaternion, Matrix44
from .CtrlPlaceCellView import CtrlPlaceCellView
from ...Robot.RobotDefine import ROBOT_COLOR_SENSOR_X, ROBOT_SETTINGS_4, ROBOT_FLOOR_SENSOR_X, ROBOT_HEAD_X
from ...Workspace import Workspace
from ...Memory.PlaceMemory.PlaceCell import PlaceCell
from ...Memory.PlaceMemory.Cue import Cue
from ...Memory.EgocentricMemory.Experience import Experience, EXPERIENCE_FLOOR, EXPERIENCE_ALIGNED_ECHO, EXPERIENCE_PLACE
from ...Utils import quaternion_translation_to_matrix
from ...Robot.Enaction import Enaction
from ...Robot.Outcome import Outcome
from ...Proposer.Interaction import Interaction, OUTCOME_NO_FOCUS
from ...Proposer.Action import ACTION_SWIPE, Action


# Initialize the workspace
workspace = Workspace("PetiteIA", "1")
controller = CtrlPlaceCellView(workspace)

# The robot position relative the place cell
workspace.memory.body_memory.body_quaternion = Quaternion.from_z_rotation(math.pi/6)
workspace.memory.body_memory.head_direction_rad = math.pi/4
controller.view.robot_rotate = 90 - workspace.memory.body_memory.body_azimuth()
controller.view.update_body_display(workspace.memory.body_memory)

# Place cue
pose_matrix = Matrix44.from_translation([ROBOT_COLOR_SENSOR_X, 0, 0], dtype=float)
e00 = Experience(0, pose_matrix, EXPERIENCE_PLACE, 1, workspace.memory.body_memory.body_quaternion)
cue00 = Cue(e00.id, e00.polar_pose_matrix(), e00.type, e00.clock, e00.color_index, e00.polar_sensor_point())

# Floor cue
pose_matrix = Matrix44.from_translation([ROBOT_FLOOR_SENSOR_X + ROBOT_SETTINGS_4["retreat_distance"][0], 0, 0], dtype=float)
e01 = Experience(1, pose_matrix, EXPERIENCE_FLOOR, 1, workspace.memory.body_memory.body_quaternion)
cue01 = Cue(e01.id, e01.polar_pose_matrix(), e01.type, e01.clock, e01.color_index, e01.polar_sensor_point())

# Add a second affordance
pose_matrix = quaternion_translation_to_matrix(Quaternion.from_z_rotation(math.pi/4), [ROBOT_HEAD_X + 200, 200, 0])
e02 = Experience(2, pose_matrix, EXPERIENCE_ALIGNED_ECHO, 1, workspace.memory.body_memory.body_quaternion)
cue02 = Cue(e02.id, e02.polar_pose_matrix(), e02.type, e02.clock, e02.color_index, e02.polar_sensor_point())

# Create the place cell
place_cell = PlaceCell([0, 0, 0], {cue00.id: cue00, cue01.id: cue01, cue02.id: cue02})

# Load the place cell in place memory
workspace.memory.place_memory.place_cells[0] = place_cell

# Move the robot
interaction = Interaction(Action(ACTION_SWIPE, np.array([0, 300, 0], dtype=float), 0, 1.), OUTCOME_NO_FOCUS, 0)
workspace.memory.clock += 1
enaction = Enaction(interaction, workspace.memory.save())
enaction.outcome = Outcome({'action': ACTION_SWIPE, 'clock': 0, 'duration1': 1000, 'head_angle': 0, 'yaw': 0,
                            'echo_distance': 200})
enaction.terminate()
workspace.memory.update(enaction)

# Display the last cell created
controller.view.update_body_display(workspace.memory.body_memory)
# controller.view.robot_translate = [-200, 0, 0]
last_pc = max(workspace.memory.place_memory.place_cells.keys())
controller.place_cell_id = last_pc
controller.update_cue_displays()
controller.view.set_caption(f"Place Cell {last_pc} at {workspace.memory.place_memory.place_cells[last_pc]}")

pyglet.app.run()
