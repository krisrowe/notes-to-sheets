#!/usr/bin/env python3
"""
DESTROY IMPORTED DATA - DANGEROUS OPERATION

This script will PERMANENTLY DELETE all data created by the Google Keep importer:
- "Keep Notes Import" folder and ALL its contents
- "Google Keep Notes" spreadsheet
- "Note_Images" folder and ALL uploaded images

⚠️  WARNING: This operation is IRREVERSIBLE and will delete ALL imported notes and images.
⚠️  WARNING: This will NOT affect your original Google Keep data, only the imported copies.
⚠️  WARNING: Make sure you have backups if you need the imported data.

Usage:
    python keep/wipe.py <google-drive-folder-id> [--wipe hard]
    
    --wipe hard: Delete the entire sheet and folder (default behavior)
    --wipe soft: Clear only the tabs, keeping the sheet for revision history

Example:
    python keep/wipe.py 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms --wipe soft
"""

import os
import sys
import argparse
from googleapiclient.discovery import build
from google.auth import default


def clear_sheet_tabs(drive_service, sheets_service, drive_folder_id):
    """
    Clear the tabs in the Google Keep Notes spreadsheet without deleting the sheet.
    This preserves the sheet for revision history.
    """
    print("🧹 CLEARING SHEET TABS - PRESERVING SHEET FOR REVISION HISTORY")
    print("=" * 60)
    
    try:
        # Find the "Keep Notes Import" folder
        query = f"'{drive_folder_id}' in parents and name='Keep Notes Import' and mimeType='application/vnd.google-apps.folder'"
        results = drive_service.files().list(q=query, fields="files(id,name)").execute()
        keep_import_folders = results.get('files', [])
        
        if not keep_import_folders:
            print("❌ No 'Keep Notes Import' folder found")
            return
        
        keep_import_folder_id = keep_import_folders[0]['id']
        print(f"🗂️  Found 'Keep Notes Import' folder (ID: {keep_import_folder_id})")
        
        # Find the "Google Keep Notes" spreadsheet
        query = f"'{keep_import_folder_id}' in parents and name='Google Keep Notes' and mimeType='application/vnd.google-apps.spreadsheet'"
        results = drive_service.files().list(q=query, fields="files(id,name)").execute()
        spreadsheets = results.get('files', [])
        
        if not spreadsheets:
            print("❌ No 'Google Keep Notes' spreadsheet found")
            return
        
        spreadsheet_id = spreadsheets[0]['id']
        print(f"📊 Found 'Google Keep Notes' spreadsheet (ID: {spreadsheet_id})")
        
        # Get the spreadsheet to see what tabs exist
        spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = spreadsheet.get('sheets', [])
        
        print(f"📋 Found {len(sheets)} tabs to clear:")
        
        # Clear each tab by replacing all content with just the header row
        for sheet in sheets:
            sheet_name = sheet['properties']['title']
            sheet_id = sheet['properties']['sheetId']
            print(f"    - {sheet_name}")
            
            # Determine headers based on sheet name
            if sheet_name == 'Notes':
                headers = [['ID', 'Title', 'Content', 'Created Date', 'Modified Date', 'Labels']]
            elif sheet_name == 'Attachments':
                headers = [['ID', 'Note', 'File', 'Type', 'Title']]
            else:
                headers = [['Data']]  # Generic header for unknown sheets
            
            # Clear the sheet by replacing all content with headers
            try:
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
                
                print(f"      ✅ Cleared {sheet_name}")
            except Exception as e:
                print(f"      ❌ Failed to clear {sheet_name}: {e}")
        
        # Delete the Note_Images folder if it exists
        query = f"'{keep_import_folder_id}' in parents and name='Note_Images' and mimeType='application/vnd.google-apps.folder'"
        results = drive_service.files().list(q=query, fields="files(id,name)").execute()
        image_folders = results.get('files', [])
        
        if image_folders:
            image_folder_id = image_folders[0]['id']
            print(f"🖼️  Found 'Note_Images' folder (ID: {image_folder_id})")
            
            # Get all files in the images folder
            query = f"'{image_folder_id}' in parents"
            results = drive_service.files().list(q=query, fields="files(id,name)").execute()
            image_files = results.get('files', [])
            
            print(f"💥 Found {len(image_files)} image files to delete:")
            
            for file_info in image_files:
                file_id = file_info['id']
                file_name = file_info['name']
                print(f"    - {file_name}")
                
                try:
                    drive_service.files().delete(fileId=file_id).execute()
                    print(f"      ✅ Deleted {file_name}")
                except Exception as e:
                    print(f"      ❌ Failed to delete {file_name}: {e}")
            
            # Delete the images folder itself
            try:
                drive_service.files().delete(fileId=image_folder_id).execute()
                print(f"🖼️  ✅ Deleted 'Note_Images' folder")
            except Exception as e:
                print(f"🖼️  ❌ Failed to delete 'Note_Images' folder: {e}")
        else:
            print("🖼️  No 'Note_Images' folder found")
            
        print("=" * 60)
        print(f"🧹 CLEARING COMPLETE: Sheet tabs cleared, images deleted")
        print("📊 Sheet preserved for revision history")
        
    except Exception as e:
        print(f"💥 ERROR during clearing: {e}")


