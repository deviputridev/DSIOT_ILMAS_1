import psycopg2
import os
import time
import warnings

import numpy as np
import pandas as pd
import joblib
import tensorflow as tf

from tensorflow.keras.models import load_model

warnings.filterwarnings('ignore')

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

tf.get_logger().setLevel('ERROR')


DB_CONFIG = {
    "host": "100.115.172.95",
    "port": 5432,
    "user": "user_longsor",
    "dbname": "db_longsor",
    "password": "password_kuat",

   
    "keepalives": 1,
    "keepalives_idle": 30,
    "keepalives_interval": 10,
    "keepalives_count": 5
}


SEQUENCE_LENGTH = 20

SLEEP_INTERVAL = 1


FEATURE_NAMES = [
    'moisture',
    'moisture_percent',
    'ax',
    'ay',
    'az',
    'gx',
    'gy',
    'gz',
    'pitch',
    'roll'
]


LSTM_FEATURES = FEATURE_NAMES

CLASS_NAMES = {
    0: "AMAN",
    1: "WASPADA",
    2: "BAHAYA"
}

print("\nLoading AI models...")

MODEL_PATH = './'

try:

    scaler = joblib.load(
        MODEL_PATH + 'lstm_scaler.pkl'
    )

    rf_model = joblib.load(
        MODEL_PATH + 'rf_model.pkl'
    )

    lstm_model = load_model(
        MODEL_PATH + 'lstm_model.h5',
        compile=False
    )

    print("All AI models loaded.\n")

except Exception as e:

    print(f"[ERROR] Failed loading model: {e}")

    exit()


def get_db_connection():

    try:

        conn = psycopg2.connect(**DB_CONFIG)

        conn.autocommit = False

        return conn

    except Exception as e:

        print(f"[ERROR] Database connection: {e}")

        return None

def load_initial_buffer(cursor):

    print("Loading initial sequence buffer...")

    cursor.execute("""

        SELECT
            moisture,
            moisture_percent,
            ax,
            ay,
            az,
            gx,
            gy,
            gz,
            pitch,
            roll

        FROM sensor_data

        ORDER BY timestamp DESC

        LIMIT %s

    """, (SEQUENCE_LENGTH,))

    rows = cursor.fetchall()

    rows.reverse()

    buffer = [list(r) for r in rows]

    print(f"Loaded {len(buffer)} rows.\n")

    return buffer

def predict_current_status(data_now):

    df_rf = pd.DataFrame(
        [data_now],
        columns=FEATURE_NAMES
    )

    rf_pred = rf_model.predict(df_rf)[0]

    rf_proba = rf_model.predict_proba(df_rf)[0]

    rf_conf = round(
        float(np.max(rf_proba)) * 100,
        2
    )

    return {
        "status": CLASS_NAMES[int(rf_pred)],
        "confidence": rf_conf
    }

def forecast_future(data_buffer):

    df_seq = pd.DataFrame(
        data_buffer,
        columns=FEATURE_NAMES
    )

    sequence = df_seq[LSTM_FEATURES]

    scaled = scaler.transform(sequence)

    lstm_input = np.expand_dims(
        scaled,
        axis=0
    )

    pred = lstm_model.predict(
        lstm_input,
        verbose=0
    )[0]

    pred_class = int(np.argmax(pred))

    lstm_conf = round(
        float(np.max(pred)) * 100,
        2
    )

    return {
        "status": CLASS_NAMES[pred_class],
        "confidence": lstm_conf
    }

def calculate_vibration(data_now):

    vibration = round(

        abs(float(data_now[2])) +
        abs(float(data_now[3])) +
        abs(float(data_now[4])),

        2

    )

    return vibration

def save_result(
    cursor,
    conn,
    row_id,
    current_result,
    forecast_result,
    vibration
):

    try:

        cursor.execute("""

            UPDATE sensor_data

            SET

                status = %s,

                vibration = %s,

                forecast_status = %s,

                forecast_confidence = %s,

                rf_confidence = %s,

                lstm_confidence = %s

            WHERE id = %s

        """, (

            current_result['status'],

            vibration,

            forecast_result['status'],

            forecast_result['confidence'],

            current_result['confidence'],

            forecast_result['confidence'],

            row_id

        ))

        conn.commit()

    except Exception as e:

        conn.rollback()

        print(f"[ERROR] Save database: {e}")


def print_result(
    row_id,
    current_result,
    forecast_result,
    vibration
):

    print(
        f"[ID {row_id}] "
        f"CURRENT: {current_result['status']} "
        f"({current_result['confidence']}%) | "
        f"FORECAST: {forecast_result['status']} "
        f"({forecast_result['confidence']}%) | "
        f"VIBRATION: {vibration}"
    )


def main():

    
    print("AI LANDSLIDE PIPELINE STARTED \n")

    conn = get_db_connection()

    if conn is None:

        return

    cursor = conn.cursor()

    data_buffer = load_initial_buffer(cursor)

    last_id = None

    try:

        while True:

            try:

                conn.rollback()

                cursor.execute("""

                    SELECT
                        id,
                        moisture,
                        moisture_percent,
                        ax,
                        ay,
                        az,
                        gx,
                        gy,
                        gz,
                        pitch,
                        roll

                    FROM sensor_data

                    ORDER BY timestamp DESC

                    LIMIT 1

                """)

                row = cursor.fetchone()

                if row is None:

                    print("[WAIT] No sensor data...")

                    time.sleep(2)

                    continue

                row_id = row[0]

                if row_id == last_id:

                    time.sleep(SLEEP_INTERVAL)

                    continue

                last_id = row_id

                data_now = list(row[1:])

                data_buffer.append(data_now)

                if len(data_buffer) > SEQUENCE_LENGTH:

                    data_buffer.pop(0)

                if len(data_buffer) < SEQUENCE_LENGTH:

                    print(
                        f"[BUFFER] "
                        f"{len(data_buffer)}/"
                        f"{SEQUENCE_LENGTH}"
                    )

                    time.sleep(SLEEP_INTERVAL)

                    continue

                current_result = predict_current_status(
                    data_now
                )

                
                forecast_result = forecast_future(
                    data_buffer
                )

                
                vibration = calculate_vibration(
                    data_now
                )

                
                print_result(
                    row_id,
                    current_result,
                    forecast_result,
                    vibration
                )

                
                save_result(
                    cursor,
                    conn,
                    row_id,
                    current_result,
                    forecast_result,
                    vibration
                )

                time.sleep(SLEEP_INTERVAL)

            except Exception as e:

                print(f"[ERROR] Main loop: {e}")

                time.sleep(3)

    except KeyboardInterrupt:

        print("\n[STOPPED] AI pipeline stopped.")

    finally:

        try:

            cursor.close()

            conn.close()

        except:
            pass

        print("[CLOSED] Database connection closed.")

if __name__ == "__main__":

    main()
