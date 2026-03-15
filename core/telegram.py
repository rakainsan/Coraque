import os
import time
import requests
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID")
TELEGRAM_API_URL   = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
LAST_UPDATE_ID     = None


def send_telegram_notification(svr_forecast: float, rekomendasi: dict,
                                source: str = "-") -> bool:
    tanggal  = datetime.now().strftime("%d-%m-%Y %H:%M")
    tipe     = rekomendasi.get("tipe", "-").upper()
    severity = rekomendasi.get("severity", "-").upper()

    # Bahan kimia
    if rekomendasi.get("bahan_kimia"):
        bahan_lines = ""
        for b in rekomendasi["bahan_kimia"]:
            bahan_lines += (
                f"\n  - <b>{b['nama']}</b>"
                f"\n    Dosis  : {b['dosis']}"
                f"\n    Lokasi : {b.get('lokasi', '-')}"
            )
    else:
        bahan_lines = "\n  Tidak diperlukan bahan kimia tambahan."

    # Tindakan infrastruktur
    if rekomendasi.get("infrastruktur"):
        infra_lines = ""
        for inf in rekomendasi["infrastruktur"]:
            infra_lines += f"\n  - <b>{inf['nama']}</b>: {inf['tindakan']}"
        infra_section = f"\n\n<b>Tindakan Tambahan:</b>{infra_lines}"
    else:
        infra_section = ""

    message = (
        f"<b>PERINGATAN ANOMALI — SISTEM CORAQ</b>\n"
        f"────────────────────────\n"
        f"Tanggal  : {tanggal}\n"
        f"Sensor   : {svr_forecast:.0f}x aktivasi\n"
        f"Volume   : {svr_forecast * 292:.2f} liter\n"
        f"Tipe     : {tipe}\n"
        f"Severity : {severity}\n"
        f"────────────────────────\n"
        f"<b>Tindakan:</b>\n{rekomendasi.get('tindakan', '-')}\n"
        f"\n<b>Bahan Kimia:</b>{bahan_lines}"
        f"{infra_section}\n"
        f"────────────────────────\n"
        f"Sumber: {source}"
    )

    try:
        resp = requests.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": message,
                  "parse_mode": "HTML"},
            timeout=10,
        )
        return resp.ok
    except Exception as e:
        print(f"[Telegram] Gagal kirim notifikasi: {e}")
        return False


def polling_telegram(ask_llm_fn):
    global LAST_UPDATE_ID
    while True:
        try:
            params = {"timeout": 30}
            if LAST_UPDATE_ID:
                params["offset"] = LAST_UPDATE_ID + 1

            resp    = requests.get(f"{TELEGRAM_API_URL}/getUpdates",
                                   params=params, timeout=35)
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
                        "Halo, saya <b>CoraqBot</b>.\n"
                        "Terhubung dengan sistem monitoring limbah batik CORAQ.\n"
                        "Tanya apa saja tentang sensor, prediksi, atau anomali."
                    )
                else:
                    reply = ask_llm_fn(text)

                requests.post(
                    f"{TELEGRAM_API_URL}/sendMessage",
                    json={"chat_id": chat_id, "text": reply,
                          "parse_mode": "HTML"},
                    timeout=10,
                )
        except Exception as e:
            print(f"[Polling] Error: {e}")
        time.sleep(1)