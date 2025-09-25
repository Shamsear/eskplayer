#!/usr/bin/env python3
"""
ImageKit Upload Test Script

This script tests different methods of uploading to ImageKit to find the working approach.
"""

import os
import base64
import io
import tempfile
from dotenv import load_dotenv
from imagekitio import ImageKit

# Load environment variables
load_dotenv()

# ImageKit Configuration
IMAGEKIT_PUBLIC_KEY = "public_y7A0ZvJbvGQMifNQuDAAH4t+NaQ="
IMAGEKIT_PRIVATE_KEY = os.getenv('IMAGEKIT_PRIVATE_KEY', '')
IMAGEKIT_URL_ENDPOINT = os.getenv('IMAGEKIT_URL_ENDPOINT', '')

# Initialize ImageKit
imagekit = None
try:
    if IMAGEKIT_PRIVATE_KEY and IMAGEKIT_URL_ENDPOINT:
        imagekit = ImageKit(
            public_key=IMAGEKIT_PUBLIC_KEY,
            private_key=IMAGEKIT_PRIVATE_KEY,
            url_endpoint=IMAGEKIT_URL_ENDPOINT
        )
        print("✅ ImageKit initialized successfully")
    else:
        print("❌ ImageKit credentials missing")
        exit(1)
except Exception as e:
    print(f"❌ Failed to initialize ImageKit: {e}")
    exit(1)

# Create test image data (simple PNG)
def create_test_image_data():
    """Create a simple test image as bytes"""
    # Simple 1x1 PNG in base64
    simple_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    return base64.b64decode(simple_png_b64)

def test_method_1_raw_bytes():
    """Test Method 1: Upload raw bytes directly"""
    print("\n🧪 Testing Method 1: Raw bytes")
    try:
        image_data = create_test_image_data()
        
        upload_response = imagekit.upload_file(
            file=image_data,
            file_name="test_method1.png"
        )
        
        print(f"✅ Method 1 SUCCESS: {upload_response.url}")
        return True, upload_response
    except Exception as e:
        print(f"❌ Method 1 FAILED: {e}")
        return False, None

def test_method_2_base64_string():
    """Test Method 2: Upload base64 string"""
    print("\n🧪 Testing Method 2: Base64 string")
    try:
        image_data = create_test_image_data()
        b64_string = base64.b64encode(image_data).decode('utf-8')
        
        upload_response = imagekit.upload_file(
            file=b64_string,
            file_name="test_method2.png"
        )
        
        print(f"✅ Method 2 SUCCESS: {upload_response.url}")
        return True, upload_response
    except Exception as e:
        print(f"❌ Method 2 FAILED: {e}")
        return False, None

def test_method_3_data_url():
    """Test Method 3: Upload data URL"""
    print("\n🧪 Testing Method 3: Data URL")
    try:
        image_data = create_test_image_data()
        b64_string = base64.b64encode(image_data).decode('utf-8')
        data_url = f"data:image/png;base64,{b64_string}"
        
        upload_response = imagekit.upload_file(
            file=data_url,
            file_name="test_method3.png"
        )
        
        print(f"✅ Method 3 SUCCESS: {upload_response.url}")
        return True, upload_response
    except Exception as e:
        print(f"❌ Method 3 FAILED: {e}")
        return False, None

def test_method_4_bytesio():
    """Test Method 4: Upload BytesIO object"""
    print("\n🧪 Testing Method 4: BytesIO object")
    try:
        image_data = create_test_image_data()
        bytes_io = io.BytesIO(image_data)
        
        upload_response = imagekit.upload_file(
            file=bytes_io,
            file_name="test_method4.png"
        )
        
        print(f"✅ Method 4 SUCCESS: {upload_response.url}")
        return True, upload_response
    except Exception as e:
        print(f"❌ Method 4 FAILED: {e}")
        return False, None

def test_method_5_temp_file():
    """Test Method 5: Upload temporary file"""
    print("\n🧪 Testing Method 5: Temporary file")
    try:
        image_data = create_test_image_data()
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            temp_file.write(image_data)
            temp_file_path = temp_file.name
        
        try:
            # Open file for upload
            with open(temp_file_path, 'rb') as file_obj:
                upload_response = imagekit.upload_file(
                    file=file_obj,
                    file_name="test_method5.png"
                )
            
            print(f"✅ Method 5 SUCCESS: {upload_response.url}")
            return True, upload_response
        finally:
            # Clean up temp file
            os.unlink(temp_file_path)
            
    except Exception as e:
        print(f"❌ Method 5 FAILED: {e}")
        return False, None

def test_method_6_file_like_object():
    """Test Method 6: Custom file-like object"""
    print("\n🧪 Testing Method 6: Custom file-like object")
    try:
        image_data = create_test_image_data()
        
        class FileWrapper:
            def __init__(self, data):
                self.data = data
                self.pos = 0
            
            def read(self, size=-1):
                if size == -1:
                    result = self.data[self.pos:]
                    self.pos = len(self.data)
                else:
                    result = self.data[self.pos:self.pos + size]
                    self.pos += len(result)
                return result
            
            def seek(self, pos, whence=0):
                if whence == 0:
                    self.pos = pos
                elif whence == 1:
                    self.pos += pos
                elif whence == 2:
                    self.pos = len(self.data) + pos
                return self.pos
            
            def tell(self):
                return self.pos
        
        file_wrapper = FileWrapper(image_data)
        
        upload_response = imagekit.upload_file(
            file=file_wrapper,
            file_name="test_method6.png"
        )
        
        print(f"✅ Method 6 SUCCESS: {upload_response.url}")
        return True, upload_response
    except Exception as e:
        print(f"❌ Method 6 FAILED: {e}")
        return False, None

def main():
    print("=" * 60)
    print("IMAGEKIT UPLOAD METHOD TESTING")
    print("=" * 60)
    
    methods = [
        test_method_1_raw_bytes,
        test_method_2_base64_string, 
        test_method_3_data_url,
        test_method_4_bytesio,
        test_method_5_temp_file,
        test_method_6_file_like_object
    ]
    
    working_methods = []
    
    for method in methods:
        success, response = method()
        if success:
            working_methods.append(method.__name__)
    
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    
    if working_methods:
        print("✅ Working methods:")
        for method in working_methods:
            print(f"  • {method}")
        print(f"\n🎯 Best method to use: {working_methods[0]}")
    else:
        print("❌ No methods worked! Check ImageKit credentials and connection.")
    
    print("=" * 60)

if __name__ == "__main__":
    main()