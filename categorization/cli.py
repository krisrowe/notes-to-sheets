#!/usr/bin/env python3
"""
Command-line interface for categorizing notes in Google Sheets using Gemini API.
"""
import argparse
import os
import sys
from typing import Optional

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from categorization.gemini_client import GeminiCategorizer
from categorization.config import CategorizationConfig
from categorization.categorization_service import CategorizationService
from categorization.rules_manager import RulesManager
from categorization.data_sources.google_sheets import GoogleSheetsDataSource
from categorization.data_sources.csv_source import CSVDataSource


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Categorize notes using Gemini AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use Google Sheets (default)
  python -m categorization
  
  # Use CSV files for testing
  python -m categorization --data-source csv
  
  # Process only 5 notes
  python -m categorization --limit 5
  
  # CSV with limit
  python -m categorization --data-source csv --limit 3

Configuration:
  - All settings are in config.yaml (tabs, files, processing)
  - Sensitive data (Sheet ID, API key) in config.ini
  - Rules from file or Label tab in data source
"""
    )
    
    parser.add_argument(
        '--data-source',
        choices=['sheets', 'csv'],
        default='sheets',
        help='Data source type: sheets (Google Sheets) or csv (CSV files for testing)'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit the number of notes to process (overrides config.yaml default)'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = CategorizationConfig()
    
    # Load configuration
    config = CategorizationConfig()
    yaml_config = config.get_yaml_config()
    
    # Get required sensitive data from config.ini
    sheet_id = config.get_sheet_id()
    if not sheet_id and args.data_source == 'sheets':
        print("❌ Error: Google Sheet ID is required for sheets data source.")
        print("   Set it in categorization/config.ini")
        sys.exit(1)
    
    api_key = config.get_gemini_api_key()
    if not api_key:
        print("❌ Error: Gemini API key is required.")
        print("   Set it in categorization/config.ini or GEMINI_API_KEY environment variable.")
        print("   Get your API key from: https://aistudio.google.com/app/apikey")
        sys.exit(1)
    
    # Get configuration from YAML
    if args.data_source == 'csv':
        source_tab = yaml_config.get_csv_source_file()
        output_tab = yaml_config.get_csv_output_file()
    else:
        source_tab = yaml_config.get_sheets_source_tab()
        output_tab = yaml_config.get_sheets_output_tab()
    
    limit = args.limit or yaml_config.get_default_limit()
    dry_run = yaml_config.get_dry_run()
    
    print("🚀 Starting note categorization...")
    print(f"📊 Sheet ID: {sheet_id}")
    print(f"📖 Source tab: {source_tab}")
    print(f"📝 Output tab: {output_tab}")
    print(f"🔍 Dry run: {'Yes' if dry_run else 'No'}")
    if limit:
        print(f"📏 Limit: {limit} notes")
    print()
    
    try:
        # Initialize components
        print("🔧 Initializing components...")
        
        # Create data source based on type
        if args.data_source == 'csv':
            data_source = CSVDataSource(yaml_config)
            print("📊 Using CSV data source for testing")
        else:
            data_source = GoogleSheetsDataSource(sheet_id, yaml_config)
            print(f"📊 Using Google Sheets data source: {sheet_id}")
        
        gemini_categorizer = GeminiCategorizer(api_key)
        rules_manager = RulesManager(data_source)
        categorization_service = CategorizationService(data_source, gemini_categorizer, rules_manager, yaml_config)
        
        # Run categorization
        if dry_run:
            print("🔍 Dry run mode: will not save results")
        
        result = categorization_service.categorize_notes(
            source_table=source_tab,
            output_table=output_tab,
            limit=limit
        )
        
        # Display results summary
        print("📊 Categorization Results Summary:")
        print("-" * 60)
        print(f"Total notes processed: {result['total_notes']}")
        print(f"Successfully categorized: {result['categorized_notes']}")
        print(f"Errors: {result['errors']}")
        print("-" * 60)
        
        # Display individual results
        for res in result['results']:
            print(f"Note ID: {res['note_id']}")
            print(f"Labels:  {res['labels']}")
            print("-" * 40)
        
        if dry_run:
            print("🔍 Dry run completed. No data was written.")
        else:
            print("✅ Categorization completed successfully!")
            if args.data_source == 'sheets':
                print(f"🔗 View results: https://docs.google.com/spreadsheets/d/{sheet_id}")
    
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
