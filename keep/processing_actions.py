"""
Processing actions for handling note attributes during import.
"""

from enum import Enum


class ProcessingAction(Enum):
    """Defines how to handle specific note attributes during processing."""
    LABEL = "label"      # Capture value as a label
    ERROR = "error"      # Throw error and exit without processing further notes
    SKIP = "skip"        # Skip importing this note and log it
    IGNORE = "ignore"    # Process as if attribute wasn't specified (with logging for HTML) 