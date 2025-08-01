import os
import json
import sys
import gspread
import mimetypes
import hashlib
import time
import argparse
import yaml
import random
import glob
from datetime import datetime
from google.cloud import storage
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from jsonschema import validate, ValidationError
from note_processor import process_note, ProcessedNote, generate_appsheet_id

# --- Configuration ---
# The name of your Google Cloud Storage bucket containing the Keep Takeout files.
# This will be passed as a command line argument.

# The name of the Google Sheet to create.
SHEET_NAME = 'Google Keep Notes'

# The name of the subfolder for images.
IMAGES_FOLDER_NAME = 'Note_Images'

# The scopes required for the APIs.
SCOPES = [
    'https://www.googleapis.com/auth/devstorage.read_only',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]

# Load configuration
def load_config():
    """Load the configuration file."""
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Warning: Config file not found at {config_path}. Using default settings.")
        return get_default_config()
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML config file: {e}")
        return get_default_config()

def get_default_config():
    """Return default configuration if config file is not found."""
    return {
        'processing': {
            'color': 'label',
            'trashed': 'skip',
            'archived': 'skip',
            'pinned': 'label',
            'html_content': 'ignore',
            'shared': 'label'
        },
        'labels': {
            'trashed': 'Trashed',
            'pinned': 'Pinned',
            'archived': 'Archived',
            'shared': 'Shared',
            'received': 'Received'
        }
    }

# Load JSON schema for validation
def load_keep_schema():
    """Load the JSON schema for Google Keep note validation."""
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.json')
    try:
        with open(schema_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: Schema file not found at {schema_path}. Skipping validation.")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON schema file: {e}")
        return None


def exponential_backoff_with_retry(operation, max_retries=5, base_delay=1, max_delay=64):
    """
    Execute an operation with exponential backoff retry logic.
    
    Args:
        operation: Function to execute
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        
    Returns:
        Result of the operation if successful
        
    Raises:
        Exception: If all retries are exhausted
    """
    delay = base_delay
    
    for attempt in range(max_retries + 1):
        try:
            return operation()
        except Exception as e:
            if "429" not in str(e) or attempt == max_retries:
                raise e
            
            # Add jitter to prevent thundering herd
            jitter = random.uniform(0, 0.1 * delay)
            actual_delay = min(delay + jitter, max_delay)
            
            print(f"    - Rate limited (attempt {attempt + 1}/{max_retries + 1}), waiting {actual_delay:.1f} seconds...")
            time.sleep(actual_delay)
            
            # Exponential backoff: double the delay for next attempt
            delay = min(delay * 2, max_delay)
    
    # This should never be reached, but just in case
    raise Exception("Max retries exceeded")


def validate_keep_note(note_data, schema=None):
    """
    Validate a Google Keep note against the JSON schema.
    
    Args:
        note_data (dict): The note data to validate
        schema (dict, optional): The schema to validate against. If None, loads from keep_schema.json
        
    Returns:
        tuple: (is_valid, error_message, error_path, schema_path)
        - is_valid (bool): True if validation passes, False otherwise
        - error_message (str): Description of the validation error (empty if valid)
        - error_path (list): Path to the error in the note data (empty if valid)
        - schema_path (list): Path to the error in the schema (empty if valid)
    """
    if schema is None:
        schema = load_keep_schema()
    
    if schema is None:
        return True, "", [], []  # Skip validation if schema can't be loaded
    
    try:
        validate(instance=note_data, schema=schema)
        return True, "", [], []
    except ValidationError as e:
        return False, e.message, list(e.path), list(e.schema_path)




