// Libraries
#include <dimmable_light.h>
#include "DHT.h"
#include <PID_v1.h>
#include <SoftwareSerial.h>

// Define PINs
#define zcPIN 2
#define psmPIN 3
#define DHT22_1_PIN 11  
#define DHT22_2_PIN 10  
#define DHT22_3_PIN 9 
#define DHT22_4_PIN 8 
#define fanPIN_1 4
#define fanPIN_2 7
#define RX_PIN 12  //might need to change
#define TX_PIN 13 //might need to change

// Initiate objects
DHT dht22_1(DHT22_1_PIN,DHT22);
DHT dht22_2(DHT22_2_PIN,DHT22);
DHT dht22_3(DHT22_3_PIN,DHT22);
DHT dht22_4(DHT22_4_PIN,DHT22);
DimmableLight light(psmPIN);
SoftwareSerial espSerial(RX_PIN, TX_PIN);

// Constants 
const unsigned long refreshTime = 2000; //milliseconds
const int dPower_MaxP = 160; // Max output is 255 by default, but its too hot for the box
const double startDiffTemp = 2.5; 

// Changing variables
double setPoint = 32;
double dht22_1_t = 0;
double dht22_2_t = 0;
double dht22_3_t = 0;
double dht22_4_t = 0;
double meanTemp = NAN;
unsigned long time = 0;
unsigned long _lastreadtime = 0;
int dPower = 0;
double dPowerdb = 0; //for PID function, needs double type
int fansOutput = LOW;
bool start = true; //usually "true" for max power at start
int chosenSensor = 1; // [1 = DHT22_1, 2 = DHT22_2, 3 = DHT22_3, 4 = DHT22_4, 5 = Mean of all four]
double *defaultSensor = &dht22_1_t; //needs to be changed to specified sensor
double *pTempSensor = defaultSensor;
bool readSuccess_dht22_1_t = true;
bool readSuccess_dht22_2_t = true;
bool readSuccess_dht22_3_t = true;
bool readSuccess_dht22_4_t = true;
bool *pReadSuccess = &readSuccess_dht22_1_t;

// Temperature stabilization startup phase specific variables
bool stabilizeP = false;
const int stabilizeSlopeTime = 32; //seconds between slope maximum same values
const int stabLoops = stabilizeSlopeTime*1000/refreshTime;
double pTempArray[stabLoops];


//PID parameters
double Kp = 55.0;
double Ki = 0.2;
double Kd = 29.1;
PID myPID(pTempSensor, &dPowerdb, &setPoint, Kp, Ki, Kd, DIRECT);

void setup(){

  Serial.begin(115200);
  espSerial.begin(115200);
  Serial.println();
  Serial.print("Initializing DimmableLight library... ");
  DimmableLight::setSyncPin(zcPIN);
  DimmableLight::begin();
  Serial.println("Done!");
  printStartUpText();
  
  pinMode(fanPIN_1,OUTPUT);
  pinMode(fanPIN_2,OUTPUT);
  digitalWrite(fanPIN_1,HIGH);
  digitalWrite(fanPIN_2,HIGH);
  myPID.SetSampleTime(refreshTime);
  myPID.SetOutputLimits(0, dPower_MaxP);

  delay(refreshTime);
  readTempData(); // call once to avoid first scan error in loop
  myPID.SetMode(AUTOMATIC); //turn the PID on
}

void loop()
{
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');  // Read the value from serial
    input.trim();

    if (input.startsWith("setpoint:")) {  // Ensure not empty message
      String subInput = input.substring(9);
      subInput.trim();
      double setpointValue = subInput.toDouble();
      setPoint = setpointValue;
    }
    else if (input.startsWith("sensor:")){
      String subInput = input.substring(7);
      subInput.trim();
      int newSensor = subInput.toInt();
      if (newSensor >= 1 && newSensor <= 5){  // 1-4 are individual sensors, 5 is mean
        chosenSensor = newSensor;
        //updateSensorSelection(chosenSensor);
        }
    }
  }
  //Limit refresh rate, 2 sec from DHT22 datasheet
  if (millis() - _lastreadtime >= refreshTime){
    readTempData();

    if(stabilizeP){
      dPowerdb = 0;
      if (pTempArray[stabLoops-1] <= pTempArray[0]){
        stabilizeP = false;
      }
    }
    
    if(start){
      if(setPoint - *pTempSensor > startDiffTemp){
        startingPhase();
      }
      else{
        start = false;
        stabilizeP = true;
      }
    }

    if(!start && !stabilizeP){
      myPID.Compute();
    }
  
    dPower = dPowerdb;
    light.setBrightness(dPower);
    printText();
  }
}

