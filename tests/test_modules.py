'''This module contains tests for the Flask and OpenSense modules.'''
# pylint: disable=protected-access
import re
import unittest
import unittest.mock as mock
import io
import json
import requests
import redis
from minio.error import S3Error, InvalidResponseError
from app.storage import store_temperature_data
from app.main import app
from app import opensense
from app import readiness

class TestFlaskApp(unittest.TestCase):
    """Test cases for Flask application endpoints"""

    def setUp(self):
        """Set up test client"""
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        """Clean up after tests"""
        self.app_context.pop()

    def test_app_exists(self):
        """Test that the Flask app exists"""
        self.assertIsNotNone(app)

    def test_version_endpoint(self):
        """Test version endpoint returns 200"""
        response = self.client.get('/version')
        self.assertEqual(response.status_code, 200)

    def test_temperature_endpoint(self):
        """Test temperature endpoint returns 200 or 500"""
        with mock.patch('app.opensense.requests.get',
                        return_value=MockOpenSenseResponse(20)):
            response = self.client.get('/temperature')
            self.assertIn(response.status_code, [200, 500])

    def test_metrics_endpoint(self):
        """Test metrics endpoint returns 200"""
        response = self.client.get('/metrics')
        self.assertEqual(response.status_code, 200)

    def test_store_endpoint_success(self):
        """Test store endpoint with successful storage"""
        with mock.patch('app.storage.store_temperature_data') as mock_store:
            mock_store.return_value = "Temperature data successfully uploaded"

            response = self.client.get('/store')

            self.assertEqual(response.status_code, 200)
            self.assertIn("successfully uploaded", response.get_data(as_text=True))
            mock_store.assert_called_once()

    def test_readyz_endpoint_ready(self):
        """Test /readyz endpoint when service is ready"""
        with mock.patch('app.readiness.readiness_check', return_value=200):
            response = self.client.get('/readyz')
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data['status'], 'ready')

    def test_readyz_endpoint_not_ready(self):
        """Test /readyz endpoint when service is not ready"""
        with mock.patch('app.readiness.readiness_check', return_value=503):
            response = self.client.get('/readyz')
            self.assertEqual(response.status_code, 503)
            data = response.get_json()
            self.assertEqual(data['status'], 'not ready')
            self.assertIn('error', data)


class MockOpenSenseResponse:
    """Mock response class to simulate OpenSenseMap API response."""

    def __init__(self, temp_value):
        self.text = "mock response text"
        self.temp_value = temp_value
        payload = json.dumps([{
            'sensors': [
                {
                    'title': 'Temperatur',
                    'unit': '°C',
                    'lastMeasurement': {'value': str(self.temp_value)}
                }
            ]
        }]).encode('utf-8')
        self.raw = io.BytesIO(payload)
        self.raw.decode_content = False

    def raise_for_status(self):
        """Raise an error for HTTP errors."""
        return None

    def json(self):
        """Return a mock JSON response."""
        return [{
            'sensors': [
                {
                    'title': 'Temperatur',
                    'unit': '°C',
                    'lastMeasurement': {'value': str(self.temp_value)}
                }
            ]
        }]


class FakeRespStreamBad:
    """Response with an invalid JSON stream to trigger ijson parse error."""
    def __init__(self):
        self.raw = io.BytesIO(b'{"not_valid_json"')
        self.raw.decode_content = False
    def raise_for_status(self):
        """No-op for status check."""
        return None

class FakeRespJSONBad:
    """Response without .raw; .json raises to trigger fallback error."""
    def json(self):
        """Raise JSON decode error."""
        raise ValueError("bad json")
    def raise_for_status(self):
        """No-op for status check."""
        return None


