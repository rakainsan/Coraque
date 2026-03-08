from flask import Flask, request, jsonify
import joblib
import numpy as np
import requests
import os
import warnings
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
import threading
import time
load_dotenv()
from flask_cors import CORS


warnings.filterwarnings("ignore")

app = Flask(__name__)
CORS(app)

# Chatbot
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID")
TELEGRAM_API_URL   = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
groq_client  = Groq(api_key=GROQ_API_KEY)

# Load Groq model
def ask_llm(prompt: str) -> str:
    # Bangun konteks prediksi dinamis
    if last_prediction_context:
        ctx = last_prediction_context
        status = "ANOMALI ⚠️" if ctx["is_anomaly"] else "NORMAL ✅"
        prediksi_info = f"""

    ## 📊 Hasil Prediksi Terakhir (diperbarui {ctx['tanggal']})
    - SVR Forecast      : {ctx['svr_forecast']} event
    - Estimasi Volume   : {ctx['volume_liter']} liter
    - Status OCSVM      : {status}
    - OCSVM Score       : {ctx['ocsvm_score']} (> 0 normal, < 0 anomali)
    - Event Lag 1       : {ctx['event_lag1']} (kemarin)
    - Event Lag 2       : {ctx['event_lag2']} (2 hari lalu)
    - Event Lag 3       : {ctx['event_lag3']} (3 hari lalu)
    - Jumlah Kain       : {ctx['jumlah_kain']} lembar
    - Panjang Kain      : {ctx['panjang_kain_m']} meter
    Gunakan data ini jika user bertanya tentang kondisi limbah, prediksi, atau status hari ini.
    """
    else:
        prediksi_info = "\n    ## 📊 Prediksi\n    Belum ada prediksi yang dijalankan. Minta user untuk menjalankan prediksi terlebih dahulu.\n"

    system_prompt = f"""
    Kamu adalah CoraqBot, asisten cerdas sistem monitoring limbah batik CORAQ (Continuous Observation Remote Analysis Quantification) di Pekalongan.

    Sistem CORAQ terdiri dari 4 bak:
    - Bak 1: Monitoring awal (sensor pH, suhu, TDS, turbidity, water level)
    - Bak 2: Elektrokoagulasi (6 plat elektroda besi, memecah partikel warna)
    - Bak 3: Flokulasi & Sedimentasi (motor pengaduk, flok mengendap)
    - Bak 4: Monitoring akhir (sensor sama seperti bak 1, output ke saluran)

    Machine Learning yang digunakan:
    - SVR: forecast jumlah event sensor untuk hari berikutnya
    - OCSVM: deteksi anomali berdasarkan pola lag + data produksi kain
    - 1 event = 292 liter limbah
    - Jika anomali terdeteksi, bot Telegram mengirim peringatan otomatis
    {prediksi_info}
    Jawab dalam bahasa Indonesia, ramah, ringkas, dan jelas.
    Jika ditanya di luar konteks CORAQ, arahkan kembali ke topik sistem ini.
    """
    try:
        res = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": prompt}
            ]
        )
        return res.choices[0].message.content
    except Exception as e:
        return f"Maaf, terjadi kesalahan: {str(e)}"
# Load models
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

svr_model     = joblib.load(os.path.join(BASE_DIR, "models", "CORAQUE.pkl"))
svr_scaler    = joblib.load(os.path.join(BASE_DIR, "models", "CORAQUEscaler.pkl"))
ocsvm_model   = joblib.load(os.path.join(BASE_DIR, "models", "CORAQUE_ocsvm.pkl"))
ocsvm_scaler  = joblib.load(os.path.join(BASE_DIR, "models", "CORAQUE_ocsvm_scaler.pkl"))
feature_names = joblib.load(os.path.join(BASE_DIR, "models", "CORAQUEfeatures.pkl"))
ocsvm_feature_names = joblib.load(os.path.join(BASE_DIR, "models", "CORAQUE_ocsvm_features.pkl"))
last_prediction_context = None


# Telegram Sended Message
def send_telegram_notification(svr_forecast, source="-"):
    tanggal = datetime.now().strftime("%d-%m-%Y")
    message = (
        "🚨 <b>PERINGATAN DINI!!</b>\n"
        f"Tanggal: {tanggal}\n"
        f"Sensor Aktif: {svr_forecast:.0f} kali\n"
        f"Prediksi Volume: {svr_forecast* 292:.2f} liter\n"
        "Status: ANOMALI TERDETEKSI ⚠️"
    )
    try:
        resp = requests.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"},
            timeout=10,
        )
        return resp.ok
    except Exception as e:
        print(f"[Telegram] Gagal kirim notifikasi: {e}")
        return False
    
LAST_UPDATE_ID = None

def polling_telegram():
    global LAST_UPDATE_ID
    while True:
        try:
            params = {"timeout": 30}
            if LAST_UPDATE_ID:
                params["offset"] = LAST_UPDATE_ID + 1

            resp    = requests.get(f"{TELEGRAM_API_URL}/getUpdates", params=params, timeout=35)
            updates = resp.json().get("result", [])

            for update in updates:
                LAST_UPDATE_ID = update["update_id"]
                message = update.get("message", {})
                chat_id = message.get("chat", {}).get("id")
                text    = message.get("text", "")

                if not chat_id or not text:
                    continue

                if text.lower() == "/start":
                    reply = (
                        "👋 Halo! Aku <b>CoraqBot</b>.\n"
                        "Terhubung dengan sistem IoT monitoring limbah batik CORAQ.\n"
                        "Tanya apa saja tentang sensor, prediksi, atau anomali!"
                    )
                else:
                    reply = ask_llm(text)

                requests.post(
                    f"{TELEGRAM_API_URL}/sendMessage",
                    json={"chat_id": chat_id, "text": reply, "parse_mode": "HTML"},
                    timeout=10,
                )
        except Exception as e:
            print(f"[Polling] Error: {e}")
        time.sleep(1)

