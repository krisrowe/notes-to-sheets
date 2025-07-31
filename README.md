# notes-to-sheets
Facilitates importing of notes from tools like Google Keep and Evernote into Google Sheets

# Google Keep

This script exports your Google Keep notes to a Google Sheet. It saves associated images to a corresponding Google Drive folder and links them in the sheet, creating an organized, AppSheet-friendly backup.

**Disclaimer:** This script uses the enterprise-only Google Keep API and requires a Google Workspace account with a service account configured for domain-wide delegation.

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

1.  **Upload Takeout Files**: Unzip your Google Keep Takeout file and upload all its contents (all `.json` and image files) to your GCS bucket.
2.  **Configure Script**: Open `keep.py` and update the `GCS_BUCKET_NAME` variable with the name of your bucket.
3.  **Execute**: Run the script from your terminal:

```bash
python keep.py
```

The script will authenticate, read the notes and images from your GCS bucket, create a "Google Keep Notes" sheet and a "Google Keep Images" Drive folder, and then populate them with your notes and linked images.

## AppSheet Integration (Optional)

The generated Google Sheet is structured for easy integration with AppSheet, allowing you to create a mobile app from your notes.


