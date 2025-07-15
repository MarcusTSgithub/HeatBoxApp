#include <WiFi.h>
#include <FirebaseESP32.h>
#include <NTPClient.h>
#include <time.h>

// Define RX and TX pins
#define RX_PIN 16
#define TX_PIN 17

// Firebase Realtime Database credentials
#define FIREBASE_HOST "heatbox-78006-default-rtdb.europe-west1.firebasedatabase.app"
#define FIREBASE_AUTH "Y1RwNd5ebfXySQu6uzZ2PJ9J9Uo5BBvfZkoDrN5S"

// NTP Time Configuration
const char* ntpServer = "pool.ntp.org";
const long gmtOffset_sec = 0;  // UTC time (no offset)
const int daylightOffset_sec = 0;  // No daylight saving

// Firebase
FirebaseData firebaseData;
FirebaseConfig firebaseConfig;
FirebaseAuth firebaseAuth;
FirebaseJson json;

// WiFi Credentials
const char* ssid = "Marcuss iPhone";
const char* password = "makkeswifi";

// Define sensor data variables
double power, temp1, temp2, temp3, temp4, tempMean, setPoint;
unsigned long timestamp = 0;
int chosenSensor;
bool recentClear = false;

// Setup WiFi and Firebase
void setup() {
  Serial.begin(115200);
  Serial1.begin(115200, SERIAL_8N1, RX_PIN, TX_PIN);

  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }
  Serial.println("\nConnected to WiFi!");
  Serial.println("IP Address: " + WiFi.localIP().toString());

  // Firebase Configuration
  firebaseConfig.host = FIREBASE_HOST;
  firebaseConfig.signer.tokens.legacy_token = FIREBASE_AUTH;
  
  // Initialize Firebase with configuration and auth
  Firebase.begin(&firebaseConfig, &firebaseAuth);
  Firebase.reconnectWiFi(true);

    // Initialize and sync time from NTP
  configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
  Serial.println("Synchronizing time...");
  struct tm timeinfo;
  while (!getLocalTime(&timeinfo)) {
    Serial.println("Failed to obtain time, retrying...");
    delay(2000);
  }
  Serial.println("Time synchronized!");
}

// Function to get the current timestamp (Unix time)
unsigned long getTimestamp() {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    Serial.println("Failed to get time");
    return 0;
  }
  return mktime(&timeinfo);  // Convert to Unix timestamp
}

// Process incoming data
void processData(String data) {
  String tempData = data;

  tempData.trim();
  if (tempData.startsWith("Clear")) {
    Serial.println("Clear command received. Clearing Firebase data...");
    clearDatabase();
    recentClear = true;
    return;
  }
 
  const char* dataString = data.c_str(); // convert string to char array

  // Parse incoming data and store it in variables
  int parsedValues = sscanf(dataString, "Dim Power:\t%lf\tDHT22_1:\t%lf\tDHT22_2:\t%lf\tDHT22_3:\t%lf\tDHT22_4:\t%lf\tTime (ms):\t%lu\t%lf\tChosen sensor:\t%d\tMean temp:\t%lf", 
                            &power, &temp1, &temp2, &temp3, &temp4, &timestamp, &setPoint, &chosenSensor, &tempMean);
}

// Push data to Firebase
void pushDataToFirebase() {
  Serial.println("Sending data to Firebase...");
  bool errorflag = true; 

  // Get current UTC timestamp
  unsigned long utcTimestamp = getTimestamp();

  // Variable Firebase paths
  String powerPath = "/power/";
  String timePath = "/time/";
  String sensorPath = "/sensors/";

// Push data (unique key of timestamp for each new set of data)
  errorflag &= Firebase.setFloat(firebaseData, powerPath + String(timestamp), power);
  errorflag &= Firebase.setFloat(firebaseData, sensorPath + "temp1/" + String(timestamp), temp1);
  errorflag &= Firebase.setFloat(firebaseData, sensorPath + "temp2/" + String(timestamp), temp2);
  errorflag &= Firebase.setFloat(firebaseData, sensorPath + "temp3/" + String(timestamp), temp3);
  errorflag &= Firebase.setFloat(firebaseData, sensorPath + "temp4/" + String(timestamp), temp4);
  errorflag &= Firebase.setFloat(firebaseData, sensorPath + "tempMean/" + String(timestamp), tempMean);
  errorflag &= Firebase.setFloat(firebaseData, timePath + String(timestamp), timestamp);
  errorflag &= Firebase.set(firebaseData, "/lastUpdate", utcTimestamp);

    if (errorflag) {
        Serial.println("All data sent successfully!");
    } else {
        Serial.println("Some data failed to send.");
    }
}

// Clear Firebase database 
void clearDatabase() {
  if (Firebase.deleteNode(firebaseData, "/power")) {
    Serial.println("Power data cleared successfully!");
  } else {
    Serial.println("Failed to clear Power data: " + firebaseData.errorReason());
  }

  if (Firebase.deleteNode(firebaseData, "/sensors")) {
    Serial.println("Sensor data cleared successfully!");
  } else {
    Serial.println("Failed to clear sensor data: " + firebaseData.errorReason());
  }

  if (Firebase.deleteNode(firebaseData, "/time")) {
    Serial.println("Time data cleared successfully!");
  } else {
    Serial.println("Failed to clear Time data: " + firebaseData.errorReason());
  }
}



void loop() {
  static unsigned long lastCheck = 0;
    if (millis() - lastCheck > 20000) {  // check Wifi connection every 20 seconds
      if (WiFi.status() != WL_CONNECTED) {
        Serial.print("Connection lost, reconnecting to WiFi...");
        while (WiFi.status() != WL_CONNECTED) {
          WiFi.disconnect();  // Disconnect and try again
          WiFi.begin(ssid, password);
          delay(5000);  // Wait for 5 seconds before trying again
          Serial.println("Reconnected to WiFi!");
          }
        Serial.println("Reconnected to WiFi!");
      }
      lastCheck = millis();
    }
  
 // Wait for incoming data from Arduino, process it and send to Firebase
  if (Serial1.available() > 0) {
    String data = Serial1.readStringUntil('\n');
    processData(data);  // Process incoming data
    if(recentClear){
      recentClear = false;
    }else{
      pushDataToFirebase();  // Push data to Firebase
    }
  }
}
