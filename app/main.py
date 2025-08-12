'''Module containing the main function of the app.'''
import os
import socket
from flask import Flask, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from app import opensense
from app import storage
from app import readiness

app = Flask(__name__)

HOSTNAME = socket.gethostname()
IPADDR = socket.gethostbyname(HOSTNAME)

@app.route('/version')
def print_version():
    '''Function printing the current version of the app.'''
    version_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'version.txt')

    with open(version_file, 'r', encoding="utf-8") as f:
        version = f.read()

    return f"Current app version: {version}\n"

@app.route('/temperature')
def get_temperature():
    '''Function to get the current temperature.'''
    return opensense.get_temperature() + f"From: {IPADDR}\n"

@app.route('/metrics')
def metrics():
    '''Function to return Prometheus metrics.'''
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

@app.route('/store')
def store():
    '''Function to store results in MinIO.'''
    return storage.store_temperature_data()

@app.route('/readyz')
def readyz():
    '''Readiness probe endpoint'''
    status_code = readiness.readiness_check()

    if status_code == 200:
        return {"status": "ready"}, 200

    return {
        "status": "not ready", 
        "error": "More than 50% of sensors unreachable and cache expired"
    }, 503

if __name__ == "__main__":
    app.run()
