/*
  Swipe_left.cpp - library for controlling the move swipe left interaction
  Created by Olivier Georgeon, mai 31 2023
  released into the public domain
*/
#include "../wifi/WifiCat.h"
#include "../../Robot_define.h"
#include "../../Color.h"
#include "../../Floor.h"
#include "../../Head.h"
#include "../../Imu.h"
#include "../../Interaction.h"
#include "../../Action_define.h"
#include "Swipe.h"

Swipe::Swipe(Floor& FLO, Head& HEA, Imu& IMU, WifiCat& WifiCat, JSONVar json_action) :
  Interaction(FLO, HEA, IMU, WifiCat, json_action)
{
}

// STEP 0: Start the interaction
void Swipe::begin()
{
  if (_focus_speed > 0)
    _FLO._OWM.shiftLeft(SHIFT_SPEED);
  else
    _FLO._OWM.shiftRight(SHIFT_SPEED);

  _HEA._next_saccade_time = _action_end_time - SACCADE_DURATION;  // Inhibit HEA during the interaction
  _step = INTERACTION_ONGOING;
}

// STEP 1: Control the enaction
void Swipe::ongoing()
{
  if (_is_focussed)  // Keep the head towards the focus (HEA is inhibited during the action)
    _HEA.turnHead(_HEA.head_direction(_focus_x, _focus_y - _focus_speed * (float)(millis() - _action_start_time)/1000.));
  // Check if Floor Change Retreat
  if (_FLO._is_retreating)
  {
    _FLO.extraDuration(RETREAT_EXTRA_DURATION); // Increase retreat duration because need to reverse speed
    _status ="1";
    // Proceed to step 2 for enacting Floor Change Retreat
    _duration1 = millis()- _action_start_time;
    _action_end_time = _FLO._retreat_end_time + TURN_SPOT_ENDING_DELAY;
    _step = INTERACTION_TERMINATE;
  }
  // If no floor change, check whether duration has elapsed or impact
  else if ((_action_end_time < millis()) || (_IMU.get_impact_leftwards() > 0) && (_focus_speed >= 0)
                                         || (_IMU.get_impact_rightwards() > 0) && (_focus_speed < 0))
  {
    if (!_HEA._is_enacting_head_alignment)
      _HEA.beginEchoAlignment();  // Force HEA
    _duration1 = millis() - _action_start_time;
    _FLO._OWM.stopMotion();
    _step = INTERACTION_TERMINATE;
    _action_end_time = 0;
  }
}

void Swipe::outcome(JSONVar & outcome_object)
{
  if (_focus_speed > 0)
    _IMU.outcome_leftwards(outcome_object);
  else
    _IMU.outcome_rightwards(outcome_object);
}