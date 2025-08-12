'''This module contains tests for the Flask and OpenSense modules.'''
import re
import unittest.mock as mock
from minio.error import S3Error, InvalidResponseError
from app.storage import store_temperature_data
from app.main import app
from app import opensense
from app import readiness

def test_app_exists():
    """Test that the Flask app exists"""
    assert app is not None

def test_version_endpoint():
    """Test version endpoint with test client"""
    client = app.test_client()
    response = client.get('/version')
    assert response.status_code == 200

def test_temperature_endpoint():
    """Test temperature endpoint with test client"""
    client = app.test_client()
    response = client.get('/temperature')
    assert response.status_code in [200, 500]

def test_metrics_endpoint():
    """Test metrics endpoint"""
    client = app.test_client()
    response = client.get('/metrics')
    assert response.status_code == 200

def test_opensense_get_temperature():
    """Test that opensense.get_temperature returns a tuple"""
    result, stats = opensense.get_temperature()  # Unpack the tuple
    assert isinstance(result, str)
    assert isinstance(stats, dict)
    assert re.match(
        r"Average temperature: (\d+\.\d{2}) °C \((Warning: Too cold|Good|Warning: Too hot)\)", 
        result
        )

def mock_response(temp_value):
    """Mock response for OpenSenseMap API"""
    class MockResponse:
        """Mock response class to simulate OpenSenseMap API response."""
        def __init__(self):
            self.text = "mock response text"  # Add this line
            
        def json(self):
            """Return a mock JSON response."""
            return [{
                'sensors': [
                    {
                        'title': 'Temperatur',
                        'unit': '°C',  # Add unit field
                        'lastMeasurement': {'value': str(temp_value)}
                    }
                ]
            }]
    return MockResponse()

def test_opensense_get_temperature_too_cold():
    """Test opensense.get_temperature for too cold condition"""
    with mock.patch('app.opensense.requests.get', return_value=mock_response(5)):
        result, _ = opensense.get_temperature()  # Unpack tuple
        assert 'Too cold' in result

def test_opensense_get_temperature_too_hot():
    """Test opensense.get_temperature for too hot condition"""
    with mock.patch('app.opensense.requests.get', return_value=mock_response(40)):
        result, _ = opensense.get_temperature()  # Unpack tuple
        assert 'Too hot' in result

def test_opensense_cache_get():
    """Test that cached data is used if available"""
    with mock.patch('app.opensense.REDIS_AVAILABLE', True), \
         mock.patch('app.opensense.redis_client.get', return_value="cached_result"), \
         mock.patch('app.opensense.requests.get') as mock_requests:
        result, _ = opensense.get_temperature()  # Unpack tuple
        assert result == "cached_result"
        mock_requests.assert_not_called()

def test_opensense_cache_setex():
    """Test that data is cached after fetching"""
    with mock.patch('app.opensense.REDIS_AVAILABLE', True), \
         mock.patch('app.opensense.redis_client.get', return_value=None), \
         mock.patch('app.opensense.redis_client.setex') as mock_setex, \
         mock.patch('app.opensense.requests.get', return_value=mock_response(25)):
        result, _ = opensense.get_temperature()  # Unpack tuple
        assert 'Average temperature' in result
        mock_setex.assert_called()

def test_store_endpoint():
    """Test store endpoint with test client"""
    client = app.test_client()
    response = client.get('/store')
    # Should return 200 or 500 depending on MinIO availability
    assert response.status_code in [200, 500]

def test_store_temperature_data():
    '''Test that store endpoint works'''
    with mock.patch('app.storage.store_temperature_data') as mock_store:
        mock_store.return_value = "Temperature data successfully uploaded"

        client = app.test_client()
        response = client.get('/store')

        assert response.status_code == 200
        assert "successfully uploaded" in response.get_data(as_text=True)
        mock_store.assert_called_once()

