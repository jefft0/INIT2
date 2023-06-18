/*
  imu.cpp - library for controlling the GY521 / MPU6050 IMU
  Created by Olivier Georgeon, june 28 2021
  Uses Korneliusz Jarzebski's MPU6050 library provided in the ELEGOO kit
  https://github.com/jarzebski/Arduino-MPU6050
  released into the public domain
*/
#include <Wire.h>
#include "Arduino.h"
#include "Imu.h"
#include "Action_define.h"
#include "Robot_define.h"
#include "src/lib/MPU6050.h"
#include "Action_define.h"
#if ROBOT_COMPASS_TYPE == 1
#include <HMC5883L.h>
#endif
#if ROBOT_COMPASS_TYPE == 2
#include "src/lib/MMC5883.h"
#endif

Imu::Imu()
{
  _next_imu_read_time = 0;
  _yaw = 0;
  //_debug_message = "";
}
void Imu::setup()
{
  #if ROBOT_HAS_MPU6050 == true
  // Initialize MPU6050

  _mpu.begin(MPU6050_SCALE_2000DPS, MPU6050_RANGE_2G);
  // _mpu.begin(MPU6050_SCALE_2000DPS, MPU6050_RANGE_2G);

  //while(!_mpu.begin(MPU6050_SCALE_2000DPS, MPU6050_RANGE_2G))
  //{
  //  Serial.println("Could not find a valid MPU6050 sensor, check wiring!");
  //  Serial.println("You may need to check the WHO_AM_I address in line 54 in library MPU6050.cpp");
  //  delay(500);
  //}

  // Set DLP Filter
  // See https://ulrichbuschbaum.wordpress.com/2015/01/18/using-the-mpu6050s-dlpf/
  _mpu.setDLPFMode(MPU6050_DLPF_4);  // Filter out frequencies over 21 Hz

  // Calibrate gyroscope. The robot must be at rest during calibration.
  // If you don't want calibrate, comment this line.
  _mpu.calibrateGyro();

  // Set threshold sensitivity. Default 3.
  // If you don't want use threshold, comment this line or set 0.
  _mpu.setThreshold(3); // Tried without but gives absurd results

  #else
    #warning "No MPU6050"
  #endif

  #if ROBOT_COMPASS_TYPE > 0

  // Initialize HMC5883L
  _mpu.setI2CMasterModeEnabled(false);
  _mpu.setI2CBypassEnabled(true) ;
  _mpu.setSleepEnabled(false);
  Serial.println("Initialize compass");

  #endif

  #if ROBOT_COMPASS_TYPE == 1

  while (!compass.begin())
  {
    Serial.println("Could not find a valid HMC5883L sensor, check wiring!");
    delay(500);
  }

  // Set measurement range
  compass.setRange(HMC5883L_RANGE_1_3GA);

  // Set measurement mode
  compass.setMeasurementMode(HMC5883L_CONTINOUS);

  // Set data rate
  compass.setDataRate(HMC5883L_DATARATE_30HZ); // HMC5883L_DATARATE_15HZ

  // Set number of samples averaged
  compass.setSamples(HMC5883L_SAMPLES_4); // HMC5883L_SAMPLES_8

  // Set calibration offset. See HMC5883L_calibration.ino
  compass.setOffset(COMPASS_X_OFFSET, COMPASS_Y_OFFSET);
  #endif

  #if ROBOT_COMPASS_TYPE == 2
  Serial.println("Initializing MMC5883");
  compass.begin();
  compass.setOffset(COMPASS_X_OFFSET, COMPASS_Y_OFFSET);
  #endif
}
void Imu::begin()
{
  _yaw = 0;
  _impact_forward = 0;
  _impact_leftwards = 0;
  _impact_rightwards = 0;
  _cycle_count = 0;
  _blocked = false;
  _max_positive_x_acc = 0;
  _min_negative_x_acc = 0;
  _max_positive_y_acc = 0;
  _min_negative_y_acc = 0;
  _max_speed = 0;
  _min_speed = 0;
  _xSpeed = 0;
  _xDistance = 0;
  _max_positive_yaw_left = 0.0;
  _min_negative_yaw_right = 0.0;
}
int Imu::update(int interaction_step)
{
  unsigned long timer = millis();
  if (_next_imu_read_time < timer)
  {
    _next_imu_read_time = timer + IMU_READ_PERIOD;
    _cycle_count++;

    #if ROBOT_HAS_MPU6050 == true
    // Read normalized values
    // Serial.println("Read Acceleration"); // for debug
    Vector normAccel = _mpu.readNormalizeAccel();
    // Serial.println("Read Gyro"); // for debug
    Vector normGyro = _mpu.readNormalizeGyro();
    // Serial.println("end read mpu"); // for debug

    int x_acceleration = -normAccel.XAxis * 100 + ACCELERATION_X_OFFSET;
    int y_acceleration = -normAccel.YAxis * 100 + ACCELERATION_Y_OFFSET;

    // Integrate yaw during the interaction
    float _ZAngle = normGyro.ZAxis * IMU_READ_PERIOD / 1000 * GYRO_COEF;
    _yaw += _ZAngle;

    // During the first step of the interaction, check acceleration
    if (interaction_step == INTERACTION_ONGOING)
    {
      // Record the min acceleration (deceleration) during the interaction to detect impact
      if (x_acceleration < _min_negative_x_acc)
        _min_negative_x_acc =  x_acceleration;

      // Record the max acceleration during the interaction to detect block
      if (x_acceleration > _max_positive_x_acc)
        _max_positive_x_acc =  x_acceleration;

      // Record the min acceleration (deceleration) during the interaction to detect impact
      if (y_acceleration < _min_negative_y_acc)
        _min_negative_y_acc = y_acceleration;

      // Record the max acceleration during the interaction to detect block
      if (y_acceleration > _max_positive_y_acc)
        _max_positive_y_acc =  y_acceleration;

      // Record the max positive yaw during the interaction to detect impact on the left
      if (_ZAngle > _max_positive_yaw_left)
        _max_positive_yaw_left = _ZAngle;

      // Record the min negative yaw during the interaction to detect impact on the right
      if (_ZAngle < _min_negative_yaw_right)
        _min_negative_yaw_right = _ZAngle;

      // Check for turned to the right by more than 1°/s after the first 250ms
      // if ((_ZAngle < -GYRO_SHOCK_THRESHOLD) && (_cycle_count > IMU_ACCELERATION_CYCLES))
        // If moving forward, this will mean collision on the right
        // _impact_forward = B01;

      // Check for x impact or blocked
      if ((x_acceleration < ACCELERATION_IMPACT_THRESHOLD) ||
         (_cycle_count >= IMU_ACCELERATION_CYCLES) && (_max_positive_x_acc < ACCELERATION_BLOCK_THRESHOLD))
      {
        if (_min_negative_yaw_right < -GYRO_IMPACT_THRESHOLD)
          _impact_forward = B01;
        else if (_max_positive_yaw_left > GYRO_IMPACT_THRESHOLD)
          _impact_forward = B10;
        else
          _impact_forward = B11;
      }

      // Check for leftwards impact or blocked (y positive)
      if ((y_acceleration < -100) ||
         (_cycle_count >= IMU_ACCELERATION_CYCLES) && (_max_positive_y_acc < 80))  // 100
        _impact_leftwards = 1;

      // Check for rightwards impact or blocked
      if ((y_acceleration > 100) ||
         (_cycle_count >= IMU_ACCELERATION_CYCLES) && (_min_negative_y_acc > -80))
        _impact_rightwards = 1;

      // Check for turned to the left by more than 1°/s after the first 250ms
      // if ((_ZAngle > GYRO_SHOCK_THRESHOLD) && (_cycle_count > IMU_ACCELERATION_CYCLES))
        // If moving forward, this will mean collision on the left
        // _impact_forward = B10;

      // Check for blocked on the front
      // (the initial acceleration did not pass the threshold)
//      if (_cycle_count >= IMU_ACCELERATION_CYCLES) && (_max_positive_x_acc < ACCELERATION_BLOCK_THRESHOLD)
//      {
//        _impact_forward = B111;  // Stop the motors
//        _blocked = true;
//      }

      // Trying to compute the speed by integrating acceleration (not working)
      _xSpeed += (x_acceleration) * IMU_READ_PERIOD / 100;
      if (_xSpeed > _max_speed) _max_speed = _xSpeed;
      if (_xSpeed < _min_speed) _min_speed = _xSpeed;
      // Trying to compute the distance by integrating the speed (not working)
      _xDistance += _xSpeed * IMU_READ_PERIOD / 1000;
    }
    #endif
  }
  return _impact_forward;
}

