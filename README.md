# ILMAS — Intelligent Landslide Monitoring and Alert System

Sistem deteksi dini bencana tanah longsor berbasis IoT dan kecerdasan buatan yang memantau kondisi tanah secara *real-time*, mengklasifikasikan tingkat bahaya menggunakan model *machine learning*, serta mengirimkan peringatan otomatis melalui Telegram.

---

## Daftar Isi

1. [Deskripsi Proyek](#1-deskripsi-proyek)
2. [Alur Sistem](#2-alur-sistem)
3. [Alat dan Bahan](#3-alat-dan-bahan)
4. [Foto Alat](#4-foto-alat)
5. [Teknologi yang Digunakan](#5-teknologi-yang-digunakan)
6. [Struktur Basis Data](#6-struktur-basis-data)
7. [Struktur Direktori](#7-struktur-direktori)
8. [Panduan Instalasi](#8-panduan-instalasi)
9. [Video Demonstrasi](#9-video-demonstrasi)

---

## 1. Deskripsi Proyek

ILMAS (*Intelligent Landslide Monitoring and Alert System*) adalah sistem pemantauan longsor yang terintegrasi dari lapisan perangkat keras (*hardware*) hingga antarmuka web dan notifikasi. Sistem ini dirancang untuk mendeteksi dua faktor utama pemicu longsor secara simultan, yaitu kadar kelembaban tanah dan pergerakan/getaran lereng, kemudian mengolah data tersebut menggunakan dua model *machine learning* untuk menghasilkan status klasifikasi kondisi saat ini (*current status*) dan prediksi kondisi ke depan (*forecast status*).

Sistem terdiri atas empat lapisan utama yang bekerja secara berkesinambungan.

**Lapisan Sensor (Edge Layer):** ESP32 membaca data dari sensor kelembaban tanah dan sensor IMU MPU6050 setiap 5 detik, lalu mengirimkan data melalui protokol MQTT ke *broker* lokal di Raspberry Pi.

**Lapisan Data (Data Layer):** Program subscriber MQTT di Raspberry Pi menerima *payload* JSON dari ESP32 dan menyimpannya ke basis data PostgreSQL di server.

**Lapisan Kecerdasan Buatan (AI Layer):** *Pipeline* AI membaca data terbaru dari basis data, menjalankan model Random Forest untuk klasifikasi status saat ini, dan model LSTM untuk prediksi *forecast*. Hasil prediksi dituliskan kembali ke basis data pada baris yang sama.

**Lapisan Tampilan dan Notifikasi (Presentation Layer):** Web *dashboard* berbasis Laravel membaca data dari basis data secara *real-time* dan menampilkan status, grafik, serta data sensor. Apabila status menunjukkan WASPADA atau BAHAYA, sistem mengirimkan notifikasi otomatis ke Telegram Bot lengkap dengan seluruh detail data sensor.

### Kelas Klasifikasi

| Status | Keterangan | Tindakan |
|--------|------------|----------|
| AMAN | Kondisi tanah normal, tidak ada indikasi bahaya | Pemantauan rutin |
| WASPADA | Indikasi awal ketidakstabilan tanah terdeteksi | Pemantauan intensif dan persiapan evakuasi |
| BAHAYA | Risiko longsor tinggi, kondisi kritis | Evakuasi segera |

---

## 2. Alur Sistem

Berikut alur lengkap sistem dari pembacaan sensor hingga pengiriman notifikasi.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        LAPISAN SENSOR                               │
│                                                                     │
│   [Soil Moisture]──┐                                                │
│                    ├──► [ESP32] ──MQTT──► [Raspberry Pi]            │
│   [MPU6050]────────┘     (tiap 5 detik)    (broker: localhost:1883) │
└─────────────────────────────────────────────────────────────────────┘
                                                    │
                                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        LAPISAN DATA                                 │
│                                                                     │
│   ilmas.py / n8n ──► INSERT sensor_data ──► PostgreSQL              │
│                       (moisture, ax, ay, az,   (db_longsor)         │
│                        gx, gy, gz, pitch, roll,                     │
│                        vibration, status=UNKNOWN)                   │
└─────────────────────────────────────────────────────────────────────┘
                                                    │
                                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     LAPISAN KECERDASAN BUATAN                       │
│                                                                     │
│   ai_pipeline.py                                                    │
│   ├── Baca 1 data terbaru ──► Random Forest ──► status (AMAN/       │
│   │                                              WASPADA/BAHAYA)    │
│   │                                              + rf_confidence    │
│   │                                                                 │
│   └── Baca 20 data terakhir ──► LSTM ──► forecast_status            │
│        (sequence input)                  + lstm_confidence          │
│                                          + forecast_confidence      │
│                                                                     │
│   UPDATE sensor_data SET status, forecast_status, confidence...     │
└─────────────────────────────────────────────────────────────────────┘
                                                    │
                                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   LAPISAN TAMPILAN DAN NOTIFIKASI                   │
│                                                                     │
│   Web Dashboard (Laravel) ──► polling GET /api/sensor-now           │
│   ├── Tampilkan status, forecast, confidence, grafik                │
│   ├── Integrasi data cuaca BMKG (Surabaya)                          │
│   └── Chatbot AI (Gemini 2.5 Flash) berbasis data sensor terkini    │
│                                                                     │
│   TelegramAlertService                                              │
│   ├── Status WASPADA ──► kirim notifikasi (cooldown 3 menit)        │
│   └── Status BAHAYA  ──► kirim notifikasi darurat (cooldown 1 menit)│
└─────────────────────────────────────────────────────────────────────┘
```

### Detail Alur Data Sensor

Setiap paket data yang dikirim ESP32 melalui MQTT berisi bidang-bidang berikut dalam format JSON.

```json
{
  "moisture": 1255,
  "moisture_percent": 69,
  "ax": -368, "ay": 10784, "az": 13568,
  "gx": -137, "gy": 164,  "gz": 172,
  "pitch": -1.22,
  "roll": 38.47
}
```

Nilai `vibration` dihitung di sisi penerima dengan rumus:

```
vibration = |ax| + |ay| + |az|
```

Kolom `status`, `forecast_status`, `forecast_confidence`, `rf_confidence`, dan `lstm_confidence` diisi oleh `ai_pipeline.py` melalui perintah `UPDATE` setelah proses inferensi selesai.

---

## 3. Alat dan Bahan

### Perangkat Keras

| No. | Komponen | Fungsi | Keterangan |
|-----|----------|--------|------------|
| 1 | **ESP32 DevKit V1** | Mikrokontroler utama | Membaca sensor, mengirim data via MQTT over WiFi |
| 2 | **Sensor Kelembaban Tanah (Soil Moisture)** | Mengukur kadar air tanah | Output analog 0–4095 (ADC 12-bit), terpasang di pin GPIO 34 |
| 3 | **MPU6050** | Mengukur akselerasi dan sudut kemiringan | Komunikasi I2C, pin SDA=21 / SCL=22; menghasilkan data ax, ay, az, gx, gy, gz, pitch, roll |
| 4 | **Raspberry Pi 4 Model B** | Server lokal | Menjalankan MQTT broker, program penerima data, dan AI pipeline |
| 5 | **Kabel Jumper** | Koneksi antar komponen | Male-to-male dan male-to-female |
| 6 | **Breadboard** | Papan rangkaian prototyping | Untuk pemasangan sementara tanpa solder |
| 7 | **Baterai** | Sumber daya listrik | USB 5V untuk ESP32; adaptor 5V 3A untuk Raspberry Pi |

### Skema Koneksi ESP32

| Pin ESP32 | Terhubung ke |
|-----------|-------------|
| GPIO 34 | Data Soil Moisture Sensor |
| GPIO 21 (SDA) | SDA MPU6050 |
| GPIO 22 (SCL) | SCL MPU6050 |
| 3.3V | VCC MPU6050 |
| GND | GND semua komponen |

### Perangkat Lunak

| No. | Perangkat Lunak | Versi | Fungsi |
|-----|----------------|-------|--------|
| 1 | Arduino IDE | 2.x | Pemrograman firmware ESP32 |
| 2 | Python | 3.x | AI pipeline dan subscriber MQTT |
| 3 | Mosquitto | 2.x | MQTT broker lokal di Raspberry Pi |
| 4 | PostgreSQL | 14+ | Basis data penyimpan data sensor |
| 5 | PHP | 8.3 | Runtime web backend (Laravel) |
| 6 | Node.js / npm | 18+ | Build aset frontend (Vite + Tailwind CSS) |

---

## 4. Foto Alat

> **Catatan:** Ganti bagian ini dengan foto dokumentasi aktual perangkat keras proyek.

### Tampilan Keseluruhan Perangkat

```
[ Masukkan foto keseluruhan rangkaian hardware di sini ]
```

### Detail Rangkaian ESP32 + Sensor

```
[ Masukkan foto close-up rangkaian ESP32, Soil Moisture, dan MPU6050 ]
```

### Raspberry Pi dan Server

```
[ Masukkan foto Raspberry Pi 4 yang digunakan sebagai server lokal ]
```

### Tampilan Web Dashboard

```
[ Masukkan screenshot halaman utama dashboard ILMAS ]
```

### Notifikasi Telegram

```
[ Masukkan screenshot notifikasi Telegram saat status WASPADA atau BAHAYA ]
```

---

## 5. Teknologi yang Digunakan

### Firmware (ESP32)

| Teknologi | Keterangan |
|-----------|------------|
| Arduino Framework | Framework pemrograman mikrokontroler ESP32 |
| Library `Wire.h` | Komunikasi I2C untuk MPU6050 |
| Library `MPU6050` | Membaca data akselerometer dan giroskop |
| Library `PubSubClient` | Klien MQTT untuk publikasi data ke broker |
| Library `ArduinoJson` | Serialisasi data sensor ke format JSON |
| Library `WiFi.h` | Koneksi WiFi ESP32 |

### Backend Raspberry Pi

| Teknologi | Keterangan |
|-----------|------------|
| Python 3 | Bahasa pemrograman utama AI pipeline dan subscriber MQTT |
| `paho-mqtt` | Klien MQTT untuk subscribe topic `datasensor/data` |
| `psycopg2` | Koneksi Python ke basis data PostgreSQL |
| `TensorFlow / Keras` | *Framework* deep learning untuk model LSTM |
| `scikit-learn` | *Framework* machine learning untuk model Random Forest |
| `joblib` | Serialisasi dan deserialisasi model (`lstm_scaler.pkl`, `rf_model.pkl`) |
| `numpy`, `pandas` | Manipulasi array dan *dataframe* untuk inferensi model |
| Mosquitto | MQTT broker lokal yang berjalan di Raspberry Pi |

### Model Machine Learning

| Model | Fungsi | Input | Output |
|-------|--------|-------|--------|
| **Random Forest** | Klasifikasi status kondisi saat ini | 10 fitur: moisture, moisture_percent, ax, ay, az, gx, gy, gz, pitch, roll | Status (AMAN/WASPADA/BAHAYA) + rf_confidence |
| **LSTM** | Prediksi *forecast* kondisi ke depan | Sekuens 20 data terakhir (10 fitur, dinormalisasi dengan `lstm_scaler.pkl`) | forecast_status + lstm_confidence |

### Web Dashboard

| Teknologi | Versi | Keterangan |
|-----------|-------|------------|
| Laravel | 13.x | Framework PHP untuk web *backend* dan routing |
| PHP | 8.3 | Runtime bahasa pemrograman *backend* |
| Tailwind CSS | 4.x | Framework CSS *utility-first* untuk antarmuka |
| Vite | 8.x | *Build tool* aset frontend |
| Chart.js | CDN | Visualisasi grafik data sensor dan riwayat status |
| PostgreSQL | 14+ | Basis data relasional yang dibaca langsung oleh web |
| Gemini API (2.5 Flash) | v1beta | Model AI Google untuk fitur *chatbot* berbasis data sensor terkini |
| BMKG Open API | Publik | Data prakiraan cuaca Surabaya yang ditampilkan di *dashboard* |
| Telegram Bot API | v7+ | Pengiriman notifikasi peringatan otomatis ke *chat* Telegram |

### API Endpoint Web

| Method | Endpoint | Fungsi |
|--------|----------|--------|
| GET | `/` | Halaman utama *dashboard* |
| GET | `/api/sensor-now` | Data sensor terbaru beserta status dan *confidence* |
| GET | `/api/status-history` | Riwayat seluruh status untuk grafik garis |
| GET | `/api/forecast-history` | Riwayat *forecast*, *confidence*, dan data sensor |
| POST | `/api/chatbot` | *Endpoint* chatbot AI berbasis Gemini |

### Integrasi Eksternal

| Layanan | Fungsi |
|---------|--------|
| **Telegram Bot API** | Mengirim notifikasi WASPADA dan BAHAYA dengan *cooldown* otomatis (BAHAYA: 1 menit, WASPADA: 3 menit) |
| **BMKG Open API** | Menampilkan prakiraan cuaca Surabaya di *dashboard* (kondisi, curah hujan, suhu, kelembaban udara) |
| **Google Gemini 2.5 Flash** | Menjawab pertanyaan tentang kondisi sensor terkini melalui fitur *chatbot* |

### Otomasi Alur Kerja

| Teknologi | Fungsi |
|-----------|--------|
| **n8n** | Platform otomasi *workflow* yang menggantikan `ilmas.py` sebagai MQTT subscriber, meneruskan data ke PostgreSQL, serta menjalankan *alert* scheduler setiap 10 detik, rekap berkala setiap 6 jam, dan *health check* sensor setiap 1 jam |

---

## 6. Struktur Basis Data

### Tabel `sensor_data`

Tabel utama yang menyimpan seluruh data sensor dan hasil inferensi AI.

| Kolom | Tipe | Keterangan |
|-------|------|------------|
| `id` | SERIAL PRIMARY KEY | Identitas unik baris data |
| `timestamp` | TIMESTAMP | Waktu data diterima |
| `moisture` | INTEGER | Nilai ADC mentah sensor kelembaban (0–4095) |
| `moisture_percent` | INTEGER | Persentase kelembaban tanah (0–100%) |
| `ax`, `ay`, `az` | INTEGER | Akselerasi sumbu X, Y, Z dari MPU6050 |
| `gx`, `gy`, `gz` | INTEGER | Data giroskop sumbu X, Y, Z dari MPU6050 |
| `pitch` | NUMERIC | Sudut kemiringan pitch (derajat) |
| `roll` | NUMERIC | Sudut kemiringan roll (derajat) |
| `vibration` | NUMERIC | Nilai getaran hasil perhitungan: `\|ax\| + \|ay\| + \|az\|` |
| `status` | VARCHAR(20) | Status klasifikasi RF: AMAN/WASPADA/BAHAYA/UNKNOWN |
| `forecast_status` | VARCHAR(20) | Status prediksi LSTM ke depan |
| `forecast_confidence` | NUMERIC | Tingkat keyakinan prediksi LSTM (0–100%) |
| `rf_confidence` | NUMERIC | Tingkat keyakinan model Random Forest (0–100%) |
| `lstm_confidence` | NUMERIC | Tingkat keyakinan model LSTM (0–100%) |

### Tabel `telegram_alert_logs`

Tabel pencatatan riwayat pengiriman notifikasi Telegram.

| Kolom | Tipe | Keterangan |
|-------|------|------------|
| `id` | BIGINT PRIMARY KEY | Identitas unik log |
| `status` | VARCHAR(20) | Status saat notifikasi dikirim |
| `sensor_log_id` | BIGINT | Referensi ke baris `sensor_data` terkait |
| `moisture_percent` | DECIMAL | Kelembaban tanah saat notifikasi dikirim |
| `pitch`, `roll` | DECIMAL | Sudut kemiringan saat notifikasi dikirim |
| `vibration` | DECIMAL | Nilai getaran saat notifikasi dikirim |
| `rf_confidence` | DECIMAL | Keyakinan model RF saat notifikasi dikirim |
| `lstm_confidence` | DECIMAL | Keyakinan model LSTM saat notifikasi dikirim |
| `sent` | BOOLEAN | Status keberhasilan pengiriman ke Telegram |
| `sensor_timestamp` | TIMESTAMP | Waktu data sensor yang memicu notifikasi |
| `created_at` | TIMESTAMP | Waktu notifikasi diproses oleh sistem |

---

## 7. Struktur Direktori

```
ilmas/
├── ilmas_esp.ino              # Firmware ESP32 (Arduino)
│
├── raspberry-pi/
│   ├── ilmas.py               # Subscriber MQTT + INSERT ke PostgreSQL
│   ├── ai_pipeline.py         # AI pipeline: Random Forest + LSTM inference
│   ├── lstm_model.h5          # Model LSTM terlatih (TensorFlow/Keras)
│   ├── rf_model.pkl           # Model Random Forest terlatih (scikit-learn)
│   └── lstm_scaler.pkl        # Scaler normalisasi input LSTM
│
├── ilmas-web/                 # Web dashboard (Laravel)
│   ├── app/
│   │   ├── Http/Controllers/
│   │   │   ├── DashboardController.php   # Controller utama dashboard
│   │   │   ├── ChatbotController.php     # Controller chatbot Gemini
│   │   │   └── ForecastController.php    # Controller data forecast
│   │   ├── Models/
│   │   │   ├── SensorLog.php             # Model tabel sensor_data
│   │   │   └── TelegramAlertLog.php      # Model tabel telegram_alert_logs
│   │   └── Services/
│   │       └── TelegramAlertService.php  # Layanan kirim notifikasi Telegram
│   ├── resources/views/
│   │   └── dashboard.blade.php           # Tampilan utama dashboard
│   └── .env                              # Konfigurasi environment
│
└── n8n/
    └── ilmas_n8n_workflow.json  # Workflow n8n (opsional, pengganti ilmas.py)
```

---

## 8. Panduan Instalasi

### Prasyarat

- Raspberry Pi 4 dengan OS Raspberry Pi OS (Debian-based)
- Python 3.x dengan pip
- PHP 8.3 dan Composer
- Node.js 18+ dan npm
- PostgreSQL 14+
- Mosquitto MQTT Broker

### Langkah 1 — Persiapan Basis Data

Buat basis data dan tabel di PostgreSQL.

```sql
CREATE DATABASE db_longsor;
CREATE USER user_longsor WITH PASSWORD 'password_kuat';
GRANT ALL PRIVILEGES ON DATABASE db_longsor TO user_longsor;

-- Buat tabel sensor_data
CREATE TABLE sensor_data (
    id               SERIAL PRIMARY KEY,
    timestamp        TIMESTAMP DEFAULT NOW(),
    moisture         INTEGER,
    moisture_percent INTEGER,
    ax INTEGER, ay INTEGER, az INTEGER,
    gx INTEGER, gy INTEGER, gz INTEGER,
    pitch            NUMERIC(8,4),
    roll             NUMERIC(8,4),
    vibration        NUMERIC(12,4),
    status           VARCHAR(20) DEFAULT 'UNKNOWN',
    forecast_status  VARCHAR(20),
    forecast_confidence NUMERIC(6,2),
    rf_confidence    NUMERIC(6,2),
    lstm_confidence  NUMERIC(6,2)
);
```

### Langkah 2 — Konfigurasi ESP32

1. Buka `ilmas_esp.ino` menggunakan Arduino IDE.
2. Sesuaikan variabel berikut sesuai jaringan dan server yang digunakan.

```cpp
const char* ssid     = "NAMA_WIFI";
const char* password = "PASSWORD_WIFI";
const char* mqtt_server = "IP_RASPBERRY_PI";
```

3. Unggah (*upload*) firmware ke ESP32.

### Langkah 3 — Instalasi Program Raspberry Pi

```bash
pip install paho-mqtt psycopg2-binary tensorflow scikit-learn joblib numpy pandas
```

Jalankan subscriber MQTT (dapat juga digantikan oleh n8n):

```bash
python3 ilmas.py
```

Jalankan AI pipeline di *background*:

```bash
nohup python3 ai_pipeline.py &
```

### Langkah 4 — Instalasi Web Dashboard

```bash
cd ilmas-web
composer install
cp .env.example .env
php artisan key:generate
php artisan migrate
npm install
npm run build
php artisan serve --host=0.0.0.0 --port=8000
```

Sesuaikan isian `.env` berikut.

```env
DB_HOST=IP_SERVER_POSTGRES
DB_DATABASE=db_longsor
DB_USERNAME=user_longsor
DB_PASSWORD=password_kuat

GEMINI_API_KEY=API_KEY_GEMINI
TELEGRAM_BOT_TOKEN=TOKEN_BOT_TELEGRAM
TELEGRAM_CHAT_ID=CHAT_ID_TUJUAN
```


## 9. Video Demonstrasi

