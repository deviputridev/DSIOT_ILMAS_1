import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import joblib


df = pd.read_csv("sensor_data_labeled.csv")

features = ['moisture', 'moisture_percent', 'ax', 'ay', 'az', 'gx', 'gy', 'gz', 'pitch', 'roll']
X = df[features]
y = df['status']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

print("Sedang melatih model Random Forest...")
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
print("\n=== HASIL EVALUASI MODEL ===")
print(f"Akurasi: {accuracy_score(y_test, y_pred) * 100:.2f}%")
print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=['Aman (0)', 'Waspada (1)', 'Bahaya (2)']))

model_filename = "rf_model.pkl"
joblib.dump(model, model_filename)
print(f"\nModel berhasil disimpan dengan nama '{model_filename}'!")