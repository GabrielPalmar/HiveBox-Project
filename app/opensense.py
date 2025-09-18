"""Module to get entries from OpenSenseMap API and get the average temperature"""
from datetime import datetime, timezone, timedelta
import json
from typing import Iterable, Dict, Tuple, Optional
import time
import requests
import redis
import ijson
from ijson.common import JSONError as IjsonJSONError
from app.config import create_redis_client, CACHE_TTL

try:
    REDIS_CLIENT, REDIS_AVAILABLE = create_redis_client()
except (redis.ConnectionError, redis.TimeoutError, OSError, ImportError) as e:
    print(f"Warning: Redis client creation failed - {e}")
    REDIS_CLIENT = None
    REDIS_AVAILABLE = False

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

def _get_cached_temperature() -> Optional[Tuple[str, Dict[str, int]]]:
    if not REDIS_AVAILABLE:
        return None
    try:
        cached_temp = REDIS_CLIENT.get("temperature_data")
        cached_stats = REDIS_CLIENT.get("temperature_stats")
        if cached_temp and cached_stats:
            temp = cached_temp.decode("utf-8") if isinstance(
                cached_temp,
                (bytes, bytearray)
                ) else cached_temp
            stats = json.loads(cached_stats)
            return temp, stats
    except (redis.RedisError, json.JSONDecodeError):
        return None
    return None

def _set_cached_temperature(value: str, stats: Dict[str, int]) -> None:
    if not REDIS_AVAILABLE:
        return
    try:
        REDIS_CLIENT.setex("temperature_data", CACHE_TTL, value)
        REDIS_CLIENT.setex("temperature_stats", CACHE_TTL, json.dumps(stats))
    except redis.RedisError:
        pass

def _build_params() -> Dict[str, str]:
    time_iso = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    return {"date": time_iso, "format": "json"}

def _request_boxes(params: Dict[str, str], max_retries: int = 3):
    """Request boxes with retry logic and shorter timeouts."""
    for attempt in range(max_retries):
        try:
            # Reduce timeout to avoid nginx timeout
            resp = requests.get(
                "https://api.opensensemap.org/boxes",
                params=params,
                stream=True,
                timeout=(5, 30),  # 5 seconds connect, 30 seconds read (was 60, 90)
                headers={
                    'User-Agent': 'HiveBox-Project/1.0',
                    'Accept': 'application/json'
                }
            )

            if resp.status_code == 503:
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 5)  # Max 5 seconds wait
                    time.sleep(wait_time)
                    continue
                return None, "Error: API service unavailable (503)\n"

            resp.raise_for_status()
            if hasattr(resp, "raw") and hasattr(resp.raw, "decode_content"):
                resp.raw.decode_content = True
            return resp, None

        except requests.Timeout:
            if attempt < max_retries - 1:
                time.sleep(1)  # Short delay before retry
                continue
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
        return cached  # Now returns (temperature, stats) tuple

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

    _set_cached_temperature(result, stats)
    _sensor_stats.update(stats)
    return result, stats  # Return the current stats, not global
