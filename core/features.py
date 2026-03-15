import numpy as np

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