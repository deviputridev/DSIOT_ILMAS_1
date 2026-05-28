import json
import psycopg2
import paho.mqtt.client as mqtt

DB_HOST = "100.115.172.95"
DB_NAME = "db_longsor"
DB_USER = "user_longsor"
DB_PASS = "password_kuat"
DB_PORT = 5432

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())

        conn = psycopg2.connect(
            host="100.115.172.95",
            database="db_longsor",
            user="user_longsor",
            password="password_kuat",
            port=5432
        )
        cur = conn.cursor()

        vibration = round(
            abs(data.get("ax", 0)) + abs(data.get("ay", 0)) + abs(data.get("az", 0)), 2
        )

        query = """
        INSERT INTO sensor_data
        (moisture, moisture_percent, ax, ay, az, gx, gy, gz, pitch, roll, vibration, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(query, (
            data.get("moisture"),
            data.get("moisture_percent"),
            data.get("ax"), data.get("ay"), data.get("az"),
            data.get("gx"), data.get("gy"), data.get("gz"),
            data.get("pitch"), data.get("roll"),
            vibration,
            "UNKNOWN" 
        ))

        conn.commit()
        print("Data berhasil masuk sensor_data")
        cur.close()
        conn.close()

    except Exception as e:
        print("ERROR:", e)

client = mqtt.Client()
client.on_message = on_message

client.connect("localhost", 1883, 60)

client.subscribe("datasensor/data")

print("Menunggu data MQTT dari ESP32...")

client.loop_forever()