double getMeanTemperature() {
    double meanTemp = 0;
    int validSensors = 0;

    // Sum up the temperatures of valid sensors
    if (!isnan(dht22_1_t)) {
        validSensors++;
        meanTemp += dht22_1_t;
    }
    if (!isnan(dht22_2_t)) {
        validSensors++;
        meanTemp += dht22_2_t;
    }
    if (!isnan(dht22_3_t)) {
        validSensors++;
        meanTemp += dht22_3_t;
    }
    if (!isnan(dht22_4_t)) {
        validSensors++;
        meanTemp += dht22_4_t;
    }

    // Calculate the mean only if there are valid sensors
    if (validSensors > 0) {
        meanTemp /= validSensors;
    }
    return meanTemp;
}

void updateSensorSelection(int sensorChoice) {
    switch (sensorChoice) {
        case 1: pTempSensor = &dht22_1_t; break;
        case 2: pTempSensor = &dht22_2_t; break;
        case 3: pTempSensor = &dht22_3_t; break;
        case 4: pTempSensor = &dht22_4_t; break;
        case 5: pTempSensor = &meanTemp; break;
        default: pTempSensor = defaultSensor; break;  // Fallback to default sensor
    }
}


void startingPhase(){
  dPowerdb = dPower_MaxP;
}


void readTempData() {
  
      //DHT22_1
     dht22_1_t = dht22_1.readTemperature();
     if (isnan(dht22_1_t)) {
        readSuccess_dht22_1_t = false;
        Serial.println(F("Failed to read from DHT22_1 sensor!!"));
      }

      //DHT22_2
     dht22_2_t = dht22_2.readTemperature();
     if (isnan(dht22_2_t)) {
        readSuccess_dht22_2_t = false;
        Serial.println(F("Failed to read from DHT22_2 sensor!!"));
      }

      //DHT22_3
     dht22_3_t = dht22_3.readTemperature();
     if (isnan(dht22_3_t)) {
        readSuccess_dht22_3_t = false;
        Serial.println(F("Failed to read from DHT22_3 sensor!!"));
      }

      //DHT22_4
     dht22_4_t = dht22_4.readTemperature();
     if (isnan(dht22_4_t)) {
        readSuccess_dht22_4_t = false;
        Serial.println(F("Failed to read from DHT22_4 sensor!!"));
      }


    // Mean temperature of all sensors
      meanTemp = getMeanTemperature();
    
    //TempSensor = dht22_1_t; //needs to be changed for specified sensor
     if (*pReadSuccess){ //needs to be changed for specified sensor
      for (int i = 0; i < stabLoops-1; i++){
        pTempArray[i] = pTempArray[i+1];
       }
       pTempArray[stabLoops-1] = *pTempSensor;
    }
      readSuccess_dht22_1_t = true;
      readSuccess_dht22_2_t = true;
      readSuccess_dht22_3_t = true;
      readSuccess_dht22_4_t = true;


      //time 
      time = millis();
      _lastreadtime = time; 
}

void printStartUpText(){
    Serial.println("Initialize temperature sensors...");
  dht22_1.begin();
  dht22_2.begin();
  dht22_3.begin();
  dht22_4.begin();
  Serial.println("Done!");
  Serial.print("DHT22 Heat Dim Test: Temperature setpoint at\t");
  Serial.print(setPoint);
  Serial.print("\t");
  Serial.print("degrees\t");
  Serial.print("PID reference sensor(s)\t");
  Serial.print(chosenSensor);
  Serial.println();
  Serial.print("pid values:\t");
  Serial.print(Kp);
  Serial.print("\t");
  Serial.print(Ki);
  Serial.print("\t");
  Serial.print(Kd);
  Serial.print("\t");
  Serial.print("Stabilize Temperature Difference:");
  Serial.print("\t");
  Serial.print(startDiffTemp);
  Serial.println();
  Serial.println("Clear sensor data...");
  espSerial.println("Initializing espSerial");
  espSerial.println("Clear sensor data...");
  Serial.println("Wait a few seconds for text to start updating...");
}
void printText(){
  String dataString = "Dim Power:\t" + String(dPower) + 
                      "\tDHT22_1:\t" + String(dht22_1_t, 1) + 
                      "\tDHT22_2:\t" + String(dht22_2_t, 1) + 
                      "\tDHT22_3:\t" + String(dht22_3_t, 1) + 
                      "\tDHT22_4:\t" + String(dht22_4_t, 1) + 
                      "\tTime (ms):\t" + String(time) + 
                      "\t" + String(setPoint) + 
                      "\tChosen sensor:\t" + String(chosenSensor) + 
                      "\tMean temp:\t" + String(meanTemp, 1);
    
    Serial.println(dataString);
    espSerial.println(dataString);
  }