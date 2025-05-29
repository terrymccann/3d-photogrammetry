#!/usr/bin/env python3
"""
Simple test to verify the main processing endpoints work correctly.
"""

import requests
import time
import json

def test_basic_functionality():
    """Test the basic functionality without actual images."""
    base_url = "http://localhost:5000"
    
    print("🔧 Testing Basic Functionality")
    print("=" * 40)
    
    # Test health check
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            health = response.json()
            print("✅ Health check passed")
            print(f"   Status: {health.get('status')}")
            print(f"   COLMAP available: {health.get('services', {}).get('colmap', False)}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False
    
    # Test API overview
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            api_info = response.json()
            print("✅ API overview endpoint works")
            endpoints = api_info.get('endpoints', {})
            print(f"   Available endpoints: {list(endpoints.keys())}")
        else:
            print(f"❌ API overview failed: {response.status_code}")
    except Exception as e:
        print(f"❌ API overview error: {e}")
    
    # Test status endpoint for non-existent session
    try:
        response = requests.get(f"{base_url}/status/test_session")
        if response.status_code == 404:
            print("✅ Status endpoint correctly returns 404 for non-existent session")
        else:
            print(f"⚠️ Status endpoint returned unexpected code: {response.status_code}")
    except Exception as e:
        print(f"❌ Status endpoint error: {e}")
    
    # Test process endpoint for non-existent session
    try:
        response = requests.post(
            f"{base_url}/process",
            json={"session_id": "non_existent_session"}
        )
        if response.status_code == 404:
            print("✅ Process endpoint correctly returns 404 for non-existent session")
        else:
            print(f"⚠️ Process endpoint returned unexpected code: {response.status_code}")
    except Exception as e:
        print(f"❌ Process endpoint error: {e}")
    
    print("\n🎉 Basic functionality test completed!")
    return True

if __name__ == "__main__":
    print("To run this test, make sure the Flask app is running:")
    print("python app.py")
    print()
    
    choice = input("Is the Flask app running? (y/n): ").strip().lower()
    if choice == 'y':
        test_basic_functionality()
    else:
        print("Please start the Flask app first with: python app.py")