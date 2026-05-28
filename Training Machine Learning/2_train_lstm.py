import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
import joblib

# 1. Load data yang sudah diberi label
df = pd.read_csv("sensor_data_labeled.csv")

# 2. Pilih Fitur dan Target
features = ['moisture', 'moisture_percent', 'ax', 'ay', 'az', 'gx', 'gy', 'gz', 'pitch', 'roll']
X = df[features].values
y = df['status'].values

# 3. Normalisasi Data (Wajib untuk Deep Learning agar training stabil)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
# Simpan scaler agar bisa dipakai di Raspberry Pi nanti
joblib.dump(scaler, "lstm_scaler.pkl")

# 4. Ubah Data Menjadi Bentuk Sekuensial (Time-Steps)
# Masukkan nilai 5 artinya: model memprediksi status berdasarkan 5 data terakhir secara berurutan
def create_sequences(X_data, y_data, time_steps=5):
    Xs, ys = [], []
    for i in range(len(X_data) - time_steps):
        Xs.append(X_data[i:(i + time_steps)])
        ys.append(y_data[i + time_steps])
    return np.array(Xs), np.array(ys)

X_seq, y_seq = create_sequences(X_scaled, y, time_steps=5)

# 5. Split Data (80% Train, 20% Test)
X_train, X_test, y_train, y_test = train_test_split(X_seq, y_seq, test_size=0.2, random_state=42)

# 6. Arsitektur Model LSTM
model = Sequential([
    # Input shape: (time_steps, jumlah_fitur) -> (5, 10)
    LSTM(64, input_shape=(X_train.shape[1], X_train.shape[2]), return_sequences=False),
    Dropout(0.2), # Mencegah overfitting
    Dense(32, activation='relu'),
    Dense(3, activation='softmax') # 3 output karena kelas kita ada 3 (0, 1, 2)
])

# 7. Compile & Train Model
model.compile(optimizer='adam', 
              loss='sparse_categorical_crossentropy', 
              metrics=['accuracy'])

print("Sedang melatih model LSTM...")
model.fit(X_train, y_train, epochs=15, batch_size=32, validation_data=(X_test, y_test))

# 8. Simpan Model LSTM (.h5 atau .keras)
model.save("lstm_model.h5")
print("Model LSTM ('lstm_model.h5') dan Scaler ('lstm_scaler.pkl') berhasil disimpan!")