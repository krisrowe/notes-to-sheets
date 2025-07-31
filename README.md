# notes-to-sheets
Facilitates importing of notes from tools like Google Keep and Evernote into Google Sheets

# Google Keep

This script exports your Google Keep notes to a Google Sheet. It saves associated images to a corresponding Google Drive folder and links them in the sheet, creating an organized, AppSheet-friendly backup.

**Disclaimer:** This script uses the enterprise-only Google Keep API and requires a Google Workspace account with a service account configured for domain-wide delegation.

## Prerequisites

* A Google Workspace account.
* A Debian-based Linux distribution (e.g., Debian, Ubuntu, Mint).
* Familiarity with the command line.

## Setup on Debian

First, ensure your system is up-to-date and has Python installed. Then, create and activate a virtual environment for the project.

```bash
# Update system and install Python tools
sudo apt update && sudo apt upgrade
sudo apt install python3 python3-pip python3-venv

# Create and activate a virtual environment
mkdir google-keep-exporter
cd google-keep-exporter
python3 -m venv venv
source venv/bin/activate
```

## Google Cloud Project Setup

### 1. Create a Google Cloud Project

Start by creating a new project in the [Google Cloud Console](https://console.cloud.google.com/).

### 2. Enable APIs

Enable the **Google Drive API**, **Google Sheets API**, and **Google Keep API** in the "APIs & Services" > "Library" section of your project.

### 3. Create a Service Account

A service account is needed for the script to make authorized API calls.

1. Navigate to "APIs & Services" > "Credentials".
2. Click "Create Credentials" and select "Service account."
3. Name the account and grant it the "Editor" role.
4. From the "Keys" tab, create and download a new JSON key. **Keep this file secure.**

### 4. Grant Domain-Wide Delegation

The Keep API requires you to grant domain-wide delegation to the service account.

1. From the service account's details in the Cloud Console, copy its "Client ID."
2. Go to your Google Workspace Admin console.
3. Navigate to "Security" > "Access and data control" > "API controls."
4. Under "Domain-wide Delegation," add a new client using the copied ID.
5. Authorize the following OAuth scopes:
   * `https://www.googleapis.com/auth/keep`
   * `https://www.googleapis.com/auth/drive`
   * `https://www.googleapis.com/auth/spreadsheets`

## Project Setup

### 1. Clone the Repository

Clone this repository or create a new directory and place the script inside.

### 2. Create `requirements.txt`
Create a file named `requirements.txt` in your project directory and add the following lines. This file lists all the Python libraries the script needs.

```
google-api-python-client
google-auth-httplib2
google-auth-oauthlib
gspread
google-auth
```

### 3. Install Dependencies

With your virtual environment active, install the necessary libraries using the file you just created:

```bash
pip install -r requirements.txt
```

### 4. Configure the Service Account

Rename your downloaded JSON key to `service_account.json` and place it in the project's root directory. To keep your credentials out of version control, create a `.gitignore` file with the following content:

```
# Ignore credentials and cache
service_account.json
__pycache__/
```

## Running the Script

Execute the `main.py` file to begin the export:

```bash
python main.py
```

The script will authenticate, create a "Google Keep Notes" sheet and a "Google Keep Images" Drive folder, and then populate them with your notes and linked images.

## AppSheet Integration (Optional)

The generated Google Sheet is structured for easy integration with AppSheet, allowing you to create a mobile app from your notes.

