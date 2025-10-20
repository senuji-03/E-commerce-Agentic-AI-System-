#!/usr/bin/env python3
"""
Simple test script for the authentication system
"""

import os
import sys
from user_auth import UserAuth

def test_auth_system():
    """Test the authentication system"""
    print("Testing Authentication System")
    print("=" * 50)
    
    # Initialize auth system
    auth = UserAuth("test_users.json")
    
    # Test 1: Register a new user
    print("\n1. Testing user registration...")
    result = auth.register_user("testuser", "test@example.com", "password123")
    if result["success"]:
        print("[PASS] User registration successful")
        print(f"   User ID: {result['user_id']}")
    else:
        print(f"[FAIL] User registration failed: {result['message']}")
        return False
    
    # Test 2: Try to register the same user again
    print("\n2. Testing duplicate user registration...")
    result = auth.register_user("testuser", "test2@example.com", "password456")
    if not result["success"]:
        print("[PASS] Duplicate user registration correctly rejected")
    else:
        print("[FAIL] Duplicate user registration should have been rejected")
        return False
    
    # Test 3: Try to register with same email
    print("\n3. Testing duplicate email registration...")
    result = auth.register_user("testuser2", "test@example.com", "password789")
    if not result["success"]:
        print("[PASS] Duplicate email registration correctly rejected")
    else:
        print("[FAIL] Duplicate email registration should have been rejected")
        return False
    
    # Test 4: Login with correct credentials
    print("\n4. Testing login with correct credentials...")
    result = auth.login_user("testuser", "password123")
    if result["success"]:
        print("[PASS] Login successful")
        print(f"   Username: {result['username']}")
        print(f"   Email: {result['email']}")
    else:
        print(f"[FAIL] Login failed: {result['message']}")
        return False
    
    # Test 5: Login with incorrect password
    print("\n5. Testing login with incorrect password...")
    result = auth.login_user("testuser", "wrongpassword")
    if not result["success"]:
        print("[PASS] Incorrect password correctly rejected")
    else:
        print("[FAIL] Incorrect password should have been rejected")
        return False
    
    # Test 6: Login with non-existent user
    print("\n6. Testing login with non-existent user...")
    result = auth.login_user("nonexistent", "password123")
    if not result["success"]:
        print("[PASS] Non-existent user correctly rejected")
    else:
        print("[FAIL] Non-existent user should have been rejected")
        return False
    
    # Test 7: Get user data
    print("\n7. Testing get user data...")
    user_data = auth.get_user("testuser")
    if user_data:
        print("[PASS] User data retrieved successfully")
        print(f"   Email: {user_data['email']}")
        print(f"   Created: {user_data['created_at']}")
    else:
        print("[FAIL] Failed to retrieve user data")
        return False
    
    # Test 8: Get user by ID
    print("\n8. Testing get user by ID...")
    user_id = user_data['user_id']
    user_by_id = auth.get_user_by_id(user_id)
    if user_by_id:
        print("[PASS] User data retrieved by ID successfully")
        print(f"   Username: {user_by_id['username']}")
    else:
        print("[FAIL] Failed to retrieve user data by ID")
        return False
    
    # Test 9: List users
    print("\n9. Testing list users...")
    users = auth.list_users()
    if users and "testuser" in users:
        print("[PASS] Users listed successfully")
        print(f"   Found {len(users)} user(s)")
    else:
        print("[FAIL] Failed to list users")
        return False
    
    # Test 10: Delete user
    print("\n10. Testing user deletion...")
    if auth.delete_user("testuser"):
        print("[PASS] User deleted successfully")
    else:
        print("[FAIL] Failed to delete user")
        return False
    
    # Test 11: Try to login deleted user
    print("\n11. Testing login with deleted user...")
    result = auth.login_user("testuser", "password123")
    if not result["success"]:
        print("[PASS] Deleted user correctly rejected")
    else:
        print("[FAIL] Deleted user should have been rejected")
        return False
    
    # Cleanup
    if os.path.exists("test_users.json"):
        os.remove("test_users.json")
        print("\n[Cleanup] Cleaned up test files")
    
    print("\n" + "=" * 50)
    print("[SUCCESS] All authentication tests passed!")
    return True

if __name__ == "__main__":
    try:
        success = test_auth_system()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[FAIL] Test failed with error: {e}")
        sys.exit(1)
