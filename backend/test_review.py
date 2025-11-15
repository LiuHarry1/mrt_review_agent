#!/usr/bin/env python3
"""
Test script for review service.
Usage:
    python test_review.py
"""
import os
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Setup logging FIRST, before any imports that use logging
import logging
from app.logger import setup_logging

# Configure logging to output to both console and file (force=True to override any existing config)
setup_logging(
    log_level=logging.INFO,
    log_dir="logs",
    log_file="test_review.log",
    console_output=True,
    file_output=True,
    force=True  # Force reconfiguration for test scripts
)
from dotenv import load_dotenv
from app.models import ReviewRequest
from app.service.review import ReviewService


def test_review():
    """Test review service."""
    print("\n" + "="*60)
    print("Testing Review Service")
    print("="*60)
    
    # Load environment variables
    load_dotenv()
    
    # Create review service
    service = ReviewService()
    
    # Test data
    mrt_content = """
Test Case ID: TC-001
Title: User Login Test
Preconditions:
    - User account exists
    - Application is running
Test Steps:
    1. Navigate to login page
    2. Enter username: testuser
    3. Enter password: testpass
    4. Click login button
Expected Result:
    - User should be successfully logged in
    - Dashboard page should be displayed
    """
    
    software_requirement = """
Requirement: User Authentication
Description: Users should be able to log in to the application using their credentials.
Verification Criteria:
    - Username and password fields are present
    - Login button is functional
    - Successful login redirects to dashboard
    - Failed login shows error message
    """
    
    success_count = 0
    total_tests = 2
    
    # Test Case 1: Review without software requirement
    print("\nTest Case 1: Review without software requirement")
    print("-" * 60)
    try:
        request = ReviewRequest(mrt_content=mrt_content.strip())
        response = service.review(request)
        
        print("✓ Review completed successfully")
        print(f"Response length: {len(response.raw_content or '')} characters")
        print("-------------  response result begin-------------------")
        print(response.raw_content)
        print("-------------  response result begin-------------------")

            
        success_count += 1
    except Exception as e:
        print(f"✗ Review failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test Case 2: Review with software requirement
    print("\nTest Case 2: Review with software requirement")
    print("-" * 60)
    try:
        request = ReviewRequest(
            mrt_content=mrt_content.strip(),
            software_requirement=software_requirement.strip()
        )
        response = service.review(request)
        
        print("✓ Review with requirement completed successfully")
        print(f"Response length: {len(response.raw_content or '')} characters")
        print("-------------  response result begin-------------------")
        print(response.raw_content)
        print("-------------  response result begin-------------------")
        success_count += 1
    except Exception as e:
        print(f"✗ Review with requirement failed: {e}")
        import traceback
        traceback.print_exc()
    
    return success_count == total_tests


def main():
    """Main entry point."""
    print("="*60)
    print("Review Service Test")
    print("="*60)
    print("\nNote: This test requires API keys to be set in environment variables:")
    print("  - For Qwen: DASHSCOPE_API_KEY or QWEN_API_KEY")
    print("  - For Azure OpenAI: AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT")
    print("\nCheck config.yaml for provider configuration.")
    
    try:
        result = test_review()
        
        print("\n" + "="*60)
        print("Test Summary")
        print("="*60)
        print(f"Status: {'Success' if result else 'Failed'}")
        
        return 0 if result else 1
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    # sys.exit(main())
    test_review()

