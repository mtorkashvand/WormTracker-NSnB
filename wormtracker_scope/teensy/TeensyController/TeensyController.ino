#include <AccelStepper.h>


#define N_RESET_SLEEP 2
#define MS3 3
#define MS2 4
#define MS1 5
#define N_ENABLE 6
#define LED 21
#define LASER 23

AccelStepper stepperX(AccelStepper::DRIVER,1,0);
AccelStepper stepperY(AccelStepper::DRIVER,8,7);
AccelStepper stepperZ(AccelStepper::DRIVER,15,14);


float xspeed, yspeed, zspeed;
long x,y,z;
char *comBuf;
int nChar;

void setStepMode(int axis, int mode)
{
  if (mode == 0){
    digitalWrite(MS1 + 7*axis, 0); 
    digitalWrite(MS2 + 7*axis, 0); 
    digitalWrite(MS3 + 7*axis, 0); 
  } 
  if (mode == 1){
    digitalWrite(MS1 + 7*axis, 1); 
    digitalWrite(MS2 + 7*axis, 0); 
    digitalWrite(MS3 + 7*axis, 0); 
  }
  if (mode == 2){
    digitalWrite(MS1 + 7*axis, 0); 
    digitalWrite(MS2 + 7*axis, 1); 
    digitalWrite(MS3 + 7*axis, 0); 
  }
  if (mode == 3){
    digitalWrite(MS1 + 7*axis, 1); 
    digitalWrite(MS2 + 7*axis, 1); 
    digitalWrite(MS3 + 7*axis, 0); 
  }
  if (mode == 4){
    digitalWrite(MS1 + 7*axis, 0); 
    digitalWrite(MS2 + 7*axis, 0); 
    digitalWrite(MS3 + 7*axis, 1); 
  }
  if (mode == 5){
    digitalWrite(MS1 + 7*axis, 1); 
    digitalWrite(MS2 + 7*axis, 1); 
    digitalWrite(MS3 + 7*axis, 1); 
  }
}


void setup()
{
  Serial.begin(115200);
  for (int j=0; j<25; j++)
    pinMode(j, OUTPUT);

  stepperX.setMaxSpeed(1000.0);
  stepperY.setMaxSpeed(1000.0);
  stepperZ.setMaxSpeed(1000.0);
  stepperX.setAcceleration(50000.0);
  stepperY.setAcceleration(50000.0);
  stepperZ.setAcceleration(5000.0);
  stepperX.setSpeed(0.0);
  stepperY.setSpeed(0.0);
  stepperZ.setSpeed(0.0);
  
  setStepMode(0,5);
  setStepMode(1,5);
  setStepMode(2,5);
  
  comBuf = (char*) malloc(24);
  nChar=0;
}

void loop()
{
  if (Serial.available()>0)
  {
    Serial.readBytes(comBuf+nChar, 1);
    nChar++;  
    if (comBuf[nChar-1] == '\n')
    {
      if (comBuf[0] == 'l')
      {
        if (comBuf[1] == '0') digitalWrite(LED, LOW);
        else if (comBuf[1] == '1') digitalWrite(LED, HIGH);
      }
      else if (comBuf[0] == 'v')
      {
        if (comBuf[1] == 'x') stepperX.setSpeed(atof(comBuf+2));
        else if (comBuf[1] == 'y') stepperY.setSpeed(atof(comBuf+2));
        else if (comBuf[1] == 'z') stepperZ.setSpeed(atof(comBuf+2));
      }
      else if (comBuf[0] == 'q')
      {
        stepperX.setSpeed(0);
        stepperY.setSpeed(0);
        stepperZ.setSpeed(0);
        for (int j=0; j<3; j++)
        {

          digitalWrite(N_RESET_SLEEP +7*j,LOW);
          digitalWrite(N_ENABLE +7*j,HIGH);
        }
      }
      else if (comBuf[0] == 'e')
      {
        for (int j=0; j<3; j++)
        {
          digitalWrite(N_RESET_SLEEP +7*j,HIGH);
          digitalWrite(N_ENABLE +7*j,LOW);
        }
        stepperX.setSpeed(0);
        stepperY.setSpeed(0);
        stepperZ.setSpeed(0);
        stepperX.setCurrentPosition(0);
        stepperY.setCurrentPosition(0);
        stepperZ.setCurrentPosition(0);
      }
      nChar = 0;
      
      x=stepperX.currentPosition();
      y=stepperY.currentPosition();
      z=stepperZ.currentPosition();
      Serial.print(x);
      Serial.print(" ");
      Serial.print(y);
      Serial.print(" ");
      Serial.print(z);
      Serial.print("\n");
      Serial.send_now();
    }
  }
  x=stepperX.currentPosition();
  y=stepperY.currentPosition();
  z=stepperZ.currentPosition();
  xspeed=stepperX.speed();
  yspeed=stepperY.speed();
  zspeed=stepperZ.speed();
  
  if (x >  18000 && xspeed > 0) stepperX.setSpeed(0);
  if (x < -25000 && xspeed < 0) stepperX.setSpeed(0);
  if (y >  18000 && yspeed > 0) stepperY.setSpeed(0);
  if (y < -18000 && yspeed < 0) stepperY.setSpeed(0);
  if (z >  20000 && zspeed > 0) stepperZ.setSpeed(0);
  if (z <      0 && zspeed < 0) stepperZ.setSpeed(0);
  
  stepperX.runSpeed();
  stepperY.runSpeed();
  stepperZ.runSpeed();
}
