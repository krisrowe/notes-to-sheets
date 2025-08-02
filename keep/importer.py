import os
import sys
import argparse
import yaml
import json
from jsonschema import validate, ValidationError
from execution.processor import process_notes
from keep.note_source import KeepNoteSource
from execution.config import config, DEFAULT_BATCH_SIZE, DEFAULT_IGNORE_ERRORS

# --- Configuration ---
# The name of your Google Cloud Storage bucket containing the Keep Takeout files.
# This will be passed as a command line argument.

# The name of the Google Sheet to create.
SHEET_NAME = 'Google Keep Notes'

# The name of the subfolder for images.
IMAGES_FOLDER_NAME = 'Note_Images'



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










def main(source_path, target_config, max_batches=None, ignore_errors=None, no_image_import=None, batch_size=None, wipe_mode=None):
    """
    Main function to run the export process using abstract source and target interfaces.
    
    Args:
        source_path: Source path (interpreted by source implementation)
        target_config: Configuration for target (interpreted by target implementation)
        max_batches: Maximum number of batches to process (-1 for unlimited)
        ignore_errors: Whether to continue on errors
        no_image_import: Whether to skip image uploads
        batch_size: Number of notes per batch
        wipe_mode: If 'soft' or 'hard', wipe the target before importing
    """
    # Get processor configuration values (batch size, paths, etc.)
    final_max_batches = config.get_max_batches()
    final_ignore_errors = config.get_ignore_errors()
    final_no_image_import = config.get_no_image_import()
    final_batch_size = config.get_batch_size()
    
    # Load Keep processing configuration (how to handle trashed notes, colors, etc.)
    keep_config = load_config()
    print("✅ Configuration loaded")

    # Load JSON schema for validation
    schema = load_keep_schema()
    if schema:
        print("✅ JSON schema validation enabled")
    else:
        print("⚠️  JSON schema validation disabled")

    # Create source file manager based on source path
    source_files = create_source_manager(source_path)
    
    # Handle wipe mode if specified
    if wipe_mode:
        print(f"🧹 WIPE MODE: {wipe_mode.upper()}")
        if wipe_mode == 'soft':
            print("Clearing sheet tabs and deleting images folder...")
            wipe_target_soft(target_config)
        elif wipe_mode == 'hard':
            print("Deleting entire import folder and all contents...")
            wipe_target_hard(target_config)
        print("Wipe complete!")
    
    # Create target manager based on target config (after wipe operations)
    target = create_target_manager(target_config)
    
    # Get existing notes from target
    existing_notes = get_existing_notes_from_target(target)
    print(f"Found {len(existing_notes)} existing notes in target")
    print(f"Found {sum(existing_notes.values())} notes with attachments")

    # Create schema validator callback


    # Create note source with validation and Keep config
    note_source = KeepNoteSource(source_files, schema, keep_config)
    
    # Process notes using the execution processor
    summary = process_notes(
        note_source=note_source,
        target=target,
        existing_notes=existing_notes,
        config=keep_config,
        max_batches=final_max_batches,
        batch_size=final_batch_size,
        ignore_errors=final_ignore_errors,
        sync_images=not final_no_image_import
    )

    print("\nImport complete!")


