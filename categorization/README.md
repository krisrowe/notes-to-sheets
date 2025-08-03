# Notes Categorization Module

Automatically categorize notes using Google's Gemini AI with smart filtering and batch processing. Supports both **Google Sheets** (production) and **CSV files** (testing).

## ⚡ Quick Start

1. **Setup configuration:**
   ```bash
   # Copy example configs
   cp categorization/config.ini.example categorization/config.ini
   
   # Edit config.ini - add your Sheet ID and Gemini API key
   # Get API key from: https://aistudio.google.com/app/apikey
   ```

2. **Run categorization:**
   ```bash
   # Categorize 20 notes from Google Sheets
   python -m categorization --data-source sheets --limit 20
   
   # Test with CSV files
   python -m categorization --data-source csv --limit 10
   ```

## 🎯 Key Features

- **Smart Filtering**: Only process notes with specific labels (e.g., "AI Vetted")
- **Duplicate Skipping**: Automatically skips already-processed notes
- **Batch Processing**: Process exact number of new notes (duplicates don't count toward limit)
- **Flexible Rules**: Load categorization rules from files or Google Sheets tabs
- **Dual Data Sources**: Google Sheets for production, CSV for testing
- **Configuration-Driven**: Minimal CLI, most settings in config files

## 📋 Configuration

### Required Files

**`config.ini`** (sensitive data - gitignored):
```ini
[categorization]
sheet_id = your-google-sheet-id
gemini_api_key = your-gemini-api-key
```

**`config.yaml`** (storage and processing settings):
```yaml
storage:
  sheets:
    source_tab: "Note"          # Tab with notes
    rules_tab: "Label"          # Tab with categorization rules  
    output_tab: "labeled_notes"  # Tab for results
  csv:
    data_dir: "test_data"
    source_file: "notes"         # notes.csv
    rules_file: "label"          # label.csv
    output_file: "labeled_notes" # labeled_notes.csv

processing:
  default_limit: 10
  dry_run: false
  api_delay: 0.1
  max_retries: 3

filters:
  label: ""  # Filter by existing label (e.g., "AI Vetted")
```

## 🚀 Usage

### Basic Commands

```bash
# Process 20 notes from Google Sheets
python -m categorization --data-source sheets --limit 20

# Process 10 notes from CSV files (testing)
python -m categorization --data-source csv --limit 10

# Use default limit from config.yaml
python -m categorization --data-source sheets
```

### Label Filtering

To only process notes with specific existing labels:

1. Edit `config.yaml`:
   ```yaml
   filters:
     label: "AI Vetted"  # Only process notes with this label
   ```

2. Run categorization:
   ```bash
   python -m categorization --data-source sheets --limit 20
   ```

The system will:
- Skip notes already processed (duplicates)
- Skip notes without the "AI Vetted" label
- Process exactly 20 new notes with that label

## 📊 Data Structure

### Google Sheets Requirements

**Source Tab ("Note"):**
- `id` or `note_id` - Unique identifier
- `title` or `Title` - Note title
- `content` or `Content` - Note content
- `Labels` - Existing labels (for filtering)

**Rules Tab ("Label"):**
- `Name` - Label name
- `Description` - When to use this label
- `Auto` - TRUE/FALSE to include in categorization

**Output Tab ("labeled_notes"):**
- `Note ID` - Note identifier
- `Labels` - AI-generated labels

### CSV Files (for testing)

Place in `categorization/test_data/`:
- `notes.csv` - Source notes
- `label.csv` - Categorization rules (optional)
- `labeled_notes.csv` - Results (created automatically)

### Prerequisites

1. **Google Sheets API access**: Project should already be configured
2. **Gemini API key**: Get from [Google AI Studio](https://aistudio.google.com/app/apikey)
3. **Python dependencies**: `pip install -r requirements.txt`

### Initial Setup

```bash
# 1. Copy example configuration
cp categorization/config.ini.example categorization/config.ini

# 2. Edit config.ini with your credentials:
#    - sheet_id = your-google-sheet-id-from-url
#    - gemini_api_key = your-api-key-from-ai-studio

# 3. Optionally customize config.yaml for:
#    - Tab/file names
#    - Processing limits
#    - Label filtering
```

## 🎛️ Command Line Interface

**The CLI only accepts 2 arguments - everything else is configured in files:**

```bash
python -m categorization --data-source {sheets|csv} [--limit N]
```

**Arguments:**
- `--data-source`: Required. Either `sheets` or `csv`
- `--limit`: Optional. Number of new notes to process (overrides config.yaml default)

**Examples:**
```bash
# Process default number of notes from Google Sheets
python -m categorization --data-source sheets

# Process exactly 50 new notes from Google Sheets
python -m categorization --data-source sheets --limit 50

# Test with CSV files (limit 5)
python -m categorization --data-source csv --limit 5
```

## 🧪 Testing

```bash
# Run unit tests (fast, no API key needed)
python -m pytest categorization/tests/unit/

# Run integration tests (requires API key in config.ini)
python -m pytest categorization/tests/integration/

# Run all tests
python -m pytest categorization/tests/

# Test with CSV data source
python -m categorization --data-source csv --limit 3
```

## 🔧 Troubleshooting

**Common Issues:**

1. **"No API key found"**: Add `gemini_api_key` to `config.ini`
2. **"Sheet not found"**: Check `sheet_id` in `config.ini`
3. **"Tab not found"**: Verify tab names in `config.yaml` match your sheet
4. **"No notes found"**: Check label filter in `config.yaml` or remove it

**Getting Help:**
- Check console output for detailed error messages
- Verify your Google Sheets has the required column names
- Test with CSV data source first: `--data-source csv`

## 📁 File Structure

```
categorization/
├── config.ini              # Your credentials (gitignored)
├── config.ini.example      # Template for config.ini
├── config.yaml             # Storage and processing settings
├── cli.py                  # Main command-line interface
├── test_data/              # CSV files for testing
│   ├── notes.csv          # Sample notes
│   ├── label.csv          # Sample rules
│   └── labeled_notes.csv  # Generated results
└── tests/                  # Test suite
    ├── unit/              # Fast unit tests
    └── integration/       # Real API tests
```

## 🎯 Tips for Success

1. **Start small**: Use `--limit 5` for initial testing
2. **Use label filtering**: Set `filters.label` in `config.yaml` to process specific notes
3. **Test with CSV first**: Validate your setup before using Google Sheets
4. **Monitor duplicates**: System automatically skips already-processed notes
5. **Check your rules**: Rules come from "Label" tab or local files

## 🔄 Batch Processing Workflow

```bash
# 1. Filter notes by existing label (e.g., "AI Vetted")
# Edit config.yaml: filters.label = "AI Vetted"

# 2. Process batch of 20 new notes
python -m categorization --data-source sheets --limit 20

# 3. System will:
#    - Skip notes already processed (duplicates)
#    - Skip notes without "AI Vetted" label  
#    - Process exactly 20 new matching notes
#    - Append results to existing data

# 4. Repeat as needed - duplicates are automatically handled
```

This workflow is perfect for processing large datasets incrementally while avoiding duplicate work.

---

## 🎉 Ready to Get Started?

1. **Copy the config template**: `cp config.ini.example config.ini`
2. **Add your credentials**: Edit `config.ini` with Sheet ID and API key
3. **Run your first batch**: `python -m categorization --data-source sheets --limit 5`
4. **Scale up**: Increase the limit and use label filtering as needed

The system handles duplicates automatically, so you can run it multiple times safely. Perfect for processing large note collections efficiently!

**Need help?** Check the troubleshooting section above or test with CSV data first.
