from __future__ import annotations

import json
import os
import time

import redis
from redis.exceptions import RedisError


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
STREAM_KEY = "telemetry:stream"
ALERTS_KEY = "alerts:recent"
ALERT_TTL_SECONDS = 24 * 60 * 60
LAST_ID_KEY = "alert_worker:last_id"
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def detect_anomaly(fields: dict[str, str]) -> tuple[str, str] | None:
    try:
        temperature = float(fields["temperature"])
        battery_level = float(fields["battery_level"])
    except (KeyError, TypeError, ValueError):
        return "invalid_measurement", "Temperature or battery value is not numeric"

    if not -50 <= temperature <= 125 or not 0 <= battery_level <= 100:
        return "invalid_measurement", "Measurement is outside the physical range"
    if fields.get("status") == "offline":
        return "device_offline", "Device reported an interruption"
    if temperature > 75:
        return "overheating", f"Temperature {temperature:.1f}°C exceeds 75°C"
    return None


def record_alert(stream_id: str, fields: dict[str, str], anomaly: tuple[str, str]) -> None:
    alert_id = f"alert:{stream_id}"
    alert = {
        "id": stream_id,
        "device_id": fields.get("device_id", "unknown"),
        "type": anomaly[0],
        "message": anomaly[1],
        "temperature": fields.get("temperature", ""),
        "timestamp": fields.get("timestamp", ""),
    }
    encoded_alert = json.dumps(alert)

    with redis_client.pipeline(transaction=True) as pipeline:
        pipeline.set(alert_id, encoded_alert, ex=ALERT_TTL_SECONDS, nx=True)
        pipeline.zadd(ALERTS_KEY, {alert_id: time.time()})
        pipeline.expire(ALERTS_KEY, ALERT_TTL_SECONDS)
        results = pipeline.execute()

    if not results[0]:
        redis_client.zrem(ALERTS_KEY, alert_id)


def process_entry(stream_id: str, fields: dict[str, str]) -> None:
    anomaly = detect_anomaly(fields)
    if anomaly is not None:
        record_alert(stream_id, fields, anomaly)
        print(f"Alert {anomaly[0]} for {fields.get('device_id', 'unknown')} ({stream_id})")


def run() -> None:
    redis_client.ping()
    last_id = redis_client.get(LAST_ID_KEY) or "0-0"
    print(f"Listening to {STREAM_KEY} from {last_id}")

    while True:
        try:
            batches = redis_client.xread({STREAM_KEY: last_id}, count=100, block=5000)
            for _, entries in batches:
                for stream_id, fields in entries:
                    process_entry(stream_id, fields)
                    redis_client.set(LAST_ID_KEY, stream_id)
                    last_id = stream_id
        except RedisError as exc:
            print(f"Redis error: {exc}; retrying in 2 seconds")
            time.sleep(2)


if __name__ == "__main__":
    run()