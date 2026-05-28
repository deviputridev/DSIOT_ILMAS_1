import pandas as pd

df = pd.read_csv("sensor_data.csv")

def create_label(row):
    moisture = row['moisture_percent']
    is_moving = abs(row['pitch']) > 20 
    
    if is_moving and (moisture < 40 or moisture > 70):
        return 2  
    elif moisture > 70:
        return 1  
    elif is_moving:
        return 1  
    elif moisture < 40:
        return 1
    else:
        return 0  

df['status'] = df.apply(create_label, axis=1)

df.to_csv("sensor_data_labeled.csv", index=False)
print("Labeling berhasil diperbarui dengan logika geologis yang aman!")