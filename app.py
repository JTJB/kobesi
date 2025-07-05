from flask import Flask, request, jsonify, render_template_string
import sqlite3
import os
import hashlib
import json
from datetime import datetime

app = Flask(__name__)

DB_FILE = 'data.db'

# Setup DB
def init_db():
    if not os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        # Create users table
        c.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password_hash TEXT,
                is_admin INTEGER DEFAULT 0
            )
        ''')
        
        # Create activity table
        c.execute('''
            CREATE TABLE activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                week TEXT,
                approaches INTEGER DEFAULT 0,
                conversations INTEGER DEFAULT 0,
                sharings INTEGER DEFAULT 0,
                saved INTEGER DEFAULT 0,
                timestamp TEXT,
                FOREIGN KEY (username) REFERENCES users (username)
            )
        ''')
        
        # Create admin user (password: admin123)
        admin_password = hashlib.sha256('admin123'.encode()).hexdigest()
        c.execute('INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)', 
                 ('admin', admin_password, 1))
        
        conn.commit()
        conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, password_hash):
    return hashlib.sha256(password.encode()).hexdigest() == password_hash

init_db()

@app.route('/')
def home():
    # Read the HTML file content
    try:
        with open('paste.txt', 'r', encoding='utf-8') as file:
            html_content = file.read()
        return html_content
    except FileNotFoundError:
        return "HTML file not found. Please make sure 'paste.txt' exists in the same directory."

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required"})
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Check if user exists
    c.execute('SELECT username FROM users WHERE username = ?', (username,))
    if c.fetchone():
        conn.close()
        return jsonify({"success": False, "error": "Username already exists"})
    
    # Create new user
    password_hash = hash_password(password)
    c.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', 
             (username, password_hash))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required"})
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute('SELECT password_hash, is_admin FROM users WHERE username = ?', (username,))
    result = c.fetchone()
    conn.close()
    
    if not result:
        return jsonify({"success": False, "error": "Invalid username or password"})
    
    password_hash, is_admin = result
    if not verify_password(password, password_hash):
        return jsonify({"success": False, "error": "Invalid username or password"})
    
    return jsonify({"success": True, "isAdmin": bool(is_admin)})

@app.route('/save', methods=['POST'])
def save_data():
    data = request.get_json()
    week = data.get("week")
    week_data = data.get("data", {})
    username = data.get("user")
    
    if not username:
        return jsonify({"status": "error", "error": "User not specified"})
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Check if data for this week already exists
    c.execute('SELECT id FROM activity WHERE username = ? AND week = ?', (username, week))
    existing = c.fetchone()
    
    if existing:
        # Update existing record
        c.execute('''
            UPDATE activity 
            SET approaches = ?, conversations = ?, sharings = ?, saved = ?, timestamp = ?
            WHERE username = ? AND week = ?
        ''', (
            week_data.get('approaches', 0),
            week_data.get('conversations', 0),
            week_data.get('sharings', 0),
            week_data.get('saved', 0),
            week_data.get('timestamp', datetime.now().isoformat()),
            username,
            week
        ))
    else:
        # Insert new record
        c.execute('''
            INSERT INTO activity (username, week, approaches, conversations, sharings, saved, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            username,
            week,
            week_data.get('approaches', 0),
            week_data.get('conversations', 0),
            week_data.get('sharings', 0),
            week_data.get('saved', 0),
            week_data.get('timestamp', datetime.now().isoformat())
        ))
    
    conn.commit()
    conn.close()
    
    return jsonify({"status": "success"})

@app.route('/load', methods=['GET'])
def load_data():
    user = request.args.get('user')
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    if user:
        # Load data for specific user
        c.execute('SELECT week, approaches, conversations, sharings, saved, timestamp FROM activity WHERE username = ?', (user,))
        rows = c.fetchall()
        
        user_data = {}
        for row in rows:
            week, approaches, conversations, sharings, saved, timestamp = row
            user_data[week] = {
                'approaches': approaches,
                'conversations': conversations,
                'sharings': sharings,
                'saved': saved,
                'timestamp': timestamp,
                'user': user
            }
        
        conn.close()
        return jsonify({"success": True, "data": user_data})
    else:
        # Load all data (admin only)
        c.execute('SELECT username, week, approaches, conversations, sharings, saved, timestamp FROM activity')
        rows = c.fetchall()
        
        all_data = {}
        for row in rows:
            username, week, approaches, conversations, sharings, saved, timestamp = row
            if username not in all_data:
                all_data[username] = {}
            
            all_data[username][week] = {
                'approaches': approaches,
                'conversations': conversations,
                'sharings': sharings,
                'saved': saved,
                'timestamp': timestamp,
                'user': username
            }
        
        conn.close()
        return jsonify({"success": True, "data": all_data})

@app.route('/save_user', methods=['POST'])
def save_user_data():
    data = request.get_json()
    username = data.get('username')
    user_data = data.get('data', {})
    
    # This endpoint could be used for additional user settings/preferences
    # For now, we'll just return success
    return jsonify({"status": "success"})

@app.route('/load_user', methods=['GET'])
def load_user_data():
    username = request.args.get('username')
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    if username:
        c.execute('SELECT username, is_admin FROM users WHERE username = ?', (username,))
        result = c.fetchone()
        if result:
            username, is_admin = result
            user_info = {
                'username': username,
                'is_admin': bool(is_admin)
            }
            conn.close()
            return jsonify({"success": True, "data": user_info})
    else:
        # Load all users (admin only)
        c.execute('SELECT username, is_admin FROM users')
        users = []
        for row in c.fetchall():
            username, is_admin = row
            users.append({
                'username': username,
                'is_admin': bool(is_admin)
            })
        
        conn.close()
        return jsonify({"success": True, "data": users})
    
    conn.close()
    return jsonify({"success": False, "error": "User not found"})

if __name__ == '__main__':
    app.run(debug=True)