import os
from imagekitio import ImageKit
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ImageKit Configuration
IMAGEKIT_PUBLIC_KEY = "public_y7A0ZvJbvGQMifNQuDAAH4t+NaQ="
IMAGEKIT_PRIVATE_KEY = os.getenv('IMAGEKIT_PRIVATE_KEY', '')  # Add this to your .env file
IMAGEKIT_URL_ENDPOINT = os.getenv('IMAGEKIT_URL_ENDPOINT', '')  # Add this to your .env file

# Initialize ImageKit
imagekit = ImageKit(
    public_key=IMAGEKIT_PUBLIC_KEY,
    private_key=IMAGEKIT_PRIVATE_KEY,
    url_endpoint=IMAGEKIT_URL_ENDPOINT
)

class PhotoManager:
    """Utility class for managing player photos with ImageKit"""
    
    @staticmethod
    def upload_photo(file, player_name, player_id):
        """
        Upload a player photo to ImageKit
        
        Args:
            file: File object (from Flask request.files)
            player_name: Name of the player for folder organization
            player_id: Player ID for unique identification
            
        Returns:
            dict: Contains 'success', 'url', 'file_id', and 'error' keys
        """
        try:
            if not file or file.filename == '':
                return {'success': False, 'error': 'No file selected'}
            
            # Validate file type
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
            if not PhotoManager._allowed_file(file.filename, allowed_extensions):
                return {'success': False, 'error': 'Invalid file type. Only PNG, JPG, JPEG, GIF, and WebP are allowed.'}
            
            # Validate file size (max 5MB)
            file.seek(0, 2)  # Seek to end
            file_size = file.tell()
            file.seek(0)  # Reset to beginning
            
            if file_size > 5 * 1024 * 1024:  # 5MB limit
                return {'success': False, 'error': 'File size too large. Maximum 5MB allowed.'}
            
            # Generate unique filename
            file_extension = file.filename.rsplit('.', 1)[1].lower()
            unique_filename = f"player_{player_id}_{player_name.replace(' ', '_').lower()}.{file_extension}"
            
            # Upload to ImageKit
            upload_response = imagekit.upload_file(
                file=file,
                file_name=unique_filename,
                options={
                    "folder": "/players/",
                    "tags": [f"player_{player_id}", "tournament_player"],
                    "custom_metadata": {
                        "player_id": str(player_id),
                        "player_name": player_name
                    },
                    "transformation": {
                        "pre": "w-400,h-400,c-face",  # Auto-crop to face, 400x400
                        "post": [
                            {
                                "type": "transformation",
                                "value": "q-80,f-webp"  # Optimize quality and format
                            }
                        ]
                    }
                }
            )
            
            if upload_response.response_metadata.http_status_code == 200:
                return {
                    'success': True,
                    'url': upload_response.url,
                    'file_id': upload_response.file_id,
                    'thumbnail_url': f"{upload_response.url}?tr=w-150,h-150,c-face,q-80,f-webp"
                }
            else:
                return {'success': False, 'error': 'Upload failed'}
                
        except Exception as e:
            return {'success': False, 'error': f'Upload error: {str(e)}'}
    
    @staticmethod
    def delete_photo(file_id):
        """
        Delete a photo from ImageKit
        
        Args:
            file_id: ImageKit file ID
            
        Returns:
            dict: Contains 'success' and 'error' keys
        """
        try:
            if not file_id:
                return {'success': True}  # No photo to delete
            
            delete_response = imagekit.delete_file(file_id)
            return {'success': True}
            
        except Exception as e:
            # Don't fail the operation if photo deletion fails
            print(f"Warning: Failed to delete photo {file_id}: {str(e)}")
            return {'success': True, 'warning': f'Photo deletion failed: {str(e)}'}
    
    @staticmethod
    def update_photo(old_file_id, file, player_name, player_id):
        """
        Update a player photo (delete old, upload new)
        
        Args:
            old_file_id: Current photo file ID to delete
            file: New file object
            player_name: Player name
            player_id: Player ID
            
        Returns:
            dict: Upload result
        """
        # Delete old photo first (don't fail if deletion fails)
        if old_file_id:
            PhotoManager.delete_photo(old_file_id)
        
        # Upload new photo
        return PhotoManager.upload_photo(file, player_name, player_id)
    
    @staticmethod
    def get_optimized_url(base_url, width=None, height=None, quality=80):
        """
        Generate optimized image URL with transformations
        
        Args:
            base_url: Base ImageKit URL
            width: Target width
            height: Target height
            quality: Image quality (1-100)
            
        Returns:
            str: Optimized URL
        """
        if not base_url:
            return None
        
        transformations = []
        
        if width and height:
            transformations.append(f"w-{width},h-{height},c-face")
        elif width:
            transformations.append(f"w-{width}")
        elif height:
            transformations.append(f"h-{height}")
        
        transformations.append(f"q-{quality},f-webp")
        
        transformation_string = ",".join(transformations)
        return f"{base_url}?tr={transformation_string}"
    
    @staticmethod
    def _allowed_file(filename, allowed_extensions):
        """Check if file extension is allowed"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in allowed_extensions

# Convenience functions
def upload_player_photo(file, player_name, player_id):
    """Convenience function for uploading player photos"""
    return PhotoManager.upload_photo(file, player_name, player_id)

def delete_player_photo(file_id):
    """Convenience function for deleting player photos"""
    return PhotoManager.delete_photo(file_id)

def get_player_photo_url(base_url, size='medium'):
    """Get optimized player photo URL for different sizes"""
    if not base_url:
        return None
    
    size_configs = {
        'thumbnail': {'width': 50, 'height': 50},
        'small': {'width': 100, 'height': 100},
        'medium': {'width': 200, 'height': 200},
        'large': {'width': 400, 'height': 400}
    }
    
    config = size_configs.get(size, size_configs['medium'])
    return PhotoManager.get_optimized_url(base_url, **config)