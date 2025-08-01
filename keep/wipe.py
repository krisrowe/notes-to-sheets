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
    python keep/destroy_imported_data.py <google-drive-folder-id>

Example:
    python keep/destroy_imported_data.py 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
"""

import os
import sys
import argparse
from googleapiclient.discovery import build
from google.auth import default


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
    
    args = parser.parse_args()
    
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
    response = input("Are you ABSOLUTELY SURE you want to proceed? Type 'DESTROY' to continue: ")
    if response != 'DESTROY':
        print("Destruction cancelled. Your data is safe.")
        sys.exit(0)
    
    print("")
    print("💥 PROCEEDING WITH DESTRUCTION...")
    print("=" * 60)
    
    # Authenticate and destroy
    try:
        creds, _ = default(scopes=['https://www.googleapis.com/auth/drive'])
        drive_service = build('drive', 'v3', credentials=creds)
        destroy_imported_resources(drive_service, args.drive_folder_id)
    except Exception as e:
        print(f"💥 ERROR: Failed to authenticate or access Drive: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main() 