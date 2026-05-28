# ==========================================
# 1. URUTAN IMPORT
# ==========================================
import psycopg2
import os
import time
import random

import numpy as np
import pandas as pd
import joblib
import tensorflow as tf
from tensorflow.keras.models import load_model

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2' 

# ==========================================
# 2. KONFIGURASI DATABASE (HARDCODED)
# ==========================================
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host="100.115.172.95",        
            port=5432,                    
            user="user_longsor",          
            dbname="db_longsor",    
            password="password_kuat"     
        )
        return conn
    except Exception as e:
        print(f"[!] Gagal sambung ke Database: {e}")
        return None

# ==========================================
# 3. LOAD MODEL AI
# ==========================================
path = './' 
print("\n[Mulai] Memuat AI ke dalam memori...")

try:
    scaler = joblib.load(path + 'lstm_scaler.pkl')
    rf_model = joblib.load(path + 'rf_model.pkl')
    lstm_model = load_model(path + 'lstm_model.h5')
    print("[Sukses] AI berhasil ditrain!\n")
except Exception as e:
    print(f"[!] Gagal memuat file AI: {e}")
    exit()

# ==========================================
# 4. LOOPING UTAMA (PREDIKSI & KIRIM DATA)
# ==========================================
def main():
    conn = get_db_connection()
    if conn is None:
        return

    cursor = conn.cursor()
    print(">>> Sistem Hybrid Prediction Berjalan <<<\n")

    data_buffer = []
    feature_names = ['moisture', 'moisture_percent', 'ax', 'ay', 'az', 'gx', 'gy', 'gz', 'pitch', 'roll']

    try:
        while True:
            # -- A. BACA DATA TERBARU DARI DATABASE --
            cursor.execute("""
                SELECT id, moisture, moisture_percent, ax, ay, az, gx, gy, gz, pitch, roll
                FROM sensor_data
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            row = cursor.fetchone()

            if row is None:
                print("[Tunggu] Belum ada data di database...")
                time.sleep(2)
                continue

            row_id = row[0]
            data_sekarang = list(row[1:])  # moisture s.d. roll

            data_buffer.append(data_sekarang)

            if len(data_buffer) < 5:
                print(f"[Memulai] Kumpulkan data awal LSTM... ({len(data_buffer)}/5)")
                time.sleep(1)
                continue

            if len(data_buffer) > 5:
                data_buffer.pop(0)

            # -- B. PREDIKSI AI --
            df_rf_input = pd.DataFrame([data_sekarang], columns=feature_names)
            rf_pred = rf_model.predict(df_rf_input)[0]

            np_buffer = np.array(data_buffer)
            scaled_buffer = scaler.transform(np_buffer)
            lstm_input = np.expand_dims(scaled_buffer, axis=0)
            lstm_pred_prob = lstm_model.predict(lstm_input, verbose=0)
            lstm_pred = np.argmax(lstm_pred_prob)

            if rf_pred == 2 or lstm_pred == 2:
                status = "BAHAYA"
            elif rf_pred == 1 or lstm_pred == 1:
                status = "WASPADA"
            else:
                status = "AMAN"

            vibration_db = round(
                abs(data_sekarang[2]) + abs(data_sekarang[3]) + abs(data_sekarang[4]), 2
            )

            print(f"[Update] ID:{row_id} | Getaran:{vibration_db} | RF:{rf_pred} | LSTM:{lstm_pred} -> {status}")

            # -- C. UPDATE BARIS TERBARU DI DATABASE --
            cursor.execute("""
                UPDATE sensor_data
                SET status = %s, vibration = %s
                WHERE id = %s
            """, (status, vibration_db, row_id))
            conn.commit()

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[!] Dihentikan.")
    finally:
        cursor.close()
        conn.close()
        print("[!] Koneksi database ditutup.")

if __name__ == "__main__":
    main()