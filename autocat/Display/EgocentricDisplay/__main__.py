import pyglet
from .CtrlEgocentricView import CtrlEgocentricView
from autocat.Display.PointOfInterest import *
from ...Workspace import Workspace
from ...Memory.EgocentricMemory.Experience import Experience, EXPERIENCE_FLOOR


# Displaying EgocentricView with points of interest.
# Allow selecting points of interest and inserting and deleting phenomena
# py -m autocat.Display.EgocentricDisplay
workspace = Workspace()
controller = CtrlEgocentricView(workspace)

# The body position in body memory
workspace.memory.body_memory.set_head_direction_degree(-45)
controller.update_body_robot()

# Add experiences
# experience1 = Experience(150, 0, EXPERIENCE_FLOOR, 0, 0, experience_id=0)
# experience2 = Experience(300, -300, EXPERIENCE_ALIGNED_ECHO, 0, 1, experience_id=1)
# poi1 = controller.create_point_of_interest(experience1)
# poi1 = controller.add_point_of_interest(experience1.point[0], experience1.point[1], experience1.type)
poi1 = controller.add_point_of_interest(150, 0, EXPERIENCE_FLOOR)
controller.points_of_interest.append(poi1)
# poi2 = controller.create_point_of_interest(experience2)
# poi2 = controller.add_point_of_interest(experience2.point[0], experience2.point[1], experience2.type)
poi2 = controller.add_point_of_interest(300, -300, EXPERIENCE_ALIGNED_ECHO)
controller.points_of_interest.append(poi2)

# Test the save method
# experience3 = experience1.save()

pyglet.app.run()
