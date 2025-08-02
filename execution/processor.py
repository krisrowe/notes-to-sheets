"""
Core processing logic for importing notes.
This module is independent of Google Keep, GCS, Sheets, or Drive.
It uses abstract interfaces for source files and target writing.
"""

import time
from typing import Dict, Any
from execution.note import ProcessedNote


def process_notes(
    note_source,  # NoteSource interface
    target: Any,  # Target interface with write_notes_and_attachments, save_image, get_existing_images methods
    existing_notes: Dict[str, bool],  # note_id -> has_attachments
    config: Dict[str, Any],
    max_batches: int = -1,
    batch_size: int = 20,
    ignore_errors: bool = False,
    sync_images: bool = True
) -> Dict[str, Any]:
    """
    Process notes in batches using abstract note source and target interfaces.

    Args:
        note_source: Object implementing NoteSource interface
        target: Object implementing target interface with write_notes_and_attachments, save_image, get_existing_images methods
        existing_notes: Dictionary mapping note_id to has_attachments boolean
        config: Configuration dictionary
        max_batches: Maximum number of batches to process (-1 for unlimited)
        batch_size: Number of notes per batch
        ignore_errors: Whether to continue on errors
        sync_images: Whether to sync images to target

    Returns:
        Dictionary containing processing summary and timing statistics
    """
    # Initialize timing statistics
    timing_stats = {
        'source_total_time': 0.0,
        'target_total_time': 0.0,
        'processing_total_time': 0.0,
        'start_time': time.time()
    }

    # Initialize summary tracking
    summary = {
        'processed': 0,
        'imported': 0,
        'duplicates': 0,
        'errors': 0,
        'attachments_added': 0,
        'totals': {},
        'ignored': {},
        'skipped': {}
    }

    # Initialize batching
    staged_notes = []
    staged_attachments = []
    batched_note_id_count = 0
    total_batches = 0

    # Process notes using cursor pattern
    print("Starting note processing...")

    # Process each note using fetch_next
    while note_source.has_more():
        summary['processed'] += 1

        try:
            # Load, validate, and transform note using the note source
            source_start = time.time()
            processed_note = note_source.fetch_next()
            timing_stats['source_total_time'] += time.time() - source_start
        except Exception as e:
            print(f"Error loading note: {e}")
            summary['errors'] += 1
            if not ignore_errors:
                raise
            continue

        # Check if note was successfully loaded and processed
        if processed_note is None:
            print(f"  - Skipped note (failed to load or validate)")
            continue

        # Check if note exists and if it has any attachments
        target_exists = processed_note.note_id in existing_notes
        target_has_attachments = existing_notes.get(processed_note.note_id, False)

        writes_staged = False

        if target_exists and target_has_attachments:
            # Note exists with attachments - skip as complete duplicate
            print(f"  - Skipping duplicate note: '{processed_note.title}' (ID: {processed_note.note_id})")
            summary['duplicates'] += 1
            continue
        elif target_exists and not target_has_attachments:
            if processed_note.attachments:
                # Note exists in target but has no attachments, and source has attachments - add attachments only
                print(f"  - Note exists but missing attachments, adding attachments: '{processed_note.title}' (ID: {processed_note.note_id})")
                summary['attachments_added'] = summary.get('attachments_added', 0) + 1
                
                # Stage attachments for writing
                for attachment in processed_note.attachments:
                    # Convert attachment to target format (attachment already has correct Type, File, Title)
                    target_attachment = {
                        'ID': _generate_id(f"{processed_note.note_id}_{attachment.get('File', '')}", ""),
                        'Note': processed_note.note_id,
                        'File': attachment.get('File', ''),
                        'Type': attachment.get('Type', ''),
                        'Title': attachment.get('Title', '')
                    }
                    staged_attachments.append(target_attachment)
                writes_staged = True
            else:
                # Note exists in target but has no attachments, and source also has no attachments - skip as duplicate
                print(f"  - Skipping duplicate note (no attachments to add): '{processed_note.title}' (ID: {processed_note.note_id})")
                summary['duplicates'] += 1
                continue
        else:
            # Note doesn't exist - add note and attachments
            print(f"  - Adding new note: '{processed_note.title}' (ID: {processed_note.note_id})")
            
            # Stage note for writing
            staged_notes.append(processed_note.to_dict())
            
            # Stage attachments for writing
            for attachment in processed_note.attachments:
                # Convert attachment to target format (attachment already has correct Type, File, Title)
                target_attachment = {
                    'ID': _generate_id(f"{processed_note.note_id}_{attachment.get('File', '')}", ""),
                    'Note': processed_note.note_id,
                    'File': attachment.get('File', ''),
                    'Type': attachment.get('Type', ''),
                    'Title': attachment.get('Title', '')
                }
                staged_attachments.append(target_attachment)
            writes_staged = True
        
        # Track successful import
        if writes_staged:
            summary['imported'] += 1
            batched_note_id_count += 1
        
        # Flush batch if it's full
        if batched_note_id_count >= batch_size:
            if staged_notes or staged_attachments:
                target_start = time.time()
                target.write_notes_and_attachments(staged_notes, staged_attachments)
                timing_stats['target_total_time'] += time.time() - target_start
                total_batches += 1
                print(f"  ✅ Flushed batch {total_batches} ({len(staged_notes)} notes, {len(staged_attachments)} attachments)")
            
            # Clear staged data
            staged_notes = []
            staged_attachments = []
            batched_note_id_count = 0
            
            # Check if we've reached the max_batches limit
            if max_batches > 0 and total_batches >= max_batches:
                print(f"\nReached maximum batch limit of {max_batches} batches. Stopping import.")
                break
    
    # Flush any remaining batch
    if staged_notes or staged_attachments:
        target_start = time.time()
        target.write_notes_and_attachments(staged_notes, staged_attachments)
        timing_stats['target_total_time'] += time.time() - target_start
        total_batches += 1
        print(f"  ✅ Flushed final batch {total_batches} ({len(staged_notes)} notes, {len(staged_attachments)} attachments)")
    
    # Image sync phase
    if sync_images:
        # Get session images from the note source's underlying source files
        session_images = note_source.source_files.get_session_images()
        if session_images:
            print(f"\n🖼️  Starting image sync phase...")
            print(f"📊 Syncing {len(session_images)} images from this session")
            
            # Get existing images in target
            existing_images = target.get_existing_images()
            print(f"📁 Found {len(existing_images)} existing images in target")
            
            # Determine which images need to be saved
            missing_images = session_images - existing_images
            existing_session_images = session_images & existing_images
            
            print(f"📊 Image sync summary:")
            print(f"  - Session images: {len(session_images)}")
            print(f"  - Already in target: {len(existing_session_images)}")
            print(f"  - Need to save: {len(missing_images)}")
            
            # Save missing images
            if missing_images:
                print(f"\n📤 Saving {len(missing_images)} images to target...")
                saved_count = 0
                failed_count = 0
                
                for i, filename in enumerate(missing_images, 1):
                    print(f"  [{i}/{len(missing_images)}] Saving {filename}...")
                    
                    try:
                        # Get image bytes from source
                        image_bytes = note_source.source_files.get_image_bytes(filename)
                        if not image_bytes:
                            print(f"    ❌ File not found: {filename}")
                            failed_count += 1
                            if not ignore_errors:
                                continue
                            else:
                                continue
                        
                        # Save to target
                        if target.save_image(image_bytes, filename):
                            saved_count += 1
                        else:
                            failed_count += 1
                                
                    except Exception as e:
                        print(f"    ❌ Failed to save {filename}: {e}")
                        failed_count += 1
                        if not ignore_errors:
                            raise
                
                print(f"\n📊 Image sync results:")
                print(f"  - Saved: {saved_count}")
                print(f"  - Already existing: {len(existing_session_images)}")
                print(f"  - Failed to save: {failed_count}")
            else:
                print(f"✅ All session images already exist in target")
    
    # Calculate final timing statistics
    timing_stats['processing_total_time'] = time.time() - timing_stats['start_time']
    
    # Add batch count to summary
    summary['batches_completed'] = total_batches
    
    # Print final summary
    print(f"\n📊 Processing Summary:")
    print(f"  - Notes processed: {summary['processed']}")
    print(f"  - Notes imported: {summary['imported']}")
    print(f"  - Duplicates skipped: {summary['duplicates']}")
    print(f"  - Errors encountered: {summary['errors']}")
    print(f"  - Attachments added to existing notes: {summary.get('attachments_added', 0)}")
    print(f"  - Batches completed: {total_batches}")
    
    print(f"\n⏱️  Timing Summary:")
    print(f"  - Total processing time: {timing_stats['processing_total_time']:.2f}s")
    print(f"  - Source loading time: {timing_stats['source_total_time']:.2f}s")
    print(f"  - Target writing time: {timing_stats['target_total_time']:.2f}s")
    
    return summary


def _generate_id(title: str, created_timestamp: str) -> str:
    """Generate a unique ID for attachments (AppSheet-compatible format)."""
    import hashlib
    
    # Create a unique string from title and timestamp
    unique_string = f"{title}_{created_timestamp}"
    
    # Generate MD5 hash and take first 8 characters
    hash_object = hashlib.md5(unique_string.encode())
    return hash_object.hexdigest()[:8] 