def destroy_imported_resources(drive_service, drive_folder_id):
    """
    Destroy all resources created by the Google Keep importer.
    """
    print("🔥 DESTROYING IMPORTED DATA - IRREVERSIBLE OPERATION")
    print("=" * 60)
    
    try:
        # Find the "Keep Notes Import" folder
        query = f"'{drive_folder_id}' in parents and name='Keep Notes Import' and mimeType='application/vnd.google-apps.folder'"
        results = drive_service.files().list(q=query, fields="files(id,name)").execute()
        keep_import_folders = results.get('files', [])
        
        if not keep_import_folders:
            print("❌ No 'Keep Notes Import' folder found to destroy")
            return
        
        keep_import_folder_id = keep_import_folders[0]['id']
        print(f"🗂️  Found 'Keep Notes Import' folder (ID: {keep_import_folder_id})")
        
        # Find all files and folders within the Keep Notes Import folder
        query = f"'{keep_import_folder_id}' in parents"
        results = drive_service.files().list(q=query, fields="files(id,name,mimeType)").execute()
        files_to_destroy = results.get('files', [])
        
        print(f"💥 Found {len(files_to_destroy)} items to DESTROY:")
        
        destroyed_count = 0
        for file_info in files_to_destroy:
            file_id = file_info['id']
            file_name = file_info['name']
            file_type = "folder" if file_info['mimeType'] == 'application/vnd.google-apps.folder' else "file"
            print(f"    - {file_name} ({file_type})")
            
            try:
                drive_service.files().delete(fileId=file_id).execute()
                print(f"      ✅ DESTROYED {file_name}")
                destroyed_count += 1
            except Exception as e:
                print(f"      ❌ Failed to destroy {file_name}: {e}")
        
        # Destroy the Keep Notes Import folder itself
        try:
            drive_service.files().delete(fileId=keep_import_folder_id).execute()
            print(f"🗂️  ✅ DESTROYED 'Keep Notes Import' folder")
            destroyed_count += 1
        except Exception as e:
            print(f"🗂️  ❌ Failed to destroy 'Keep Notes Import' folder: {e}")
            
        print("=" * 60)
        print(f"💀 DESTRUCTION COMPLETE: {destroyed_count} items destroyed")
        print("⚠️  All imported Google Keep data has been PERMANENTLY DELETED")
        
    except Exception as e:
        print(f"💥 ERROR during destruction: {e}")


def main():
    """Main function with multiple confirmation prompts."""
    parser = argparse.ArgumentParser(
        description='DESTROY all imported Google Keep data - IRREVERSIBLE OPERATION',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
⚠️  WARNING: This will PERMANENTLY DELETE:
  - All imported Google Keep notes
  - All uploaded images
  - The entire "Keep Notes Import" folder structure

⚠️  This operation is IRREVERSIBLE!
⚠️  Make sure you have backups if needed!
        """
    )
    parser.add_argument('drive_folder_id', help='ID of the Google Drive folder containing imported data')
    parser.add_argument('--wipe', choices=['soft', 'hard'], default='hard',
                       help='Wipe mode: soft=clear tabs only (preserves sheet), hard=delete everything (default)')
    
    args = parser.parse_args()
    
    if args.wipe == 'soft':
        print("🧹 SOFT WIPE - CLEAR SHEET TABS ONLY")
        print("=" * 60)
        print("This will clear the tabs in the Google Keep Notes spreadsheet")
        print("and delete the Note_Images folder, but preserve the sheet for revision history.")
        print("")
        print("What will be cleared:")
        print("  - All data in 'Notes' and 'Attachments' tabs")
        print("  - 'Note_Images' folder and ALL uploaded images")
        print("")
        print("What will be preserved:")
        print("  - 'Google Keep Notes' spreadsheet (for revision history)")
        print("  - 'Keep Notes Import' folder structure")
        print("")
    else:
        print("🔥 DESTROY IMPORTED DATA - DANGEROUS OPERATION")
        print("=" * 60)
        print("This script will PERMANENTLY DELETE all data created by the Google Keep importer.")
        print("")
        print("What will be destroyed:")
        print("  - 'Keep Notes Import' folder and ALL its contents")
        print("  - 'Google Keep Notes' spreadsheet")
        print("  - 'Note_Images' folder and ALL uploaded images")
        print("")
        print("⚠️  WARNING: This operation is IRREVERSIBLE!")
        print("⚠️  WARNING: This will NOT affect your original Google Keep data")
        print("⚠️  WARNING: Only imported copies will be deleted")
        print("")
    
    # Single confirmation
    if args.wipe == 'soft':
        response = input("Are you sure you want to clear the sheet tabs? Type 'CLEAR' to continue: ")
        if response != 'CLEAR':
            print("Clearing cancelled. Your data is safe.")
            sys.exit(0)
    else:
        response = input("Are you ABSOLUTELY SURE you want to proceed? Type 'DESTROY' to continue: ")
        if response != 'DESTROY':
            print("Destruction cancelled. Your data is safe.")
            sys.exit(0)
    
    print("")
    if args.wipe == 'soft':
        print("🧹 PROCEEDING WITH CLEARING...")
    else:
        print("💥 PROCEEDING WITH DESTRUCTION...")
    print("=" * 60)
    
    # Authenticate and perform operation
    try:
        creds, _ = default(scopes=['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets'])
        drive_service = build('drive', 'v3', credentials=creds)
        
        if args.wipe == 'soft':
            sheets_service = build('sheets', 'v4', credentials=creds)
            clear_sheet_tabs(drive_service, sheets_service, args.drive_folder_id)
        else:
            destroy_imported_resources(drive_service, args.drive_folder_id)
    except Exception as e:
        print(f"💥 ERROR: Failed to authenticate or access Drive: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main() 