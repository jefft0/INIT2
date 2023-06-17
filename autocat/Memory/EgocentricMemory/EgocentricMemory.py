import numpy as np
from playsound import playsound
from pyrr import matrix44
from ...Memory.EgocentricMemory.Experience import Experience, EXPERIENCE_LOCAL_ECHO, EXPERIENCE_CENTRAL_ECHO, \
    EXPERIENCE_PLACE, EXPERIENCE_FLOOR, EXPERIENCE_ALIGNED_ECHO, EXPERIENCE_IMPACT
from ...Robot.RobotDefine import ROBOT_COLOR_X, ROBOT_FRONT_X, LINE_X, ROBOT_FRONT_Y, ROBOT_HEAD_X
from ...Decider.Action import ACTION_SCAN, ACTION_FORWARD, ACTION_BACKWARD, ACTION_LEFTWARD, ACTION_RIGHTWARD
import math
import colorsys

EXPERIENCE_PERSISTENCE = 10
FOCUS_MAX_DELTA = 200  # 100 (mm) Maximum delta to keep focus  TODO improve the focus position when impact


class EgocentricMemory:
    """Stores and manages the egocentric memory"""

    def __init__(self):
        self.focus_point = None  # The point where the agent is focusing
        self.prompt_point = None  # The point where the agent is prompted do go
        self.experiences = {}
        self.experience_id = 0  # A unique ID for each experience in memory

    def manage_focus(self, enacted_enaction):
        """Manage focus catch, lost, or update. Also move the prompt"""
        if self.focus_point is not None:
            # If focussed then adjust the displacement
            # The new estimated position of the focus point
            displacement_matrix = enacted_enaction.displacement_matrix
            translation = enacted_enaction.translation
            rotation_matrix = enacted_enaction.rotation_matrix
            if enacted_enaction.echo_point is not None:
                action_code = enacted_enaction.action.action_code
                prediction_focus_point = matrix44.apply_to_vector(displacement_matrix, self.focus_point)
                # The error between the expected and the actual position of the echo
                prediction_error_focus = prediction_focus_point - enacted_enaction.echo_point

                if np.linalg.norm(prediction_error_focus) < FOCUS_MAX_DELTA:
                    # The focus has been kept
                    enacted_enaction.is_focussed = True
                    # If the action has been completed
                    if enacted_enaction.duration1 >= 1000:
                        # If the head is forward then correct longitudinal displacements
                        if -20 < enacted_enaction.head_angle < 20:
                            if action_code in [ACTION_FORWARD, ACTION_BACKWARD]:
                                translation[0] = translation[0] + prediction_error_focus[0]
                                # TODO pass the action to correct the estimated speed:
                                # self.workspace.actions[action_code].adjust_translation_speed(translation)
                        # If the head is sideways then correct lateral displacements
                        if 60 < enacted_enaction.head_angle or enacted_enaction.head_angle < -60:
                            if action_code in [ACTION_LEFTWARD, ACTION_RIGHTWARD]:
                                translation[1] = translation[1] + prediction_error_focus[1]
                                # TODO pass the action to correct the estimated speed:
                                # self.workspace.actions[action_code].adjust_translation_speed(translation)
                        # Update the displacement matrix according to the new translation
                        translation_matrix = matrix44.create_from_translation(-translation)
                        displacement_matrix = matrix44.multiply(rotation_matrix, translation_matrix)
                        enacted_enaction.translation = translation
                        enacted_enaction.displacement_matrix = displacement_matrix

                        # If the focus was kept then update it
                        # if 'focus' in enacted_interaction:
                        # if 'echo_xy' in enacted_interaction:  # Not sure why this is necessary
                        # self.focus_point = np.array([enacted_interaction['echo_xy'][0],
                        #                              enacted_interaction['echo_xy'][1], 0])
                    self.focus_point = enacted_enaction.echo_point
                    print("UPDATE FOCUS by delta", prediction_error_focus)
                    # If the focus was lost then reset it
                else:
                    # The focus was lost, override the echo outcome
                    print("LOST FOCUS due to delta", prediction_error_focus)
                    enacted_enaction.lost_focus = True  # Used by agent_circle
                    self.focus_point = None
                    # playsound('autocat/Assets/R5.wav', False)
            else:
                # The focus was lost, override the echo outcome
                print("LOST FOCUS due to no echo")
                enacted_enaction.lost_focus = True  # Used by agent_circle
                self.focus_point = None
                # playsound('autocat/Assets/R5.wav', False)
        else:
            if enacted_enaction.action.action_code in [ACTION_SCAN, ACTION_FORWARD] and enacted_enaction.echo_point is not None:
                # Catch focus
                # playsound('autocat/Assets/R11.wav', False)
                self.focus_point = enacted_enaction.echo_point
                print("CATCH FOCUS", self.focus_point)

        # Impact or block catch focus
        if enacted_enaction.impact > 0 or enacted_enaction.blocked:
            if enacted_enaction.echo_point is not None:
                self.focus_point = enacted_enaction.echo_point
            else:
                self.focus_point = np.array([ROBOT_FRONT_X, 0, 0])
            # Reset lost focus because because DecideCircle must trigger a scan
            enacted_enaction.lost_focus = False
            print("CATCH FOCUS IMPACT", self.focus_point)

        # Move the prompt
        if self.prompt_point is not None:
            self.prompt_point = matrix44.apply_to_vector(enacted_enaction.displacement_matrix, self.prompt_point).astype(int)
            print("Prompt moved to egocentric: ", self.prompt_point)

    def update_and_add_experiences(self, enacted_enaction, body_direction_rad):
        """ Process the enacted interaction to update the egocentric memory
        - Move the previous experiences
        - Add new experiences
        """

        last_experience_id = self.experience_id
        # Move the existing experiences
        for experience in self.experiences.values():
            experience.displace(enacted_enaction.displacement_matrix)

        # Add the PLACE experience with the sensed color
        place_exp = Experience(ROBOT_COLOR_X, 0, EXPERIENCE_PLACE, body_direction_rad, enacted_enaction.clock,
                               self.experience_id, durability=EXPERIENCE_PERSISTENCE,
                               color_index=enacted_enaction.color_index)
        self.experiences[place_exp.id] = place_exp
        self.experience_id += 1

        # The FLOOR experience
        if enacted_enaction.floor > 0:
            if enacted_enaction.floor == 0b01:
                # Black line on the right
                experience_x, experience_y = LINE_X, 0  # 100, 0  # 20
            elif enacted_enaction.floor == 0b10:
                # Black line on the left
                experience_x, experience_y = LINE_X, 0  # 100, 0  # -20
            else:
                # Black line on the front
                experience_x, experience_y = LINE_X, 0
            # Place the experience point
            floor_exp = Experience(experience_x, experience_y, EXPERIENCE_FLOOR, body_direction_rad,
                                   enacted_enaction.clock, experience_id=self.experience_id,
                                   durability=EXPERIENCE_PERSISTENCE, color_index=enacted_enaction.color_index)
            self.experiences[floor_exp.id] = floor_exp
            self.experience_id += 1

        # The ALIGNED_ECHO experience
        if enacted_enaction.echo_point is not None:
            aligned_exp = Experience(enacted_enaction.echo_point[0], enacted_enaction.echo_point[1],
                                     EXPERIENCE_ALIGNED_ECHO, body_direction_rad,
                                     enacted_enaction.clock, experience_id=self.experience_id,
                                     durability=EXPERIENCE_PERSISTENCE, color_index=enacted_enaction.color_index)
            self.experiences[aligned_exp.id] = aligned_exp
            self.experience_id += 1

        # The IMPACT experience
        if enacted_enaction.impact > 0:
            if enacted_enaction.impact == 0b01:  # Impact on the right
                experience_x, experience_y = ROBOT_FRONT_X, -ROBOT_FRONT_Y
            elif enacted_enaction.impact == 0b11:  # Impact on the front
                experience_x, experience_y = ROBOT_FRONT_X, 0
            else:  # Impact on the left
                experience_x, experience_y = ROBOT_FRONT_X, ROBOT_FRONT_Y
            impact_exp = Experience(experience_x, experience_y, EXPERIENCE_IMPACT, body_direction_rad,
                                    enacted_enaction.clock, experience_id=self.experience_id,
                                    durability=EXPERIENCE_PERSISTENCE, color_index=enacted_enaction.color_index)
            self.experiences[impact_exp.id] = impact_exp
            self.experience_id += 1

        # The BLOCKED experience, only if move forward
        if enacted_enaction.blocked and enacted_enaction.action.action_code == ACTION_FORWARD:
            blocked_exp = Experience(ROBOT_FRONT_X, 0, EXPERIENCE_IMPACT, body_direction_rad,
                                     enacted_enaction.clock, experience_id=self.experience_id,
                                     durability=EXPERIENCE_PERSISTENCE, color_index=enacted_enaction.color_index)
            self.experiences[blocked_exp.id] = blocked_exp
            self.experience_id += 1

        # The LOCAL ECHO experiences
        local_echos = []
        for e in enacted_enaction.echos.items():
            angle = math.radians(int(e[0]))
            x = ROBOT_HEAD_X + math.cos(angle) * e[1]
            y = math.sin(angle) * e[1]
            local_exp = Experience(x, y, EXPERIENCE_LOCAL_ECHO, body_direction_rad,
                                   enacted_enaction.clock, experience_id=self.experience_id,
                                   durability=EXPERIENCE_PERSISTENCE, color_index=enacted_enaction.color_index)
            self.experiences[local_exp.id] = local_exp
            self.experience_id += 1
            local_echos.append((angle, e[1], local_exp))


        # Create new experiences from points in the enacted_interaction
        # for p in enacted_enaction.enacted_points:
        #     experience = Experience(p[1], p[2], p[0], body_direction_rad, enacted_enaction.clock,
        #                             experience_id=self.experience_id, durability=EXPERIENCE_PERSISTENCE,
        #                             color_index=color_index)
        #     # new_experiences.append(experience)
        #     self.experiences[experience.id] = experience
        #     self.experience_id += 1

        # Add the central echos from the local echos
        # echos = [e for e in self.experiences.values() if e.type == EXPERIENCE_LOCAL_ECHO and e.id > last_experience_id]
        self.add_central_echos(local_echos)
        # for e in central_echos:
        #     self.experiences[e.id] = e

        # Remove the experiences from egocentric memory when they are two old
        # self.experiences = [e for e in self.experiences if e.clock >= enacted_interaction["clock"] - e.durability]

    # def revert_echoes_to_angle_distance(self, echo_list):
    #     """Convert echo interaction to triples (angle,distance,interaction)"""
    #     # TODO use the angle and the distance from the head
    #     output = []
    #     for elem in echo_list:
    #         # compute the angle using elem x and y
    #         angle = math.atan2(elem.point[1], elem.point[0])
    #         # compute the distance using elem x and y
    #         distance = math.sqrt(elem.point[0] ** 2 + elem.point[1] ** 2)
    #         output.append((angle, distance, elem))
    #     return output

    def add_central_echos(self, echos):
        """In case of a sweep we obtain an array of echo, this function discretizes
        it to try to find the real position of the objects that sent back the echo

        To do so use 'strikes' which are series of consecutive echoes that are
        close enough to be considered as the same object, and consider that the
        real position of the object is at the middle of the strike"""
        # experiences_central_echo = []
        if len(echos) == 0:
            return
        body_direction_rad = echos[0][2].absolute_direction_rad
        clock = echos[0][2].clock
        # echos = self.revert_echoes_to_angle_distance(echos)
        max_delta_dist = 160
        max_delta_angle = math.radians(20)
        streaks = [[], [], [], [], [], [], [], [], [], [], [], []]
        angle_dist = [[], [], [], [], [], [], [], [], [], [], [], []]
        current_id = 0
        echos = sorted(echos, key=lambda elem: elem[0])  # on trie par angle, pour avoir les streak "préfaites"
        for angle, distance, interaction in echos:
            check = False
            for i, streak in enumerate(streaks):
                if len(streak) > 0 and not check:
                    if any((abs(ele[1] - distance) < max_delta_dist and abs(angle - ele[0]) < max_delta_angle) for ele in
                           streak):
                        streak.append((angle, distance, interaction))
                        angle_dist[i].append((math.degrees(angle), distance))
                        check = True
            if check:
                continue
            if len(streaks[current_id]) == 0:
                streaks[current_id].append((angle, distance, interaction))
                angle_dist[current_id].append((math.degrees(angle), distance))
            else:
                current_id = (current_id + 1)
                streaks[current_id].append((angle, distance, interaction))
                angle_dist[current_id].append((math.degrees(angle), distance))
        for streak in streaks:
            if len(streak) == 0:
                continue
            else:
                x_mean, y_mean = 0, 0
                if len(streak) % 2 == 0:
                    # Compute the means of x and y values for the two elements at the center of the array
                    x_mean = (streak[int(len(streak) / 2)][2].point[0] + streak[int(len(streak) / 2) - 1][2].point[0]) / 2
                    y_mean = (streak[int(len(streak) / 2)][2].point[1] + streak[int(len(streak) / 2) - 1][2].point[1]) / 2
                else:
                    # The x and y are at the center of the array
                    x_mean = streak[int(len(streak) / 2)][2].point[0]
                    y_mean = streak[int(len(streak) / 2)][2].point[1]
                experience_central_echo = Experience(int(x_mean), int(y_mean), EXPERIENCE_CENTRAL_ECHO,
                                                     body_direction_rad, clock, experience_id=self.experience_id,
                                                     durability=5)
                self.experiences[experience_central_echo.id] = experience_central_echo
                self.experience_id += 1
                # experiences_central_echo.append(experience_central_echo)
        # return experiences_central_echo

    def save(self):
        """Return a deep clone of egocentric memory for simulation"""
        saved_egocentric_memory = EgocentricMemory()
        if self.focus_point is not None:
            saved_egocentric_memory.focus_point = self.focus_point.copy()
        if self.prompt_point is not None:
            saved_egocentric_memory.prompt_point = self.prompt_point.copy()
        saved_egocentric_memory.experiences = {key: e.save() for key, e in self.experiences.items()}
        saved_egocentric_memory.experience_id = self.experience_id
        return saved_egocentric_memory
