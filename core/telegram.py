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
    sev      = rekomendasi.get("severity", "normal")
    tipe     = rekomendasi.get("tipe", "normal")
    emoji    = rekomendasi.get("emoji", "✅")
    tindakan = rekomendasi.get("tindakan", "-")
    volume   = svr_forecast * 292

    # ── Header per severity ───────────────────────────────────────────
    header_map = {
        "normal"    : "SISTEM NORMAL — CORAQ",
        "ringan"    : "ANOMALI SPIKE RINGAN — CORAQ",
        "sedang"    : "ANOMALI SPIKE SEDANG — CORAQ",
        "berat"     : "ANOMALI SPIKE BERAT — CORAQ",
        "peringatan": "PERINGATAN DROP VOLUME — CORAQ",
    }
    header = header_map.get(sev, "NOTIFIKASI CORAQ")

    # ── Info volume ───────────────────────────────────────────────────
    volume_line = (
        f"Sensor   : {svr_forecast:.0f}x aktivasi\n"
        f"Volume   : {volume:.2f} liter\n"
        f"Tipe     : {tipe.upper()}\n"
        f"Severity : {sev.upper()}\n"
    )

    # ── Bahan kimia ───────────────────────────────────────────────────
    bahan_section = ""
    if rekomendasi.get("bahan_kimia"):
        bahan_section = "\n\n<b>Bahan Kimia:</b>"
        for b in rekomendasi["bahan_kimia"]:
            bahan_section += (
                f"\n  ▸ <b>{b['nama']}</b>"
                f"\n    Dosis  : {b['dosis']}"
                f"\n    Lokasi : {b.get('lokasi', '-')}"
            )
    elif sev not in ("normal",):
        bahan_section = "\n\n<b>Bahan Kimia:</b>\n  Tidak diperlukan bahan kimia tambahan."

    # ── Infrastruktur / langkah ───────────────────────────────────────
    infra_section = ""
    if rekomendasi.get("infrastruktur"):
        infra_section = "\n\n<b>Tindakan Tambahan:</b>"
        for inf in rekomendasi["infrastruktur"]:
            infra_section += f"\n  ▸ <b>{inf['nama']}</b>"
            if inf.get("tindakan"):
                infra_section += f"\n    {inf['tindakan']}"
            if inf.get("langkah"):
                for idx, l in enumerate(inf["langkah"], 1):
                    infra_section += f"\n    {idx}. {l}"

    # ── Rakit pesan per severity ──────────────────────────────────────
    if sev == "normal":
        message = (
            f"✅ <b>{header}</b>\n"
            f"────────────────────────\n"
            f"Tanggal  : {tanggal}\n"
            f"{volume_line}"
            f"────────────────────────\n"
            f"{tindakan}\n"
            f"────────────────────────\n"
            f"Sumber: {source}"
        )

    elif sev == "ringan":
        message = (
            f"⚠️ <b>{header}</b>\n"
            f"────────────────────────\n"
            f"Tanggal  : {tanggal}\n"
            f"{volume_line}"
            f"────────────────────────\n"
            f"<b>Tindakan:</b>\n{tindakan}"
            f"{bahan_section}\n"
            f"────────────────────────\n"
            f"Sumber: {source}"
        )

    elif sev == "sedang":
        message = (
            f"🚨 <b>{header}</b>\n"
            f"════════════════════════\n"
            f"Tanggal  : {tanggal}\n"
            f"{volume_line}"
            f"════════════════════════\n"
            f"<b>Tindakan:</b>\n{tindakan}"
            f"{bahan_section}\n"
            f"════════════════════════\n"
            f"Sumber: {source}"
        )

    elif sev == "berat":
        message = (
            f"🆘 <b>{header}</b>\n"
            f"▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓\n"
            f"Tanggal  : {tanggal}\n"
            f"{volume_line}"
            f"▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓\n"
            f"<b>Tindakan Segera:</b>\n{tindakan}"
            f"{bahan_section}"
            f"{infra_section}\n"
            f"▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓\n"
            f"Sumber: {source}"
        )

    else:  # peringatan (drop)
        message = (
            f"🔻 <b>{header}</b>\n"
            f"────────────────────────\n"
            f"Tanggal  : {tanggal}\n"
            f"{volume_line}"
            f"────────────────────────\n"
            f"<b>Tindakan:</b>\n{tindakan}"
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