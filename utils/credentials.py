# utils/credentials.py
import boto3
import json
import os
import tempfile


def get_google_credentials(secret_name='football-scraper/google-credentials'):
    """Retrieve Google credentials from AWS Secrets Manager."""
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)

    # Get the credentials JSON
    credentials_json = json.loads(response['SecretString'])

    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, mode='w') as f:
        json.dump(credentials_json, f)
        temp_path = f.name

    # Set environment variable to point to this file
    os.environ['GOOGLE_CREDS_PATH'] = temp_path

    return temp_path