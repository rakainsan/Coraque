import numpy as np
from flask import Blueprint, jsonify, request, current_app
from datetime import datetime
from core.features import build_features
from core.rekomendasi import get_rekomendasi
from core.telegram import send_telegram_notification

bp = Blueprint("predict", __name__)


@bp.route("/predict", methods=["POST"])
def predict_combined():
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "Body JSON kosong."}), 400

    try:
        feats = (build_features(data["events"]) if "events" in data
                 else data.get("features"))
        if feats is None:
            return jsonify({"error": "Kirim 'events' atau 'features'."}), 400

        source = data.get("source", "-")
        models = current_app.config["MODELS"]

        # SVR forecast
        X_svr    = np.array([[feats[f] for f in models["feature_names"]]])
        svr_pred = float(models["svr"].predict(
                       models["svr_scaler"].transform(X_svr))[0])

        # OCSVM detect
        feats["svr_pred"]       = svr_pred
        feats["jumlah_kain"]    = float(data.get("jumlah_kain", 0))
        feats["panjang_kain_m"] = float(data.get("panjang_kain_m", 0))

        X_oc    = np.array([[feats[f] for f in models["ocsvm_feature_names"]]])
        X_oc_sc = models["ocsvm_scaler"].transform(X_oc)
        oc_label  = int(models["ocsvm"].predict(X_oc_sc)[0])
        oc_score  = float(models["ocsvm"].decision_function(X_oc_sc)[0])
        is_anomaly = oc_label == -1

        # Rekomendasi berbasis oc_score
        rekomendasi = get_rekomendasi(
            oc_score       = oc_score,
            event_lag1     = feats["event_lag1"],
            rolling_mean_3 = feats["rolling_mean_3"]
        )

        # Update context LLM
        current_app.config["LAST_PREDICTION"] = {
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
            "rekomendasi"   : rekomendasi,
        }

        telegram_sent = False
        if is_anomaly:
            telegram_sent = send_telegram_notification(
                svr_pred, rekomendasi, source)

        return jsonify({
            "svr"          : {"forecast": round(svr_pred, 4)},
            "ocsvm"        : {"is_anomaly": is_anomaly, "label": oc_label,
                              "score": round(oc_score, 6)},
            "rekomendasi"  : rekomendasi,
            "telegram_sent": telegram_sent,
        }), 200

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 422
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/predict/rolling", methods=["POST"])
def predict_rolling():
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "Body JSON kosong."}), 400

    try:
        events = data.get("events", [])
        if len(events) < 3:
            return jsonify({"error": "Dibutuhkan minimal 3 data event."}), 400

        days   = max(1, min(int(data.get("days", 7)), 7))
        models = current_app.config["MODELS"]
        window = list(events[-3:])
        results = []

        for i in range(days):
            feats = {
                "event_lag1"    : float(window[-1]),
                "event_lag2"    : float(window[-2]),
                "event_lag3"    : float(window[-3]),
                "rolling_mean_3": float(np.mean(window[-3:])),
                "rolling_std_3" : float(np.std(window[-3:], ddof=0)),
            }
            X    = np.array([[feats[f] for f in models["feature_names"]]])
            pred = float(models["svr"].predict(
                       models["svr_scaler"].transform(X))[0])
            margin = pred * 0.05 * (i + 1)

            results.append({
                "day"           : i + 1,
                "forecast_event": round(pred, 4),
                "forecast_liter": round(pred * 292, 2),
                "upper_event"   : round(pred + margin, 4),
                "lower_event"   : round(max(0, pred - margin), 4),
                "upper_liter"   : round((pred + margin) * 292, 2),
                "lower_liter"   : round(max(0, pred - margin) * 292, 2),
            })
            window.append(pred)
            window = window[-3:]

        return jsonify({"events": events, "days": days,
                        "forecasts": results}), 200

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 422
    except Exception as e:
        return jsonify({"error": str(e)}), 500