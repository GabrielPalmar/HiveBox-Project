'''This module contains the test cases for the opensense module.'''
import sys
import re
import requests

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

def test_get_version():
    '''Function to test the get_version function from the opensense module.'''
    url = "http://127.0.0.1:5000/version"
    pattern = r"Current app version: (\d+\.\d+\.\d+)"
    version_success, match = make_request(url, pattern)

    if version_success and match:
        version = match.group(1)
        print(f"✅ Version test passed: {version}\n")

    return version_success

def test_get_temperature():
    '''Function to test the get_temperature function from the opensense module.'''
    url = "http://127.0.0.1:5000/temperature"
    pattern = r"Average temperature: (\d+\.\d+) °C"
    temperature_success, match = make_request(url, pattern)

    if temperature_success and match:
        temperature = float(match.group(1))
        print(f"✅ Temperature test passed: {temperature:.2f}°C\n")

    return temperature_success

def run_all_tests():
    '''Run all tests and return overall success status.'''
    version_success = test_get_version()
    temperature_success = test_get_temperature()

    return version_success and temperature_success

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
    