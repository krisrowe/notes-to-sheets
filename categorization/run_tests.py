#!/usr/bin/env python3
"""
Test runner script for categorization module.

Provides convenient commands to run different types of tests following Python best practices.

Usage:
    python run_tests.py unit          # Run only unit tests (fast)
    python run_tests.py integration   # Run only integration tests (requires API key)
    python run_tests.py all           # Run all tests
    python run_tests.py --help        # Show help
"""
import sys
import os
import subprocess
import argparse


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n🚀 {description}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, check=True, cwd=os.path.dirname(__file__))
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"❌ Command not found: {cmd[0]}")
        print("Make sure pytest is installed: pip install pytest")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Test runner for categorization module",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py unit                    # Fast unit tests only
  python run_tests.py integration             # Integration tests with real API
  python run_tests.py all                     # All tests
  python run_tests.py unit --verbose          # Unit tests with extra output
  
Environment Variables:
  GEMINI_API_KEY    Required for integration tests
        """
    )
    
    parser.add_argument(
        'test_type',
        choices=['unit', 'integration', 'all'],
        help='Type of tests to run'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--coverage',
        action='store_true',
        help='Run with coverage reporting (requires pytest-cov)'
    )
    
    args = parser.parse_args()
    
    # Base pytest command
    pytest_cmd = ['python', '-m', 'pytest']
    
    if args.verbose:
        pytest_cmd.append('-vv')
    
    if args.coverage:
        pytest_cmd.extend(['--cov=categorization', '--cov-report=term-missing'])
    
    success = True
    
    if args.test_type == 'unit':
        # Run unit tests only
        cmd = pytest_cmd + ['tests/unit/', '-m', 'not integration']
        success = run_command(cmd, "Running unit tests")
        
    elif args.test_type == 'integration':
        # Check for API key
        if not os.getenv('GEMINI_API_KEY'):
            print("❌ GEMINI_API_KEY environment variable is required for integration tests")
            print("Set it with: export GEMINI_API_KEY='your-api-key'")
            sys.exit(1)
        
        # Run integration tests only
        cmd = pytest_cmd + ['tests/integration/', '-m', 'integration']
        success = run_command(cmd, "Running integration tests")
        
    elif args.test_type == 'all':
        # Run unit tests first
        cmd = pytest_cmd + ['tests/unit/', '-m', 'not integration']
        success = run_command(cmd, "Running unit tests")
        
        if success:
            # Check for API key for integration tests
            if os.getenv('GEMINI_API_KEY'):
                cmd = pytest_cmd + ['tests/integration/', '-m', 'integration']
                success = run_command(cmd, "Running integration tests")
            else:
                print("\n⚠️  Skipping integration tests (GEMINI_API_KEY not set)")
                print("To run integration tests, set: export GEMINI_API_KEY='your-api-key'")
    
    if success:
        print(f"\n🎉 All {args.test_type} tests completed successfully!")
        sys.exit(0)
    else:
        print(f"\n💥 Some {args.test_type} tests failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()