def wipe_target_soft(target_config):
    """Wipe target using soft mode - clear tabs and delete images folder."""
    from googleapiclient.discovery import build
    from google.auth import default
    
    try:
        creds, _ = default(scopes=['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets'])
        drive_service = build('drive', 'v3', credentials=creds)
        sheets_service = build('sheets', 'v4', credentials=creds)
        
        # Find the "Keep Notes Import" folder
        query = f"'{target_config}' in parents and name='Keep Notes Import' and mimeType='application/vnd.google-apps.folder'"
        results = drive_service.files().list(q=query, fields="files(id,name)").execute()
        keep_import_folders = results.get('files', [])
        
        if not keep_import_folders:
            print("❌ No 'Keep Notes Import' folder found")
            return
        
        keep_import_folder_id = keep_import_folders[0]['id']
        
        # Find the "Google Keep Notes" spreadsheet
        query = f"'{keep_import_folder_id}' in parents and name='Google Keep Notes' and mimeType='application/vnd.google-apps.spreadsheet'"
        results = drive_service.files().list(q=query, fields="files(id,name)").execute()
        spreadsheets = results.get('files', [])
        
        if not spreadsheets:
            print("❌ No 'Google Keep Notes' spreadsheet found")
            return
        
        spreadsheet_id = spreadsheets[0]['id']
        
        # Get the spreadsheet to see what tabs exist
        spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = spreadsheet.get('sheets', [])
        
        # Clear each tab by replacing all content with just the header row
        for sheet in sheets:
            sheet_name = sheet['properties']['title']
            
            # Determine headers based on sheet name
            if sheet_name == 'Note':
                headers = [['ID', 'Title', 'Content', 'Created Date', 'Modified Date', 'Labels']]
            elif sheet_name == 'Attachment':
                headers = [['ID', 'Note', 'File', 'Type', 'Title']]
            else:
                headers = [['Data']]  # Generic header for unknown sheets
            
            # Clear the sheet by replacing all content with headers
            sheets_service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=sheet_name
            ).execute()
            
            # Add headers back
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A1",
                valueInputOption='RAW',
                body={'values': headers}
            ).execute()
        
        # Delete the Note_Images folder if it exists
        query = f"'{keep_import_folder_id}' in parents and name='Note_Images' and mimeType='application/vnd.google-apps.folder'"
        results = drive_service.files().list(q=query, fields="files(id,name)").execute()
        image_folders = results.get('files', [])
        
        if image_folders:
            image_folder_id = image_folders[0]['id']
            
            # Get all files in the images folder
            query = f"'{image_folder_id}' in parents"
            results = drive_service.files().list(q=query, fields="files(id,name)").execute()
            image_files = results.get('files', [])
            
            for file_info in image_files:
                file_id = file_info['id']
                drive_service.files().delete(fileId=file_id).execute()
            
            # Delete the images folder itself
            drive_service.files().delete(fileId=image_folder_id).execute()
        
        print("✅ Soft wipe completed")
        
    except Exception as e:
        print(f"❌ Error during soft wipe: {e}")


def wipe_target_hard(target_config):
    """Wipe target using hard mode - delete entire import folder."""
    from googleapiclient.discovery import build
    from google.auth import default
    
    try:
        creds, _ = default(scopes=['https://www.googleapis.com/auth/drive'])
        drive_service = build('drive', 'v3', credentials=creds)
        
        # Find the "Keep Notes Import" folder
        query = f"'{target_config}' in parents and name='Keep Notes Import' and mimeType='application/vnd.google-apps.folder'"
        results = drive_service.files().list(q=query, fields="files(id,name)").execute()
        keep_import_folders = results.get('files', [])
        
        if not keep_import_folders:
            print("❌ No 'Keep Notes Import' folder found")
            return
        
        keep_import_folder_id = keep_import_folders[0]['id']
        
        # Find all files and folders within the Keep Notes Import folder
        query = f"'{keep_import_folder_id}' in parents"
        results = drive_service.files().list(q=query, fields="files(id,name,mimeType)").execute()
        files_to_destroy = results.get('files', [])
        
        for file_info in files_to_destroy:
            file_id = file_info['id']
            drive_service.files().delete(fileId=file_id).execute()
        
        # Destroy the Keep Notes Import folder itself
        drive_service.files().delete(fileId=keep_import_folder_id).execute()
        
        print("✅ Hard wipe completed")
        
    except Exception as e:
        print(f"❌ Error during hard wipe: {e}")



def create_source_manager(source_path):
    """Create source manager based on source path."""
    if source_path.startswith('gs://'):
        # GCS source
        bucket_name = source_path[5:]  # Remove 'gs://' prefix
        from google.cloud import storage
        from google.auth import default
        creds, _ = default(scopes=['https://www.googleapis.com/auth/devstorage.read_only'])
        storage_client = storage.Client(credentials=creds)
        bucket = storage_client.get_bucket(bucket_name)
        
        from storage.gcs_source import GCSSourceFileManager
        source_files = GCSSourceFileManager(bucket)
        print(f"Using GCS source: {bucket_name}")
    elif os.path.isdir(source_path):
        # Local source
        from storage.local_source import LocalSourceFileManager
        source_files = LocalSourceFileManager(source_path)
        print(f"Using local source: {source_path}")
    else:
        print(f"Error: '{source_path}' is not a valid source path")
        print("Examples:")
        print("  GCS: gs://my-bucket-name")
        print("  Local: /path/to/directory or ./relative/path")
        sys.exit(1)
    
    return source_files


def create_target_manager(target_config):
    """Create target manager based on target configuration."""
    # For now, assume target_config is a folder ID for Google Sheets
    from storage.sheets_target import GoogleSheetsTarget
    target = GoogleSheetsTarget(
        target_config,
        import_folder_name="Keep Notes Import",
        sheet_name="Google Keep Notes",
        images_folder_name="Note_Images"
    )
    print(f"Using Google Sheets target with folder ID: {target_config}")
    return target


