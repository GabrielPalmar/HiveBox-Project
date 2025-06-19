'''This module contains tests for the Flask and OpenSense modules.'''
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
    assert "Average temperature:" in result
