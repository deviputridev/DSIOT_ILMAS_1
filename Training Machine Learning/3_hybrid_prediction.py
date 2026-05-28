import numpy as np
import pandas as pd
import joblib
from tensorflow.keras.models import load_model
import time

# ==========================================
# 1. LOAD KEDUA MODEL (INTEGRASI)
# ==========================================
path_dir = "/home/kelompoksatu/"

# Load Otak Random Forest
model_rf = joblib.load(path_dir + "rf_model.pkl")

# Load Otak LSTM + Scaler-nya
model_lstm = load_model(path_dir + "lstm_model.h5")
scaler_lstm = joblib.load(path_dir + "lstm_scaler.pkl")

print("INTEGRASI BERHASIL: Model Random Forest & LSTM siap digunakan!")

# Buffer khusus untuk menyimpan 5 data terakhir (kebutuhan LSTM)
data_buffer = []
feature_names = ['moisture', 'moisture_percent', 'ax', 'ay', 'az', 'gx', 'gy', 'gz', 'pitch', 'roll']

def baca_data_sensor_realtime():
    # Simulasi data sensor masuk (Hubungkan dengan sensor aslimu nanti)
    # Susunan list harus urut sesuai isi 'feature_names'
    return [350, 35.5, 0.1, -0.2, 9.8, 0.01, 0.05, -0.02, 25.4, 2.1]

# ==========================================
# 2. LOOP MONITORING UTAMA
# ==========================================
try:
    while True:
        data_sekarang = baca_data_sensor_realtime()
        
        # Masukkan ke antrean buffer untuk LSTM
        data_buffer.append(data_sekarang)
        
        # Jika data belum terkumpul 5, tunggu dulu (RF juga nunggu agar sinkron)
        if len(data_buffer) < 5:
            print(f"Mengisi memori sensor... ({len(data_buffer)}/5)")
            time.sleep(1)
            continue
            
        if len(data_buffer) > 5:
            data_buffer.pop(0) # Buang data tertua (Prinsip FIFO)

        # ------------------------------------------
        # PREDIKSI MODEL 1: RANDOM FOREST (Instan)
        # ------------------------------------------
        # RF hanya butuh 1 data paling terakhir saat ini
        df_rf_input = pd.DataFrame([data_sekarang], columns=feature_names)
        pred_rf = model_rf.predict(df_rf_input)[0]

        # ------------------------------------------
        # PREDIKSI MODEL 2: LSTM (Tren Waktu)
        # ------------------------------------------
        # LSTM butuh ke-5 data di dalam buffer, lalu dinormalisasi
        np_buffer = np.array(data_buffer)
        scaled_buffer = scaler_lstm.transform(np_buffer)
        input_lstm = np.expand_dims(scaled_buffer, axis=0)
        
        pred_lstm_prob = model_lstm.predict(input_lstm, verbose=0)
        pred_lstm = np.argmax(pred_lstm_prob)

        # ------------------------------------------
        # 3. LOGIKA INTEGRASI (SOS / VOTING)
        # ------------------------------------------
        # Aturan Kritis: Jika salah satu bilang BAHAYA (2), status akhir wajib BAHAYA!
        if pred_rf == 2 or pred_lstm == 2:
            status_final = 2
            teks_final = "[SOS] BAHAYA LONGSOR! (Terdeteksi oleh salah satu/kedua model)"
            
        # Jika tidak ada yang bahaya, tapi ada yang bilang WASPADA (1)
        elif pred_rf == 1 or pred_lstm == 1:
            status_final = 1
            teks_final = "WASPADA! Sistem mendeteksi gejala anomali tanah."
            
        # Jika kedua model setuju kondisi aman
        else:
            status_final = 0
            teks_final = "AMAN. Kondisi tanah stabil."

        # Cetak perbandingan prediksi di terminal untuk analisa kelompokmu
        print("\n" + "="*50)
        print(f"[RF Predict]  : {pred_rf}")
        print(f"[LSTM Predict]: {pred_lstm}")
        print(f"[STATUS AKHIR]: {teks_final} (Code: {status_final})")
        print("="*50)
        
        time.sleep(1) # Ambil data tiap 1 detik

except KeyboardInterrupt:
    print("\nMonitoring hibrida dihentikan.")