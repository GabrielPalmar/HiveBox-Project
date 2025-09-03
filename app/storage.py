'''This script uploads the output to a MinIO bucket.'''
import os
import io
import datetime
from minio import Minio
from minio.error import S3Error, InvalidResponseError
from app import opensense

MINIO_HOST = os.getenv('MINIO_HOST', 'localhost')
MINIO_PORT = int(os.environ.get('MINIO_PORT', 9000))
MINIO_ACCESS_KEY = os.environ.get('MINIO_ACCESS_KEY', 'minioadmin')
MINIO_SECRET_KEY = os.environ.get('MINIO_SECRET_KEY', 'minioadmin')

def store_temperature_data():
    '''Function to upload temperature data to MinIO.'''
    try:
        client = Minio(f"{MINIO_HOST}:{MINIO_PORT}",
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False
        )

        # Check if the MinIO server is reachable
        try:
            client.list_buckets()
        except ConnectionError as conn_exc:
            error_msg = f"Cannot connect to MinIO server: {conn_exc}"
            print(error_msg)
            return error_msg

        bucket_name = "temperature-data"
        destination_file = f"temperature_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S%f')}.txt"

        # Get the temperature data - unpack the tuple
        temperature_result, _ = opensense.get_temperature()

        text_bytes = temperature_result.encode('utf-8')
        text_stream = io.BytesIO(text_bytes)

        # Make the bucket if it doesn't exist.
        found = client.bucket_exists(bucket_name)
        if not found:
            client.make_bucket(bucket_name)
            print("Created bucket", bucket_name)
        else:
            print("Bucket", bucket_name, "already exists")

        # Upload the data
        client.put_object(
            bucket_name,
            destination_file,
            text_stream,
            length=len(text_bytes),
            content_type='text/plain'
        )

        return (f"Temperature data successfully uploaded as "
                f"{destination_file} to bucket {bucket_name}\n")

    except (S3Error, InvalidResponseError) as exc:
        error_msg = f"MinIO S3 error occurred: {exc}"
        print(error_msg)
        return error_msg

if __name__ == "__main__":
    RESULT = store_temperature_data()
    print(RESULT)
