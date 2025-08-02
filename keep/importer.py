import os
import sys
import argparse
import yaml
import json
from jsonschema import validate, ValidationError
from execution.processor import process_notes
from keep.note_source import KeepNoteSource

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










def main(source_path, target_config, max_batches=-1, ignore_errors=False, no_image_import=False, batch_size=20):
    """
    Main function to run the export process using abstract source and target interfaces.
    
    Args:
        source_path: Source path (interpreted by source implementation)
        target_config: Configuration for target (interpreted by target implementation)
        max_batches: Maximum number of batches to process (-1 for unlimited)
        ignore_errors: Whether to continue on errors
        no_image_import: Whether to skip image uploads
        batch_size: Number of notes per batch
    """
    # Load configuration
    config = load_config()
    print("✅ Configuration loaded")

    # Load JSON schema for validation
    schema = load_keep_schema()
    if schema:
        print("✅ JSON schema validation enabled")
    else:
        print("⚠️  JSON schema validation disabled")

    # Create source file manager based on source path
    source_files = create_source_manager(source_path)
    
    # Create target manager based on target config
    target = create_target_manager(target_config)
    
    # Get existing notes from target
    existing_notes = get_existing_notes_from_target(target)
    print(f"Found {len(existing_notes)} existing notes in target")
    print(f"Found {sum(existing_notes.values())} notes with attachments")

    # Create schema validator callback


    # Create note source with validation and config
    note_source = KeepNoteSource(source_files, schema, config)
    
    # Process notes using the execution processor
    summary = process_notes(
        note_source=note_source,
        target=target,
        existing_notes=existing_notes,
        config=config,
        max_batches=max_batches,
        batch_size=batch_size,
        ignore_errors=ignore_errors,
        sync_images=not no_image_import
    )

    print("\nImport complete!")





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
        return {}





if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Import Google Keep notes using abstract source and target interfaces',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import from GCS bucket to Google Sheets
  python keep/importer.py gs://keep-notes-takeout-bucket 1JCoTPNHQcawMi1wOmQ5PM3xUOVQYwTKf

  # Import from local directory to Google Sheets
  python keep/importer.py ../keep-notes-takeout 1JCoTPNHQcawMi1wOmQ5PM3xUOVQYwTKf

  # Import with batch limits and error handling
  python keep/importer.py gs://keep-notes-takeout-bucket 1JCoTPNHQcawMi1wOmQ5PM3xUOVQYwTKf --max-batches 5 --ignore-errors

  # Import without uploading images (faster, metadata only)
  python keep/importer.py ../keep-notes-takeout 1JCoTPNHQcawMi1wOmQ5PM3xUOVQYwTKf --no-image-import

  # Import with custom batch size for better performance
  python keep/importer.py ../keep-notes-takeout 1JCoTPNHQcawMi1wOmQ5PM3xUOVQYwTKf --batch-size 50

  # Import with both batch size and count limits
  python keep/importer.py ../keep-notes-takeout 1JCoTPNHQcawMi1wOmQ5PM3xUOVQYwTKf --batch-size 30 --max-batches 10
        """
    )
    parser.add_argument('source_path', 
                       help='Source path: gs://bucket-name for GCS or /path/to/directory for local files')
    parser.add_argument('target_config', help='Target configuration (e.g., Google Drive folder ID)')
    parser.add_argument('--max-batches', type=int, default=-1,
                       help='Maximum number of batches to process (default: unlimited, -1)')
    parser.add_argument('--batch-size', type=int, default=20,
                       help='Number of notes to process in each batch (default: 20)')
    parser.add_argument('--ignore-errors', action='store_true', 
                       help='Continue processing even if schema validation fails (default: exit on first error)')
    parser.add_argument('--no-image-import', action='store_true',
                       help='Skip uploading images (only record filenames in target)')
    
    args = parser.parse_args()
    
    main(args.source_path, args.target_config, args.max_batches, args.ignore_errors, args.no_image_import, args.batch_size)