def main(source_path, drive_folder_id, max_notes=None, ignore_errors=False, no_image_import=False, batch_size=20):
    # Initialize timing statistics
    timing_stats = {
        'gcs_total_time': 0.0,
        'sheets_total_time': 0.0,
        'drive_total_time': 0.0,
        'processing_total_time': 0.0,
        'start_time': time.time()
    }
    """
    Main function to run the export process from GCS Takeout or local directory to Sheets.
    
    Args:
        source_path: Either a GCS bucket name (e.g., 'my-bucket') or local directory path
        drive_folder_id: Google Drive folder ID where to create the import
        max_notes: Maximum number of notes to import (None for all)
        ignore_errors: Whether to continue on errors
    """
    # Determine if source_path is a GCS bucket or local directory
    # If it starts with gs://, it's GCS. Otherwise, check if it's a valid directory path
    if source_path.startswith('gs://'):
        # Extract bucket name from gs://bucket-name format
        bucket_name = source_path[5:]  # Remove 'gs://' prefix
        is_gcs = True
        source_path = bucket_name  # Use just the bucket name for GCS operations
    elif os.path.isdir(source_path):
        is_gcs = False
    else:
        print(f"Error: '{source_path}' is not a valid GCS bucket (gs://bucket-name) or local directory path")
        print("Examples:")
        print("  GCS: gs://my-bucket-name")
        print("  Local: /path/to/directory or ./relative/path")
        sys.exit(1)
    
    if is_gcs:
        print("Starting Google Keep Takeout import from GCS...")
        print(f"Using bucket: {source_path}")
    else:
        print("Starting Google Keep Takeout import from local directory...")
        print(f"Using directory: {source_path}")
    
    print(f"Using Drive folder ID: {drive_folder_id}")

    # Load configuration
    config = load_config()
    print("✅ Configuration loaded")

    # Load JSON schema for validation
    schema = load_keep_schema()
    if schema:
        print("✅ JSON schema validation enabled")
    else:
        print("⚠️  JSON schema validation disabled")

    # Authenticate with personal account for all operations (you'll own everything)
    from google.auth import default
    creds, _ = default(scopes=['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/devstorage.read_only'])
    
    drive_service = build('drive', 'v3', credentials=creds)
    gspread_client = gspread.authorize(creds)
    print("✅ Using personal account for all operations - you will own all created files")

    # Initialize GCS client only if needed
    storage_client = None
    bucket = None
    if is_gcs:
        storage_client = storage.Client(credentials=creds)
        # Get the GCS bucket
        try:
            bucket = storage_client.get_bucket(source_path)
        except Exception as e:
            print(f"Error accessing GCS bucket '{source_path}': {e}")
            print("Please ensure the bucket exists and your personal account has 'Storage Object Viewer' role.")
            return

    # Check for existing import folder or create a new one
    import_folder_name = "Keep Notes Import"
    
    # Search for existing import folder
    try:
        query = f"name='{import_folder_name}' and '{drive_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = drive_service.files().list(q=query, fields="files(id,name)").execute()
        files = results.get('files', [])
        
        if files:
            import_folder_id = files[0]['id']
            print(f"Found existing import folder: '{import_folder_name}' (ID: {import_folder_id})")
        else:
            # Create new import folder
            import_folder_id = create_drive_folder(drive_service, import_folder_name, parent_id=drive_folder_id)
            if not import_folder_id:
                print("Could not create the import folder. Aborting.")
                return
            print(f"Created new import folder: '{import_folder_name}'")
    except Exception as e:
        print(f"Could not check for existing import folder: {e}")
        # Fallback to creating new folder
        import_folder_id = create_drive_folder(drive_service, import_folder_name, parent_id=drive_folder_id)
        if not import_folder_id:
            print("Could not create the import folder. Aborting.")
            return
        print(f"Created new import folder: '{import_folder_name}'")

    # Check if a sheet with the same name already exists in the import folder
    existing_sheet = None
    try:
        # Search for existing sheet in the import folder (excluding trashed files)
        query = f"name='{SHEET_NAME}' and '{import_folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
        results = drive_service.files().list(q=query, fields="files(id,name)").execute()
        files = results.get('files', [])
        
        if files:
            existing_sheet = files[0]
            print(f"Found existing sheet: '{SHEET_NAME}' (ID: {existing_sheet['id']})")
        else:
            print(f"No existing sheet found, will create new one")
    except Exception as e:
        print(f"Could not check for existing sheet: {e}")
    
    if existing_sheet:
        # Use existing sheet
        spreadsheet = gspread_client.open_by_key(existing_sheet['id'])
        print(f"✅ Using existing Google Sheet: '{SHEET_NAME}'")
        print(f"📊 Sheet ID: {existing_sheet['id']}")
        print(f"📁 Folder ID: {import_folder_id}")
        
        # Get existing worksheets
        try:
            notes_worksheet = spreadsheet.worksheet('Notes')
            print("Found existing Notes worksheet")
        except:
            notes_worksheet = spreadsheet.sheet1
            print("Using first worksheet as Notes")
            
            try:
                attachments_worksheet = spreadsheet.worksheet('Attachment')
                print("Found existing Attachment worksheet")
            except:
                attachments_worksheet = spreadsheet.add_worksheet(title='Attachment', rows=1000, cols=5)
                attachments_worksheet.append_row(['ID', 'Note', 'File', 'Type', 'Title'])
                print("Created new Attachment worksheet")
    else:
        # Create new sheet
        spreadsheet = gspread_client.create(SHEET_NAME)
        
        # Move the spreadsheet to the import folder
        try:
            drive_service.files().update(
                fileId=spreadsheet.id,
                addParents=import_folder_id,
                removeParents='root',
                fields='id, parents'
            ).execute()
            print(f"✅ Created new Google Sheet: '{SHEET_NAME}' in import folder")
            print(f"📊 Sheet ID: {spreadsheet.id}")
            print(f"📁 Folder ID: {import_folder_id}")
        except Exception as e:
            print(f"Warning: Could not move sheet to import folder: {e}")
        
        # Create the main notes worksheet
        notes_worksheet = spreadsheet.sheet1
        notes_worksheet.append_row(['ID', 'Title', 'Text', 'Labels', 'Created Date', 'Modified Date'])

        # Create the attachments worksheet
        attachments_worksheet = spreadsheet.add_worksheet(title='Attachment', rows=1000, cols=5)
        attachments_worksheet.append_row(['ID', 'Note', 'File', 'Type', 'Title'])
        print("Created new Notes and Attachment worksheets")

    # Check for existing images subfolder or create a new one
    images_folder_id = None
    try:
        query = f"name='{IMAGES_FOLDER_NAME}' and '{import_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = drive_service.files().list(q=query, fields="files(id,name)").execute()
        files = results.get('files', [])
        
        if files:
            images_folder_id = files[0]['id']
            print(f"Found existing images folder: '{IMAGES_FOLDER_NAME}' (ID: {images_folder_id})")
        else:
            # Create new images folder
            images_folder_id = create_drive_folder(drive_service, IMAGES_FOLDER_NAME, parent_id=import_folder_id)
            if not images_folder_id:
                print("Could not create the images folder. Aborting.")
                return
            print(f"Created new images folder: '{IMAGES_FOLDER_NAME}'")
    except Exception as e:
        print(f"Could not check for existing images folder: {e}")
        # Fallback to creating new folder
        images_folder_id = create_drive_folder(drive_service, IMAGES_FOLDER_NAME, parent_id=import_folder_id)
        if not images_folder_id:
            print("Could not create the images folder. Aborting.")
            return
        print(f"Created new images folder: '{IMAGES_FOLDER_NAME}'")

    # Get all files from the source (GCS bucket or local directory)
    if is_gcs:
        print(f"Fetching files from GCS bucket '{source_path}'...")
        gcs_start = time.time()
        blobs = storage_client.list_blobs(source_path)
        timing_stats['gcs_total_time'] += time.time() - gcs_start
        
        # Create a dictionary mapping file paths to blobs for quick lookup
        blob_map = {blob.name: blob for blob in blobs}
        json_files = [blob for name, blob in blob_map.items() if name.endswith('.json')]
    else:
        print(f"Scanning files in local directory '{source_path}'...")
        # Get all JSON files from local directory
        json_pattern = os.path.join(source_path, "*.json")
        json_files = glob.glob(json_pattern)
        # Convert to list of file paths for consistency
        json_files = [os.path.basename(f) for f in json_files]

    if not json_files:
        if is_gcs:
            print("No .json files found in the bucket.")
        else:
            print("No .json files found in the directory.")
        return

    print(f"Found {len(json_files)} JSON note files.")
    
    # Note: max_notes limit will be applied after successful imports, not to the file list
    if max_notes:
        print(f"Will limit import to {max_notes} successfully imported notes.")
    
    print(f"Using batch size: {batch_size} notes per batch")
    print(f"Processing mode: {'Metadata only (no images)' if no_image_import else 'Full import with image sync'}")
    
    # Check for existing imported notes to avoid duplicates (scalable approach)
    existing_notes = {}  # note_id -> has_attachments (boolean)
    try:
        # Get only the ID column from notes worksheet
        notes_col_a = notes_worksheet.col_values(1)  # Column A (ID column)
        if len(notes_col_a) > 1:  # Skip header row
            for note_id in notes_col_a[1:]:  # Skip header
                if note_id:  # Skip empty cells
                    existing_notes[note_id] = False  # Note exists, assume no attachments initially
        print(f"Found {len(existing_notes)} existing notes in sheet")
        
        # Get only the Note ID column from attachments worksheet to mark notes with attachments
        attachments_col_b = attachments_worksheet.col_values(2)  # Column B (Note ID column)
        if len(attachments_col_b) > 1:  # Skip header row
            for note_id in attachments_col_b[1:]:  # Skip header
                if note_id:  # Skip empty cells
                    existing_notes[note_id] = True  # Note has attachments
        print(f"Found {sum(existing_notes.values())} notes with attachments")
    except Exception as e:
        print(f"Could not check existing notes: {e}")
        existing_notes = {}

    # Initialize summary tracking
    summary = {
        'processed': 0,
        'imported': 0,
        'duplicates': 0,
        'errors': 0,
        'totals': {},
        'ignored': {},
        'skipped': {}
    }
    
    # Initialize session image tracking and batching
    session_images = set()  # Track all image filenames from this session
    current_batch = {
        'notes': [],
        'attachments': []
    }
    batch_count = 0
    total_batches = 0

    def flush_batch_to_sheet():
        """Flush the current batch to Google Sheets."""
        nonlocal batch_count, total_batches
        
        if not current_batch['notes'] and not current_batch['attachments']:
            return
            
        batch_count += 1
        print(f"\n📊 Uploading batch {batch_count}...")
        
        # Upload notes
        if current_batch['notes']:
            try:
                def add_notes_batch():
                    sheets_start = time.time()
                    # Prepare batch data as list of lists
                    notes_data = [
                        [
                            note_data['ID'], 
                            note_data['Title'], 
                            note_data['Content'], 
                            note_data['Labels'], 
                            note_data['Created Date'], 
                            note_data['Modified Date']
                        ]
                        for note_data in current_batch['notes']
                    ]
                    notes_worksheet.append_rows(notes_data)
                    timing_stats['sheets_total_time'] += time.time() - sheets_start
                
                exponential_backoff_with_retry(add_notes_batch)
                print(f"  ✅ Added {len(current_batch['notes'])} notes to sheet (batch upload)")
                time.sleep(0.1)  # Small delay to avoid rate limiting
            except Exception as e:
                print(f"  ❌ Error adding notes batch to sheet: {e}")
                if not ignore_errors:
                    raise
        
        # Upload attachments
        if current_batch['attachments']:
            try:
                def add_attachments_batch():
                    sheets_start = time.time()
                    # Prepare batch data as list of lists
                    attachments_data = [
                        [
                            attachment_data['ID'],
                            attachment_data['Note'],
                            attachment_data['File'],
                            attachment_data['Type'],
                            attachment_data['Title']
                        ]
                        for attachment_data in current_batch['attachments']
                    ]
                    attachments_worksheet.append_rows(attachments_data)
                    timing_stats['sheets_total_time'] += time.time() - sheets_start
                
                exponential_backoff_with_retry(add_attachments_batch)
                print(f"  ✅ Added {len(current_batch['attachments'])} attachments to sheet (batch upload)")
                time.sleep(0.1)  # Small delay to avoid rate limiting
            except Exception as e:
                print(f"  ❌ Error adding attachments batch to sheet: {e}")
                if not ignore_errors:
                    raise
        
        # Clear the batch
        current_batch['notes'] = []
        current_batch['attachments'] = []
        total_batches += 1

    # Process each JSON file.
    for file_item in json_files:
        if is_gcs:
            # file_item is a blob
            print(f"\nProcessing note: {file_item.name}")
            summary['processed'] += 1
            
            try:
                gcs_start = time.time()
                note_data = json.loads(file_item.download_as_text())
                timing_stats['gcs_total_time'] += time.time() - gcs_start
            except Exception as e:
                print(f"Error reading file {file_item.name}: {e}")
                summary['errors'] += 1
                if not ignore_errors:
                    raise
                continue
        else:
            # file_item is a filename
            print(f"\nProcessing note: {file_item}")
            summary['processed'] += 1
            
            try:
                file_path = os.path.join(source_path, file_item)
                with open(file_path, 'r', encoding='utf-8') as f:
                    note_data = json.load(f)
            except Exception as e:
                print(f"Error reading file {file_item}: {e}")
                summary['errors'] += 1
                if not ignore_errors:
                    raise
                continue

        # Validate against JSON schema if available
        if schema:
            is_valid, error_msg, error_path, schema_path = validate_keep_note(note_data, schema)
            if not is_valid:
                if is_gcs:
                    print(f"  - JSON schema validation failed for {file_item.name}")
                else:
                    print(f"  - JSON schema validation failed for {file_item}")
                print(f"    Error: {error_msg}")
                print(f"    Path: {' -> '.join(str(p) for p in error_path)}")
                print(f"    Schema path: {' -> '.join(str(p) for p in schema_path)}")
                
                if ignore_errors:
                    print("  - Skipping note due to validation error (--ignore-errors flag set)")
                    continue
                else:
                    print("  - Exiting due to schema validation error (use --ignore-errors to continue)")
                    sys.exit(1)

        # Process the note using the canonical processor
        try:
            processing_start = time.time()
            processed_note, ignore_actions = process_note(note_data, config)
            timing_stats['processing_total_time'] += time.time() - processing_start
            
            # Track ignore actions
            for action_type, count in ignore_actions.items():
                if count > 0:
                    summary['ignored'][action_type] = summary['ignored'].get(action_type, 0) + count
            
            # Track skip reasons
            if processed_note is None:
                # Determine skip reason for reporting
                if note_data.get('isTrashed', False):
                    summary['skipped']['trashed'] = summary['skipped'].get('trashed', 0) + 1
                    print(f"  - Skipped trashed note: '{note_data.get('title', 'Unknown')}'")
                elif note_data.get('isArchived', False):
                    summary['skipped']['archived'] = summary['skipped'].get('archived', 0) + 1
                    print(f"  - Skipped archived note: '{note_data.get('title', 'Unknown')}'")
                elif note_data.get('isPinned', False):
                    summary['skipped']['pinned'] = summary['skipped'].get('pinned', 0) + 1
                    print(f"  - Skipped pinned note: '{note_data.get('title', 'Unknown')}'")
                elif note_data.get('color', 'DEFAULT') != 'DEFAULT':
                    summary['skipped']['colored'] = summary['skipped'].get('colored', 0) + 1
                    print(f"  - Skipped colored note: '{note_data.get('title', 'Unknown')}'")
                elif bool(note_data.get('textContentHtml', '').strip()):
                    summary['skipped']['html'] = summary['skipped'].get('html', 0) + 1
                    print(f"  - Skipped HTML note: '{note_data.get('title', 'Unknown')}'")
                elif note_data.get('sharees'):
                    summary['skipped']['shared'] = summary['skipped'].get('shared', 0) + 1
                    print(f"  - Skipped shared note: '{note_data.get('title', 'Unknown')}'")
                else:
                    print(f"  - Skipped note: '{note_data.get('title', 'Unknown')}'")
                continue
                
        except ValueError as e:
            # This is a processing action error (e.g., "error" action)
            print(f"  - Processing error: {e}")
            if ignore_errors:
                print("  - Skipping note due to processing error (--ignore-errors flag set)")
                continue
            else:
                print("  - Exiting due to processing error (use --ignore-errors to continue)")
                sys.exit(1)
        except Exception as e:
            print(f"  - Unexpected error processing note: {e}")
            summary['errors'] += 1
            if ignore_errors:
                continue
            else:
                sys.exit(1)
        
        # Check if note exists and if it has any attachments
        if processed_note.note_id in existing_notes:
            if existing_notes[processed_note.note_id]:
                # Note exists with attachments - skip as complete duplicate
                print(f"  - Skipping complete duplicate note: '{processed_note.title}' (ID: {processed_note.note_id})")
                summary['duplicates'] += 1
                
                # Track images from duplicates for fail-safe cleanup
                attachments = note_data.get('attachments', [])
                for attachment in attachments:
                    if attachment.get('mimetype', '').startswith('image/'):
                        filename = os.path.basename(attachment.get('filePath', ''))
                        if filename:
                            session_images.add(filename)
                            print(f"    - Tracked image from duplicate: {filename}")
                
                continue
            else:
                # Note exists but has no attachments - add attachments only
                print(f"  - Note exists but missing attachments, adding attachments: '{processed_note.title}' (ID: {processed_note.note_id})")
                summary['attachments_added'] = summary.get('attachments_added', 0) + 1

        # Track annotations and attachments statistics
        annotations = note_data.get('annotations', [])
        attachments = note_data.get('attachments', [])
        
        if annotations:
            summary['totals']['notes_with_annotations'] = summary['totals'].get('notes_with_annotations', 0) + 1
            summary['totals']['annotations'] = summary['totals'].get('annotations', 0) + len(annotations)
        
        if attachments:
            summary['totals']['notes_with_attachments'] = summary['totals'].get('notes_with_attachments', 0) + 1
            summary['totals']['attachments'] = summary['totals'].get('attachments', 0) + len(attachments)

        # Process file attachments and track images for batch processing
        attachments = note_data.get('attachments', [])
        for attachment in attachments:
            file_path_in_gcs = attachment.get('filePath')
            if not file_path_in_gcs:
                continue

            # Determine attachment type and title
            mimetype = attachment.get('mimetype', '')
            
            # Error if attachment is not an image
            if not mimetype.startswith('image/'):
                print(f"ERROR: Non-image attachment found in note '{processed_note.title}'")
                print(f"  File: {file_path_in_gcs}")
                print(f"  MIME type: {mimetype}")
                print("Script only supports image attachments. Exiting.")
                sys.exit(1)
            
            attachment_type = "Image"
            
            # For links, try to get title from annotations
            attachment_title = ""
            annotations = note_data.get('annotations', [])
            for annotation in annotations:
                if annotation.get('source') in ['WEBLINK', 'SHEETS', 'DOCS', 'GMAIL']:
                    attachment_title = annotation.get('title', '')
                    break

            # Track image filename for session
            filename = os.path.basename(file_path_in_gcs)
            if filename:
                session_images.add(filename)
                print(f"    - Tracked image: {filename}")

            # Generate attachment ID and add to batch
            attachment_id = generate_appsheet_id(f"{processed_note.note_id}_{file_path_in_gcs}", note_data.get('createdTimestampUsec', ''))
            
            # Add to batch (no Drive upload during processing phase)
            current_batch['attachments'].append({
                'ID': attachment_id,
                'Note': processed_note.note_id,
                'File': filename,  # Just the filename, not full path
                'Type': attachment_type,
                'Title': attachment_title
            })
            
            print(f"    - Added attachment to batch: {filename}")

        # Process WEBLINK, SHEETS, DOCS, and GMAIL annotations (links without file attachments)
        annotations = note_data.get('annotations', [])
        for annotation in annotations:
            # Error if annotation is not WEBLINK, SHEETS, DOCS, or GMAIL
            if annotation.get('source') not in ['WEBLINK', 'SHEETS', 'DOCS', 'GMAIL']:
                print(f"ERROR: Unsupported annotation source found in note '{processed_note.title}'")
                print(f"  Source: {annotation.get('source', 'unknown')}")
                print(f"  Annotation: {annotation}")
                print("Script only supports WEBLINK, SHEETS, DOCS, and GMAIL annotations. Exiting.")
                sys.exit(1)
            
            url = annotation.get('url', '')
            title = annotation.get('title', '')
            
            if url:  # Only process if there's actually a URL
                # Generate attachment ID for the link
                attachment_id = generate_appsheet_id(f"{processed_note.note_id}_{url}", note_data.get('createdTimestampUsec', ''))
                
                # Add to batch
                current_batch['attachments'].append({
                    'ID': attachment_id,
                    'Note': processed_note.note_id,
                    'File': url,
                    'Type': 'Link',
                    'Title': title
                })
                
                print(f"    - Added link to batch: {title or url}")

        # Add the note to the batch
        note_dict = processed_note.to_dict()
        current_batch['notes'].append(note_dict)
        print(f"  - Added note to batch: '{processed_note.title}' (ID: {processed_note.note_id})")
        
        # Track successful import
        summary['imported'] += 1
        
        # Flush batch if it's full
        if len(current_batch['notes']) >= batch_size:
            flush_batch_to_sheet()
        
        # Check if we've reached the max_notes limit
        if max_notes and summary['imported'] >= max_notes:
            print(f"\nReached maximum import limit of {max_notes} notes. Stopping import.")
            break

    # Flush any remaining batch
    flush_batch_to_sheet()
    
    # Image sync phase (if not skipping images)
    if not no_image_import and session_images:
        print(f"\n🖼️  Starting image sync phase...")
        print(f"📊 Syncing {len(session_images)} images from this session")
        
        # Get existing images in Drive folder
        drive_images = set()
        try:
            query = f"'{images_folder_id}' in parents and trashed=false"
            results = drive_service.files().list(q=query, fields="files(name)").execute()
            drive_images = {file['name'] for file in results.get('files', [])}
            print(f"📁 Found {len(drive_images)} existing images in Drive folder")
        except Exception as e:
            print(f"❌ Error checking Drive folder contents: {e}")
            if not ignore_errors:
                raise
        
        # Determine which images need to be copied
        missing_images = session_images - drive_images
        existing_session_images = session_images & drive_images
        
        print(f"📊 Image sync summary:")
        print(f"  - Session images: {len(session_images)}")
        print(f"  - Already in Drive: {len(existing_session_images)}")
        print(f"  - Need to copy: {len(missing_images)}")
        
        # Copy missing images
        if missing_images:
            print(f"\n📤 Copying {len(missing_images)} images to Drive...")
            copied_count = 0
            failed_count = 0
            
            for i, filename in enumerate(missing_images, 1):
                print(f"  [{i}/{len(missing_images)}] Copying {filename}...")
                
                try:
                    # Find the image file in source
                    if is_gcs:
                        # Look for the file in GCS
                        file_blob = None
                        for blob in blob_map.values():
                            if os.path.basename(blob.name) == filename:
                                file_blob = blob
                                break
                        
                        if not file_blob:
                            print(f"    ❌ File not found in GCS: {filename}")
                            failed_count += 1
                            if not ignore_errors:
                                continue
                            else:
                                continue
                        
                        # Download to temp file and upload to Drive
                        local_temp_path = filename
                        try:
                            gcs_start = time.time()
                            file_blob.download_to_filename(local_temp_path)
                            timing_stats['gcs_total_time'] += time.time() - gcs_start
                            
                            drive_start = time.time()
                            upload_file_to_drive(drive_service, local_temp_path, images_folder_id)
                            timing_stats['drive_total_time'] += time.time() - drive_start
                            
                            copied_count += 1
                            print(f"    ✅ Copied from GCS: {filename}")
                        finally:
                            if os.path.exists(local_temp_path):
                                os.remove(local_temp_path)
                    else:
                        # Look for the file in local directory
                        local_file_path = None
                        for root, dirs, files in os.walk(source_path):
                            if filename in files:
                                local_file_path = os.path.join(root, filename)
                                break
                        
                        if not local_file_path or not os.path.exists(local_file_path):
                            print(f"    ❌ File not found locally: {filename}")
                            failed_count += 1
                            if not ignore_errors:
                                continue
                            else:
                                continue
                        
                        # Upload to Drive
                        drive_start = time.time()
                        upload_file_to_drive(drive_service, local_file_path, images_folder_id)
                        timing_stats['drive_total_time'] += time.time() - drive_start
                        
                        copied_count += 1
                        print(f"    ✅ Copied from local: {filename}")
                        
                except Exception as e:
                    print(f"    ❌ Failed to copy {filename}: {e}")
                    failed_count += 1
                    if not ignore_errors:
                        raise
            
            print(f"\n📊 Image sync results:")
            print(f"  - Copied for newly imported: {copied_count}")
            print(f"  - Already existing: {len(existing_session_images)}")
            print(f"  - Failed to copy: {failed_count}")
        else:
            print(f"✅ All session images already exist in Drive folder")
    
    # Print final summary
    print("\n" + "="*60)
    print("IMPORT SUMMARY")
    print("="*60)
    print(f"Notes processed: {summary['processed']}")
    print(f"Notes imported: {summary['imported']}")
    print(f"Attachments added to existing notes: {summary.get('attachments_added', 0)}")
    print(f"Notes skipped: {summary['skipped']}")
    print(f"Duplicates: {summary['duplicates']}")
    print(f"Errors: {summary['errors']}")
    
    # Content statistics (only show if > 0)
    if summary['totals']:
        print(f"\nTotals:")
        for key, value in summary['totals'].items():
            print(f"  {key}: {value}")
    
    # Skip reasons (only show if > 0)
    if summary['skipped']:
        print(f"\nSkipped:")
        for reason, count in summary['skipped'].items():
            print(f"  {reason}: {count}")
    
    # Ignore actions (only show if > 0)
    if summary['ignored']:
        print(f"\nIgnored:")
        for reason, count in summary['ignored'].items():
            print(f"  {reason}: {count}")
    
    # Check if HTML conversions occurred (this would be tracked in process_note)
    # For now, we'll note that HTML processing behavior is configured
    html_action = config['processing']['html_content']
    if html_action == 'ignore':
        print(f"\nHTML content processing: Using plain text (ignore action)")
    elif html_action == 'label':
        print(f"\nHTML content processing: Using HTML content with 'HTML' label")
    elif html_action == 'skip':
        print(f"\nHTML content processing: Skipping notes with HTML content")
    elif html_action == 'error':
        print(f"\nHTML content processing: Exiting on HTML content (error action)")
    
    # Calculate total time and timing statistics
    total_time = time.time() - timing_stats['start_time']
    print(f"\n" + "="*60)
    print("TIMING STATISTICS")
    print("="*60)
    print(f"Total execution time: {total_time:.2f} seconds")
    print(f"GCS operations: {timing_stats['gcs_total_time']:.2f} seconds ({timing_stats['gcs_total_time']/total_time*100:.1f}%)")
    print(f"Google Sheets operations: {timing_stats['sheets_total_time']:.2f} seconds ({timing_stats['sheets_total_time']/total_time*100:.1f}%)")
    print(f"Google Drive operations: {timing_stats['drive_total_time']:.2f} seconds ({timing_stats['drive_total_time']/total_time*100:.1f}%)")
    print(f"Note processing: {timing_stats['processing_total_time']:.2f} seconds ({timing_stats['processing_total_time']/total_time*100:.1f}%)")
    print(f"Other operations: {total_time - timing_stats['gcs_total_time'] - timing_stats['sheets_total_time'] - timing_stats['drive_total_time'] - timing_stats['processing_total_time']:.2f} seconds")
    
    print("\nImport complete!")

