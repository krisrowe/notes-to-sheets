# keep.py

import os
import json
import gspread
import mimetypes
from google.cloud import storage
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- Configuration ---
# The ID of the Google Drive folder where you want to store the sheet and images.
# Find this in the URL of the folder (e.g., .../drive/folders/THIS_IS_THE_ID)
PARENT_DRIVE_FOLDER_ID = 'your-parent-folder-id-here'

# The name of your Google Cloud Storage bucket containing the Keep Takeout files.
GCS_BUCKET_NAME = 'your-gcs-bucket-name'

# The name of the Google Sheet to create.
SHEET_NAME = 'Google Keep Notes Import'

# The name of the main folder to create in Google Drive for images.
DRIVE_FOLDER_NAME = 'Google Keep Images'

# The path to your service account key file.
SERVICE_ACCOUNT_FILE = 'service_account.json'

# The scopes required for the APIs.
SCOPES = [
    'https://www.googleapis.com/auth/devstorage.read_only',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]

def main():
    """
    Main function to run the export process from GCS Takeout to Sheets.
    """
    print("Starting Google Keep Takeout import from GCS...")

    # Authenticate and create API clients.
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    storage_client = storage.Client(credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    gspread_client = gspread.authorize(creds)

    # Get the GCS bucket
    try:
        bucket = storage_client.get_bucket(GCS_BUCKET_NAME)
    except Exception as e:
        print(f"Error accessing GCS bucket '{GCS_BUCKET_NAME}': {e}")
        print("Please ensure the bucket exists and the service account has 'Storage Object Viewer' role.")
        return

    # Create the main folder for images inside the specified parent folder.
    drive_folder_id = create_drive_folder(drive_service, DRIVE_FOLDER_NAME, parent_id=PARENT_DRIVE_FOLDER_ID)
    if not drive_folder_id:
        print(f"Could not create the main Google Drive folder inside parent '{PARENT_DRIVE_FOLDER_ID}'. Aborting.")
        return
    print(f"Created Google Drive folder: '{DRIVE_FOLDER_NAME}'")

    # Create the Google Sheet and move it into the parent folder.
    spreadsheet = gspread_client.create(SHEET_NAME)
    worksheet = spreadsheet.sheet1
    worksheet.append_row(['Title', 'Text', 'Image Folder Link', 'Labels'])
    
    # Move the newly created spreadsheet to the specified parent folder
    try:
        file = drive_service.files().get(fileId=spreadsheet.id, fields='parents').execute()
        previous_parents = ",".join(file.get('parents'))
        drive_service.files().update(
            fileId=spreadsheet.id,
            addParents=PARENT_DRIVE_FOLDER_ID,
            removeParents=previous_parents,
            fields='id, parents'
        ).execute()
        print(f"Created and moved Google Sheet '{SHEET_NAME}' to the specified parent folder.")
    except Exception as e:
        print(f"Warning: Could not move the sheet to the parent folder. It will be in your Drive's root. Error: {e}")


    # Get all files from the GCS bucket.
    print(f"Fetching files from GCS bucket '{GCS_BUCKET_NAME}'...")
    blobs = storage_client.list_blobs(GCS_BUCKET_NAME)
    
    blob_map = {blob.name: blob for blob in blobs}
    json_files = [blob for name, blob in blob_map.items() if name.endswith('.json')]

    if not json_files:
        print("No .json files found in the bucket.")
        return

    print(f"Found {len(json_files)} JSON note files.")

    # Process each JSON file.
    for blob in json_files:
        print(f"\nProcessing note: {blob.name}")
        try:
            note_data = json.loads(blob.download_as_text())
        except Exception as e:
            print(f"  - Could not parse JSON file {blob.name}. Skipping. Error: {e}")
            continue

        title = note_data.get('title', '')
        text_content = note_data.get('textContent', '')
        attachments = note_data.get('attachments', [])
        labels = ", ".join([label['name'] for label in note_data.get('labels', [])])
        image_folder_link = ''

        if attachments:
            sanitized_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
            note_folder_name = sanitized_title if sanitized_title else f"Note_{os.path.splitext(os.path.basename(blob.name))[0]}"
            
            note_drive_folder_id = create_drive_folder(drive_service, note_folder_name, parent_id=drive_folder_id)

            if note_drive_folder_id:
                image_folder_link = f"https://drive.google.com/drive/folders/{note_drive_folder_id}"
                print(f"  - Created Drive subfolder: '{note_folder_name}'")

                for attachment in attachments:
                    image_path_in_gcs = attachment.get('filePath')
                    if not image_path_in_gcs:
                        continue

                    image_blob = blob_map.get(image_path_in_gcs)
                    if not image_blob:
                        print(f"    - Image not found in GCS: {image_path_in_gcs}")
                        continue
                    
                    local_temp_path = os.path.basename(image_path_in_gcs)
                    try:
                        image_blob.download_to_filename(local_temp_path)
                        print(f"    - Downloaded {image_path_in_gcs} from GCS.")
                        
                        upload_file_to_drive(drive_service, local_temp_path, note_drive_folder_id)
                        print(f"    - Uploaded {local_temp_path} to Drive.")

                    except Exception as e:
                        print(f"    - Error processing attachment {image_path_in_gcs}: {e}")
                    finally:
                        if os.path.exists(local_temp_path):
                            os.remove(local_temp_path)

        worksheet.append_row([title, text_content, image_folder_link, labels])
        print(f"  - Added note to sheet: '{title}'")

    print("\nImport complete!")

def create_drive_folder(drive_service, folder_name, parent_id=None):
    """Creates a folder in Google Drive."""
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
    """Uploads a file to a specific folder in Google Drive."""
    file_metadata = {
        'name': os.path.basename(file_path),
        'parents': [folder_id]
    }
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
    main()
