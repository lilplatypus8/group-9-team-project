import time
import requests
import base64
import os
from pathlib import Path

# The full URL of your live application's API endpoint.
# For local testing, this would be "http://localhost:3000/api/upload"
API_URL = "https://6000-firebase-studio-1768466146622.cluster-lpra5aacdzglovxc2rqngqgonm.cloudworkstations.dev/api/upload" 

# Your secret API key. This must match the key in your .env file.
API_KEY = "0bf4e9af08aafea1e866de863e27e20eb25dfd6bbcd243125403547be3a35f59"  

IMAGES_DIR = Path(r"C:\Users\L&L\Desktop\transmission_images\decrypted_images")

def upload_image(api_url, api_key, image_path, filename):
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
        response = requests.post(api_url, headers=headers, json=payload)
        
        # 4. Check the response from the server
        if response.status_code == 200:
            print("Upload successful!")
            print("Response:", response.json())
        else:
            print(f"Upload failed with status code: {response.status_code}")
            print("Response:", response.text)
            
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while making the request: {e}")

def upload_all(IMAGES_DIR):
    
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
        upload_image(API_URL, API_KEY, filepath, file.name)
        
        print(f"Uploaded {file} successfully.")
        
if __name__ == "__main__":
    
    if API_KEY == "0bf4e9af08aafea1e866de863e27e20eb25dfd6bbcd243125403547be3a35f59" or API_URL == "https://6000-firebase-studio-1768466146622.cluster-lpra5aacdzglovxc2rqngqgonm.cloudworkstations.dev/api/upload":
        print("Please update the placeholder values for API_URL and API_KEY in the script before running.")
    else:    
        upload_all(IMAGES_DIR)
    
    print("All uploads complete.")