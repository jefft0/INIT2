import numpy as np
import networkx as nx
from pyrr import Matrix44
import copy
from ...Memory.PlaceMemory.PlaceCell import PlaceCell
from ...Memory.PlaceMemory.Cue import Cue
from ...Memory.EgocentricMemory.Experience import EXPERIENCE_COMPASS, EXPERIENCE_NORTH, EXPERIENCE_CENTRAL_ECHO, \
    EXPERIENCE_LOCAL_ECHO, EXPERIENCE_ALIGNED_ECHO
from .PlaceGeometry import nearby_place_cell, transform_estimation_cue_to_cue


class PlaceMemory:
    """The memory of place cells"""
    def __init__(self):
        """Initialize the list of place cells"""
        self.place_cells = {}
        self.place_cell_id = 0  # Incremental cell id (first cell is 1)
        self.place_cell_graph = nx.Graph()
        self.place_cell_distances = dict(dict())
        self.previous_cell_id = 0
        self.current_cell_id = 0  # The place cell where the robot currently is
        self.proposed_correction = np.array([0, 0, 0])  # Proposed correction of robot and place cell position
        self.observe_better = False
        self.graph_start_id = 1  # The first place cell of the current graph to display

    def add_or_update_place_cell(self, memory):
        """Create e new place cell or update the existing one"""

        # The new experiences for place cell
        experiences = [e for e in memory.egocentric_memory.experiences.values() if (e.clock >= memory.clock) and
                       e.type not in [EXPERIENCE_COMPASS, EXPERIENCE_NORTH, EXPERIENCE_CENTRAL_ECHO]]

        # If no place cell then create Place Cell 1
        if self.current_cell_id == 0:
            self.create_place_cell(memory.allocentric_memory.robot_point, experiences)
            return np.array([0, 0, 0])

        # Find the closest cell if any
        existing_id = nearby_place_cell(memory.allocentric_memory.robot_point, self.place_cells)

        # If the robot is near a known cell (the same or another)
        if existing_id > 0:
            # If the cell is fully observed
            if self.place_cells[existing_id].is_fully_observed():
                # Add the new cues except the local echos
                non_echoes = [e for e in experiences if (e.clock >= memory.clock) and e.type != EXPERIENCE_LOCAL_ECHO]
                self.add_cues_relative_to_center(existing_id, memory.allocentric_memory.robot_point, non_echoes)
                # Compute the position adjustment
                local_echoes = [e for e in experiences if (e.clock >= memory.clock) and e.type == EXPERIENCE_LOCAL_ECHO]
                # If a scan has been performed then find the position correction based on local echoes
                if len(local_echoes) > 0:
                    points = np.array([e.polar_point() for e in local_echoes])
                    estimated_robot_point = self.place_cells[existing_id].translation_estimation_echo(points)
                    estimated_allo_robot_point = estimated_robot_point + self.place_cells[existing_id].point
                    # The robot position correction
                    self.proposed_correction[:] = estimated_allo_robot_point - memory.allocentric_memory.robot_point
                    print(f"Position relative to place cell {self.current_cell_id}: "
                          f"{tuple(estimated_robot_point[:2].astype(int))}, "
                          f" propose correction:  {tuple(self.proposed_correction[:2].astype(int))}")
                # If no local echoes then try to adjust the position based on aligned echo
                else:
                    align_experiences = [e for e in memory.egocentric_memory.experiences.values()
                                         if (e.clock >= memory.clock) and e .type == EXPERIENCE_ALIGNED_ECHO]
                    if len(align_experiences) == 1:  # One algine echo experience
                        point = align_experiences[0].polar_point()
                        self.proposed_correction[:] = self.place_cells[existing_id].translation_estimate_aligned_echo(
                            point)
                        print(f"Proposed correction to nearest central echo: "
                              f"{tuple(self.proposed_correction[:2].astype(int))}")
                        # estimated_robot_point = self.place_cells[existing_id].translation_estimate_aligned_echo(point)
                        # estimated_allo_robot_point = estimated_robot_point + self.place_cells[existing_id].point
                        # # The robot position correction
                        # self.proposed_correction[:] = estimated_allo_robot_point - memory.allocentric_memory.robot_point
                        # print(f"Position relative to place cell {self.current_cell_id}: "
                        #       f"{tuple(estimated_robot_point[:2].astype(int))}, "
                        #       f"proposed correction: {tuple(self.proposed_correction[:2].astype(int))}")
            # If the cell is not fully observed
            else:
                # Add the cues including the local echoes
                self.add_cues_relative_to_center(existing_id, memory.allocentric_memory.robot_point, experiences)
                # Recompute the echo curve
                self.place_cells[existing_id].compute_echo_curve()

            # If the robot just moved to an existing place cell
            if existing_id != self.current_cell_id:
                # Add the edge and the distance from the previous place cell to the newly recognized one
                self.place_cell_graph.add_edge(self.current_cell_id, existing_id)
                self.place_cell_distances[existing_id] = {self.current_cell_id: np.linalg.norm(
                    self.place_cells[existing_id].point - self.place_cells[self.current_cell_id].point)}
                self.previous_cell_id = self.current_cell_id
                self.current_cell_id = existing_id
                print(f"Moving from Place {self.previous_cell_id} to existing Place {self.current_cell_id}")
            else:
                print(f"Coming from Place {self.previous_cell_id} and staying at Place {self.current_cell_id}")

        # If the robot is not near a known cell
        else:
            # Create a new place cell
            self.create_place_cell(memory.allocentric_memory.robot_point, experiences)
            print(f"Moving from Place {self.previous_cell_id} to new Place {self.current_cell_id}")

        self.place_cells[self.current_cell_id].last_visited_clock = memory.clock

    def create_place_cell(self, point, experiences):
        """Create a new place cell and add it to the list and to the graph"""
        # Create the cues from the experiences
        cues = []
        for e in experiences:
            cue = Cue(e.id, e.polar_pose_matrix(), e.type, e.clock, e.color_index, e.polar_sensor_point())
            cues.append(cue)
        # The new place cell gets half the confidence of the previous one
        self.previous_cell_id = self.current_cell_id
        if self.previous_cell_id > 0:
            confidence = self.place_cells[self.previous_cell_id].position_confidence // 2
        else:
            confidence = 100
        # Create the place cell from the cues
        self.place_cell_id += 1
        self.place_cells[self.place_cell_id] = PlaceCell(self.place_cell_id, point, cues, confidence)
        self.place_cells[self.place_cell_id].compute_echo_curve()
        # Add the edge and the distance from the previous place cell to the new one
        if self.place_cell_id > 1:  # Don't create Node 0
            self.place_cell_graph.add_edge(self.current_cell_id, self.place_cell_id)
            self.place_cell_distances[self.current_cell_id] = {self.place_cell_id: np.linalg.norm(
                self.place_cells[self.current_cell_id].point - self.place_cells[self.place_cell_id].point)}
        self.current_cell_id = self.place_cell_id

    def probable_place_cell(self, robot_point, points):
        """Return the probability to be on each place cell computed from robot point and local echoes"""
        residual_distances = {}
        for k, p in self.place_cells.items():
            if p.is_fully_observed():
                # The translation to go from the robot to the place
                translation = p.point - robot_point
                # points += translation
                # Measure the distance to transfer the echo points to the cell points (less points must go first)
                reg_p2p, residual_distance = transform_estimation_cue_to_cue(
                    points, [c.point() for c in p.cues if c.type == EXPERIENCE_LOCAL_ECHO]
                )
                residual_distances[k] = residual_distance
                # Return the polar translation from the place cell to the robot
                # Must take the opposite to obtain the polar coordinates of the place cell
                print("Transformation\n", reg_p2p.transformation)
                print(f"Cell {k} expected at: {tuple(translation[0:2].astype(int))}, "
                      f"observed at: {tuple(-reg_p2p.transformation[0:2,3].astype(int))}, "
                      f"residual distance: {residual_distance:.0f}mm")
        if len(residual_distances) > 0:
            most_similar_place_id = min(residual_distances, key=residual_distances.get)
            print(f"Most similar place cell is {most_similar_place_id}")

    def add_cues_relative_to_center(self, place_cell_id, point, experiences):
        """Create the cues relative to the place cell and add them. Return null position correction"""
        # Adjust the cue position to the place cell by adding the relative position of the robot
        d_matrix = Matrix44.from_translation(point - self.place_cells[place_cell_id].point)
        # Create the cues from the experiences and append them to the place cell
        for e in experiences:
            pose_matrix = d_matrix * e.polar_pose_matrix()
            cue = Cue(e.id, pose_matrix, e.type, e.clock, e.color_index, e.polar_sensor_point())
            self.place_cells[place_cell_id].cues.append(cue)
        # Add the cues to the existing place cell
        # self.place_cells[place_cell_id].cues.extend(cues)
        # Recompute the echo curve
        # self.place_cells[place_cell_id].compute_echo_curve()
        # The robot is at this place cell
        # self.current_robot_cell_id = place_cell_id

    def current_place_cell(self):
        """Return the current place cell"""
        if self.current_cell_id > 0:
            return self.place_cells[self.current_cell_id]

    def save(self):
        """Return a clone of place memory for memory snapshot"""
        saved_place_memory = PlaceMemory()
        saved_place_memory.place_cells = {k: p.save() for k, p in self.place_cells.items()}
        saved_place_memory.place_cell_id = self.place_cell_id
        saved_place_memory.place_cell_graph = self.place_cell_graph.copy()
        saved_place_memory.previous_cell_id = self.previous_cell_id
        saved_place_memory.current_cell_id = self.current_cell_id
        saved_place_memory.place_cell_distances = copy.deepcopy(self.place_cell_distances)
        saved_place_memory.observe_better = self.observe_better
        saved_place_memory.proposed_correction[:] = self.proposed_correction
        return saved_place_memory
