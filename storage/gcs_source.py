from google.auth import default
from google.cloud import storage
import json
import os


class GCSSourceFileManager:
    """Source files from Google Cloud Storage."""
    
    def __init__(self, bucket):
        self.bucket = bucket
        self.bucket_name = bucket.name
        self.blob_map = None
        self._session_images = set()
    
    def _get_blob_map(self):
        """Get or create blob mapping."""
        if self.blob_map is None:
            blobs = self.bucket.list_blobs()
            self.blob_map = {blob.name: blob for blob in blobs}
        return self.blob_map
    
    def list_files(self):
        """List all JSON files in bucket."""
        blob_map = self._get_blob_map()
        return [name for name in blob_map.keys() if name.endswith('.json')]
    
    def get_json_content(self, filename):
        """Download JSON file from GCS and return parsed JSON."""
        blob_map = self._get_blob_map()
        if filename not in blob_map:
            raise FileNotFoundError(f"File {filename} not found in bucket {self.bucket_name}")
        
        content = blob_map[filename].download_as_text()
        data = json.loads(content)
        
        # Track image filenames from this note
        attachments = data.get('attachments', [])
        for attachment in attachments:
            if attachment.get('mimetype', '').startswith('image/'):
                filename = os.path.basename(attachment.get('filePath', ''))
                if filename:
                    self._session_images.add(filename)
        
        return data
    
    def get_image_bytes(self, filename):
        """Download image file from GCS."""
        blob_map = self._get_blob_map()
        # Search for the file by basename
        for blob_name, blob in blob_map.items():
            if os.path.basename(blob_name) == filename:
                return blob.download_as_bytes()
        return None  # Return None instead of raising exception
    
    def get_session_images(self):
        """Get set of image filenames from this session."""
        return self._session_images 