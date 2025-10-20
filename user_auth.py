import json
import os
import hashlib
import secrets
from typing import Optional, Dict, Any
from datetime import datetime

class UserAuth:
    def __init__(self, users_file: str = "users.json"):
        self.users_file = users_file
        self.users = self._load_users()
    
    def _load_users(self) -> Dict[str, Dict[str, Any]]:
        """Load users from JSON file"""
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}
        return {}
    
    def _save_users(self):
        """Save users to JSON file"""
        with open(self.users_file, 'w') as f:
            json.dump(self.users, f, indent=2)
    
    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256 with salt"""
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}:{password_hash}"
    
    def _verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify password against stored hash"""
        try:
            salt, password_hash = stored_hash.split(':')
            return hashlib.sha256((password + salt).encode()).hexdigest() == password_hash
        except ValueError:
            return False
    
    def register_user(self, username: str, email: str, password: str) -> Dict[str, Any]:
        """Register a new user"""
        # Validate input
        if not username or not email or not password:
            return {"success": False, "message": "All fields are required"}
        
        if len(password) < 6:
            return {"success": False, "message": "Password must be at least 6 characters long"}
        
        if username in self.users:
            return {"success": False, "message": "Username already exists"}
        
        # Check if email already exists
        for user_data in self.users.values():
            if user_data.get("email") == email:
                return {"success": False, "message": "Email already registered"}
        
        # Create new user
        user_id = secrets.token_hex(8)
        self.users[username] = {
            "user_id": user_id,
            "email": email,
            "password_hash": self._hash_password(password),
            "created_at": datetime.now().isoformat(),
            "last_login": None
        }
        
        self._save_users()
        return {"success": True, "message": "User registered successfully", "user_id": user_id}
    
    def login_user(self, username: str, password: str) -> Dict[str, Any]:
        """Login a user"""
        if not username or not password:
            return {"success": False, "message": "Username and password are required"}
        
        if username not in self.users:
            return {"success": False, "message": "Invalid username or password"}
        
        user_data = self.users[username]
        
        if not self._verify_password(password, user_data["password_hash"]):
            return {"success": False, "message": "Invalid username or password"}
        
        # Update last login
        user_data["last_login"] = datetime.now().isoformat()
        self._save_users()
        
        return {
            "success": True, 
            "message": "Login successful",
            "user_id": user_data["user_id"],
            "username": username,
            "email": user_data["email"]
        }
    
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user data by username"""
        return self.users.get(username)
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user data by user ID"""
        for username, user_data in self.users.items():
            if user_data.get("user_id") == user_id:
                return {"username": username, **user_data}
        return None
    
    def update_user(self, username: str, **kwargs) -> bool:
        """Update user data"""
        if username not in self.users:
            return False
        
        for key, value in kwargs.items():
            if key != "password_hash":  # Don't allow direct password hash updates
                self.users[username][key] = value
        
        self._save_users()
        return True
    
    def delete_user(self, username: str) -> bool:
        """Delete a user"""
        if username in self.users:
            del self.users[username]
            self._save_users()
            return True
        return False
    
    def list_users(self) -> Dict[str, Dict[str, Any]]:
        """List all users (for admin purposes)"""
        # Return users without password hashes
        safe_users = {}
        for username, user_data in self.users.items():
            safe_users[username] = {
                "user_id": user_data.get("user_id"),
                "email": user_data.get("email"),
                "created_at": user_data.get("created_at"),
                "last_login": user_data.get("last_login")
            }
        return safe_users
