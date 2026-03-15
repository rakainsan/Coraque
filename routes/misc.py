import os
import requests
from datetime import datetime
from flask import Blueprint, jsonify
from flask import send_from_directory

bp = Blueprint("misc", __name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID")
TELEGRAM_API_URL   = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


@bp.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ok", "message": "CORAQUE API is running"}), 200

@bp.route("/docs", methods=["GET"])
def docs():
    return send_from_directory(
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "static"),
        "docs.html"
    )


@bp.route("/telegram/test", methods=["GET"])
def telegram_test():
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
            json={"chat_id": TELEGRAM_CHAT_ID, "text": message,
                  "parse_mode": "MarkdownV2"},
            timeout=10,
        )
        if resp.ok:
            return jsonify({"status": "ok",
                            "message": "Pesan test berhasil dikirim."}), 200
        return jsonify({"status": "error", "detail": resp.json()}), 502
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500