class TestOpenSense(unittest.TestCase):
    """Test cases for OpenSense module"""

    def test_get_temperature_returns_tuple(self):
        """Test that opensense.get_temperature returns a tuple with correct format"""
        with mock.patch('app.opensense.requests.get',
                        return_value=MockOpenSenseResponse(20)):
            result, stats = opensense.get_temperature()
        self.assertIsInstance(result, str)
        self.assertIsInstance(stats, dict)
        self.assertIn('total_sensors', stats)
        self.assertIn('null_count', stats)
        self.assertIsNotNone(re.match(
            r"Average temperature: (\d+\.\d{2}) °C \((Warning: Too cold|Good|Warning: Too hot)\)", 
            result
        ))

    def test_temperature_too_cold(self):
        """Test opensense.get_temperature for too cold condition (< 10°C)"""
        with mock.patch('app.opensense.requests.get',
                       return_value=MockOpenSenseResponse(5)):
            result, _ = opensense.get_temperature()
            self.assertIn('Too cold', result)

    def test_temperature_good_range(self):
        """Test opensense.get_temperature for good temperature range (10-30°C)"""
        with mock.patch('app.opensense.requests.get',
                       return_value=MockOpenSenseResponse(20)):
            result, _ = opensense.get_temperature()
            self.assertIn('Good', result)

    def test_temperature_too_hot(self):
        """Test opensense.get_temperature for too hot condition (> 30°C)"""
        with mock.patch('app.opensense.requests.get',
                       return_value=MockOpenSenseResponse(40)):
            result, _ = opensense.get_temperature()
            self.assertIn('Too hot', result)

    def test_cache_hit(self):
        """Test that cached data is returned when available"""
        mock_redis_client = mock.MagicMock()
        mock_redis_client.get.return_value = "cached_result"

        with mock.patch('app.opensense.REDIS_AVAILABLE', True), \
             mock.patch('app.opensense.redis_client', mock_redis_client), \
             mock.patch('app.opensense.requests.get') as mock_requests:

            result, _ = opensense.get_temperature()
            self.assertEqual(result, "cached_result")
            mock_requests.assert_not_called()
            mock_redis_client.get.assert_called_once_with("temperature_data")

    def test_cache_miss_and_store(self):
        """Test that data is fetched and cached on cache miss"""
        mock_redis_client = mock.MagicMock()
        mock_redis_client.get.return_value = None

        with mock.patch('app.opensense.REDIS_AVAILABLE', True), \
             mock.patch('app.opensense.redis_client', mock_redis_client), \
             mock.patch('app.opensense.requests.get',
                       return_value=MockOpenSenseResponse(25)):

            result, _ = opensense.get_temperature()
            self.assertIn('Average temperature', result)
            mock_redis_client.setex.assert_called()
            # Verify cache key and TTL
            call_args = mock_redis_client.setex.call_args
            self.assertEqual(call_args[0][0], "temperature_data")
            self.assertGreater(call_args[0][1], 0)  # TTL should be positive

    def test_cache_hit_bytes_decoded(self):
        """Redis returns bytes; ensure decoded string is returned."""
        mock_redis_client = mock.MagicMock()
        mock_redis_client.get.return_value = b"cached_result"
        with mock.patch('app.opensense.REDIS_AVAILABLE', True), \
             mock.patch('app.opensense.redis_client', mock_redis_client), \
             mock.patch('app.opensense.requests.get') as req_get:
            result, stats = opensense.get_temperature()
        self.assertEqual(result, "cached_result")
        self.assertEqual(stats, {"total_sensors": 0, "null_count": 0})
        req_get.assert_not_called()

    def test_api_timeout(self):
        """requests timeout should return timeout error string and empty stats."""
        with mock.patch('app.opensense.REDIS_AVAILABLE', False), \
             mock.patch('app.opensense.requests.get', side_effect=requests.Timeout):
            result, stats = opensense.get_temperature()
        self.assertTrue(result.startswith("Error: API request timed out"))
        self.assertEqual(stats, {"total_sensors": 0, "null_count": 0})

    def test_api_request_exception(self):
        """Generic request exception should return error string and empty stats."""
        with mock.patch('app.opensense.REDIS_AVAILABLE', False), \
             mock.patch(
                 'app.opensense.requests.get',
                 side_effect=requests.RequestException("boom")
                 ):
            result, stats = opensense.get_temperature()
        self.assertIn("API request failed", result)
        self.assertEqual(stats, {"total_sensors": 0, "null_count": 0})

    def test_streaming_parse_error(self):
        """Invalid stream should trigger parse error path."""
        with mock.patch('app.opensense.REDIS_AVAILABLE', False), \
             mock.patch('app.opensense._request_boxes', return_value=(FakeRespStreamBad(), None)):
            result, stats = opensense.get_temperature()
        self.assertTrue(result.startswith("Error: parse failed"))
        self.assertEqual(stats, {"total_sensors": 0, "null_count": 0})

    def test_fallback_json_decode_error(self):
        """When no .raw, JSON decode error should be handled."""
        with mock.patch('app.opensense.REDIS_AVAILABLE', False), \
             mock.patch('app.opensense._request_boxes', return_value=(FakeRespJSONBad(), None)):
            result, stats = opensense.get_temperature()
        self.assertTrue(result.startswith("Error: parse failed"))
        self.assertEqual(stats, {"total_sensors": 0, "null_count": 0})


