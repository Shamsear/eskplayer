#!/usr/bin/env python3
"""
Test to verify image data integrity - save what we're sending to ImageKit
"""

import base64
import os

def test_image_integrity():
    original_path = "C:\\Drive d\\html\\task17\\Benfica.png"
    processed_path = "C:\\Drive d\\html\\task17\\processed_benfica.png"
    
    if not os.path.exists(original_path):
        print(f"❌ Original image not found: {original_path}")
        return
    
    try:
        # Read the original image
        with open(original_path, 'rb') as f:
            original_data = f.read()
            print(f"✅ Original image: {len(original_data)} bytes")
        
        # Simulate what our upload function does
        print("🔄 Simulating upload process...")
        
        # Step 1: Convert to base64 (what JS would do)
        base64_data = base64.b64encode(original_data).decode('utf-8')
        print(f"   Base64 length: {len(base64_data)} characters")
        
        # Step 2: Create data URL (what JS sends)
        data_url = f"data:image/png;base64,{base64_data}"
        print(f"   Data URL length: {len(data_url)} characters")
        
        # Step 3: Remove data URL prefix (what our server does)
        if data_url.startswith('data:image/'):
            processed_base64 = data_url.split(',')[1]
        else:
            processed_base64 = data_url
        print(f"   Processed base64 length: {len(processed_base64)} characters")
        
        # Step 4: Decode back to bytes (what our server does)
        processed_data = base64.b64decode(processed_base64)
        print(f"   Processed image: {len(processed_data)} bytes")
        
        # Step 5: Save the processed data to compare
        with open(processed_path, 'wb') as f:
            f.write(processed_data)
        print(f"✅ Saved processed image: {processed_path}")
        
        # Compare the data
        if original_data == processed_data:
            print("✅ SUCCESS: Image data is identical after processing!")
        else:
            print("❌ ERROR: Image data changed during processing!")
            print(f"   Original size: {len(original_data)} bytes")
            print(f"   Processed size: {len(processed_data)} bytes")
            print(f"   First 20 bytes original: {original_data[:20]}")
            print(f"   First 20 bytes processed: {processed_data[:20]}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_image_integrity()