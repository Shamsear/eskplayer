#!/usr/bin/env python3
"""
Test base64 upload with data URL prefix (as sent from frontend)
"""

import base64
from imagekit_config import upload_player_photo_base64

def test_data_url_upload():
    """Test uploading with data URL prefix (typical frontend format)"""
    
    # Create a simple 1x1 PNG image in base64
    png_bytes = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAHGjHSjQgAAAABJRU5ErkJggg==')
    png_base64 = base64.b64encode(png_bytes).decode('utf-8')
    
    # Create data URL (as would come from frontend JavaScript canvas.toDataURL())
    data_url = f"data:image/png;base64,{png_base64}"
    
    print("Testing data URL upload...")
    print(f"Data URL length: {len(data_url)}")
    print(f"Data URL prefix: {data_url[:50]}...")
    
    # Test upload with data URL
    result = upload_player_photo_base64(data_url, "Frontend Test Player", 1000)
    
    if result['success']:
        print("✅ Data URL upload successful!")
        print(f"URL: {result['url']}")
        print(f"File ID: {result['file_id']}")
        print(f"Thumbnail URL: {result['thumbnail_url']}")
        return True
    else:
        print("❌ Data URL upload failed!")
        print(f"Error: {result['error']}")
        return False

if __name__ == "__main__":
    test_data_url_upload()