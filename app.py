import os
import warnings
import threading
import joblib
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from groq import Groq


load_dotenv()
warnings.filterwarnings("ignore")

from core.telegram import polling_telegram
from routes.predict import bp as predict_bp
from routes.misc    import bp as misc_bp

app = Flask(__name__)
CORS(app)

# ── Load models sekali saat startup ─────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
def _load(name):
    return joblib.load(os.path.join(BASE_DIR, "models", name))

app.config["MODELS"] = {
    "svr"               : _load("CORAQUE.pkl"),
    "svr_scaler"        : _load("CORAQUEscaler.pkl"),
    "feature_names"     : _load("CORAQUEfeatures.pkl"),
    "ocsvm"             : _load("CORAQUE_ocsvm.pkl"),
    "ocsvm_scaler"      : _load("CORAQUE_ocsvm_scaler.pkl"),
    "ocsvm_feature_names": _load("CORAQUE_ocsvm_features.pkl"),
}
app.config["LAST_PREDICTION"] = None

# ── Groq LLM ────────────────────────────────────────────────────────────────
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def ask_llm(prompt: str) -> str:
    ctx = app.config.get("LAST_PREDICTION")
    if ctx:
        rek = ctx.get("rekomendasi", {})
        status = "ANOMALI ⚠️" if ctx["is_anomaly"] else "NORMAL ✅"
        if ctx["is_anomaly"] and rek:
            bahan_str = ", ".join(
                f"{b['nama']} ({b['dosis']})"
                for b in rek.get("bahan_kimia", [])
            ) or "tidak ada"
            rek_info = (
                f"\n    - Tipe Anomali : {rek.get('tipe','').upper()} — {rek.get('severity','')}"
                f"\n    - Tindakan     : {rek.get('tindakan','')}"
                f"\n    - Bahan Kimia  : {bahan_str}"
            )
        else:
            rek_info = "\n    - Rekomendasi  : Kondisi normal, tidak ada tindakan khusus."

        prediksi_info = f"""
    ## 📊 Hasil Prediksi Terakhir ({ctx['tanggal']})
    - SVR Forecast : {ctx['svr_forecast']} event
    - Volume       : {ctx['volume_liter']} liter
    - Status OCSVM : {status}
    - OCSVM Score  : {ctx['ocsvm_score']}
    - Lag 1/2/3    : {ctx['event_lag1']} / {ctx['event_lag2']} / {ctx['event_lag3']}
    - Jumlah Kain  : {ctx['jumlah_kain']} lembar
    {rek_info}"""
    else:
        prediksi_info = "\n    Belum ada prediksi. Minta user jalankan prediksi dahulu."

    system_prompt = f"""
    Kamu adalah CoraqBot, asisten kecerdasan buatan sistem monitoring limbah batik CORAQ singkatan dari Continuous Observation Remote Analysis Quantification di Kota Pekalongan.
    Sistem CORAQ: Bak 1 (monitoring awal) → Bak 2 (elektrokoagulasi, 30 menit) →
    Bak 3 (flokulasi 20 menit + sedimentasi 30 menit) → Bak 4 (netralisasi + monitoring akhir).
    ML: SVR forecast volume harian, OCSVM deteksi anomali. 1 event = 292 liter.
    {prediksi_info}
    Jawab bahasa Indonesia, ramah, ringkas. Jika di luar konteks CORAQ, arahkan kembali.
    """
    try:
        res = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user",   "content": prompt}]
        )
        return res.choices[0].message.content
    except Exception as e:
        return f"Maaf, terjadi kesalahan: {str(e)}"

# ── Register blueprints ──────────────────────────────────────────────────────
app.register_blueprint(predict_bp)
app.register_blueprint(misc_bp)

# ── Telegram polling — jalan saat startup gunicorn ───────────────────────────
threading.Thread(
    target=polling_telegram, args=(ask_llm,), daemon=True
).start()

# ── Run (development only) ───────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port, use_reloader=False)