'''Module containing the main function of the app.'''
from flask import Flask, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from app import opensense
#import test_main

app = Flask(__name__)

@app.route('/version')
def print_version():
    '''Function printing the current version of the app.'''

    with open('../version.txt', 'r', encoding="utf-8") as f:
        version = f.read()

    return f"Current app version: {version}\n"

@app.route('/temperature')
def get_temperature():
    '''Function to get the current temperature.'''
    return opensense.get_temperature()

@app.route('/metrics')
def metrics():
    '''Function to return Prometheus metrics.'''
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

### Test module ###
# @app.route('/test')
# def test():
#     '''Function to test the app.'''
#     success = test_main.run_all_tests()
#     if success:
#         return "All tests passed!\n", 200
#     else:
#         return "Some tests failed. Check the logs for details.\n", 500

if __name__ == "__main__":
    app.run()
