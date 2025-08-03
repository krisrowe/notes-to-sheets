"""
Integration tests for categorization module.

Integration tests use real external services (Gemini API) with CSV data sources.
These tests are slower and require API keys but validate end-to-end functionality.

Environment variables required:
- GEMINI_API_KEY: Your Gemini API key for testing

Test naming conventions:
- test_integration_* for integration test methods
- *_integration_test.py for integration test files
"""
