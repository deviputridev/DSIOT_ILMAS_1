import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
import joblib


df = pd.read_csv("sensor_data_labeled.csv")

features = ['moisture', 'moisture_percent', 'ax', 'ay', 'az', 'gx', 'gy', 'gz', 'pitch', 'roll']
X = df[features].values
y = df['status'].values

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
joblib.dump(scaler, "lstm_scaler.pkl")

def create_sequences(X_data, y_data, time_steps=5):
    Xs, ys = [], []
    for i in range(len(X_data) - time_steps):
        Xs.append(X_data[i:(i + time_steps)])
        ys.append(y_data[i + time_steps])
    return np.array(Xs), np.array(ys)

X_seq, y_seq = create_sequences(X_scaled, y, time_steps=5)

X_train, X_test, y_train, y_test = train_test_split(X_seq, y_seq, test_size=0.2, random_state=42)

model = Sequential([
    LSTM(64, input_shape=(X_train.shape[1], X_train.shape[2]), return_sequences=False),
    Dropout(0.2),
    Dense(32, activation='relu'),
    Dense(3, activation='softmax')
])

model.compile(optimizer='adam', 
              loss='sparse_categorical_crossentropy', 
              metrics=['accuracy'])

print("Sedang melatih model LSTM...")
model.fit(X_train, y_train, epochs=15, batch_size=32, validation_data=(X_test, y_test))

model.save("lstm_model.h5")
print("Model LSTM ('lstm_model.h5') dan Scaler ('lstm_scaler.pkl') berhasil disimpan!")