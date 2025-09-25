#!/usr/bin/env python3
"""
Test uploading a known good image to verify the process works
"""

from imagekit_config import upload_player_photo_base64

# This is a valid 1x1 red pixel PNG in base64
RED_PIXEL_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="

# Test as data URL (what frontend sends)
DATA_URL = f"data:image/png;base64,{RED_PIXEL_PNG_B64}"

def test_known_good_image():
    print("Testing with known good image data...")
    
    # Test 1: Upload with data URL format
    print("Test 1: Data URL format")
    result1 = upload_player_photo_base64(DATA_URL, "Test Player", 999)
    print(f"Result: {result1}")
    
    # Test 2: Upload with just base64 string
    print("\nTest 2: Plain base64 format")
    result2 = upload_player_photo_base64(RED_PIXEL_PNG_B64, "Test Player 2", 998)
    print(f"Result: {result2}")

if __name__ == "__main__":
    test_known_good_image()