class TestOpenSenseHelpers(unittest.TestCase):
    """Unit tests for helper functions in opensense."""
    def test_classify_temperature_ranges(self):
        """Test temperature classification logic."""
        self.assertIn("Too cold", opensense.classify_temperature(-5))
        self.assertEqual("Good", opensense.classify_temperature(20))
        self.assertEqual("Good", opensense.classify_temperature(36))
        self.assertIn("Too hot", opensense.classify_temperature(40))

    def test_compute_stats_counts(self):
        """Test statistics computation from sensor data."""
        sensors = [
            {"unit": "°C", "lastMeasurement": {"value": "10"}},
            {"unit": "°C", "lastMeasurement": {"value": "x"}},
            {"unit": "°C"},
            {"unit": "°F", "lastMeasurement": {"value": "20"}},
        ]
        temp_sum, temp_count, stats = opensense._compute_stats(sensors)
        self.assertEqual(temp_sum, 10.0)
        self.assertEqual(temp_count, 1)
        self.assertEqual(stats["total_sensors"], len(sensors))
        self.assertEqual(stats["null_count"], 2)

    def test_iter_sensors_from_json(self):
        """Test sensor iteration from loaded JSON boxes."""
        boxes = [
            {"sensors": [{"unit": "°C"}, {"unit": "°F"}]},
            {"sensors": [{"unit": "°C"}]},
        ]
        items = list(opensense._iter_sensors_from_json(boxes))
        self.assertEqual(len(items), 3)
        self.assertTrue(all(isinstance(s, dict) for s in items))

    def test_iter_sensors_from_stream(self):
        """Test sensor iteration from streaming JSON boxes."""
        payload = json.dumps([
            {"sensors": [{"unit": "°C"}, {"unit": "°F"}]},
            {"sensors": [{"unit": "°C"}]},
        ]).encode("utf-8")
        stream = io.BytesIO(payload)
        sensors = list(opensense._iter_sensors_from_stream(stream))
        self.assertEqual(len(sensors), 3)
        self.assertEqual(sum(1 for s in sensors if s.get("unit") == "°C"), 2)


