from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from .note import ProcessedNote


class NoteSource(ABC):
    """Abstract interface for note sources that can load and validate notes."""
    
    @abstractmethod
    def fetch_next(self) -> Optional[ProcessedNote]:
        """
        Fetch the next note from the source.
        
        Returns:
            ProcessedNote object if a note is available, None if no more notes
        """
        pass
    
    @abstractmethod
    def reset(self) -> None:
        """
        Reset the cursor to the beginning of the source.
        """
        pass
    
    @abstractmethod
    def has_more(self) -> bool:
        """
        Check if there are more notes available to fetch.
        
        Returns:
            True if more notes are available, False otherwise
        """
        pass 