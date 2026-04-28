import json
import hashlib
from pathlib import Path

USER_FILE = Path("users.json")


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def load_users():
    if not USER_FILE.exists():
        USER_FILE.write_text("{}")

    users = json.loads(USER_FILE.read_text())

    # Create default admin user
    if "admin" not in users:
        users["admin"] = hash_password("admin")
        save_users(users)

    return users


def save_users(users):
    USER_FILE.write_text(json.dumps(users, indent=4))


def signup(username, password):
    username = username.strip()

    if not username or not password:
        return False, "Username and password are required."

    users = load_users()

    if username in users:
        return False, "Username already exists."

    users[username] = hash_password(password)
    save_users(users)

    return True, "Account created successfully. You can now login."


def login(username, password):
    username = username.strip()
    users = load_users()

    if username not in users:
        return False, "User not found."

    if users[username] != hash_password(password):
        return False, "Incorrect password."

    return True, "Login successful."


def logout():
    return False, ""