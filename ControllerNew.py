import json
from MemoryV1 import MemoryV1
from RobotDefine import *
import threading
from WifiInterface import WifiInterface
from Phenomenon import Phenomenon
import math
from OsoyooCar import OsoyooCar
from EgoMemoryWindowNew import EgoMemoryWindowNew
import pyglet
from pyrr import matrix44
from Interaction import *
from MemoryNew import *
from Agent5 import *

import time


class ControllerNew:
    """Controller of the application
    It is the only object in the application that should have access to every of the following objects :
    Robot, Agent, Memory, View

    It is responsible of the following tasks :
        -Translate Robot datas into Interaction, Outcomes, and position changes (angle, distance)
        -Translate the Agent Actions into Robot Actions, and command the robot to execute them

    It has the following communications :
        VOCABULARY : for a class X wich the Y class (here Controller) communicate with : 
            Ask = X.ask(_) (a method of x is called, and x return a result)
            Send = X.receive(data) (a method of x is called, wich change the inner state of X)
            Receive = X does Y.receive(data)
            It is important to consider that both Ask and Send can be done by a single method
    
        Agent Related :
            - Ask for Action from the Agent 
            - Send Outcomes to the Agent

        Memory Related :
            - Send Interaction to the Memory
            - Send position changes (angle,distance) to the Memory

        View Related :
            - Ask the View to refresh itself after an action from the robot
            - Ask if the User has interacted with the view since the last iteration

        Robot Related :
            - Send Actions to the robot
            - Receive Datas from the robot
    """

    def __init__(self, view, agent, memory):
        # View
        self.view = view
        self.agent = agent
        self.memory = memory

        self.wifiInterface = WifiInterface()
        self.outcome_bytes = b'{"status":"T"}'  # Default status T timeout

        self.outcome = 0
        self.enact_step = 0
        self.action = ""
        """    
        # Model
        
        self.phenomena = []
        self.robot = OsoyooCar(self.view.batch)

       
        
        self.outcome_bytes = b'{"status":"T"}'  # Default status T timeout
        """


    

    
    ################################################# AGENT RELATED #################################################################
       

    def ask_agent_for_action(self,outcome):
        """ Ask for Action from the Agent 
            and Send Outcomes to the Agent
        """
        return self.agent.action(outcome)


    ################################################# MEMORY RELATED #################################################################
    def send_phenom_info_to_memory(self,phenom_info):
        """Send Interaction to the Memory
        """
        self.memory.add(phenom_info)

    def send_position_change_to_memory(self, angle, translation):
        """Send position changes (angle,distance) to the Memory
        """
        self.memory.move(angle, translation)

    ################################################# VIEW RELATED #################################################################
    def ask_view_to_refresh_and_get_last_interaction_from_user(self,memory):
        """ Ask the View to refresh itself after an action from the robot
            Ask if the User has interacted with the view since the last iteration
        """
        return self.view.refresh(memory)

    ################################################# ROBOT RELATED #################################################################

    def command_robot(self,action): #NOT TESTED
        """ Creating an asynchronous thread to send the action to the robot and to wait for outcome """
        self.outcome_bytes = "Waiting"
        def enact_thread():
            """ Sending the action to the robot and waiting for outcome """
            # print("Send " + self.action)
            self.outcome_bytes = self.wifiInterface.enact(self.action)
            print("Receive ", end="")
            print(self.outcome_bytes)
            self.enact_step = 2
            # self.watch_outcome()

        self.action = action
        self.enact_step = 1
        thread = threading.Thread(target=enact_thread)
        thread.start()

        

        #data = self.outcome_bytes
        #return data


    ################################################# SPECIFIC TASKS #################################################################

    def translate_agent_action_to_robot_command(self,action): #NOT IMPLEMENTED, not needed I think
        command = action
        # 0-> '8', 1-> '1', 2-> '3'
        commands = ['8', '1', '3']
        return commands[action]

    def translate_robot_data(self,data): #PAS FINITO ?
        angle = 0
        outcome_for_agent = 0
        phenom_info = (0,0,0,0,None,None)
        translation = [0,0]
        rotation = 0

        json_outcome = json.loads(self.outcome_bytes)

        """ Updating the model from the latest received outcome """
        outcome = json.loads(data)
        floor = 0
        if 'floor' in outcome:
            floor = outcome['floor']
            outcome_for_agent = json_outcome['floor']
        shock = 0
        if 'shock' in outcome:
            shock = outcome['shock']
            outcome_for_agent = json_outcome['shock']
        blocked = 0
        if 'blocked' in outcome:
            blocked = outcome['blocked']
            outcome_for_agent = json_outcome['shock'] #OULAH

        # floor_outcome = outcome['outcome']  # Agent5 uses floor_outcome

        if outcome['status'] == "T":  # If timeout no ego memory update
            print("No ego memory update")
        else:
            # Presupposed displacement of the robot relative to the environment
            translation = [0, 0]
            rotation = 0
            if self.action == "1":
                rotation = 45
            if self.action == "2":
                translation[0] = -STEP_FORWARD_DISTANCE
            if self.action == "3":
                rotation = -45
            if self.action == "4":
                translation[1] = SHIFT_DISTANCE
            if self.action == "6":
                translation[1] = -SHIFT_DISTANCE
            if self.action == "8":
                if not blocked:
                    translation[0] = STEP_FORWARD_DISTANCE * outcome['duration'] / 1000

            # Actual measured displacement if any
            if 'yaw' in outcome:
                rotation = outcome['yaw']

            # Estimate displacement due to floor change retreat
            if floor > 0:  # Black line detected
                # Update the translation
                if self.action == "8":  # TODO Other actions
                    forward_duration = outcome['duration'] - 300  # Subtract retreat duration
                    translation[0] = STEP_FORWARD_DISTANCE * forward_duration/1000 - RETREAT_DISTANCE  # To be adjusted
            angle = rotation


            # Check for collision when moving forward
            if self.action == "8" and floor == 0:
                if blocked:
                    # Create a new pressing interaction
                    wall = Phenomenon(110, 0, self.view.batch, 2, 1) # TODO : oubli
                    self.phenomena.append(wall)
                else:
                    # Create a new blocked interaction
                    if shock == 0b01: # TODO : remettre en literral bit dans la traduction de MemoryNew
                        shock = 1
                        # wall = Phenomenon(110, -80, self.view.batch, 2)
                        # self.phenomena.append(wall)
                    if shock == 0b11:
                        shock = 2
                        # wall = Phenomenon(110, 0, self.view.batch, 2)
                        # self.phenomena.append(wall)
                    if shock == 0b10:
                        shock = 3
                        # wall = Phenomenon(110, 80, self.view.batch, 2)
                        # self.phenomena.append(wall)

            # Update head angle
            if 'head_angle' in outcome:
                head_angle = outcome['head_angle']
                #self.robot.rotate_head(head_angle) TODO: Add robot to view 
                if self.action == "-" or self.action == "*" or self.action == "1" or self.action == "3":
                    # Create a new echo phenomenon
                    echo_distance = outcome['echo_distance']
                    if echo_distance > 0:  # echo measure 0 is false measure
                        x = self.robot.head_x + math.cos(math.radians(head_angle)) * echo_distance
                        y = self.robot.head_y + math.sin(math.radians(head_angle)) * echo_distance
                        obstacle = 1
            #TODO
            """ # Update the azimuth 
            if 'azimuth' in outcome:
                self.view.azimuth = outcome['azimuth']
                        #phenom_info = (floor,shock,blocked,x,y)
            """
            
            phenom_info = (floor,shock,blocked,obstacle,x,y)
            print("DEBUG CONTROLLERNEW OUTCOME_FOR_AGENT :", outcome_for_agent)
        angle = rotation
        return  phenom_info, angle, translation, outcome_for_agent
        
    """################################################# LOOP #################################################################"""

    def loop(self): #NOT IMPLEMENTED: Change of behavior when user interact with view
        print("DEBUG CONTROLLER LOOP, 1")
        self.action = self.ask_agent_for_action(self.outcome) # agent -> decider
        print("DEBUG CONTROLLER LOOP, 2")
        robot_action = self.translate_agent_action_to_robot_command(self.action) # a compléter
        print("DEBUG CONTROLLER LOOP, 3 ")
        #self.command_robot(robot_action)
        self.enact_step = 2 # FOR DEBUG
        print("DEBUG CONTROLLER LOOP, 4")

        while(self.enact_step < 2):   # refresh la vue tant que pas de reponses de command_robot 
            self.view.refresh(memory)

        print("DEBUG CONTROLLER LOOP, 5")
        self.enact_step = 0
        print("DEBUG CONTROLLER LOOP, 6")
        robot_data = self.outcome_bytes
        print("DEBUG CONTROLLER LOOP, 7")
        phenom_info, angle, translation, self.outcome = self.translate_robot_data(robot_data)
        print("DEBUG CONTROLLER LOOP, 8")
        self.send_position_change_to_memory(angle,translation) #Might be an order problem between this line and the one under it, depending on
        print("DEBUG CONTROLLER LOOP, 9")
        self.send_phenom_info_to_memory(phenom_info)                  # when the robot detect interaction (before or after moving)
        print("DEBUG CONTROLLER LOOP, 10")
        user_interaction = None
        user_interaction = self.ask_view_to_refresh_and_get_last_interaction_from_user(self.memory)
        print("DEBUG CONTROLLER LOOP, 11")
        return self.outcome,user_interaction


if __name__ == "__main__":
    view = EgoMemoryWindowNew()
    memory = MemoryV1(view)
    agent = Agent5()
    controller = ControllerNew(view,agent,memory)
    for i in range(10000):
        controller.loop()