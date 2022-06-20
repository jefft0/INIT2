import pyglet
from . HexaView import HexaView
from ... Workspace import Workspace
from ... Memory.HexaMemory.HexaMemory import HexaMemory

class CtrlHexaview:
    """Made to work with CtrlWorkspace"""

    def __init__(self, ctrl_workspace):
        self.ctrl_workspace = ctrl_workspace
        self.hexaview = HexaView(hexa_memory = self.ctrl_workspace.workspace.hexa_memory)
        self.refresh_count = 0
        self.mouse_x, self.mouse_y = None, None
        self.inde_cell_projection_done = False
        self.hexa_memory = ctrl_workspace.workspace.hexa_memory
        self.projections_for_context = self.ctrl_workspace.workspace.synthesizer.last_projection_for_context
        self.to_reset = []
        #Handlers
        def on_text_hemw(text):
                if text.upper() == "A" :
                    self.ctrl_workspace.decision_mode = "automatic"
                    print("passage du decider en mode automatique")
                    return
                if text.upper() == "M" :
                    self.ctrl_workspace.decision_mode = "manual"
                    print("passage du decider en mode manual")
                    return
                elif text.upper() == "O" :
                        print("setting synthesizer to automatic mode")
                        self.ctrl_workspace.synthesizer.set_mode("automatic")
                        return
                elif text.upper() == "P" :
                    print("setting synthesizer to manual mode")
                    self.ctrl_workspace.synthesizer.set_mode("manual")
                    return
                elif text.upper() == "R" :
                    self.ctrl_workspace.reset()
                    self.refresh_count = 0
                    return
                if ctrl_workspace.need_user_action and self.inde_cell_projection_done :
                    if text.upper() == "Y":
                        ctrl_workspace.user_action = 'y', None
                        ctrl_workspace.f_user_action_ready = True
                        self.react_to_user_interaction()
                        return
                    elif text.upper() == "N":
                        ctrl_workspace.user_action = 'n', None
                        ctrl_workspace.f_user_action_ready = True
                        self.react_to_user_interaction()
                        return
                    
                elif ctrl_workspace.need_user_to_command_robot:
                    x = self.mouse_x
                    y= self.mouse_y
                    action = text
                    ctrl_workspace.interaction_to_enact = {"action": action}
                    if x is not None and y is not None:
                        ctrl_workspace.interaction_to_enact["x"] = x
                        ctrl_workspace.interaction_to_enact["y"] = y
                    ctrl_workspace.f_interaction_to_enact_ready = True

                    print("intended interaction : ",ctrl_workspace.interaction_to_enact)
                    self.mouse_x = None
                    self.mouse_y = None

                else:
                    message = "Waiting for previous outcome before sending new action" if ctrl_workspace.enact_step != 0 else "Waiting for user action"
                    print(message)

                
        self.hexaview.on_text = on_text_hemw

        def on_mouse_press_hemw(x, y, button, modifiers):
                """ Computing the position of the mouse click in the hexagrid  """
                # Compute the position relative to the center in mm
                if ctrl_workspace.need_user_action and self.inde_cell_projection_done :
                    self.hexaview.mouse_press_x = int((x - self.hexaview.width/2)*self.hexaview.zoom_level*2)
                    self.hexaview.mouse_press_y = int((y - self.hexaview.height/2)*self.hexaview.zoom_level*2)
                    print(self.hexaview.mouse_press_x, self.hexaview.mouse_press_y)
                    cell_x, cell_y = ctrl_workspace.workspace.hexa_memory.convert_pos_in_cell(self.hexaview.mouse_press_x, self.hexaview.mouse_press_y)
                    ctrl_workspace.user_action = 'click',(cell_x,cell_y)
                    ctrl_workspace.f_user_action_ready = True
                    self.react_to_user_interaction()
                else :
                    self.mouse_x = int((x - self.hexaview.width/2)*self.hexaview.zoom_level*2)
                    self.mouse_y = int((y - self.hexaview.height/2)*self.hexaview.zoom_level*2)
        self.hexaview.on_mouse_press = on_mouse_press_hemw

    def react_to_user_interaction(self):
        """blbablal"""
        self.hexaview.indecisive_cell_shape = []
        self.inde_cell_projection_done = False

    def main(self,dt):
        """blaqbla"""
        if self.refresh_count > 500 :
            self.refresh_count = 0
        if self.refresh_count == 0 :
            #print("RESET BASE HEXAVIEW")
            self.hexaview.shapesList = []
            self.hexaview.extract_and_convert_interactions(self.hexa_memory)
            self.hexa_memory.cells_changed_recently = []
        ctrl_workspace = self.ctrl_workspace
        if ctrl_workspace.need_user_action : #and not model.f_inde_cell_projected :
            #print("projection inde_cell")
            self.hexaview.show_indecisive_cell(ctrl_workspace.cell_inde_a_traiter)
            self.inde_cell_projection_done = True
        if len(self.hexa_memory.cells_changed_recently) > 0 :
           projections = self.ctrl_workspace.workspace.synthesizer.last_projection_for_context
           self.hexaview.extract_and_convert_recently_changed_cells(self.hexa_memory,self.to_reset,projections)
           self.to_reset = projections
           self.hexa_memory.cells_changed_recently = []

     

        self.refresh_count +=1