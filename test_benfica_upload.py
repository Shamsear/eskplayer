#!/usr/bin/env python3
"""
Test uploading the Benfica image file to verify the process works with real images
"""

import base64
import os
from imagekit_config import upload_player_photo_base64

def test_benfica_image():
    image_path = "C:\\Drive d\\html\\task17\\Benfica.png"
    
    if not os.path.exists(image_path):
        print(f"❌ Image file not found: {image_path}")
        return
    
    try:
        # Read the image file
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()
            print(f"✅ Read image file: {len(image_data)} bytes")
        
        # Convert to base64
        base64_data = base64.b64encode(image_data).decode('utf-8')
        print(f"✅ Converted to base64: {len(base64_data)} characters")
        
        # Create data URL format (what the frontend would send)
        data_url = f"data:image/png;base64,{base64_data}"
        print(f"✅ Created data URL: {len(data_url)} characters")
        
        # Test the upload
        print("\n🧪 Testing upload...")
        result = upload_player_photo_base64(data_url, "Benfica Test", 997)
        
        print(f"\n📊 Upload Result:")
        print(f"Success: {result.get('success', False)}")
        if result.get('success'):
            print(f"URL: {result.get('url')}")
            print(f"File ID: {result.get('file_id')}")
            print(f"Thumbnail: {result.get('thumbnail_url')}")
        else:
            print(f"Error: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_benfica_image()