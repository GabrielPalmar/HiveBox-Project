'''This module contains tests for the Flask and OpenSense modules.'''
import re
import unittest.mock as mock
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

# Add a simple test for the opensense module
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
