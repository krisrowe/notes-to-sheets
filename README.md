# notes-to-sheets
Facilitates importing of notes from tools like Google Keep and Evernote into Google Sheets.

# Google Keep Importer

This script automates importing your Google Keep notes from a Google Takeout export stored in Google Cloud Storage (GCS) into a Google Sheet. It handles associated images by saving them to a dedicated folder in your Google Drive and linking to them from the sheet. This creates a clean, organized, and AppSheet-friendly representation of your notes.

## Prerequisites

* A Google Takeout export of your Google Keep data, unzipped and uploaded to a Google Cloud Storage bucket.
* A Debian-based Linux distribution (e.g., Debian, Ubuntu, Mint).
* Familiarity with the command line.

## Setup on Debian

First, ensure your system is up-to-date and has Python installed. Then, create and activate a virtual environment for the project.

```bash
# Update system and install Python tools
sudo apt update && sudo apt upgrade
sudo apt install python3 python3-pip python3-venv

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

Enable the following APIs in the "APIs & Services" > "Library" section of your project:

* **Google Drive API**
* **Google Sheets API**
* **Cloud Storage API**

### 3. Create a Service Account

A service account is needed for the script to make authorized API calls.

1.  Navigate to "APIs & Services" > "Credentials".
2.  Click "Create Credentials" and select "Service account."
3.  Name the account and grant it the following roles:
    * **Editor** (for creating Sheets and Drive folders)
    * **Storage Object Viewer** (for reading from GCS)
4.  From the "Keys" tab, create and download a new JSON key. **Keep this file secure.**

## Project Setup

### 1. Place Script in Project Directory

Save the Python script as `keep.py` inside your `note-importers` directory.

### 2. Create `requirements.txt`

Create a file named `requirements.txt` in your project directory and add the following lines. This file lists all the Python libraries the script needs.

```
google-api-python-client
google-auth-httplib2
google-auth-oauthlib
gspread
google-auth
google-cloud-storage
```

### 3. Install Dependencies

With your virtual environment active, install the necessary libraries:

```bash
pip install -r requirements.txt
```

### 4. Configure the Service Account

Rename your downloaded JSON key to `service_account.json` and place it in the project's root directory. To keep your credentials out of version control, create a `.gitignore` file with the following content:

```
# Ignore credentials and cache
service_account.json
__pycache__/
venv/
```

## Running the Script

1.  **Create and Share a Parent Folder in Google Drive**:
    * In your personal Google Drive, create a new folder (e.g., "Note Imports").
    * Open the folder and copy the **folder ID** from the URL in your browser's address bar. It's the long string of characters at the end.
    * Right-click the folder, click "Share," and paste the `client_email` from your `service_account.json` file into the sharing dialog.
    * Grant the service account **Editor** permissions.

2.  **Upload Takeout Files**: Unzip your Google Keep Takeout file and upload all its contents (all `.json` and image files) to your GCS bucket.

3.  **Configure Script**: Open `keep.py` and update the following variables:
    * `PARENT_DRIVE_FOLDER_ID`: Paste the folder ID you copied in step 1.
    * `GCS_BUCKET_NAME`: Enter the name of your GCS bucket.

4.  **Execute**: Run the script from your terminal:

```bash
python keep.py
```

The script will now create the Google Sheet and the "Google Keep Images" folder inside the specific parent folder you shared with it.

## AppSheet Integration (Optional)

The generated Google Sheet is structured for easy integration with AppSheet, allowing you to create a mobile app from your notes.
