# notes-to-sheets
Facilitates importing of notes from tools like Google Keep and Evernote into Google Sheets.

# Google Keep Importer

This script automates importing your Google Keep notes from a Google Takeout export stored in Google Cloud Storage (GCS) into a Google Sheet. It handles associated images by saving them to a dedicated folder in your Google Drive and linking to them from the sheet. This creates a clean, organized, and AppSheet-friendly representation of your notes.

**Note:** This script uses your personal Google account for all operations, ensuring you own all created files.

## Prerequisites

* A Google Takeout export of your Google Keep data, unzipped and uploaded to a Google Cloud Storage bucket.
* A Debian-based Linux distribution (e.g., Debian, Ubuntu, Mint).
* A Google account with access to Google Drive, Google Sheets, and Google Cloud Storage.
* Familiarity with the command line.

## Setup on Debian

First, ensure your system is up-to-date and install the required tools. Then, create and activate a virtual environment for the project.

```bash
# Update system and install Python tools
sudo apt update && sudo apt upgrade
sudo apt install python3 python3-pip python3-venv

# Install Google Cloud CLI
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
echo "deb https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
sudo apt update
sudo apt install google-cloud-cli

# Create and activate a virtual environment
mkdir note-importers
cd note-importers
python3 -m venv venv
source venv/bin/activate
```

## Google Cloud Project Setup

### 1. Create a Google Cloud Project