def get_existing_notes_from_target(target):
    """Get existing notes from target."""
    # This is specific to Google Sheets target for now
    # In the future, this could be abstracted further
    try:
        notes_col_a = target.notes_worksheet.col_values(1)  # Column A (ID column)
        existing_notes = {}
        
        if len(notes_col_a) > 1:  # Skip header row
            for note_id in notes_col_a[1:]:  # Skip header
                if note_id:  # Skip empty cells
                    existing_notes[note_id] = False  # Note exists, assume no attachments initially
        
        # Get only the Note ID column from attachments worksheet to mark notes with attachments
        attachments_col_b = target.attachments_worksheet.col_values(2)  # Column B (Note ID column)
        if len(attachments_col_b) > 1:  # Skip header row
            for note_id in attachments_col_b[1:]:  # Skip header
                if note_id:  # Skip empty cells
                    existing_notes[note_id] = True  # Note has attachments
                    
        return existing_notes
    except Exception as e:
        print(f"Could not check existing notes: {e}")
        import traceback
        traceback.print_exc()
        return {}





if __name__ == '__main__':
    # Get defaults from centralized config
    default_source_path = config.get_source_path()
    default_target_config = config.get_target_config()
    default_batch_size = config.get_batch_size()
    default_ignore_errors = config.get_ignore_errors()
    
    parser = argparse.ArgumentParser(
        description='Import Google Keep notes using abstract source and target interfaces',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import from GCS bucket to Google Sheets
  python -m keep.importer gs://keep-notes-takeout-bucket 1EXAMPLE123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ

  # Import from local directory to Google Sheets
  python -m keep.importer ../keep-notes-takeout 1EXAMPLE123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ

  # Import with batch limits and error handling
  python -m keep.importer gs://keep-notes-takeout-bucket 1EXAMPLE123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ --max-batches 5 --ignore-errors

  # Import without uploading images (faster, metadata only)
  python -m keep.importer ../keep-notes-takeout 1EXAMPLE123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ --no-image-import

  # Import with custom batch size for better performance
  python -m keep.importer ../keep-notes-takeout 1EXAMPLE123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ --batch-size 50

  # Import with both batch size and count limits
  python -m keep.importer ../keep-notes-takeout 1EXAMPLE123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ --batch-size 30 --max-batches 10

  # Import with soft wipe (clear tabs, preserve sheet for revision history)
  python -m keep.importer ../keep-notes-takeout 1EXAMPLE123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ --wipe

  # Import with hard wipe (delete everything and start fresh)
  python -m keep.importer ../keep-notes-takeout 1EXAMPLE123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ --wipe-hard
        """
    )
    
    # Make source_path and target_config optional if defaults are provided
    if default_source_path and default_target_config:
        parser.add_argument('source_path', nargs='?', default=default_source_path,
                           help='Source path: gs://bucket-name for GCS or /path/to/directory for local files')
        parser.add_argument('target_config', nargs='?', default=default_target_config,
                           help='Target configuration (e.g., Google Drive folder ID)')
    else:
        parser.add_argument('source_path', 
                           help='Source path: gs://bucket-name for GCS or /path/to/directory for local files')
        parser.add_argument('target_config', help='Target configuration (e.g., Google Drive folder ID)')
    
    parser.add_argument('--max-batches', type=int, default=config.get_max_batches(),
                       help='Maximum number of batches to process (default: unlimited, -1)')
    parser.add_argument('--batch-size', type=int, default=config.get_batch_size(),
                       help=f'Number of notes to process in each batch (default: {DEFAULT_BATCH_SIZE})')
    parser.add_argument('--ignore-errors', action='store_true', default=config.get_ignore_errors(),
                       help=f'Continue processing even if schema validation fails (default: {DEFAULT_IGNORE_ERRORS})')
    parser.add_argument('--no-image-import', action='store_true',
                       help='Skip uploading images (only record filenames in target)')
    parser.add_argument('--wipe', action='store_true', default=False,
                       help='Wipe target before importing (soft wipe: clear tabs only, preserve sheet for revision history)')
    parser.add_argument('--wipe-hard', action='store_true', default=False,
                       help='Hard wipe: delete entire import folder and all contents')
    
    args = parser.parse_args()
    
    # Determine wipe mode
    wipe_mode = None
    if args.wipe_hard:
        wipe_mode = 'hard'
    elif args.wipe:
        wipe_mode = 'soft'
    
    main(args.source_path, args.target_config, config.get_max_batches(), config.get_ignore_errors(), config.get_no_image_import(), config.get_batch_size(), config.get_wipe_mode())
