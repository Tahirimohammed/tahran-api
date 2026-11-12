import os
from datetime import datetime, timezone
from typing import Literal

import redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from redis.exceptions import RedisError


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

app = FastAPI(title="IoT Monitoring API", version="1.0.0")


class Metric(BaseModel):
    device_id: str = Field(pattern=r"^device_[0-9]{2}$")
    status: Literal["online", "offline"]
    temperature: float
    battery_level: float
    humidity: float = Field(default=50.0, ge=0, le=100)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


@app.get("/health")
def health() -> dict[str, str]:
    try:
        redis_client.ping()
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Redis unavailable") from exc
    return {"status": "ok"}


@app.post("/metrics", status_code=201)
def ingest_metric(metric: Metric) -> dict[str, str]:
    timestamp = metric.timestamp.astimezone(timezone.utc).isoformat()
    fields = {
        "device_id": metric.device_id,
        "status": metric.status,
        "temperature": str(metric.temperature),
        "battery_level": str(metric.battery_level),
        "humidity": str(metric.humidity),
        "timestamp": timestamp,
    }

    try:
        with redis_client.pipeline(transaction=True) as pipeline:
            pipeline.hset(f"device:{metric.device_id}", mapping=fields)
            pipeline.xadd("telemetry:stream", fields)
            pipeline.incr("metrics:count")
            results = pipeline.execute()
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Could not write metric to Redis") from exc

    return {"device_id": metric.device_id, "stream_id": results[1]}