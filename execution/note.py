"""
Note processing module for Google Keep importer.
Handles the transformation of raw JSON note data into a canonical representation.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from keep.processing_actions import ProcessingAction


class ProcessedNote:
    """
    Canonical representation of a note imported.
    This is the final structure that will be written to the target.
    """
    
    def __init__(self, 
                 title: str,
                 content: str,
                 labels: str,
                 created_date: str,
                 modified_date: str,
                 has_attachments: bool = False,
                 attachment_count: int = 0,
                 attachments: List[Dict[str, Any]] = None):
        self.title = title
        self.content = content
        self.labels = labels
        self.created_date = created_date
        self.modified_date = modified_date
        self.has_attachments = has_attachments
        self.attachment_count = attachment_count
        self.attachments = attachments or []
    
    @property
    def note_id(self) -> str:
        """Calculate a unique ID based on title and created date."""
        import hashlib
        
        # Create a unique string from title and formatted date
        unique_string = f"{self.title}_{self.created_date}"
        
        # Generate MD5 hash and take first 8 characters
        hash_object = hashlib.md5(unique_string.encode())
        result = hash_object.hexdigest()[:8]
        
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for sheet writing."""
        return {
            'ID': self.note_id,
            'Title': self.title,
            'Content': self.content,
            'Labels': self.labels,
            'Created Date': self.created_date,
            'Modified Date': self.modified_date,
            'Has Attachments': 'Yes' if self.has_attachments else 'No',
            'Attachment Count': self.attachment_count
        }
    
    def __eq__(self, other):
        if not isinstance(other, ProcessedNote):
            return False
        return (self.note_id == other.note_id and
                self.title == other.title and
                self.content == other.content and
                self.labels == other.labels and
                self.created_date == other.created_date and
                self.modified_date == other.modified_date and
                self.has_attachments == other.has_attachments and
                self.attachment_count == other.attachment_count)
    
    def __repr__(self):
        return (f"ProcessedNote(id='{self.note_id}', title='{self.title}', "
                f"labels='{self.labels}', attachments={self.attachment_count})")





