'''This module contains the test cases for the opensense module.'''
import sys
import re
import os
import requests
import vcr

API_HOST = os.environ.get('API_HOST', 'http://127.0.0.1:5000')

my_vcr = vcr.VCR(
    cassette_library_dir='tests/fixtures/vcr_cassettes',
    record_mode='once',
    match_on=['uri', 'method'],
)

def make_request(url, expected_pattern):
    '''Reusable function to make requests and assert responses.'''
    try:
        response = requests.get(url, timeout=240)
        print(f"Response: {response.text}")

        # Check status code
        assert response.status_code == 200, "The request was not successful."

        # Check response content
        match = re.search(expected_pattern, response.text)
        assert match is not None, f"Pattern '{expected_pattern}' not found in response"

        return True, match

    except requests.exceptions.RequestException as e:
        print(f"❌ TEST FAILED: Network error: {str(e)}")
        return False, None
    except (AssertionError, TypeError, ValueError) as e:
        print(f"❌ TEST FAILED: {str(e)}")
        return False, None

@my_vcr.use_cassette('version.yaml')
def test_get_version():
    '''Function to test the get_version function.'''
    url = f"{API_HOST}/version"
    pattern = r"Current app version: (\d+\.\d+\.\d+)"
    version_success, match = make_request(url, pattern)

    if version_success and match:
        version = match.group(1)
        print(f"✅ Version test passed: {version}\n")

    return version_success

@my_vcr.use_cassette('temperature.yaml')
def test_get_temperature():
    '''Function to test the get_temperature function from the opensense module.'''
    url = f"{API_HOST}/temperature"
    pattern = r"Average temperature: (\d+\.\d+) °C"
    temperature_success, match = make_request(url, pattern)

    if temperature_success and match:
        temperature = float(match.group(1))
        print(f"✅ Temperature test passed: {temperature:.2f}°C\n")

    return temperature_success

@my_vcr.use_cassette('metrics.yaml')
def test_get_metrics():
    '''Function to test the metrics function.'''
    url = f"{API_HOST}/metrics"
    pattern = r"python_info"
    metrics_success, match = make_request(url, pattern)

    if metrics_success and match:
        print("✅ Metrics test passed: Prometheus metrics found\n")

    return metrics_success

def run_all_tests():
    '''Run all tests and return overall success status.'''
    version_success = test_get_version()
    temperature_success = test_get_temperature()
    metrics_success = test_get_metrics()

    return version_success and temperature_success and metrics_success

if __name__ == "__main__":
    SUCCESS = run_all_tests()
    sys.exit(0 if SUCCESS else 1)
