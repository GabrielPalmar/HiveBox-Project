'''Module to get entries from OpenSenseMap API and get the average temperature'''
from datetime import datetime, timezone, timedelta
import requests


def get_temperature():
    '''Function to get the average temperature from OpenSenseMap API.'''
    # Ensuring that data is not older than 1 hour.
    subs_time = datetime.now(timezone.utc) - timedelta(hours=1)
    time_iso = subs_time.isoformat().replace("+00:00", "Z")

    api_endpoint = "https://api.opensensemap.org/boxes"

    params = {
        "date": time_iso,
        "format": "json"
    }

    print('Getting data from OpenSenseMap API...')
    response = requests.get(api_endpoint, params=params, timeout=240)
    print('Data retrieved successfully!')

    res = [d.get('sensors') for d in response.json() if 'sensors' in d]

    temp_list = []

    for sensor_list in res:
        for measure in sensor_list:
            if measure.get('title') == "Temperatur" and 'lastMeasurement' in measure:
                last_measurement = measure['lastMeasurement']
                if last_measurement is not None and 'value' in last_measurement:
                    last_measurement_int = float(last_measurement['value'])
                    temp_list.append(last_measurement_int)
                    
    total_sum = sum(temp_list)
    average = total_sum / len(temp_list) if temp_list else 0

    return f'Average temperature: {average:.2f} °C\n'
