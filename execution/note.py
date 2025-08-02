"""
Note processing module for Google Keep importer.
Handles the transformation of raw JSON note data into a canonical representation.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
import hashlib
from keep.processing_actions import ProcessingAction


def calculate_note_id(title: str, created_date: str) -> str:
    """Calculate a unique ID based on title and created date."""
    # Create a unique string from title and formatted date
    unique_string = f"{title}_{created_date}"
    
    # Generate MD5 hash and take first 8 characters
    hash_object = hashlib.md5(unique_string.encode())
    result = hash_object.hexdigest()[:8]
    
    return result


class ProcessedNote:
    """Canonical representation of a processed note."""
    
    def __init__(self, 
                 title: str,
                 content: str,
                 labels: str,
                 created_date: str,
                 modified_date: str,
                 attachments: List[Dict[str, Any]] = None,
                 note_id: str = ''):
        self.title = title
        self.content = content
        self.labels = labels
        self.created_date = created_date
        self.modified_date = modified_date
        self.attachments = attachments or []
        self.note_id = note_id

    @property
    def has_attachments(self) -> bool:
        """Check if the note has any attachments."""
        return len(self.attachments) > 0
    
    @property
    def attachment_count(self) -> int:
        """Get the number of attachments."""
        return len(self.attachments)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for sheet writing."""
        return {
            'ID': self.note_id,
            'Title': self.title,
            'Content': self.content,
            'Created Date': self.created_date,
            'Modified Date': self.modified_date,
            'Labels': self.labels,
            'Has Attachments': 'Yes' if self.has_attachments else 'No',
            'Attachment Count': self.attachment_count
        }
    
    def __repr__(self):
        return (f"ProcessedNote(id='{self.note_id}', title='{self.title}', "
                f"content='{self.content[:50]}...', labels='{self.labels}')")





