'''This module contains tests for the Flask and OpenSense modules.'''
import re
import unittest.mock as mock
from app.storage import store_temperature_data
from app.main import app
from app import opensense

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
    """Test that opensense.get_temperature returns a string"""
    result = opensense.get_temperature()
    assert isinstance(result, str)
    assert re.match(
        r"Average temperature: (\d+\.\d{2}) °C \((Warning: Too cold|Good|Warning: Too hot)\)", 
        result
        )

def mock_response(temp_value):
    """Mock response for OpenSenseMap API"""
    class MockResponse:
        """Mock response class to simulate OpenSenseMap API response."""
        def json(self):
            """Return a mock JSON response."""
            return [{
                'sensors': [
                    {
                        'title': 'Temperatur',
                        'lastMeasurement': {'value': str(temp_value)}
                    }
                ]
            }]
    return MockResponse()

def test_opensense_get_temperature_too_cold():
    """Test opensense.get_temperature for too cold condition"""
    with mock.patch('app.opensense.requests.get', return_value=mock_response(5)):
        result = opensense.get_temperature()
        assert 'Too cold' in result

def test_opensense_get_temperature_too_hot():
    """Test opensense.get_temperature for too hot condition"""
    with mock.patch('app.opensense.requests.get', return_value=mock_response(40)):
        result = opensense.get_temperature()
        assert 'Too hot' in result

def test_opensense_cache_get():
    """Test that cached data is used if available"""
    with mock.patch('app.opensense.REDIS_AVAILABLE', True), \
         mock.patch('app.opensense.redis_client.get', return_value="cached_result"), \
         mock.patch('app.opensense.requests.get') as mock_requests:
        result = opensense.get_temperature()
        assert result == "cached_result"
        mock_requests.assert_not_called()

def test_opensense_cache_setex():
    """Test that data is cached after fetching"""
    with mock.patch('app.opensense.REDIS_AVAILABLE', True), \
         mock.patch('app.opensense.redis_client.get', return_value=None), \
         mock.patch('app.opensense.redis_client.setex') as mock_setex, \
         mock.patch('app.opensense.requests.get', return_value=mock_response(25)):
        result = opensense.get_temperature()
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

        # Mock temperature data
        with mock.patch('app.opensense.get_temperature') as mock_temp:
            mock_temp.return_value = "Average temperature: 22.5 °C (Good)\nFrom: test\n"

            # Import and call the actual function
            result = store_temperature_data()

            # Test the result
            assert "successfully uploaded" in result
            mock_client.put_object.assert_called_once()
