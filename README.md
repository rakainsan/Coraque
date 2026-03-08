# CORAQUE Flask API — Panduan Deploy

## Struktur Folder

```
coraque-api/
├── app.py
├── requirements.txt
└── models/
    ├── CORAQUE.pkl
    ├── CORAQUE_ocsvm.pkl
    ├── CORAQUE_ocsvm_scaler.pkl
    ├── CORAQUEfeatures.pkl
    └── CORAQUEscaler.pkl
```

## Instalasi & Menjalankan

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Jalankan server
python app.py
# Server berjalan di http://localhost:5000
```

---

## Endpoint API

### `GET /`
Health check — memastikan server berjalan.

---

### `POST /predict`
**Prediksi SVR + deteksi anomali OCSVM sekaligus (recommended).**

**Request Body:**
```json
{
    "events": [12.5, 13.0, 11.8]
}
```
> `events` adalah array minimal 3 nilai event, urutan **lama → baru**.

**Response:**
```json
{
    "svr": {
        "prediction": 12.34
    },
    "ocsvm": {
        "is_anomaly": false,
        "label": 1,
        "score": 0.123456
    },
    "features": {
        "event_lag1": 11.8,
        "event_lag2": 13.0,
        "event_lag3": 12.5,
        "rolling_mean_3": 12.43,
        "rolling_std_3": 0.51
    }
}
```

---

### `POST /predict/svr`
Hanya prediksi SVR.

---

### `POST /predict/ocsvm`
Hanya deteksi anomali OCSVM.

**Response tambahan:**
- `is_anomaly: true` → data **anomali**
- `is_anomaly: false` → data **normal**
- `score` → semakin negatif = semakin anomali

---

## Integrasi Laravel

Di Laravel, gunakan HTTP Client untuk memanggil API:

```php
use Illuminate\Support\Facades\Http;

$response = Http::post('http://localhost:5000/predict', [
    'events' => [12.5, 13.0, 11.8],
]);

$result = $response->json();

$prediction = $result['svr']['prediction'];
$isAnomaly  = $result['ocsvm']['is_anomaly'];
```

---

## Catatan Versi

Model di-train menggunakan `scikit-learn==1.6.1`.  
Pastikan versi di `requirements.txt` sama untuk menghindari warning inkompatibilitas.
