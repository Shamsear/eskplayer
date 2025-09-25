#!/usr/bin/env python3
"""
Test exact app upload scenario
"""

import os
import base64
from dotenv import load_dotenv
from imagekitio import ImageKit

# Load environment variables
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

def test_exact_app_scenario():
    """Test the exact scenario from the app"""
    # Same test data as test script
    simple_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    
    # Simulate what happens in the app
    base64_data = simple_png_b64  # This comes from frontend
    
    # Remove data URL prefix if present (this is what app does)
    if base64_data.startswith('data:image/'):
        base64_data = base64_data.split(',')[1]
    
    # Decode base64 image (this is what app does)
    try:
        image_data = base64.b64decode(base64_data)
    except Exception as e:
        print(f"Base64 decode failed: {e}")
        return
    
    print(f"Image data size: {len(image_data)} bytes")
    
    # Test the exact parameters from the app
    player_id = 999
    player_name = "Test Player"
    unique_filename = f"player_{player_id}_{player_name.replace(' ', '_').lower()}_cropped.jpg"
    
    # Try the exact upload call from the app
    try:
        print("Testing with exact app parameters...")
        upload_response = imagekit.upload_file(
            file=image_data,
            file_name=unique_filename,
            options={
                "folder": "/players/",
                "tags": [f"player_{player_id}", "tournament_player"],
                "custom_metadata": {
                    "player_id": str(player_id),
                    "player_name": player_name
                }
            }
        )
        
        print(f"✅ SUCCESS with app parameters: {upload_response.url}")
        
    except Exception as e:
        print(f"❌ FAILED with app parameters: {e}")
        print(f"Error type: {type(e)}")
        
        # Try without options
        print("\nTrying without options...")
        try:
            upload_response = imagekit.upload_file(
                file=image_data,
                file_name=unique_filename
            )
            print(f"✅ SUCCESS without options: {upload_response.url}")
            
        except Exception as e2:
            print(f"❌ FAILED without options: {e2}")
            
            # Try with minimal options
            print("\nTrying with minimal options...")
            try:
                upload_response = imagekit.upload_file(
                    file=image_data,
                    file_name=unique_filename,
                    options={"folder": "/players/"}
                )
                print(f"✅ SUCCESS with minimal options: {upload_response.url}")
                
            except Exception as e3:
                print(f"❌ FAILED with minimal options: {e3}")

if __name__ == "__main__":
    test_exact_app_scenario()