# fitur
def build_features(events: list) -> dict:
    if len(events) < 3:
        raise ValueError("Dibutuhkan minimal 3 data event (urutan lama → baru).")
    last3 = events[-3:]
    return {
        "event_lag1"    : float(last3[-1]),
        "event_lag2"    : float(last3[-2]),
        "event_lag3"    : float(last3[-3]),
        "rolling_mean_3": float(np.mean(last3)),
        "rolling_std_3" : float(np.std(last3, ddof=0)),
    }


# Endpoint: health check
@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ok", "message": "CORAQUE API is running"}), 200


# Endpoint: test koneksi Telegram 
@app.route("/telegram/test", methods=["GET"])
def telegram_test():
    """Kirim pesan test ke Telegram untuk verifikasi koneksi bot."""
    timestamp = datetime.now().strftime("%d %b %Y, %H:%M:%S")
    message = (
        "✅ *Koneksi Berhasil\\!*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Bot CORAQUE siap mengirim notifikasi anomali\\.\n"
        f"🕐 `{timestamp}`"
    )
    try:
        resp = requests.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "MarkdownV2"},
            timeout=10,
        )
        if resp.ok:
            return jsonify({"status": "ok", "message": "Pesan test berhasil dikirim ke Telegram."}), 200
        else:
            return jsonify({"status": "error", "detail": resp.json()}), 502
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    

# Prediksi gabungan 
@app.route("/predict", methods=["POST"])
def predict_combined():
    """
    Body JSON:
    {
        "events"        : [e_{t-3}, e_{t-2}, e_{t-1}],
        "jumlah_kain"   : 120,
        "panjang_kain_m": 2.7,
        "source"        : "IoT CORAQ"
    }
    """
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "Body JSON kosong."}), 400

    try:
        feats = build_features(data["events"]) if "events" in data else data.get("features")
        if feats is None:
            return jsonify({"error": "Kirim 'events' atau 'features'."}), 400

        source = data.get("source", "-")

        # SVR forecast
        X_svr    = np.array([[feats[f] for f in feature_names]])
        svr_pred = float(svr_model.predict(svr_scaler.transform(X_svr))[0])

        # OCSVM detect
        feats["svr_pred"]       = svr_pred
        feats["jumlah_kain"]    = float(data.get("jumlah_kain", 0))
        feats["panjang_kain_m"] = float(data.get("panjang_kain_m", 0))

        X_oc     = np.array([[feats[f] for f in ocsvm_feature_names]])
        X_oc_sc  = ocsvm_scaler.transform(X_oc)
        oc_label = int(ocsvm_model.predict(X_oc_sc)[0])
        oc_score = float(ocsvm_model.decision_function(X_oc_sc)[0])
        is_anomaly = oc_label == -1

        global last_prediction_context
        last_prediction_context = {
            "tanggal"       : datetime.now().strftime("%d-%m-%Y %H:%M"),
            "svr_forecast"  : round(svr_pred, 4),
            "volume_liter"  : round(svr_pred * 292, 2),
            "is_anomaly"    : is_anomaly,
            "ocsvm_score"   : round(oc_score, 6),
            "event_lag1"    : feats["event_lag1"],
            "event_lag2"    : feats["event_lag2"],
            "event_lag3"    : feats["event_lag3"],
            "jumlah_kain"   : feats["jumlah_kain"],
            "panjang_kain_m": feats["panjang_kain_m"],
        }
        
        telegram_sent = False
        if is_anomaly:
            telegram_sent = send_telegram_notification(svr_pred, source)
            
        return jsonify({
            "svr"          : {"forecast": round(svr_pred, 4)},
            "ocsvm"        : {"is_anomaly": is_anomaly, "label": oc_label, "score": round(oc_score, 6)},
            "telegram_sent": telegram_sent,
        }), 200

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 422
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    
@app.route("/predict/rolling", methods=["POST"])
def predict_rolling():
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "Body JSON kosong."}), 400

    try:
        events = data.get("events", [])
        if len(events) < 3:
            return jsonify({"error": "Dibutuhkan minimal 3 data event."}), 400

        days   = int(data.get("days", 7))
        days   = max(1, min(days, 7))  # max 7 hari

        window  = list(events[-3:])
        results = []

        for i in range(days):
            feats = {
                "event_lag1"    : float(window[-1]),
                "event_lag2"    : float(window[-2]),
                "event_lag3"    : float(window[-3]),
                "rolling_mean_3": float(np.mean(window[-3:])),
                "rolling_std_3" : float(np.std(window[-3:], ddof=0)),
            }
            X    = np.array([[feats[f] for f in feature_names]])
            pred = float(svr_model.predict(svr_scaler.transform(X))[0])

            margin = pred * 0.05 * (i + 1)

            results.append({
                "day"            : i + 1,
                "forecast_event" : round(pred, 4),
                "forecast_liter" : round(pred * 292, 2),
                "upper_event"    : round(pred + margin, 4),
                "lower_event"    : round(max(0, pred - margin), 4),
                "upper_liter"    : round((pred + margin) * 292, 2),
                "lower_liter"    : round(max(0, pred - margin) * 292, 2),
            })

            window.append(pred)
            window = window[-3:]

        return jsonify({
            "events"   : events,
            "days"     : days,
            "forecasts": results,
        }), 200

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 422
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
if __name__ == "__main__":
    polling_thread = threading.Thread(target=polling_telegram, daemon=True)
    polling_thread.start()
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host="0.0.0.0", port=port, use_reloader=False)