int Imu::get_impact_forward()
{
  return _impact_forward;
}

int Imu::get_impact_leftwards()
{
  return _impact_leftwards;
}

int Imu::get_impact_rightwards()
{
  return _impact_rightwards;
}

void Imu::outcome(JSONVar & outcome_object)
{
  // Always return the yaw
  #if ROBOT_HAS_MPU6050 == true
  outcome_object["yaw"] = round(_yaw);
  #endif

  // Always return the compass
  #if ROBOT_COMPASS_TYPE > 0
  read_azimuth(outcome_object);
  #endif
}

void Imu::outcome_forward(JSONVar & outcome_object)
{
  #if ROBOT_HAS_MPU6050 == true
  outcome_object["impact"] = _impact_forward;
  // outcome_object["blocked"] = _blocked;
  outcome_object["max_acc"] = _max_positive_x_acc;
  outcome_object["min_acc"] = _min_negative_x_acc;

  outcome_object["max_yaw"] = round(_max_positive_yaw_left * 100.0);
  outcome_object["min_yaw"] = round(_min_negative_yaw_right * 100.0); // Does not show negative sign of floats!

  // outcome_object["max_speed"] = (int) _max_speed;
  // outcome_object["min_speed"] = (int) _min_speed;
  // outcome_object["distance"] = (int) _xDistance;
  #endif
}

