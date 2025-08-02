import os
import glob
import json


class LocalSourceFileManager:
    """Source files from local directory."""
    
    def __init__(self, directory_path):
        self.directory_path = directory_path
        if not os.path.isdir(directory_path):
            raise ValueError(f"Invalid directory path: {directory_path}")
        self._session_images = set()
    
    def list_files(self):
        """List all JSON files in directory."""
        json_pattern = os.path.join(self.directory_path, "*.json")
        files = glob.glob(json_pattern)
        return [os.path.basename(f) for f in files]
    
    def get_json_content(self, filename):
        """Read JSON file from local directory and return parsed JSON."""
        file_path = os.path.join(self.directory_path, filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
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
        """Read image file from local directory."""
        # Search for the file in the directory
        for root, dirs, files in os.walk(self.directory_path):
            if filename in files:
                file_path = os.path.join(root, filename)
                with open(file_path, 'rb') as f:
                    return f.read()
        return None  # Return None instead of raising exception
    
    def get_session_images(self):
        """Get set of image filenames from this session."""
        return self._session_images
    
 