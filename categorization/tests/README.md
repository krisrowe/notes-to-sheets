# Testing Guide for Categorization Module

This document describes the testing structure and best practices for the categorization module.

## Test Organization

The tests are organized following Python best practices:

```
categorization/tests/
├── __init__.py                     # Test package initialization
├── README.md                       # This file
├── pytest.ini                     # Pytest configuration
├── run_tests.py                    # Test runner script
├── unit/                           # Unit tests (fast, mocked)
│   ├── __init__.py
│   └── test_categorization_service.py
├── integration/                    # Integration tests (real APIs)
│   ├── __init__.py
│   └── test_gemini_categorization_integration.py
└── fixtures/                      # Test data and utilities
    ├── __init__.py
    └── test_data.py
```

## Test Types

### Unit Tests (`tests/unit/`)
- **Purpose**: Test individual components in isolation
- **Dependencies**: Mocked (no real API calls)
- **Speed**: Fast (< 1 second per test)
- **When to run**: During development, CI/CD
- **Naming**: `test_*.py` files, `test_*` methods

### Integration Tests (`tests/integration/`)
- **Purpose**: Test end-to-end functionality with real APIs
- **Dependencies**: Real Gemini API, CSV data source
- **Speed**: Slower (API calls, network latency)
- **When to run**: Before releases, manual validation
- **Naming**: `test_integration_*.py` files, `test_integration_*` methods

## Running Tests

### Quick Start

```bash
# Navigate to categorization directory
cd categorization/

# Run unit tests (fast, no API key needed)
python run_tests.py unit

# Run integration tests (requires GEMINI_API_KEY)
export GEMINI_API_KEY="your-api-key-here"
python run_tests.py integration

# Run all tests
python run_tests.py all
```

### Using pytest directly

```bash
# Unit tests only
python -m pytest tests/unit/ -v

# Integration tests only (requires API key)
python -m pytest tests/integration/ -v

# All tests
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=categorization --cov-report=term-missing
```

### Test Runner Options

The `run_tests.py` script provides convenient options:

```bash
# Verbose output
python run_tests.py unit --verbose

# With coverage reporting
python run_tests.py unit --coverage

# Help
python run_tests.py --help
```

## Environment Variables

### Required for Integration Tests
- `GEMINI_API_KEY`: Your Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)

### Optional
- `PYTEST_VERBOSITY`: Set to `2` for extra verbose output

## Test Data

### Fixtures (`tests/fixtures/test_data.py`)
- `SAMPLE_NOTES`: 10 diverse test notes covering different categories
- `EXPECTED_CATEGORIES`: Expected categorization results for validation
- `TEST_CATEGORIZATION_RULES`: Standard rules for consistent testing

### CSV Test Data (`../test_data/Note.csv`)
- Real CSV file used by integration tests
- Contains the same data as `SAMPLE_NOTES`
- Automatically created/updated by tests

## Writing New Tests

### Unit Test Example

```python
# tests/unit/test_new_feature.py
import unittest
from unittest.mock import Mock
from categorization.new_feature import NewFeature

class TestNewFeature(unittest.TestCase):
    def setUp(self):
        self.mock_dependency = Mock()
        self.feature = NewFeature(self.mock_dependency)
    
    def test_basic_functionality(self):
        # Test with mocked dependencies
        result = self.feature.do_something()
        self.assertEqual(result, expected_value)
```

### Integration Test Example

```python
# tests/integration/test_new_integration.py
import unittest
import os
from categorization.tests.fixtures.test_data import SAMPLE_NOTES

@unittest.skipUnless(os.getenv('GEMINI_API_KEY'), "API key required")
class TestNewIntegration(unittest.TestCase):
    def test_integration_real_api(self):
        # Test with real API calls
        result = self.service.call_real_api(SAMPLE_NOTES[0])
        self.assertIsNotNone(result)
```

## Best Practices

### Test Naming Conventions
- **Files**: `test_*.py` or `*_test.py`
- **Classes**: `Test*` (e.g., `TestCategorizationService`)
- **Methods**: `test_*` (unit) or `test_integration_*` (integration)

### Test Structure
1. **Arrange**: Set up test data and mocks
2. **Act**: Execute the code under test
3. **Assert**: Verify the results

### Integration Test Guidelines
- Use real APIs but with controlled test data
- Include validation against expected results
- Handle API errors gracefully
- Use CSV data source for consistency
- Skip tests if API keys are not available

### Unit Test Guidelines
- Mock all external dependencies
- Test edge cases and error conditions
- Keep tests fast and isolated
- Use descriptive test names

## Continuous Integration

### Pre-commit Checks
```bash
# Run before committing
python run_tests.py unit
```

### CI/CD Pipeline
```bash
# In CI environment
python run_tests.py unit --coverage
# Integration tests run separately with secrets
```

## Troubleshooting

### Common Issues

1. **"GEMINI_API_KEY not set"**
   - Set the environment variable: `export GEMINI_API_KEY="your-key"`
   - Get your key from [Google AI Studio](https://aistudio.google.com/app/apikey)

2. **"pytest not found"**
   - Install pytest: `pip install pytest pytest-cov`

3. **Import errors**
   - Run tests from the categorization directory
   - Ensure the parent directory is in PYTHONPATH

4. **Integration tests failing**
   - Check API key validity
   - Verify internet connection
   - Check Gemini API service status

### Debug Mode

```bash
# Run single test with maximum verbosity
python -m pytest tests/integration/test_gemini_categorization_integration.py::TestGeminiCategorizationIntegration::test_integration_gemini_categorization_basic -vv -s
```

## Test Coverage

Target coverage levels:
- **Unit tests**: 90%+ code coverage
- **Integration tests**: Key user workflows covered
- **Combined**: 85%+ overall coverage

Check coverage:
```bash
python run_tests.py unit --coverage
```

## Performance Benchmarks

### Expected Test Times
- Unit tests: < 5 seconds total
- Integration tests: 30-60 seconds (depends on API response time)
- All tests: < 2 minutes

### API Rate Limits
- Integration tests include delays between API calls
- Limit concurrent test runs to avoid rate limiting
- Use test data that's representative but not excessive