Start by creating a new project in the [Google Cloud Console](https://console.cloud.google.com/).

### 2. Enable APIs

Enable the required APIs using the following gcloud commands:

```bash
# Enable Google Drive API
gcloud services enable drive.googleapis.com

# Enable Google Sheets API
gcloud services enable sheets.googleapis.com

# Enable Cloud Storage API
gcloud services enable storage.googleapis.com
```

### 3. Authenticate with Your Personal Account

The script uses your personal Google account for all operations. Set up authentication:

```bash
# Authenticate with your personal Google account
gcloud auth login

# Set up Application Default Credentials
gcloud auth application-default login

# Set your project as the quota project (replace with your project ID)
gcloud auth application-default set-quota-project your-project-id-here
```

**Important:** Replace `your-project-id-here` with your actual Google Cloud project ID.

### 4. Grant Storage Access

Ensure your personal account has access to the GCS bucket containing your Keep Takeout files:

```bash
# Grant Storage Object Viewer role to your personal account
gsutil iam ch user:your-email@gmail.com:objectViewer gs://your-bucket-name
```

**Important:** Replace `your-email@gmail.com` with your actual email and `your-bucket-name` with your actual bucket name.

## Project Setup

### 1. Clone or Download the Project

Download the project files to your local machine.

### 2. Install Dependencies

The project includes a `requirements.txt` file with all necessary Python libraries. With your virtual environment active, install them with:

```bash
pip install -r requirements.txt
```

## Running the Script

### Option 1: Import from Google Cloud Storage (GCS)

1. **Upload Takeout Files**: Unzip your Google Keep Takeout file and upload all its contents (all `.json` and image files) to your GCS bucket.
2. **Create a Google Drive Folder**: Create a folder in Google Drive where you want the imported notes to be stored.
3. **Get Folder ID**: Copy the folder ID from the Google Drive URL: `https://drive.google.com/drive/folders/FOLDER_ID`
4. **Execute**: Run the script from your terminal with your bucket name and folder ID:

```bash
python keep/importer.py gs://<your-gcs-bucket-name> <google-drive-folder-id> [--max-notes N] [--ignore-errors]
```

### Option 2: Import from Local Directory (Recommended for Large Imports)

For better performance with large imports, you can copy your files from GCS to a local directory first:

1. **Copy Files from GCS to Local**:
```bash
# Create a local directory for your files
mkdir keep-notes-takeout

# Copy all files from GCS to local directory
gsutil -m cp gs://your-bucket-name/* keep-notes-takeout/
```

2. **Import from Local Directory**:
```bash
python keep/importer.py keep-notes-takeout <google-drive-folder-id> [--max-notes N] [--ignore-errors]
```

**Performance Note**: Local file access is significantly faster than GCS for large imports, as it eliminates network latency for each file read operation.

### Performance Comparison

The script includes detailed timing statistics to help you understand performance characteristics:

- **GCS operations**: Time spent reading files from Google Cloud Storage
- **Google Sheets operations**: Time spent writing data to Google Sheets
- **Google Drive operations**: Time spent uploading images to Google Drive
- **Note processing**: Time spent processing and transforming note data

For large imports (1000+ notes), local file access typically provides 3-5x faster processing times compared to GCS, primarily due to reduced network latency for file reading operations.

**Additional Performance Optimization**: Using the `--no-image-import` flag can provide an additional 40-50% speed improvement by eliminating Google Drive upload overhead, making it ideal for metadata-only imports or performance testing.


**Examples:**

**GCS Import:**
```bash
# Import all notes from GCS (exits on first schema validation error)
python keep/importer.py gs://your-bucket-name your-folder-id

# Import only first 10 notes from GCS (for trial runs)
python keep/importer.py gs://your-bucket-name your-folder-id --max-notes 10

# Import from GCS with error tolerance (continues on schema validation errors)
python keep/importer.py gs://your-bucket-name your-folder-id --ignore-errors

# Import without uploading images (faster, metadata only)
python keep/importer.py gs://your-bucket-name your-folder-id --no-image-import
```

**Local Directory Import:**
```bash
# Import all notes from local directory
python keep/importer.py ../keep-notes-takeout your-folder-id

# Import only first 10 notes from local directory (for trial runs)
python keep/importer.py ../keep-notes-takeout your-folder-id --max-notes 10

# Import from local directory with error tolerance
python keep/importer.py ../keep-notes-takeout your-folder-id --ignore-errors

# Import without uploading images (faster, metadata only)
python keep/importer.py ../keep-notes-takeout your-folder-id --no-image-import

# Import with custom batch size for better performance
python keep/importer.py ../keep-notes-takeout your-folder-id --batch-size 50
```

**Where to find these values:**

**GCS Bucket:** From your GCS bucket URL
- GCS URL: `gs://my-keep-notes-bucket-2024/`
- Use in command: `gs://my-keep-notes-bucket-2024`

**Local Directory:** Path to directory containing JSON files
- Absolute path: `/home/user/keep-notes-takeout`
- Relative path: `../keep-notes-takeout`

**Folder ID:** From your Google Drive folder URL
- Drive URL: `https://drive.google.com/drive/folders/1ABC123DEF456GHI789JKL012MNO345PQR678STU901VWX`
- Folder ID: `1ABC123DEF456GHI789JKL012MNO345PQR678STU901VWX`

**Example with fake values:**
```bash
# GCS import using bucket "my-keep-notes-bucket-2024" and folder "1ABC123DEF456GHI789JKL012MNO345PQR678STU901VWX"
python keep/importer.py gs://my-keep-notes-bucket-2024 1ABC123DEF456GHI789JKL012MNO345PQR678STU901VWX

# Local import using directory "../keep-notes-takeout" and folder "1ABC123DEF456GHI789JKL012MNO345PQR678STU901VWX"
python keep/importer.py ../keep-notes-takeout 1ABC123DEF456GHI789JKL012MNO345PQR678STU901VWX
```

### Command-Line Options

The importer supports several optional flags to customize the import process:

- **`--max-notes N`**: Limit import to the first N successfully imported notes (useful for testing)
- **`--ignore-errors`**: Continue processing even if schema validation fails (skips problematic notes)
- **`--no-image-import`**: Skip uploading images to Google Drive (only record filenames in sheet)
- **`--batch-size N`**: Number of notes to process in each batch (default: 20, higher values for better performance)

**Performance Note**: Using `--no-image-import` can significantly speed up imports by eliminating Google Drive upload overhead, especially useful for large imports or when you only need the note metadata. The batching system reduces API calls by ~95% compared to individual row uploads.

**Batching**: The importer uses batch processing to improve performance. Notes are processed in batches (default: 20) and uploaded to Google Sheets in chunks, reducing API rate limiting issues. Use `--batch-size` to adjust the batch size for your needs.

**Resilient & Repeatable**: The script is designed to be safely re-run multiple times. It detects existing notes and attachments, skipping complete duplicates while adding missing attachments to incomplete notes. This handles cases where previous runs may have partially failed (e.g., notes written but attachments failed due to API limits).

The script will:
- Create a "Keep Notes Import" folder inside your specified Drive folder
- Create a Google Sheet named "Google Keep Notes" with two tabs:
  - **Notes tab**: ID, Title, Text, Labels, Created Date, Modified Date
  - **Attachment tab**: ID, Note ID, File, Type, Title
- Create a "Note_Images" folder containing all images with their original filenames (unless `--no-image-import` is used)
- Generate AppSheet-style IDs for both notes and attachments
- Import all notes from your source with their metadata and images
- Handle both image attachments and web links
- Skip trashed notes and handle archived notes appropriately
- Reuse existing folders and sheets (won't create duplicates)
- Sync images efficiently at the end of processing

### ⚠️ Data Destruction (Use with Extreme Caution)

If you need to start fresh or clean up after testing, use the dedicated destruction script:

```bash
python keep/wipe.py <google-drive-folder-id>
```

**Example:**
```bash
# Using folder "1ABC123DEF456GHI789JKL012MNO345PQR678STU901VWX"
python keep/wipe.py 1ABC123DEF456GHI789JKL012MNO345PQR678STU901VWX
```

**⚠️ WARNING: This script will PERMANENTLY DELETE:**
- All imported Google Keep notes
- All uploaded images  
- The entire "Keep Notes Import" folder structure
- The "Google Keep Notes" spreadsheet

**⚠️ SAFETY FEATURES:**
- Requires multiple confirmation prompts with specific phrases
- Only affects imported data, not your original Google Keep notes
- Provides clear warnings about the irreversible nature of the operation

**⚠️ IMPORTANT:** This operation is IRREVERSIBLE. Make sure you have backups if you need the imported data.

## Error Handling & Resilience

The importer includes JSON schema validation to ensure data integrity. By default, the script will **exit immediately** if any note fails schema validation to prevent data corruption.

### Repeatable & Safe Re-runs

The script is designed to be safely re-run multiple times without data loss or duplication:

- **Complete duplicates**: Notes with all attachments are skipped entirely
- **Incomplete notes**: Notes missing attachments have their attachments added
- **New notes**: Previously unseen notes are imported with all attachments
- **Folder reuse**: Existing import folders and sheets are reused, not recreated

This resilience handles scenarios where previous runs may have partially failed due to:
- API rate limiting during attachment uploads
- Network interruptions
- Temporary service outages
- Manual interruption of the script

The script will automatically detect and complete any partial imports from previous runs.

### Default Behavior (Strict)
```bash
# GCS import
python keep/importer.py gs://your-bucket-name your-folder-id

# Local directory import
python keep/importer.py your-local-directory your-folder-id
```
- Exits on first schema validation error
- Ensures data quality and consistency
- Recommended for production use

### Error Tolerant Mode
```bash
# GCS import with error tolerance
python keep/importer.py gs://your-bucket-name your-folder-id --ignore-errors

# Local directory import with error tolerance
python keep/importer.py your-local-directory your-folder-id --ignore-errors
```
- Continues processing even if some notes fail validation
- Skips problematic notes and continues with valid ones
- Useful for testing or when you know some notes have non-standard structure

## AppSheet Integration (Optional)

The generated Google Sheet is structured for easy integration with AppSheet, allowing you to create a mobile app from your notes.

## Testing

The project includes a comprehensive test suite to ensure reliability and catch regressions.

### Running Tests

```bash
# Run all tests (recommended) - 50 tests total
cd keep && python -m pytest tests/ -v

# Run specific test files
cd keep && python -m pytest tests/test_note_processing.py -v
cd keep && python -m pytest tests/test_sample_processing.py -v
cd keep && python -m pytest tests/test_schema_validation.py -v
cd keep && python -m pytest tests/test_label_processing.py -v
cd keep && python -m pytest tests/test_utils.py -v
cd keep && python -m pytest tests/test_sample_files.py -v

# Run specific test classes or methods
cd keep && python -m pytest tests/test_note_processing.py::TestNoteProcessing::test_basic_note_processing -v
```

### Test Structure

Tests are organized in the `keep/tests/` directory and follow pytest conventions:

- `keep/tests/test_note_processing.py` - Unit tests for the note processing module (23 tests)
- `keep/tests/test_sample_processing.py` - Integration tests using actual sample JSON files (8 tests)
- `keep/tests/test_schema_validation.py` - JSON schema validation tests (14 tests)
- `keep/tests/test_label_processing.py` - Label processing logic tests (5 tests)
- `keep/tests/test_utils.py` - Utility function tests (8 tests)
- `keep/tests/test_sample_files.py` - Sample file structure validation tests (13 tests)

All test files use the `test_` prefix and are automatically discovered by pytest.

### Test Coverage

The test suite includes **73 tests** organized into the following categories:

**ProcessedNote Class (3 tests):**
- Object creation and attribute validation
- Dictionary conversion for sheet output
- Equality comparison

**Note Processing Logic (20 tests):**
- Basic note processing with default configuration
- HTML vs plain text content selection
- Status label processing (Trashed, Pinned, Archived)
- Custom label name configuration
- Color label processing (enabled/disabled)
- Sharing label processing (Received, Shared)
- Skip logic for trashed/archived notes
- Attachment counting and processing (single, multiple, missing field)
- Checklist formatting with checkboxes
- Timestamp processing and formatting
- Existing labels processing
- Color labels processing (RED)
- Missing attachments field

**Sample File Integration (8 tests):**
- End-to-end processing using actual sample JSON files
- Configuration option validation with real data
- HTML content processing with sample files
- Skip logic validation with sample files

**Schema Validation (14 tests):**
- JSON schema loading and validation
- Sample file validation against schema (all sample files)
- Standalone validation function testing

**Label Processing (5 tests):**
- Basic label extraction and processing
- Status label conversion (trashed, pinned, archived)
- Color label handling
- Combined label processing

**Utility Functions (8 tests):**
- ID generation consistency and uniqueness
- Checklist formatting with checkboxes
- Empty data handling
- HTML content processing

**Sample File Structure (13 tests):**
- Sample file structure validation
- Expected field presence and types
- Shared note structure validation (owned vs received)
- Trashed and archived note structure validation
- Color variation (RED)
- Multiple attachments structure
- Missing attachments field
- Minimal note structure (required fields only)
- Missing timestamps structure

The testing framework validates the entire processing pipeline from raw JSON to the canonical `ProcessedNote` representation that gets written to the output sheet.

### Sample Files

The `keep/samples/` directory contains static JSON files used for testing various scenarios including notes with attachments, web links, checklists, different colors, sharing status, and various field combinations. These files ensure consistent, reliable testing without dynamic JSON construction in tests.

The sample files accurately reflect real Google Keep note structure - for example, notes without attachments (like the original `links.json` and `tasks.json`) don't include an `attachments` field at all, rather than having an empty array.

## Limitations

Only attachments of type image and annotations of type web link, Google Sheets link, Google Docs link, or Gmail link are supported at this time. If the script encounters unsupported content, it will exit with an error message showing details about the problematic file or annotation.

**Note:** The script imports only the plain text content of notes (`textContent`) and does not import the HTML version (`textContentHtml`). This ensures cleaner, more readable content in the Google Sheet without HTML markup.

**Note:** Shared notes are imported with labels to indicate sharing status:
- `Received` - Notes shared with you by others
- `Shared` - Notes you own and shared with others
- The specific sharing information (who the note is shared with) is not preserved in the export.

## Configuration

The script uses `keep/config.yaml` for customizable settings. Each note attribute can be configured with one of four processing actions:

### Processing Actions

- **`label`**: Capture the attribute value as a label (e.g., add "Trashed" label for trashed notes)
- **`error`**: Exit immediately if the attribute is present (ensures data quality)
- **`skip`**: Skip importing notes with this attribute (with console output and summary)
- **`ignore`**: Process the note normally, ignoring this attribute (with logging for HTML)

### Configurable Attributes

**Color Processing** (`processing.color`):
- `label`: Add color name as label (e.g., "RED", "BLUE")
- `error`: Exit if note has non-DEFAULT color
- `skip`: Skip notes with non-DEFAULT colors
- `ignore`: Process note normally, don't add color labels

**Trashed Notes** (`processing.trashed`):
- `label`: Add "Trashed" label to trashed notes
- `error`: Exit if note is trashed
- `skip`: Skip trashed notes entirely
- `ignore`: Process trashed notes normally, don't add "Trashed" label

**Archived Notes** (`processing.archived`):
- `label`: Add "Archived" label to archived notes
- `error`: Exit if note is archived
- `skip`: Skip archived notes entirely
- `ignore`: Process archived notes normally, don't add "Archived" label

**Pinned Notes** (`processing.pinned`):
- `label`: Add "Pinned" label to pinned notes
- `error`: Exit if note is pinned
- `skip`: Skip pinned notes entirely
- `ignore`: Process pinned notes normally, don't add "Pinned" label

**HTML Content** (`processing.html_content`):
- `label`: Use `textContentHtml` and add "HTML" label
- `error`: Exit if note has HTML content
- `skip`: Skip notes with HTML content
- `ignore`: Use `textContent` instead, log the conversion

**Sharing** (`processing.shared`):
- `label`: Add "Shared"/"Received" labels based on sharing status
- `error`: Exit if note is shared
- `skip`: Skip shared notes entirely
- `ignore`: Process shared notes normally, don't add sharing labels

### Label Customization
You can customize the label names used when `label` action is selected:

```yaml
labels:
  trashed: "Trashed"      # Change to "Deleted" if you prefer
  pinned: "Pinned"        # Change to "Important" if you prefer
  archived: "Archived"    # Change to "Stored" if you prefer
  shared: "Shared"        # Change to "Shared Out" if you prefer
  received: "Received"    # Change to "Shared With Me" if you prefer
```

### Example Use Cases

**Data Migration (Strict)**: Use `error` for critical issues
```yaml
processing:
  trashed: "error"        # Ensure no trashed notes in clean data
  archived: "error"       # Ensure no archived notes in clean data
```

**Data Cleaning**: Use `ignore` to remove unwanted attributes
```yaml
processing:
  pinned: "ignore"        # Don't track pinned status
  color: "ignore"         # Don't track colors
```

**Selective Import**: Use `skip` to filter out certain note types
```yaml
processing:
  trashed: "skip"         # Skip trashed notes
  archived: "skip"        # Skip archived notes
  html_content: "skip"    # Skip notes with HTML content
```

**Note**: If the config file is missing or invalid, the script will use default settings.

## Troubleshooting

### Authentication Issues
If you encounter authentication errors:
1. Ensure you're logged in with `gcloud auth login`
2. Set up Application Default Credentials with `gcloud auth application-default login`
3. Verify your project is set as the quota project

### Permission Issues
If you get permission errors:
1. Ensure your personal account has the necessary roles on the GCS bucket
2. Verify you have access to the Google Drive folder you're trying to use
3. Check that all required APIs are enabled in your Google Cloud project

### Content Type Errors
If you get errors about unsupported content:
1. The script will show which note contains the problematic content
2. You may need to manually review and clean your Google Keep data
3. Consider removing unsupported content before running the import



