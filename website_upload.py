import time
import requests
import base64
import os
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# The full URL of your live application's API endpoint.
# For local testing, this would be "http://localhost:3000/api/upload"
API_URL = "https://studio--studio-9059517623-ca846.us-central1.hosted.app/api/upload" 

# Your secret API key. This must match the key in your .env file.
API_KEY = "0bf4e9af08aafea1e866de863e27e20eb25dfd6bbcd243125403547be3a35f59" 

IMAGES_DIR = Path(r"C:\Users\L&L\Desktop\transmission_images\decrypted_images")

def get_session_with_retries():
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        raise_on_status=False
    )

    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session

def upload_image(session, api_url, api_key, image_path, filename):
    """
    Reads an image file, encodes it to Base64, and sends it to the API.
    
    To run this script, you first need to install the 'requests' library:
    pip install requests
    """
    
    # 1. Read the image file in binary mode and encode it to Base64
    try:
        with open(image_path, "rb") as image_file:
            # The Base64 data must be decoded to a utf-8 string for the JSON payload
            base64_encoded_data = base64.b64encode(image_file.read()).decode('utf-8')
    except FileNotFoundError:
        print(f"Error: The file '{image_path}' was not found.")
        return 

    # 2. Prepare the request headers and the JSON payload
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
    }
    
    payload = {
        "filename": filename,
        "base64Data": base64_encoded_data,
    }

    # 3. Make the POST request to the API
    print(f"Uploading {filename} to {api_url}...")
    try:
        response = session.post(api_url, headers=headers, json=payload, timeout=30)
        
        # 4. Check the response from the server
        if response.status_code == 200:
            print("Upload successful!")
            return True
            #print("Response:", response.json())
        else:
            print(f"Upload failed with status code: {response.status_code}")
            print("Response:", response.text)
            return False

            
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while making the request: {e}")

def upload_all(IMAGES_DIR):

    # Create one session to use for uploading all the images
    session = get_session_with_retries()

    try:
        # We call the base URL (not the /upload API) just to resolve DNS and trigger the server's 'Cold Start' to ensure that the connection is healthy
        base_url = "https://studio--studio-9059517623-ca846.us-central1.hosted.app"
        session.get(base_url, timeout=5) 
    except Exception:
        # Don't care if there is exceptions since this is a check
        pass
    
    time.sleep(2) # Give the DNS/Server 2 seconds 
    
    # Iterate over all images in the directory
    for file in IMAGES_DIR.iterdir():
        # Create full file path for each image
        filepath = file
        
        # Skip directories (shouldn't happen)
        if not Path.is_file(filepath):
            print(f"Skipping directory: {filepath}")
            continue
            
        # Skip non-jpg files (also shouldn't happen)
        if not file.suffix.lower().endswith(".jpg"):
            print(f"Skipping non-jpg file: {filepath}")
            continue
            
        print(f"Uploading {filepath} to Firebase Storage...")
        
        # Upload the image to Firebase Storage
        if upload_image(session, API_URL, API_KEY, filepath, file.name):
            print(f"Uploaded {file} successfully.")

        time.sleep(0.5)
        
if __name__ == "__main__":
    
    if API_KEY == "YOUR_SECRET_API_KEY" or API_URL == "https://your-app-url.com/api/upload":
        print("Please update the placeholder values for API_URL and API_KEY in the script before running.")
    else:    
        upload_all(IMAGES_DIR)
