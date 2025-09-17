"""Module to get entries from OpenSenseMap API and get the average temperature"""
from datetime import datetime, timezone, timedelta
import json
from typing import Iterable, Dict, Tuple, Optional
import requests
import redis
import ijson
from ijson.common import JSONError as IjsonJSONError
from app.config import create_redis_client, CACHE_TTL

redis_client, REDIS_AVAILABLE = create_redis_client()

_sensor_stats = {"total_sensors": 0, "null_count": 0}

def classify_temperature(average):
    """Classify temperature based on ranges using dictionary approach"""
    temp_classifications = {
        "cold": (float('-inf'), 10, "Warning: Too cold"),
        "good": (10, 36, "Good"),
        "hot": (36, float('inf'), "Warning: Too hot"),
    }
    for _, (min_temp, max_temp, status) in temp_classifications.items():
        if min_temp < average <= max_temp:
            return status
    return "Unknown"

def _iter_sensors_from_stream(stream) -> Iterable[dict]:
    """Yield sensors from a streaming JSON array of boxes."""
    yield from ijson.items(stream, 'item.sensors.item')

def _iter_sensors_from_json(boxes: Iterable[dict]) -> Iterable[dict]:
    """Yield sensors from a loaded list of boxes."""
    for box in boxes:
        yield from box.get("sensors", [])

def _compute_stats(sensors: Iterable[dict]) -> Tuple[float, int, Dict[str, int]]:
    """Compute temperature sum/count and stats from an iterable of sensors."""
    temp_sum = 0.0
    temp_count = 0
    stats = {"total_sensors": 0, "null_count": 0}

    for sensor in sensors:
        stats["total_sensors"] += 1
        if sensor.get('unit') != "°C":
            continue

        last = sensor.get('lastMeasurement')
        if not last or 'value' not in last:
            stats["null_count"] += 1
            continue

        try:
            temp_sum += float(last['value'])
            temp_count += 1
        except (TypeError, ValueError):
            stats["null_count"] += 1

    return temp_sum, temp_count, stats

def _empty_stats() -> Dict[str, int]:
    return {"total_sensors": 0, "null_count": 0}

def _get_cached_temperature() -> Optional[str]:
    if not REDIS_AVAILABLE:
        return None
    try:
        cached = redis_client.get("temperature_data")
        if cached:
            return cached.decode("utf-8") if isinstance(cached, (bytes, bytearray)) else cached
    except redis.RedisError:
        return None
    return None

def _set_cached_temperature(value: str) -> None:
    if not REDIS_AVAILABLE:
        return
    try:
        redis_client.setex("temperature_data", CACHE_TTL, value)
    except redis.RedisError:
        pass

def _build_params() -> Dict[str, str]:
    time_iso = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    return {"date": time_iso, "format": "json"}

def _request_boxes(params: Dict[str, str]):
    try:
        resp = requests.get(
            "https://api.opensensemap.org/boxes",
            params=params,
            stream=True,
            timeout=(60, 90)
        )
        if hasattr(resp, "raise_for_status"):
            resp.raise_for_status()
        if hasattr(resp, "raw") and hasattr(resp.raw, "decode_content"):
            resp.raw.decode_content = True
        return resp, None
    except requests.Timeout:
        return None, "Error: API request timed out\n"
    except requests.RequestException as e:
        return None, f"Error: API request failed - {e}\n"

def _make_sensor_iter(response) -> Tuple[Optional[Iterable[dict]], Optional[str]]:
    # Prefer streaming if raw is available; otherwise load JSON once.
    if hasattr(response, "raw") and getattr(response, "raw", None):
        return _iter_sensors_from_stream(response.raw), None
    try:
        boxes = response.json()
    except (json.JSONDecodeError, ValueError) as e:
        return None, f"Error: parse failed - {e}\n"
    return _iter_sensors_from_json(boxes), None

def get_temperature():
    '''Function to get the average temperature from OpenSenseMap API.'''
    cached = _get_cached_temperature()
    if cached:
        return cached, _empty_stats()

    params = _build_params()
    response, err = _request_boxes(params)
    if err:
        return err, _empty_stats()

    sensors_iter, err = _make_sensor_iter(response)
    if err or sensors_iter is None:
        return err or "Error: parser unavailable\n", _empty_stats()

    try:
        temp_sum, temp_count, stats = _compute_stats(sensors_iter)
    except IjsonJSONError as e:
        return f"Error: parse failed - {e}\n", _empty_stats()

    average = (temp_sum / temp_count) if temp_count else 0.0
    status = classify_temperature(average)
    result = f'Average temperature: {average:.2f} °C ({status})\n'

    _set_cached_temperature(result)
    _sensor_stats.update(stats)
    return result, _sensor_stats
