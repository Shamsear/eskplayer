#!/usr/bin/env python3
"""
Test ImageKit raw upload without any processing/transformation
"""

import base64
import os
from dotenv import load_dotenv
from imagekitio import ImageKit

load_dotenv()

# ImageKit Configuration
IMAGEKIT_PUBLIC_KEY = "public_y7A0ZvJbvGQMifNQuDAAH4t+NaQ="
IMAGEKIT_PRIVATE_KEY = os.getenv('IMAGEKIT_PRIVATE_KEY', '')
IMAGEKIT_URL_ENDPOINT = os.getenv('IMAGEKIT_URL_ENDPOINT', '')

# Initialize ImageKit
imagekit = ImageKit(
    public_key=IMAGEKIT_PUBLIC_KEY,
    private_key=IMAGEKIT_PRIVATE_KEY,
    url_endpoint=IMAGEKIT_URL_ENDPOINT
)

def test_raw_upload():
    image_path = "C:\\Drive d\\html\\task17\\Benfica.png"
    
    if not os.path.exists(image_path):
        print(f"❌ Image file not found: {image_path}")
        return
    
    try:
        # Read the image file
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()
            print(f"✅ Read image file: {len(image_data)} bytes")
        
        # Test 1: Upload raw bytes directly
        print("\n🧪 Test 1: Upload raw bytes directly (no options)")
        try:
            upload_response = imagekit.upload_file(
                file=image_data,
                file_name="benfica_raw_test.png"
            )
            print(f"✅ Raw upload successful: {upload_response.url}")
        except Exception as e:
            print(f"❌ Raw upload failed: {e}")
        
        # Test 2: Upload with PNG format specified
        print("\n🧪 Test 2: Upload with PNG format specified")
        try:
            upload_response = imagekit.upload_file(
                file=image_data,
                file_name="benfica_png_test.png",
                options={
                    "use_unique_file_name": True,
                    "response_fields": ["url", "file_id", "file_type"]
                }
            )
            print(f"✅ PNG upload successful: {upload_response.url}")
            print(f"   File type: {getattr(upload_response, 'file_type', 'unknown')}")
        except Exception as e:
            print(f"❌ PNG upload failed: {e}")
            
        # Test 3: Upload as base64 with PNG MIME type
        print("\n🧪 Test 3: Upload as base64 with PNG MIME type")
        try:
            base64_data = base64.b64encode(image_data).decode('utf-8')
            data_url = f"data:image/png;base64,{base64_data}"
            
            upload_response = imagekit.upload_file(
                file=data_url,
                file_name="benfica_b64_test.png"
            )
            print(f"✅ Base64 PNG upload successful: {upload_response.url}")
        except Exception as e:
            print(f"❌ Base64 PNG upload failed: {e}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_raw_upload()