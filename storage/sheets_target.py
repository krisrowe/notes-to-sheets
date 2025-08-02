import gspread
import time
from google.auth import default
from googleapiclient.discovery import build


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
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return operation()
        except Exception as e:
            last_exception = e
            
            if attempt == max_retries:
                # Final attempt failed, re-raise the exception
                raise last_exception
            
            # Calculate delay with exponential backoff
            delay = min(base_delay * (2 ** attempt), max_delay)
            
            # Add some jitter to avoid thundering herd
            jitter = delay * 0.1 * (2 * (attempt % 2) - 1)  # ±10% jitter
            delay += jitter
            
            print(f"  ⚠️  API call failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
            print(f"  ⏳ Retrying in {delay:.1f} seconds...")
            time.sleep(delay)
    
    # This should never be reached, but just in case
    raise last_exception


class GoogleSheetsTarget:
    """Write to Google Sheets."""
    
    def __init__(self, drive_folder_id, import_folder_name="Notes Import", sheet_name="Notes", images_folder_name="Note_Images"):
        self.drive_folder_id = drive_folder_id
        self.import_folder_name = import_folder_name
        self.sheet_name = sheet_name
        self.images_folder_name = images_folder_name
        self.drive_service = None
        self.gspread_client = None
        self.notes_worksheet = None
        self.attachments_worksheet = None
        self.import_folder_id = None
        self.images_folder_id = None
        self._setup_google_services()
    
    def _setup_google_services(self):
        """Set up Google Drive and Sheets services."""
        creds, _ = default(scopes=[
            'https://www.googleapis.com/auth/drive', 
            'https://www.googleapis.com/auth/spreadsheets'
        ])
        
        self.drive_service = build('drive', 'v3', credentials=creds)
        self.gspread_client = gspread.authorize(creds)
        
        # Set up import folder and sheets
        self.import_folder_id = self._setup_import_folder()
        self.notes_worksheet, self.attachments_worksheet = self._setup_sheets()
        self.images_folder_id = self._setup_images_folder()
    
    def _setup_import_folder(self):
        """Set up the import folder in Google Drive."""
        import_folder_name = self.import_folder_name
        
        # Search for existing import folder
        try:
            query = f"name='{import_folder_name}' and '{self.drive_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.drive_service.files().list(q=query, fields="files(id,name)").execute()
            files = results.get('files', [])
            
            if files:
                folder_id = files[0]['id']
                print(f"Found existing import folder: '{import_folder_name}' (ID: {folder_id})")
                return folder_id
        except Exception as e:
            print(f"Could not check for existing import folder: {e}")
        
        # Create new import folder
        folder_id = self._create_drive_folder(import_folder_name, parent_id=self.drive_folder_id)
        if not folder_id:
            raise Exception("Could not create the import folder")
        print(f"Created new import folder: '{import_folder_name}'")
        return folder_id
    
    def _setup_sheets(self):
        """Set up Google Sheets for notes and attachments."""
        sheet_name = self.sheet_name
        
        # Check for existing sheet
        try:
            query = f"name='{sheet_name}' and '{self.import_folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
            results = self.drive_service.files().list(q=query, fields="files(id,name)").execute()
            files = results.get('files', [])
            
            if files:
                existing_sheet = files[0]
                spreadsheet = self.gspread_client.open_by_key(existing_sheet['id'])
                print(f"Found existing sheet: '{sheet_name}' (ID: {existing_sheet['id']})")
            else:
                spreadsheet = self.gspread_client.create(sheet_name)
                # Move to import folder
                self.drive_service.files().update(
                    fileId=spreadsheet.id,
                    addParents=self.import_folder_id,
                    removeParents='root',
                    fields='id, parents'
                ).execute()
                print(f"Created new sheet: '{sheet_name}'")
        except Exception as e:
            print(f"Could not check for existing sheet: {e}")
            spreadsheet = self.gspread_client.create(sheet_name)
        
        # Set up worksheets
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
        
        return notes_worksheet, attachments_worksheet
    
    def _setup_images_folder(self):
        """Set up the images subfolder in the import folder."""
        images_folder_name = self.images_folder_name
        
        # Search for existing images folder
        try:
            query = f"name='{images_folder_name}' and '{self.import_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.drive_service.files().list(q=query, fields="files(id,name)").execute()
            files = results.get('files', [])
            
            if files:
                folder_id = files[0]['id']
                print(f"Found existing images folder: '{images_folder_name}' (ID: {folder_id})")
                return folder_id
        except Exception as e:
            print(f"Could not check for existing images folder: {e}")
        
        # Create new images folder
        folder_id = self._create_drive_folder(images_folder_name, parent_id=self.import_folder_id)
        if not folder_id:
            raise Exception("Could not create the images folder")
        print(f"Created new images folder: '{images_folder_name}'")
        return folder_id
    
    def _create_drive_folder(self, folder_name, parent_id=None):
        """Create a folder in Google Drive."""
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]

        try:
            folder = self.drive_service.files().create(body=file_metadata, fields='id').execute()
            return folder.get('id')
        except Exception as e:
            print(f"An error occurred while creating folder '{folder_name}': {e}")
            return None
    
    def write_notes_and_attachments(self, notes, attachments):
        """Write notes and attachments to Google Sheets."""
        # Write notes
        if notes:
            notes_data = [
                [
                    note_data['ID'], 
                    note_data['Title'], 
                    note_data['Content'], 
                    note_data['Labels'], 
                    note_data['Created Date'], 
                    note_data['Modified Date']
                ]
                for note_data in notes
            ]
            
            def add_notes_batch():
                self.notes_worksheet.append_rows(notes_data)
            
            exponential_backoff_with_retry(add_notes_batch)
            print(f"  ✅ Added {len(notes)} notes to sheet")
            time.sleep(0.1)  # Small delay to avoid rate limiting
        
        # Write attachments
        if attachments:
            attachments_data = [
                [
                    attachment_data['ID'],
                    attachment_data['Note'],
                    attachment_data['File'],
                    attachment_data['Type'],
                    attachment_data['Title']
                ]
                for attachment_data in attachments
            ]
            
            def add_attachments_batch():
                self.attachments_worksheet.append_rows(attachments_data)
            
            exponential_backoff_with_retry(add_attachments_batch)
            print(f"  ✅ Added {len(attachments)} attachments to sheet")
            time.sleep(0.1)  # Small delay to avoid rate limiting
    
    def save_image(self, image_bytes, filename):
        """Save image to Google Drive."""
        if not image_bytes:
            return False
        
        try:
            from googleapiclient.http import MediaIoBaseUpload
            import io
            import mimetypes
            
            file_metadata = {
                'name': filename,
                'parents': [self.images_folder_id]
            }
            # Guess the MIME type of the file, or default to a generic binary type.
            mimetype, _ = mimetypes.guess_type(filename)
            media = MediaIoBaseUpload(io.BytesIO(image_bytes), mimetype=mimetype or 'application/octet-stream')
            
            def upload_image():
                self.drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
            
            exponential_backoff_with_retry(upload_image)
            print(f"    ✅ Saved image: {filename}")
            return True
        except Exception as e:
            print(f"    ❌ Failed to save image {filename}: {e}")
            return False
    
    def get_existing_images(self):
        """Get set of existing image filenames in the images folder."""
        try:
            def list_images():
                query = f"'{self.images_folder_id}' in parents and trashed=false"
                results = self.drive_service.files().list(q=query, fields="files(name)").execute()
                return results
            
            results = exponential_backoff_with_retry(list_images)
            return {file['name'] for file in results.get('files', [])}
        except Exception as e:
            print(f"❌ Error checking images folder contents: {e}")
            return set() 