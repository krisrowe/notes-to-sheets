"""
Note processing module for Google Keep importer.
Handles the transformation of raw JSON note data into a canonical representation.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from processing_actions import ProcessingAction


class ProcessedNote:
    """
    Canonical representation of a processed Google Keep note.
    This is the final structure that will be written to the output sheet.
    """
    
    def __init__(self, 
                 note_id: str,
                 title: str,
                 content: str,
                 labels: str,
                 created_date: str,
                 modified_date: str,
                 has_attachments: bool = False,
                 attachment_count: int = 0):
        self.note_id = note_id
        self.title = title
        self.content = content
        self.labels = labels
        self.created_date = created_date
        self.modified_date = modified_date
        self.has_attachments = has_attachments
        self.attachment_count = attachment_count
    
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


def generate_appsheet_id(title: str, created_timestamp: str) -> str:
    """Generate a unique AppSheet-style ID for the note."""
    import hashlib
    # Create a unique string from title and timestamp
    unique_string = f"{title}_{created_timestamp}"
    # Generate MD5 hash and take first 8 characters
    hash_object = hashlib.md5(unique_string.encode())
    return hash_object.hexdigest()[:8]


def format_checklist_items(list_content: List[Dict[str, Any]]) -> str:
    """Format checklist items into a readable string."""
    if not list_content:
        return ""
    
    formatted_items = []
    for item in list_content:
        text = item.get('text', '').strip()
        is_checked = item.get('isChecked', False)
        checkbox = "☑" if is_checked else "☐"
        formatted_items.append(f"{checkbox} {text}")
    
    return "\n".join(formatted_items)


def process_note(note_data: Dict[str, Any], config: Dict[str, Any]) -> tuple[Optional[ProcessedNote], Dict[str, int]]:
    """
    Process a raw Google Keep note into a canonical representation.
    
    Args:
        note_data: Raw JSON note data from Google Keep
        config: Configuration dictionary from config.yaml
        
    Returns:
        Tuple of (ProcessedNote object or None if note should be skipped, ignore_actions_dict)
        
    Raises:
        ValueError: If processing action is set to "error" for any attribute
    """
    # Extract basic fields
    title = note_data.get('title', '')
    list_content = note_data.get('listContent', [])
    attachments = note_data.get('attachments', [])
    
    # Process each attribute according to configuration
    label_names = [label['name'] for label in note_data.get('labels', [])]
    
    # Track ignore actions
    ignore_actions = {
        'html': 0,
        'color': 0,
        'trashed': 0,
        'archived': 0,
        'pinned': 0,
        'shared': 0
    }
    
    # Process trashed status
    if note_data.get('isTrashed', False):
        action = ProcessingAction(config['processing']['trashed'])
        if action == ProcessingAction.ERROR:
            raise ValueError(f"Note '{title}' is trashed (processing action: error)")
        elif action == ProcessingAction.SKIP:
            return None, ignore_actions
        elif action == ProcessingAction.LABEL:
            label_names.append(config['labels']['trashed'])
        elif action == ProcessingAction.IGNORE:
            ignore_actions['trashed'] = 1
        # IGNORE: do nothing
    
    # Process archived status
    if note_data.get('isArchived', False):
        action = ProcessingAction(config['processing']['archived'])
        if action == ProcessingAction.ERROR:
            raise ValueError(f"Note '{title}' is archived (processing action: error)")
        elif action == ProcessingAction.SKIP:
            return None, ignore_actions
        elif action == ProcessingAction.LABEL:
            label_names.append(config['labels']['archived'])
        elif action == ProcessingAction.IGNORE:
            ignore_actions['archived'] = 1
        # IGNORE: do nothing
    
    # Process pinned status
    if note_data.get('isPinned', False):
        action = ProcessingAction(config['processing']['pinned'])
        if action == ProcessingAction.ERROR:
            raise ValueError(f"Note '{title}' is pinned (processing action: error)")
        elif action == ProcessingAction.SKIP:
            return None, ignore_actions
        elif action == ProcessingAction.LABEL:
            label_names.append(config['labels']['pinned'])
        elif action == ProcessingAction.IGNORE:
            ignore_actions['pinned'] = 1
        # IGNORE: do nothing
    
    # Process color
    color = note_data.get('color', 'DEFAULT')
    if color and color != 'DEFAULT':
        action = ProcessingAction(config['processing']['color'])
        if action == ProcessingAction.ERROR:
            raise ValueError(f"Note '{title}' has non-DEFAULT color '{color}' (processing action: error)")
        elif action == ProcessingAction.SKIP:
            return None, ignore_actions
        elif action == ProcessingAction.LABEL:
            label_names.append(color)
        elif action == ProcessingAction.IGNORE:
            ignore_actions['color'] = 1
        # IGNORE: do nothing
    
    # Process HTML content
    has_html_content = bool(note_data.get('textContentHtml', '').strip())
    if has_html_content:
        action = ProcessingAction(config['processing']['html_content'])
        if action == ProcessingAction.ERROR:
            raise ValueError(f"Note '{title}' has HTML content (processing action: error)")
        elif action == ProcessingAction.SKIP:
            return None, ignore_actions
        elif action == ProcessingAction.LABEL:
            text_content = note_data.get('textContentHtml', '')
            label_names.append('HTML')
        elif action == ProcessingAction.IGNORE:
            text_content = note_data.get('textContent', '')
            ignore_actions['html'] = 1
            print(f"Note '{title}' has HTML content, using plain text instead")
    else:
        text_content = note_data.get('textContent', '')
    
    # Process sharing status
    sharees = note_data.get('sharees', [])
    if sharees:
        action = ProcessingAction(config['processing']['shared'])
        if action == ProcessingAction.ERROR:
            raise ValueError(f"Note '{title}' is shared (processing action: error)")
        elif action == ProcessingAction.SKIP:
            return None, ignore_actions
        elif action == ProcessingAction.LABEL:
            is_owner = any(sharee.get('isOwner', False) for sharee in sharees)
            if is_owner:
                label_names.append(config['labels']['shared'])
            else:
                label_names.append(config['labels']['received'])
        elif action == ProcessingAction.IGNORE:
            ignore_actions['shared'] = 1
        # IGNORE: do nothing
    
    # Process checklist items if present
    if list_content:
        text_content = format_checklist_items(list_content)
    
    labels = " , ".join(label_names)
    
    # Process timestamps
    created_timestamp = note_data.get('createdTimestampUsec', '')
    created_date = ''
    if created_timestamp:
        created_date = datetime.fromtimestamp(int(created_timestamp) / 1000000).strftime('%Y-%m-%d %H:%M:%S')
    
    modified_timestamp = note_data.get('userEditedTimestampUsec', '')
    modified_date = ''
    if modified_timestamp:
        modified_date = datetime.fromtimestamp(int(modified_timestamp) / 1000000).strftime('%Y-%m-%d %H:%M:%S')
    
    # Generate note ID
    note_id = generate_appsheet_id(title, created_timestamp)
    
    # Process attachments
    has_attachments = len(attachments) > 0
    attachment_count = len(attachments)
    
    return ProcessedNote(
        note_id=note_id,
        title=title,
        content=text_content,
        labels=labels,
        created_date=created_date,
        modified_date=modified_date,
        has_attachments=has_attachments,
        attachment_count=attachment_count
    ), ignore_actions 