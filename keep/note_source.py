import json
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from jsonschema import validate, ValidationError
from execution.note_source import NoteSource
from execution.note import ProcessedNote, calculate_note_id


class KeepNoteSource(NoteSource):
    """Implementation of NoteSource for Google Keep notes."""
    
    def __init__(self, source_files, schema=None, config=None):
        """
        Initialize the Keep note source.
        
        Args:
            source_files: Source file manager (local/GCS)
            schema: JSON schema for validation (optional)
            config: Configuration for note processing (optional)
        """
        self.source_files = source_files
        self.schema = schema
        self.config = config or {}
        self._note_cache = {}  # Cache for processed notes
        
        # Initialize cursor state
        self._file_list = self.source_files.list_files()  # Cache file list
        self._cursor_index = -1  # Start before first file
    
    def fetch_next(self) -> ProcessedNote:
        """
        Fetch the next note from the source.
        
        Returns:
            ProcessedNote object if a note is available, None if no more notes
        """
        if not self.has_more():
            return None
        
        # Move cursor to next file
        self._cursor_index += 1
        filename = self._file_list[self._cursor_index]
        
        return self._load_and_process_note(filename)
    
    def load_by_filename(self, filename_without_extension: str) -> Optional[ProcessedNote]:
        """Load a specific note by filename (without .json extension) for testing."""
        full_filename = f"{filename_without_extension}.json"
        return self._load_and_process_note(full_filename)
    
    def _load_and_process_note(self, filename: str) -> Optional[ProcessedNote]:
        """Internal method to load, validate, and transform a note."""
        
        # Check cache first
        if filename in self._note_cache:
            return self._note_cache[filename]
        
        # Load JSON content
        json_content = self.source_files.get_json_content(filename)
        if not json_content:
            raise ValueError(f"Empty or missing JSON content in {filename}")
        
        # Validate against schema if provided
        if self.schema:
            validate(instance=json_content, schema=self.schema)
        
        # Process Keep-specific note data
        processed_note, ignore_actions = self._process_keep_note(json_content)
        
        # Cache the result
        self._note_cache[filename] = processed_note
        
        return processed_note
    
    def reset(self) -> None:
        """Reset the cursor to the beginning of the source."""
        self._cursor_index = -1
    
    def has_more(self) -> bool:
        """
        Check if there are more notes available to fetch.
        
        Returns:
            True if more notes are available, False otherwise
        """
        return self._cursor_index < len(self._file_list) - 1
    
    def _process_keep_note(self, note_data: Dict[str, Any]) -> tuple[Optional[ProcessedNote], Dict[str, int]]:
        """
        Process a raw Google Keep note into a canonical representation.
        
        Args:
            note_data: Raw JSON note data from Google Keep
            
        Returns:
            Tuple of (ProcessedNote object or None if note should be skipped, ignore_actions_dict)
        """
        # Initialize ignore actions counter (for fields that are ignored, not skipped)
        ignore_actions = {
            'color': 0,
            'trashed': 0,
            'archived': 0,
            'pinned': 0,
            'html_content': 0,
            'shared': 0,
            'received': 0
        }
        
        # Extract basic note information early
        title = note_data.get('title', '').strip()
        text_content = note_data.get('textContent', '').strip()
        list_content = note_data.get('listContent', [])
        
        # Process content
        content_parts = []
        if text_content:
            content_parts.append(text_content)
        if list_content:
            formatted_list = self._format_checklist_items(list_content)
            if formatted_list:
                content_parts.append(formatted_list)
        content = '\n\n'.join(content_parts) if content_parts else ''
        
        # Process dates
        created_timestamp = note_data.get('createdTimestampUsec', '')
        created_date = self._format_timestamp(created_timestamp)
        modified_date = self._format_timestamp(note_data.get('userEditedTimestampUsec', ''))
        
        # Create ProcessedNote object early
        processed_note = ProcessedNote(
            title=title,
            content=content,
            labels='',  # Will be populated during field processing
            created_date=created_date,
            modified_date=modified_date,
            attachments=[]  # Will be populated after processing attachments
        )
        
        # Calculate and assign note_id
        note_id = calculate_note_id(title, created_date)
        processed_note.note_id = note_id
        
        # Process attachments using the note's calculated ID
        # This needs to happen after note_id is set so attachments can reference it
        attachments = self._process_attachments(note_data, processed_note)
        processed_note.attachments = attachments
        
        # Add a labels list and skipped flag to the note for processing
        processed_note.labels_list = []  # Temporary list for building labels
        processed_note.skipped = False   # Flag to mark if note should be skipped
        
        # Define field processing configurations with simple lambdas
        # Each tuple: (field_name, source_attr, default_value, field_extractor, data_modifier)
        field_configs = [
            ('trashed', 'isTrashed', False, None, 
             lambda note, field_value, labels: labels.append(self.config['labels']['trashed'])),
            ('archived', 'isArchived', False, None,
             lambda note, field_value, labels: labels.append(self.config['labels']['archived'])),
            ('pinned', 'isPinned', False, None,
             lambda note, field_value, labels: labels.append(self.config['labels']['pinned'])),
            ('color', 'color', 'DEFAULT', None,
             lambda note, field_value, labels: labels.append(field_value.title())),
            ('html_content', 'textContentHtml', None, None,
             self._handle_html_content),  # Single helper function for complex case
            ('shared', 'sharees', False, 
             lambda data: any(sharee.get('isOwner', False) for sharee in data.get('sharees', [])),
             lambda note, field_value, labels: labels.append(self.config['labels']['shared'])),
            ('received', 'sharees', False,
             lambda data: len(data.get('sharees', [])) > 0 and all(not sharee.get('isOwner', False) for sharee in data.get('sharees', [])),
             lambda note, field_value, labels: labels.append(self.config['labels']['received']))
        ]
        
        # Process all fields with early exit
        for field_name, source_attr, default_value, field_extractor, data_modifier in field_configs:
            self._process_field(note_data, field_name, source_attr, default_value, ignore_actions, processed_note, 
                              field_extractor=field_extractor, data_modifier=data_modifier)
            
            # Early exit if note should be skipped
            if processed_note.skipped:
                return None, ignore_actions
        
        # Add user-defined labels
        user_labels = note_data.get('labels', [])
        for label in user_labels:
            label_name = label.get('name', '').strip()
            if label_name:
                processed_note.labels_list.append(label_name)
        
        # Finalize the note by converting labels list to string and removing temporary attributes
        processed_note.labels = ' , '.join(processed_note.labels_list) if processed_note.labels_list else ''
        delattr(processed_note, 'labels_list')
        delattr(processed_note, 'skipped')
        
        return processed_note, ignore_actions
    
    def _process_field(self, note_data: Dict[str, Any], field_name: str, source_attr: str, 
                      default_value: Any, ignore_actions: Dict[str, int], processed_note: ProcessedNote,
                      field_extractor: Optional[Callable[[Dict[str, Any]], Any]] = None,
                      data_modifier: Optional[Callable[[ProcessedNote, Any, List[str]], None]] = None) -> None:
        """
        Generic field processor that handles all processing actions and labeling.
        
        Args:
            note_data: The note data dictionary
            field_name: The field name in config (e.g., 'trashed', 'color')
            source_attr: The source attribute name (e.g., 'isTrashed', 'color')
            default_value: The default value to compare against (e.g., False, 'DEFAULT')
            ignore_actions: The ignore actions counter dict
            processed_note: The ProcessedNote object to modify
            field_extractor: Optional function to extract field value
            data_modifier: Optional function to modify the processed_note object
        """
        # Get the field value - either from extractor or direct access
        if field_extractor is not None:
            actual_field_value = field_extractor(note_data)
        else:
            actual_field_value = note_data.get(source_attr, default_value)
        
        # Check if field has a non-default value
        has_value = actual_field_value != default_value
        
        # For boolean fields, check if True
        if isinstance(default_value, bool):
            has_value = actual_field_value is True
        
        # For None default (like HTML content), check if exists
        if default_value is None:
            has_value = actual_field_value is not None
        
        if has_value:
            action = self.config['processing'][field_name]
            
            if action == 'error':
                raise ValueError(f"Note has {field_name} '{actual_field_value}' but {field_name} processing is set to 'error'")
            elif action == 'skip':
                processed_note.skipped = True # Mark note as skipped
            elif action == 'ignore':
                # Process normally but ignore this field
                ignore_actions[field_name] += 1
            elif action == 'label':
                # Add the label using extractor or default logic
                if data_modifier is not None:
                    data_modifier(processed_note, actual_field_value, processed_note.labels_list)
    
    def _format_checklist_items(self, list_content: List[Dict[str, Any]]) -> str:
        """Format checklist items into a readable string."""
        formatted_items = []
        for item in list_content:
            text = item.get('text', '').strip()
            is_checked = item.get('isChecked', False)
            if text:
                checkbox = '☑' if is_checked else '☐'
                formatted_items.append(f"{checkbox} {text}")
        return "\n".join(formatted_items) 

    def _handle_html_content(self, note: ProcessedNote, field_value: str, labels: List[str]) -> None:
        """Handle HTML content by setting the HTML label and updating content."""
        labels.append('HTML')
        note.content = field_value

    def _process_attachments(self, note_data: Dict[str, Any], processed_note: ProcessedNote) -> List[Dict[str, Any]]:
        """
        Process file and link attachments from the note data.
        """
        attachments = []
        file_attachments = note_data.get('attachments', [])
        annotations = note_data.get('annotations', [])
        
        # Add file attachments
        for attachment in file_attachments:
            attachment_info = {
                'Type': 'Image',  # Keep-specific type mapping
                'File': attachment.get('filePath', ''),  # Use filePath for File field
                'Title': '',  # Empty title for images
                'note_id': processed_note.note_id
            }
            attachments.append(attachment_info)
        
        # Add link annotations (WEBLINK, SHEETS, DOCS, GMAIL)
        for annotation in annotations:
            source = annotation.get('source', '')
            if source in ['WEBLINK', 'SHEETS', 'DOCS', 'GMAIL']:
                attachment_info = {
                    'Type': 'Link',  # Keep-specific type mapping
                    'File': annotation.get('url', ''),  # Use URL for File field
                    'Title': annotation.get('title', ''),
                    'note_id': processed_note.note_id
                }
                attachments.append(attachment_info)
        
        return attachments

    def _format_timestamp(self, timestamp_usec: str) -> str:
        """
        Helper function to format microseconds timestamp to a readable string.
        """
        if not timestamp_usec:
            return ''
        try:
            # Convert microseconds to seconds
            seconds = int(timestamp_usec) // 1000000
            return datetime.fromtimestamp(seconds).strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, OSError):
            return '' 