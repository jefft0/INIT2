#include <Arduino_JSON.h>
#include "Step0.h"
#include "../wifi/WifiCat.h"
#include "../../Robot_define.h"
#include "../../Action_define.h"
#include "../../Color.h"
#include "../../Floor.h"
#include "../../Head.h"
#include "../../Imu.h"
#include "../../Interaction.h"
#include "../interactions/Backward.h"
#include "../interactions/Forward.h"
#include "../interactions/Scan.h"
#include "../interactions/Swipe_left.h"
#include "../interactions/Swipe_right.h"
#include "../interactions/Turn_angle.h"
#include "../interactions/Turn_head.h"
#include "../interactions/Turn_left.h"
#include "../interactions/Turn_right.h"

char packetBuffer[UDP_BUFFER_SIZE];

extern Color TCS;
extern Wheel OWM;
extern Floor FCR;
extern Head HEA;
extern Imu IMU;
extern WifiCat WifiCat;

extern unsigned long action_start_time;
extern unsigned long duration1;
extern unsigned long action_end_time;
extern int interaction_step;
extern char action;
extern String status; // The outcome information used for sequential learning
extern int robot_destination_angle;
extern int head_destination_angle;
extern int target_angle;
extern int target_duration;
extern int target_focus_angle;
extern bool is_focussed;
extern int focus_x;
extern int focus_y;
extern int focus_speed;
extern int clock;
extern int previous_clock;
//extern int shock_event;

extern Interaction* INT;

void Step0()
{
  // Watch the wifi for new action
  digitalWrite(LED_BUILTIN, HIGH); // light the led during transfer
  int len = WifiCat.read(packetBuffer);
  digitalWrite(LED_BUILTIN, LOW);
  if ((len > 1) && (len < 100)) {  // > 0  do not accept single character in the buffer
    //Serial.print("Received action ");
    action = 0;  // Reset the action to rise an error if no action is in the buffer string
    target_angle = 0;
    target_duration = 1000;
    if (len == 1) {  // Not used
      // Single character is the action
      action = packetBuffer[0];
      //Serial.print(action);
    } else {
      // Multiple characters is json
      // https://github.com/arduino-libraries/Arduino_JSON/blob/master/examples/JSONObject/JSONObject.ino
      JSONVar myObject = JSON.parse(packetBuffer);
      // Serial.println(myObject);
      if (myObject.hasOwnProperty("action")) {
        action = ((const char*) myObject["action"])[0];
      }
      if (myObject.hasOwnProperty("angle")) {
        target_angle = (int)myObject["angle"]; // for non-focussed
      }
      if (myObject.hasOwnProperty("focus_x")) {
        focus_x = (int)myObject["focus_x"];
        focus_y = (int)myObject["focus_y"];
        target_focus_angle = atan2(focus_y, focus_x) * 180.0 / M_PI; // Direction of the focus relative to the robot
        is_focussed = true;
      } else {
        is_focussed = false;
      }
      if (myObject.hasOwnProperty("speed")) {
        focus_speed = (int)myObject["speed"]; // Must be positive otherwise multiplication with unsigned long fails
      }
      if (myObject.hasOwnProperty("duration")) {
        target_duration = (int)myObject["duration"]; // for non-focussed
      }
      if (myObject.hasOwnProperty("clock")) {
        clock = (int)myObject["clock"];
      }
    }

    // If received a string with the same clock then resend the outcome
    // (The previous outcome was sent but the PC did not receive it)
    if (clock == previous_clock) {
      //interaction_step = 3;
      if (INT != nullptr)
        INT->send();
    }
    else
    {
      // Delete the previous interaction (Not sure if it is needed)
      if (INT != nullptr)
      {
        delete INT;
        INT = nullptr;
      }
      previous_clock = clock;
      action_start_time = millis();
      action_end_time = millis() + target_duration;
      interaction_step = 1;
      IMU.begin();
      // shock_event = 0; // reset event from previous interaction
      FCR._floor_outcome = 0; // Reset possible floor change when the robot was placed on the floor
      //digitalWrite(LED_BUILTIN, LOW); // for debug
      status = "0";
      switch (action)
      {
        case ACTION_TURN_IN_SPOT_LEFT:
          INT = new Turn_left(TCS, FCR, HEA, IMU, WifiCat, action_end_time, action, clock, is_focussed, focus_x, focus_y,
            focus_speed, target_angle, target_focus_angle);
          break;
        case ACTION_GO_BACK:
          INT = new Backward(TCS, FCR, HEA, IMU, WifiCat, action_end_time, action, clock, is_focussed, focus_x, focus_y,
            focus_speed);
          break;
        case ACTION_TURN_IN_SPOT_RIGHT:
          INT = new Turn_right(TCS, FCR, HEA, IMU, WifiCat, action_end_time, action, clock, is_focussed, focus_x, focus_y,
            focus_speed, target_angle, target_focus_angle);
          break;
        case ACTION_SHIFT_LEFT:
          INT = new Swipe_left(TCS, FCR, HEA, IMU, WifiCat, action_end_time, action, clock, is_focussed, focus_x, focus_y,
            focus_speed);
          break;
        case ACTION_STOP:
          OWM.stopMotion();
          break;
        case ACTION_SHIFT_RIGHT:
          INT = new Swipe_right(TCS, FCR, HEA, IMU, WifiCat, action_end_time, action, clock, is_focussed, focus_x, focus_y,
            focus_speed);
          break;
        case ACTION_TURN_LEFT:
          action_end_time = millis() + 250;
          OWM.turnLeft(SPEED);
          break;
        case ACTION_GO_ADVANCE:
          INT = new Forward(TCS, FCR, HEA, IMU, WifiCat, action_end_time, action, clock, is_focussed, focus_x, focus_y,
            focus_speed);
          break;
        case ACTION_TURN_RIGHT:
          action_end_time = millis() + 250;
          OWM.turnRight(SPEED);
          break;
        case ACTION_ALIGN_HEAD:
          HEA.beginEchoAlignment();
          action_end_time = millis() + 2000;
          break;
        case ACTION_SCAN_DIRECTION:
          INT = new Turn_head(TCS, FCR, HEA, IMU, WifiCat, action_end_time, action, clock, is_focussed, focus_x, focus_y,
            focus_speed, target_angle);
          break;
        case ACTION_ECHO_SCAN:
          INT = new Scan(TCS, FCR, HEA, IMU, WifiCat, action_end_time, action, clock, is_focussed, focus_x, focus_y,
            focus_speed);
          break;
        /*case ACTION_ECHO_COMPLETE:
          HECS.beginEchoScan();
          action_end_time = millis() + 5000;
          break;*/
        case ACTION_ALIGN_ROBOT:
          INT = new Turn_angle(TCS, FCR, HEA, IMU, WifiCat, action_end_time, action, clock, is_focussed, focus_x, focus_y,
            focus_speed, target_angle);
          break;
        default:
          // Unrecognized action (for debug)
          interaction_step = 0;  // remain in step 0
          WifiCat.send("{\"status\":\"T\", \"action\":\"" + String(action) + "\"}");
          break;
      }
    }
  } else {
    if (len > 0) {
      // Unexpected length (for debug)
      WifiCat.send("{\"status\":\"T\", \"char\":\"" + String(len) + "\"}");
    }
  }
}