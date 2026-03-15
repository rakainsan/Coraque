import requests
import time
import random

URL = "https://6092-2404-c0-b302-97da-352f-a113-eb59-47eb.ngrok-free.app/predict"  

TOTAL_REQUEST = 200
berhasil = 0
gagal = 0
response_times = []

print("Memulai load test...")
start_total = time.time()

for i in range(TOTAL_REQUEST):
    payload = {
        "sensor_count": random.randint(10, 30),
        "date": "2026-03-09"
    }
    try:
        start = time.time()
        r = requests.post(URL, json=payload, timeout=10)
        elapsed = time.time() - start
        response_times.append(elapsed)
        if r.status_code == 200:
            berhasil += 1
        else:
            gagal += 1
    except Exception as e:
        gagal += 1

waktu_total = time.time() - start_total

print("\n===== HASIL LOAD TEST =====")
print(f"Total request terkirim  : {TOTAL_REQUEST}")
print(f"Request berhasil        : {berhasil}")
print(f"Request gagal           : {gagal}")
print(f"Waktu total             : {waktu_total:.2f} detik")
print(f"Rata-rata response time : {sum(response_times)/len(response_times):.4f} detik")
print(f"Response tercepat       : {min(response_times):.4f} detik")
print(f"Response terlambat      : {max(response_times):.4f} detik")
print("===========================")