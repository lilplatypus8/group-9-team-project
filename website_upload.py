import time
from pathlib import Path

IMAGES_DIR = Path(r"C:\Users\L&L\Desktop\transmission_images\decrypted_images")


# CODE FOR FIREBASE INITIALIZATION WILL GO HERE 

###############################################

def upload_images(IMAGES_DIR):
    
    # Iterate over all images in the directory
    for file in IMAGES_DIR.iterdir():
        # Create full file path for each image
        filepath = Path.joinpath(IMAGES_DIR, file)
        
        # Skip potential directories (shouldn't happen)
        if not Path.is_file(filepath):
            print(f"Skipping directory: {filepath}")
            continue
            
        # Skip non-jpg files (also shouldn't happen)
        if not file.lower().endswith(".jpg"):
            print(f"Skipping non-jpg file: {filepath}")
            continue
            
        print(f"Uploading {filepath} to Firebase Storage...")
        
        # Create Firebase Storage object from filepath
        blob = bucket.blob(f"uploads/{file}")

        # Upload the file to Firebase Storage
        blob.upload_from_filename(filepath)
        
        # Make image publicly accessible
        blob.make_public()
        
        print(f"Uploaded {file} successfully. Public URL: {blob.public_url}")
        
if __name__ == "__main__":
    
    upload_images(IMAGES_DIR)
    
    print("All uploads complete.")