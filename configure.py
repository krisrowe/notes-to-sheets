#!/usr/bin/env python3
"""
Interactive setup script for notes-to-sheets configuration.
Prompts user for required values and creates config.ini.
"""

import os
import configparser
import shutil

def main():
    print("🎯 Notes-to-Sheets Interactive Setup")
    print("=" * 40)
    
    # Check if config.ini already exists
    if os.path.exists('config.ini'):
        proceed = input("⚠️  config.ini already exists. This will overwrite it. Continue? (y/n): ").lower()
        if proceed != 'y':
            print("Setup cancelled.")
            return
    
    # Copy example file
    if os.path.exists('config.ini.example'):
        shutil.copy('config.ini.example', 'config.ini')
        print("✓ Copied config.ini.example to config.ini")
    else:
        print("❌ config.ini.example not found!")
        return
    
    # Load config for editing
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    if not config.has_section('defaults'):
        config.add_section('defaults')
    
    print("\n📝 Please provide the following information:")
    print("-" * 40)
    
    # Source path
    current_source = config.get('defaults', 'source_path', fallback='')
    print(f"\n📁 Source path (where are your Keep notes located?)")
    print(f"   Examples: ../keep-notes-takeout, /path/to/notes, gs://bucket-name")
    source_path = input(f"   Current: {current_source}\n   New value: ").strip()
    if source_path:
        config.set('defaults', 'source_path', source_path)
    
    # Target config (Google Drive folder ID)
    current_target = config.get('defaults', 'target_config', fallback='')
    print(f"\n📂 Google Drive folder ID")
    print(f"   Get this from: https://drive.google.com/drive/folders/FOLDER_ID")
    target_config = input(f"   Current: {current_target}\n   New value: ").strip()
    if target_config:
        config.set('defaults', 'target_config', target_config)
    
    # Save config
    with open('config.ini', 'w') as f:
        config.write(f)
    
    print("\n✅ Configuration saved to config.ini!")
    print("\n🚀 You can now run:")
    print("   make import-batch  # Test with single batch")
    print("   make import       # Full import")
    print("   make import-chaos # Chaos mode (ignores errors)")

if __name__ == '__main__':
    main() 