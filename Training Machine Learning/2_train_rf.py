import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import joblib

# 1. Load data yang sudah diberi label
df = pd.read_csv("sensor_data_labeled.csv")

# 2. Pilih Fitur (X) dan Target/Label (y)
# Pastikan nama kolom di list X ini sesuai persis dengan kolom di sensor_data.csv kamu
features = ['moisture', 'moisture_percent', 'ax', 'ay', 'az', 'gx', 'gy', 'gz', 'pitch', 'roll']
X = df[features]
y = df['status']

# 3. Split Data (80% Training, 20% Testing)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# 4. Train Model Random Forest
print("Sedang melatih model Random Forest...")
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# 5. Evaluasi Model
y_pred = model.predict(X_test)
print("\n=== HASIL EVALUASI MODEL ===")
print(f"Akurasi: {accuracy_score(y_test, y_pred) * 100:.2f}%")
print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=['Aman (0)', 'Waspada (1)', 'Bahaya (2)']))

# 6. Simpan Model menjadi file .pkl
model_filename = "rf_model.pkl"
joblib.dump(model, model_filename)
print(f"\nModel berhasil disimpan dengan nama '{model_filename}'!")