# Note: generate_appsheet_id and format_checklist_items are now in note_processor.py

def create_drive_folder(drive_service, folder_name, parent_id=None):
    """
    Creates a folder in Google Drive.
    """
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        file_metadata['parents'] = [parent_id]

    try:
        folder = drive_service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')
    except Exception as e:
        print(f"An error occurred while creating folder '{folder_name}': {e}")
        return None

def upload_file_to_drive(drive_service, file_path, folder_id):
    """
    Uploads a file to a specific folder in Google Drive.
    """
    file_metadata = {
        'name': os.path.basename(file_path),
        'parents': [folder_id]
    }
    # Guess the MIME type of the file, or default to a generic binary type.
    mimetype, _ = mimetypes.guess_type(file_path)
    media = MediaFileUpload(file_path, mimetype=mimetype or 'application/octet-stream')
    try:
        drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
    except Exception as e:
        print(f"An error occurred while uploading file '{os.path.basename(file_path)}': {e}")




if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Import Google Keep notes from GCS bucket or local directory to Google Sheets',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import from GCS bucket
  python keep/importer.py gs://keep-notes-takeout-bucket 1JCoTPNHQcawMi1wOmQ5PM3xUOVQYwTKf

  # Import from local directory
  python keep/importer.py ../keep-notes-takeout 1JCoTPNHQcawMi1wOmQ5PM3xUOVQYwTKf

  # Import with limits and error handling
  python keep/importer.py gs://keep-notes-takeout-bucket 1JCoTPNHQcawMi1wOmQ5PM3xUOVQYwTKf --max-notes 100 --ignore-errors

  # Import without uploading images (faster, metadata only)
  python keep/importer.py ../keep-notes-takeout 1JCoTPNHQcawMi1wOmQ5PM3xUOVQYwTKf --no-image-import

  # Import with custom batch size for better performance
  python keep/importer.py ../keep-notes-takeout 1JCoTPNHQcawMi1wOmQ5PM3xUOVQYwTKf --batch-size 50
        """
    )
    parser.add_argument('source_path', 
                       help='Source path: gs://bucket-name for GCS or /path/to/directory for local files')
    parser.add_argument('drive_folder_id', help='ID of the Google Drive folder to import into')
    parser.add_argument('--max-notes', type=int, help='Maximum number of notes to import (for trial runs)')
    parser.add_argument('--ignore-errors', action='store_true', 
                       help='Continue processing even if schema validation fails (default: exit on first error)')
    parser.add_argument('--no-image-import', action='store_true',
                       help='Skip uploading images to Google Drive (only record filenames in sheet)')
    parser.add_argument('--batch-size', type=int, default=20,
                       help='Number of notes to process in each batch (default: 20)')
    
    args = parser.parse_args()
    
    main(args.source_path, args.drive_folder_id, args.max_notes, args.ignore_errors, args.no_image_import, args.batch_size)
