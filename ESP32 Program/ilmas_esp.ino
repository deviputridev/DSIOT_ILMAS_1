#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>


const char* ssid = "MTB MARET 26";
const char* password = "pagarkehidupan";


const char* mqtt_server = "10.51.197.156";

WiFiClient espClient;
PubSubClient client(espClient);


int soilPin = 34;


const int MPU_ADDR = 0x68;
int16_t ax, ay, az, gx, gy, gz;


void setup_wifi() {
  Serial.print("Connecting WiFi");

  WiFi.begin(ssid, password);

  int retry = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
    retry++;

    if (retry > 20) {
      Serial.println("\n Gagal connect WiFi");
      ESP.restart();
    }
  }

  Serial.println("\n WiFi connected");
  Serial.print("IP ESP32: ");
  Serial.println(WiFi.localIP());
}


void reconnect() {
  while (!client.connected()) {
    Serial.print("Connecting MQTT...");

    if (client.connect("ESP32Client")) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" (retry 2s)");
      delay(2000);
    }
  }
}


void setup() {
  Serial.begin(115200);

  setup_wifi();

  client.setServer(mqtt_server, 1883);

  // MPU6050 init
  Wire.begin();
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B);
  Wire.write(0);
  Wire.endTransmission(true);
}


void loop() {

  // cek WiFi
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi putus, reconnect...");
    setup_wifi();
  }

  // cek MQTT
  if (!client.connected()) {
    reconnect();
  }

  client.loop();


  int moisture = analogRead(soilPin);
  float moisture_percent = map(moisture, 4095, 0, 0, 100);

  //Mpu6050
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 14, true);

  ax = Wire.read()<<8 | Wire.read();
  ay = Wire.read()<<8 | Wire.read();
  az = Wire.read()<<8 | Wire.read();
  Wire.read(); Wire.read();
  gx = Wire.read()<<8 | Wire.read();
  gy = Wire.read()<<8 | Wire.read();
  gz = Wire.read()<<8 | Wire.read();

  float pitch = atan2(ax, sqrt(ay*ay + az*az)) * 180/PI;
  float roll  = atan2(ay, sqrt(ax*ax + az*az)) * 180/PI;

  //json
  String payload = "{";
  payload += "\"moisture\":" + String(moisture) + ",";
  payload += "\"moisture_percent\":" + String(moisture_percent) + ",";
  payload += "\"ax\":" + String(ax) + ",";
  payload += "\"ay\":" + String(ay) + ",";
  payload += "\"az\":" + String(az) + ",";
  payload += "\"gx\":" + String(gx) + ",";
  payload += "\"gy\":" + String(gy) + ",";
  payload += "\"gz\":" + String(gz) + ",";
  payload += "\"pitch\":" + String(pitch) + ",";
  payload += "\"roll\":" + String(roll);
  payload += "}";

  // kirim mqtt
  boolean status = client.publish("datasensor/data", payload.c_str());

  Serial.println("==========");
  Serial.println(payload);

  if (status) {
    Serial.println("Terkirim ke MQTT");
  } else {
    Serial.println("Gagal kirim MQTT");
  }

  delay(5000);
}
