#!/usr/bin/env python3
"""
Test runner script for log_analyzer project.

This script provides different test execution modes:
- Unit tests only
- Integration tests only
- All tests
- Coverage reporting
- Code quality checks
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode != 0:
        print(f"\n❌ {description} failed with exit code {result.returncode}")
        return False
    else:
        print(f"\n✅ {description} completed successfully")
        return True


def install_dependencies():
    """Install test dependencies"""
    print("Installing test dependencies...")
    return run_command([
        sys.executable, "-m", "pip", "install", "-r", "requirements-test.txt"
    ], "Installing dependencies")


def run_unit_tests():
    """Run unit tests only"""
    return run_command([
        "python", "-m", "pytest", "tests/test_log_analyzer.py", "-v"
    ], "Unit tests")


def run_integration_tests():
    """Run integration tests only"""
    return run_command([
        "python", "-m", "pytest", "tests/test_integration.py", "-v"
    ], "Integration tests")


def run_all_tests():
    """Run all tests with coverage"""
    return run_command([
        "python", "-m", "pytest", "-v", "--cov=log_analyzer", 
        "--cov-report=term-missing", "--cov-report=html:htmlcov"
    ], "All tests with coverage")


def run_code_quality_checks():
    """Run code quality checks"""
    success = True
    
    # Check if flake8 is available
    try:
        subprocess.run(["flake8", "--version"], capture_output=True, check=True)
        success &= run_command([
            "flake8", "log_analyzer.py", "tests/", "--max-line-length=100", 
            "--extend-ignore=E203,W503"
        ], "Flake8 linting")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  Flake8 not available, skipping linting")
    
    # Check if black is available
    try:
        subprocess.run(["black", "--version"], capture_output=True, check=True)
        success &= run_command([
            "black", "--check", "--diff", "log_analyzer.py", "tests/"
        ], "Black code formatting check")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  Black not available, skipping formatting check")
    
    return success


def run_quick_test():
    """Run a quick smoke test"""
    return run_command([
        "python", "-m", "pytest", "tests/test_log_analyzer.py::TestExtractComponentName", "-v"
    ], "Quick smoke test")


def main():
    """Main test runner function"""
    parser = argparse.ArgumentParser(description="Test runner for log_analyzer project")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--all", action="store_true", help="Run all tests with coverage")
    parser.add_argument("--quality", action="store_true", help="Run code quality checks")
    parser.add_argument("--quick", action="store_true", help="Run quick smoke test")
    parser.add_argument("--install", action="store_true", help="Install test dependencies")
    parser.add_argument("--no-deps", action="store_true", help="Skip dependency installation")
    
    args = parser.parse_args()
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    print(f"Running tests from: {script_dir}")
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")
    
    # Install dependencies unless specifically skipped
    if not args.no_deps and not args.install:
        if not install_dependencies():
            print("❌ Failed to install dependencies")
            return 1
    
    if args.install:
        return 0 if install_dependencies() else 1
    
    success = True
    
    if args.unit:
        success &= run_unit_tests()
    elif args.integration:
        success &= run_integration_tests()
    elif args.quality:
        success &= run_code_quality_checks()
    elif args.quick:
        success &= run_quick_test()
    elif args.all:
        success &= run_all_tests()
    else:
        # Default: run all tests
        print("No specific test type specified, running all tests...")
        success &= run_all_tests()
        
        # Also run quality checks if available
        print("\nRunning code quality checks...")
        run_code_quality_checks()  # Don't fail on quality issues
    
    if success:
        print(f"\n{'🎉 All tests passed! 🎉':^60}")
        
        # Show coverage report location if it exists
        htmlcov_path = script_dir / "htmlcov" / "index.html"
        if htmlcov_path.exists():
            print(f"\n📊 Coverage report available at: {htmlcov_path}")
        
        return 0
    else:
        print(f"\n{'❌ Some tests failed ❌':^60}")
        return 1


if __name__ == "__main__":
    sys.exit(main())