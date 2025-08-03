"""
Gemini API client for categorizing notes.
"""
import google.generativeai as genai
import os
from typing import List, Dict, Any
import time


class GeminiCategorizer:
    """Client for categorizing notes using Google's Gemini API."""
    
    def __init__(self, api_key: str = None):
        """
        Initialize the Gemini categorizer.
        
        Args:
            api_key: Gemini API key. If not provided, will look for GEMINI_API_KEY env var.
        """
        if api_key is None:
            api_key = os.getenv('GEMINI_API_KEY')
        
        if not api_key:
            raise ValueError("Gemini API key is required. Set GEMINI_API_KEY environment variable or pass api_key parameter.")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def categorize_notes(self, notes: List[Dict[str, Any]], categorization_rules: str) -> List[Dict[str, Any]]:
        """
        Categorize a list of notes using the provided rules.
        
        Args:
            notes: List of note dictionaries with 'id', 'title', and 'content' keys
            categorization_rules: English description of categorization rules
            
        Returns:
            List of dictionaries with 'note_id' and 'labels' keys
        """
        results = []
        
        for note in notes:
            try:
                labels = self._categorize_single_note(note, categorization_rules)
                results.append({
                    'note_id': note.get('id', ''),
                    'labels': labels
                })
                
                # Add small delay to respect API rate limits
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error categorizing note {note.get('id', 'unknown')}: {e}")
                results.append({
                    'note_id': note.get('id', ''),
                    'labels': 'ERROR: Failed to categorize'
                })
        
        return results
    
    def _categorize_single_note(self, note: Dict[str, Any], categorization_rules: str) -> str:
        """
        Categorize a single note using Gemini API.
        
        Args:
            note: Note dictionary with 'title' and 'content' keys
            categorization_rules: English description of categorization rules
            
        Returns:
            Comma-separated string of category labels
        """
        title = note.get('title', '')
        content = note.get('content', '')
        
        prompt = f"""
Please categorize the following note based on these rules:

{categorization_rules}

Note Title: {title}
Note Content: {content}

Please respond with only the category labels, separated by commas. Do not include any explanation or additional text.
"""
        
        try:
            response = self.model.generate_content(prompt)
            labels = response.text.strip()
            
            # Clean up the response - remove any extra whitespace and ensure proper formatting
            labels = ', '.join([label.strip() for label in labels.split(',') if label.strip()])
            
            return labels
            
        except Exception as e:
            raise Exception(f"Gemini API error: {e}")