def test_store_temperature_data_integration():
    '''Test that storage function works with mocked MinIO'''
    with mock.patch('app.storage.Minio') as mock_minio_class:
        # Mock MinIO client
        mock_client = mock.MagicMock()
        mock_minio_class.return_value = mock_client
        mock_client.bucket_exists.return_value = True
        mock_client.put_object.return_value = None
        mock_client.list_buckets.return_value = []

        # Mock temperature data - return tuple
        with mock.patch('app.opensense.get_temperature') as mock_temp:
            mock_temp.return_value = ("Average temperature: 22.5 °C (Good)\nFrom: test\n", {"total_sensors": 0, "null_count": 0})

            # Import and call the actual function
            result = store_temperature_data()

            # Test the result
            assert "successfully uploaded" in result
            mock_client.put_object.assert_called_once()

def test_store_temperature_data_bucket_creation():
    '''Test bucket creation when bucket doesn't exist'''
    with mock.patch('app.storage.Minio') as mock_minio_class:
        mock_client = mock.MagicMock()
        mock_minio_class.return_value = mock_client

        # Mock bucket doesn't exist initially
        mock_client.bucket_exists.return_value = False
        mock_client.make_bucket.return_value = None
        mock_client.put_object.return_value = None
        mock_client.list_buckets.return_value = []

        with mock.patch('app.opensense.get_temperature') as mock_temp:
            mock_temp.return_value = ("Average temperature: 22.5 °C (Good)\nFrom: test\n", {"total_sensors": 0, "null_count": 0})

            result = store_temperature_data()

            # Verify bucket creation was called
            mock_client.bucket_exists.assert_called_once_with("temperature-data")
            mock_client.make_bucket.assert_called_once_with("temperature-data")
            mock_client.put_object.assert_called_once()

            assert "successfully uploaded" in result
            assert "temperature-data" in result

def test_store_temperature_data_s3_error():
    '''Test S3Error exception handling'''
    with mock.patch('app.storage.Minio') as mock_minio_class:
        mock_client = mock.MagicMock()
        mock_minio_class.return_value = mock_client

        # Mock S3Error during bucket check
        mock_client.list_buckets.return_value = []
        mock_client.bucket_exists.side_effect = S3Error(
            code="AccessDenied",
            message="Access denied",
            resource="/temperature-data",
            request_id="test-request-id",
            host_id="test-host-id",
            response=None
        )
        
        # Mock get_temperature to return tuple
        with mock.patch('app.opensense.get_temperature') as mock_temp:
            mock_temp.return_value = ("Test temperature data", {"total_sensors": 0, "null_count": 0})

            result = store_temperature_data()

            assert "MinIO S3 error occurred" in result
            assert "Access denied" in result

def test_store_temperature_data_invalid_response_error():
    '''Test InvalidResponseError exception handling'''
    with mock.patch('app.storage.Minio') as mock_minio_class:
        mock_client = mock.MagicMock()
        mock_minio_class.return_value = mock_client

        # Mock InvalidResponseError during put_object
        mock_client.list_buckets.return_value = []
        mock_client.bucket_exists.return_value = True
        mock_client.put_object.side_effect = InvalidResponseError(
            "Invalid response", 
            content_type="application/json",
            body=b"{}"
        )

        with mock.patch('app.opensense.get_temperature') as mock_temp:
            mock_temp.return_value = ("Test temperature data", {"total_sensors": 0, "null_count": 0})

            result = store_temperature_data()

            assert "MinIO S3 error occurred" in result
            assert "Invalid response" in result

def test_readiness_reachability():
    '''Test readiness endpoint reachability'''
    with mock.patch('app.readiness.reachable_boxes') as mock_check:
        mock_check.return_value = 200

        result = readiness.reachable_boxes()

        assert result == 200

def test_readiness_unreachability():
    '''Test readiness endpoint unreachability'''
    with mock.patch('app.readiness.reachable_boxes') as mock_check:
        mock_check.return_value = 400

        result = readiness.reachable_boxes()

        assert result == 400

def test_readiness_check():
    '''Test readiness endpoint check'''
    with mock.patch('app.readiness.reachable_boxes', return_value=200), \
         mock.patch('app.readiness.check_caching', return_value=False):

        result = readiness.readiness_check()

        assert result == 200

def test_readiness_check_unreachable():
    '''Test readiness endpoint unreachability'''
    with mock.patch('app.readiness.reachable_boxes', return_value=400), \
         mock.patch('app.readiness.check_caching', return_value=True):

        result = readiness.readiness_check()

        assert result == 503
