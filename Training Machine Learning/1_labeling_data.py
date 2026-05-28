import pandas as pd

df = pd.read_csv("sensor_data.csv")

def create_label(row):
    moisture = row['moisture_percent']
    # Menggunakan abs() karena kemiringan gyro bisa bernilai positif atau negatif
    is_moving = abs(row['pitch']) > 20 
    
    # 1. KONDISI BAHAYA (Skor 2)
    # Gyro bergerak aktif DAN (Tanah terlalu kering ATAU tanah terlalu basah)
    if is_moving and (moisture < 40 or moisture > 70):
        return 2  # Bahaya (Potensi longsor sangat tinggi/sedang terjadi)
        
    # 2. KONDISI WASPADA (Skor 1)
    # Pilihan A: Tanah sangat basah tapi belum bergerak (siaga hujan lebat)
    elif moisture > 70:
        return 1  # Waspada (Tanah jenuh air)
    # Pilihan B: Ada pergerakan gyro meskipun kelembapan tanah normal
    elif is_moving:
        return 1  # Waspada (Ada pergerakan aneh)
    # Pilihan C: Tanah mulai kering/retak tapi belum bergerak
    elif moisture < 40:
        return 1  # Waspada (Tanah kering/retak)
        
    # 3. KONDISI AMAN (Skor 0)
    else:
        return 0  # Aman

# Terapkan fungsi ke dataframe
df['status'] = df.apply(create_label, axis=1)

df.to_csv("sensor_data_labeled.csv", index=False)
print("Labeling berhasil diperbarui dengan logika geologis yang aman!")