class TestStorage(unittest.TestCase):
    """Test cases for storage functionality"""

    def setUp(self):
        """Set up common test data"""
        self.mock_temp_data = (
            "Average temperature: 22.5 °C (Good)\nFrom: test\n",
            {"total_sensors": 10, "null_count": 1}
        )

    def test_store_temperature_data_success(self):
        """Test successful temperature data storage"""
        with mock.patch('app.storage.Minio') as mock_minio_class:
            mock_client = mock.MagicMock()
            mock_minio_class.return_value = mock_client
            mock_client.bucket_exists.return_value = True
            mock_client.list_buckets.return_value = []

            with mock.patch('app.storage.opensense.get_temperature',
                           return_value=self.mock_temp_data):
                result = store_temperature_data()

                self.assertIn("successfully uploaded", result)
                mock_client.put_object.assert_called_once()

    def test_store_temperature_data_create_bucket(self):
        """Test bucket creation when it doesn't exist"""
        with mock.patch('app.storage.Minio') as mock_minio_class:
            mock_client = mock.MagicMock()
            mock_minio_class.return_value = mock_client
            mock_client.bucket_exists.return_value = False
            mock_client.list_buckets.return_value = []

            with mock.patch('app.storage.opensense.get_temperature',
                           return_value=self.mock_temp_data):
                result = store_temperature_data()

                mock_client.make_bucket.assert_called_once_with("temperature-data")
                self.assertIn("successfully uploaded", result)

    def test_store_temperature_data_s3_error(self):
        """Test S3Error exception handling"""
        with mock.patch('app.storage.Minio') as mock_minio_class:
            mock_client = mock.MagicMock()
            mock_minio_class.return_value = mock_client
            mock_client.list_buckets.return_value = []
            mock_client.bucket_exists.side_effect = S3Error(
                code="AccessDenied",
                message="Access denied",
                resource="/temperature-data",
                request_id="test-request-id",
                host_id="test-host-id",
                response=None
            )

            with mock.patch('app.storage.opensense.get_temperature',
                           return_value=self.mock_temp_data):
                result = store_temperature_data()

                self.assertIn("MinIO S3 error occurred", result)
                self.assertIn("Access denied", result)

    def test_store_temperature_data_invalid_response(self):
        """Test InvalidResponseError exception handling"""
        with mock.patch('app.storage.Minio') as mock_minio_class:
            mock_client = mock.MagicMock()
            mock_minio_class.return_value = mock_client
            mock_client.list_buckets.return_value = []
            mock_client.bucket_exists.return_value = True
            mock_client.put_object.side_effect = InvalidResponseError(
                "Invalid response", 
                content_type="application/json",
                body=b"{}"
            )

            with mock.patch('app.storage.opensense.get_temperature',
                           return_value=self.mock_temp_data):
                result = store_temperature_data()

                self.assertIn("MinIO S3 error occurred", result)
                self.assertIn("Invalid response", result)

    def test_store_temperature_data_connection_error(self):
        """Test connection error handling"""
        with mock.patch('app.storage.Minio') as mock_minio_class:
            mock_client = mock.MagicMock()
            mock_minio_class.return_value = mock_client
            mock_client.list_buckets.side_effect = ConnectionError("Network unreachable")
            with mock.patch('app.storage.opensense.get_temperature',
                           return_value=self.mock_temp_data):
                result = store_temperature_data()

                self.assertIn("Cannot connect to MinIO server", result)
                self.assertIn("Network unreachable", result)