void Imu::outcome_leftwards(JSONVar & outcome_object)
{
  #if ROBOT_HAS_MPU6050 == true
  outcome_object["impact"] = _impact_leftwards;
  outcome_object["max_acc"] = _max_positive_y_acc;
  outcome_object["min_acc"] = _min_negative_y_acc;
  #endif
}

void Imu::outcome_rightwards(JSONVar & outcome_object)
{
  #if ROBOT_HAS_MPU6050 == true
  outcome_object["impact"] = _impact_rightwards;
  outcome_object["max_acc"] = _max_positive_y_acc;
  outcome_object["min_acc"] = _min_negative_y_acc;
  #endif
}

#if ROBOT_COMPASS_TYPE > 0
void Imu::read_azimuth(JSONVar & outcome_object)
{
  Vector norm = compass.readNormalize();

  // Calculate heading
  float heading = atan2(norm.YAxis, norm.XAxis);
  // Serial.println("compass_x: " + String((int)norm.XAxis) + ", compass_y: " + String((int)norm.YAxis));

  // Convert to degrees
  int headingDegrees = round(heading * 180.0/M_PI);

  // Set declination angle on your location and fix heading
  // You can find your declination on: http://magnetic-declination.com/
  // (+) Positive or (-) for negative
  // For Bytom / Poland declination angle is 4'26E (positive)
  // Formula: (deg + (min / 60.0)) / (180 / M_PI) radiant;
  // float declinationAngle = (2.0 + (13.0 / 60.0));
  // heading += declinationAngle;

  headingDegrees += 180;
  if (heading >= 360)
    headingDegrees -= 360;

  outcome_object["compass_x"] = round(norm.XAxis);
  outcome_object["compass_y"] = round(norm.YAxis);
  outcome_object["azimuth"] = headingDegrees;
}
#endif