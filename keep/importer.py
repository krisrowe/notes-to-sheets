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




def main(bucket_name, drive_folder_id, max_notes=None, ignore_errors=False):
    """
    Main function to run the export process from GCS Takeout to Sheets.
    """
    print("Starting Google Keep Takeout import from GCS...")
    print(f"Using bucket: {bucket_name}")
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
    

    
    storage_client = storage.Client(credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    gspread_client = gspread.authorize(creds)
    print("✅ Using personal account for all operations - you will own all created files")

    # Get the GCS bucket
    try:
        bucket = storage_client.get_bucket(bucket_name)
    except Exception as e:
        print(f"Error accessing GCS bucket '{bucket_name}': {e}")
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

    # Create the images subfolder
    images_folder_id = create_drive_folder(drive_service, IMAGES_FOLDER_NAME, parent_id=import_folder_id)
    if not images_folder_id:
        print("Could not create the images folder. Aborting.")
        return
    print(f"Created images folder: '{IMAGES_FOLDER_NAME}'")

    # Get all files from the GCS bucket.
    print(f"Fetching files from GCS bucket '{bucket_name}'...")
    blobs = storage_client.list_blobs(bucket_name)
    
    # Create a dictionary mapping file paths to blobs for quick lookup
    blob_map = {blob.name: blob for blob in blobs}
    json_files = [blob for name, blob in blob_map.items() if name.endswith('.json')]

    if not json_files:
        print("No .json files found in the bucket.")
        return

    print(f"Found {len(json_files)} JSON note files.")
    
    # Apply max_notes limit if specified
    if max_notes:
        json_files = json_files[:max_notes]
        print(f"Limiting import to first {max_notes} notes for trial run.")
    
    # Check for existing imported notes to avoid duplicates
    existing_note_ids = set()
    try:
        existing_data = notes_worksheet.get_all_values()
        if len(existing_data) > 1:  # Skip header row
            for row in existing_data[1:]:  # Skip header
                if len(row) >= 1:
                    existing_note_ids.add(row[0])  # Note ID is in column 0
        print(f"Found {len(existing_note_ids)} existing notes in sheet")
    except Exception as e:
        print(f"Could not check existing notes: {e}")
        existing_note_ids = set()

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
    
    # Process each JSON file.
    for blob in json_files:
        print(f"\nProcessing note: {blob.name}")
        summary['processed'] += 1
        
        try:
            note_data = json.loads(blob.download_as_text())
            
            # Validate against JSON schema if available
            if schema:
                is_valid, error_msg, error_path, schema_path = validate_keep_note(note_data, schema)
                if not is_valid:
                    print(f"  - JSON schema validation failed for {blob.name}")
                    print(f"    Error: {error_msg}")
                    print(f"    Path: {' -> '.join(str(p) for p in error_path)}")
                    print(f"    Schema path: {' -> '.join(str(p) for p in schema_path)}")
                    
                    if ignore_errors:
                        print("  - Skipping note due to validation error (--ignore-errors flag set)")
                        continue
                    else:
                        print("  - Exiting due to schema validation error (use --ignore-errors to continue)")
                        sys.exit(1)
                    
        except Exception as e:
            print(f"  - Could not parse JSON file {blob.name}. Skipping. Error: {e}")
            continue

        # Process the note using the canonical processor
        try:
            processed_note, ignore_actions = process_note(note_data, config)
            
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
        
        # Skip if note already exists (check by ID)
        if processed_note.note_id in existing_note_ids:
            print(f"  - Skipping duplicate note: '{processed_note.title}' (ID: {processed_note.note_id})")
            summary['duplicates'] += 1
            continue

        # Track annotations and attachments statistics
        annotations = note_data.get('annotations', [])
        attachments = note_data.get('attachments', [])
        
        if annotations:
            summary['totals']['notes_with_annotations'] = summary['totals'].get('notes_with_annotations', 0) + 1
            summary['totals']['annotations'] = summary['totals'].get('annotations', 0) + len(annotations)
        
        if attachments:
            summary['totals']['notes_with_attachments'] = summary['totals'].get('notes_with_attachments', 0) + 1
            summary['totals']['attachments'] = summary['totals'].get('attachments', 0) + len(attachments)

        # Process file attachments and add to attachments worksheet
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

            file_blob = blob_map.get(file_path_in_gcs)
            if not file_blob:
                print(f"    - File not found in GCS: {file_path_in_gcs}")
                continue
            
            # Download file to a temporary local file
            local_temp_path = os.path.basename(file_path_in_gcs)
            try:
                file_blob.download_to_filename(local_temp_path)
                print(f"    - Downloaded {file_path_in_gcs} from GCS.")
                
                # Upload to the single images folder
                upload_file_to_drive(drive_service, local_temp_path, images_folder_id)
                print(f"    - Uploaded {local_temp_path} to Drive.")

                # Generate attachment ID and add to attachments worksheet
                attachment_id = generate_appsheet_id(f"{processed_note.note_id}_{file_path_in_gcs}", note_data.get('createdTimestampUsec', ''))
                try:
                    def add_attachment():
                        attachments_worksheet.append_row([attachment_id, processed_note.note_id, local_temp_path, attachment_type, attachment_title])
                    
                    exponential_backoff_with_retry(add_attachment)
                    time.sleep(0.1)  # Small delay to avoid rate limiting
                except Exception as e:
                    print(f"    - Error adding attachment to sheet: {e}")

            except Exception as e:
                print(f"    - Error processing attachment {file_path_in_gcs}: {e}")
            finally:
                # Clean up the local file.
                if os.path.exists(local_temp_path):
                    os.remove(local_temp_path)

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
                try:
                    def add_link():
                        attachments_worksheet.append_row([attachment_id, processed_note.note_id, url, "Link", title])
                    
                    exponential_backoff_with_retry(add_link)
                    time.sleep(0.1)  # Small delay to avoid rate limiting
                    print(f"    - Added link to sheet: {title or url}")
                except Exception as e:
                    print(f"    - Error adding link to sheet: {e}")

        # Add the note to the Google Sheet.
        try:
            def add_note():
                note_dict = processed_note.to_dict()
                notes_worksheet.append_row([
                    note_dict['ID'], 
                    note_dict['Title'], 
                    note_dict['Content'], 
                    note_dict['Labels'], 
                    note_dict['Created Date'], 
                    note_dict['Modified Date']
                ])
            
            exponential_backoff_with_retry(add_note)
            print(f"  - Added note to sheet: '{processed_note.title}' (ID: {processed_note.note_id})")
            # Add a small delay to avoid rate limiting
            time.sleep(0.1)
        except Exception as e:
            print(f"  - Error adding note to sheet: {e}")
        
        # Track successful import
        summary['imported'] += 1

    # Print final summary
    print("\n" + "="*60)
    print("IMPORT SUMMARY")
    print("="*60)
    print(f"Notes processed: {summary['processed']}")
    print(f"Notes imported: {summary['imported']}")
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
    parser = argparse.ArgumentParser(description='Import Google Keep notes from GCS to Google Sheets')
    parser.add_argument('bucket_name', help='Name of your Google Cloud Storage bucket')
    parser.add_argument('drive_folder_id', help='ID of the Google Drive folder to import into')
    parser.add_argument('--max-notes', type=int, help='Maximum number of notes to import (for trial runs)')
    parser.add_argument('--ignore-errors', action='store_true', help='Continue processing even if schema validation fails (default: exit on first error)')
    
    args = parser.parse_args()
    
    main(args.bucket_name, args.drive_folder_id, args.max_notes, args.ignore_errors)