class TestReadiness(unittest.TestCase):
    """Test cases for readiness checks"""

    def test_check_caching_redis_unavailable(self):
        """Test check_caching when Redis is not available"""
        with mock.patch('app.readiness.REDIS_AVAILABLE', False):
            result = readiness.check_caching()
            self.assertTrue(result)  # No Redis = cache is old

    def test_check_caching_key_not_exists(self):
        """Test check_caching when cache key doesn't exist"""
        mock_redis_client = mock.MagicMock()
        mock_redis_client.ttl.return_value = -2  # Key doesn't exist

        with mock.patch('app.readiness.REDIS_AVAILABLE', True), \
             mock.patch('app.readiness.redis_client', mock_redis_client):
            result = readiness.check_caching()
            self.assertTrue(result)

    def test_check_caching_key_no_expiry(self):
        """Test check_caching when cache key has no expiry"""
        mock_redis_client = mock.MagicMock()
        mock_redis_client.ttl.return_value = -1  # Key exists but no expiry

        with mock.patch('app.readiness.REDIS_AVAILABLE', True), \
             mock.patch('app.readiness.redis_client', mock_redis_client):
            result = readiness.check_caching()
            self.assertTrue(result)

    def test_check_caching_fresh_cache(self):
        """Test check_caching when cache is fresh"""
        mock_redis_client = mock.MagicMock()
        mock_redis_client.ttl.return_value = 150  # 2.5 minutes remaining

        with mock.patch('app.readiness.REDIS_AVAILABLE', True), \
             mock.patch('app.readiness.redis_client', mock_redis_client):
            result = readiness.check_caching()
            self.assertFalse(result)  # Cache is fresh

    def test_check_caching_redis_error(self):
        """TTL raises RedisError -> treated as old cache (True)"""
        mock_redis_client = mock.MagicMock()
        mock_redis_client.ttl.side_effect = redis.RedisError("boom")

        with mock.patch('app.readiness.REDIS_AVAILABLE', True), \
             mock.patch('app.readiness.redis_client', mock_redis_client), \
             mock.patch('builtins.print'):
            result = readiness.check_caching()
            self.assertTrue(result)

    def test_reachable_boxes_healthy(self):
        """Test reachable_boxes when most sensors are working"""
        mock_stats = {"total_sensors": 100, "null_count": 10}

        with mock.patch('app.readiness.get_temperature',
                       return_value=("temp_result", mock_stats)):
            result = readiness.reachable_boxes()
            self.assertEqual(result, 200)

    def test_reachable_boxes_unhealthy(self):
        """Test reachable_boxes when > 50% sensors are unreachable"""
        mock_stats = {"total_sensors": 100, "null_count": 51}

        with mock.patch('app.readiness.get_temperature',
                       return_value=("temp_result", mock_stats)), \
             mock.patch('builtins.print'):  # Suppress print output
            result = readiness.reachable_boxes()
            self.assertEqual(result, 400)

    def test_reachable_boxes_edge_cases(self):
        """Test reachable_boxes edge cases"""
        # No sensors
        with mock.patch('app.readiness.get_temperature',
                       return_value=("temp", {"total_sensors": 0, "null_count": 0})):
            self.assertEqual(readiness.reachable_boxes(), 200)

        # Exactly 50% unreachable (should be OK)
        with mock.patch('app.readiness.get_temperature',
                       return_value=("temp", {"total_sensors": 100, "null_count": 50})):
            self.assertEqual(readiness.reachable_boxes(), 200)

    def test_reachable_boxes_network_error(self):
        """requests exceptions -> treated as healthy (200)"""
        with mock.patch('app.readiness.get_temperature',
                        side_effect=requests.exceptions.RequestException("net")), \
             mock.patch('builtins.print'):
            self.assertEqual(readiness.reachable_boxes(), 200)

    def test_reachable_boxes_redis_error(self):
        """Redis errors inside get_temperature -> treated as healthy (200)"""
        with mock.patch('app.readiness.get_temperature',
                        side_effect=redis.RedisError("redis down")), \
             mock.patch('builtins.print'):
            self.assertEqual(readiness.reachable_boxes(), 200)

    def test_reachable_boxes_data_error(self):
        """Data parsing error -> returns 400"""
        # Cause a TypeError during percentage calculation
        bad_stats = {"total_sensors": 2, "null_count": "x"}
        with mock.patch('app.readiness.get_temperature',
                        return_value=("temp", bad_stats)), \
             mock.patch('builtins.print'):
            self.assertEqual(readiness.reachable_boxes(), 400)

    def test_readiness_check_redis_error_top_level(self):
        """Top-level Redis error in readiness_check -> returns 200"""
        with mock.patch('app.readiness.check_caching',
                        side_effect=redis.RedisError("ttl failed")), \
             mock.patch('builtins.print'):
            self.assertEqual(readiness.readiness_check(), 200)

    def test_readiness_check_all_good(self):
        """Test readiness_check when everything is healthy"""
        with mock.patch('app.readiness.check_caching', return_value=False), \
             mock.patch('app.readiness.reachable_boxes', return_value=200):
            result = readiness.readiness_check()
            self.assertEqual(result, 200)

    def test_readiness_check_both_bad(self):
        """Test readiness_check when both checks fail"""
        with mock.patch('app.readiness.check_caching', return_value=True), \
             mock.patch('app.readiness.reachable_boxes', return_value=400):
            result = readiness.readiness_check()
            self.assertEqual(result, 503)

    def test_readiness_check_partial_failure(self):
        """Test readiness_check when only one check fails"""
        # Only cache is old
        with mock.patch('app.readiness.check_caching', return_value=True), \
             mock.patch('app.readiness.reachable_boxes', return_value=200):
            result = readiness.readiness_check()
            self.assertEqual(result, 200)

        # Only sensors are unreachable
        with mock.patch('app.readiness.check_caching', return_value=False), \
             mock.patch('app.readiness.reachable_boxes', return_value=400):
            result = readiness.readiness_check()
            self.assertEqual(result, 200)


if __name__ == '__main__':
    unittest.main()
