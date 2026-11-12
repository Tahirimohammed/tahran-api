from __future__ import annotations

import os
import random
import time
from datetime import datetime, timezone

import requests


API_URL = os.getenv("API_URL", "http://localhost:8000")
METRICS_COUNT = 500
DEVICE_COUNT = 20
ANOMALIES = {
    24: ("offline", 22.0, 85.0),
    73: ("online", 91.0, 78.0),
    126: ("online", -100.0, 80.0),
    181: ("offline", 24.0, 70.0),
    236: ("online", 88.0, 76.0),
    291: ("online", 200.0, 73.0),
    346: ("offline", 19.0, 68.0),
    401: ("online", 96.0, 81.0),
    456: ("offline", 25.0, 72.0),
    489: ("online", 83.0, 79.0),
}


def make_metric(index: int) -> dict[str, str | float]:
    device_number = (index % DEVICE_COUNT) + 1
    status, temperature, battery_level = ANOMALIES.get(
        index,
        (
            "online",
            round(random.uniform(18.0, 35.0), 2),
            round(random.uniform(55.0, 100.0), 2),
        ),
    )
    return {
        "device_id": f"device_{device_number:02d}",
        "status": status,
        "temperature": temperature,
        "battery_level": battery_level,
        "humidity": round(random.uniform(30.0, 75.0), 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    sent = 0
    anomaly_indices = set(ANOMALIES)
    with requests.Session() as session:
        for index in range(METRICS_COUNT):
            response = session.post(f"{API_URL}/metrics", json=make_metric(index), timeout=5)
            response.raise_for_status()
            sent += 1
            label = " (anomaly injected)" if index in anomaly_indices else ""
            print(f"Sent {sent}/{METRICS_COUNT}{label}")
            time.sleep(0.01)

    print(f"Done: {sent} metrics sent, {len(ANOMALIES)} anomalies injected.")


if __name__ == "__main__":
    main()