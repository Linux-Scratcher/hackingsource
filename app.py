from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_socketio import SocketIO, emit, join_room
from datetime import datetime
import sqlite3
import hashlib
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'votre_cle_secrete_tres_securisee'
app.config['DATABASE'] = 'database/chat.db'
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialisation de la base de données
def init_db():
    if not os.path.exists('database'):
        os.makedirs('database')
    
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db():
    db = sqlite3.connect(app.config['DATABASE'])
    db.row_factory = sqlite3.Row
    return db

# Fonctions d'authentification
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate_user(username, password):
    db = get_db()
    user = db.execute(
        'SELECT * FROM users WHERE username = ?', (username,)
    ).fetchone()
    db.close()
    
    if user and user['password'] == hash_password(password):
        return user
    return None

def register_user(username, password):
    try:
        db = get_db()
        db.execute(
            'INSERT INTO users (username, password) VALUES (?, ?)',
            (username, hash_password(password))
        )
        db.commit()
        db.close()
        return True
    except sqlite3.IntegrityError:
        return False

# Routes
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('chat'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = authenticate_user(username, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('chat'))
        else:
            flash('Identifiants incorrects', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if register_user(username, password):
            flash('Compte créé avec succès! Connectez-vous', 'success')
            return redirect(url_for('login'))
        else:
            flash('Ce nom d\'utilisateur existe déjà', 'error')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    messages = db.execute('''
        SELECT messages.content, messages.timestamp, users.username 
        FROM messages 
        JOIN users ON messages.user_id = users.id
        ORDER BY messages.timestamp ASC
    ''').fetchall()
    db.close()
    
    return render_template('index.html', messages=messages, username=session['username'])

# Gestion du chat WebSocket
@socketio.on('connect')
def handle_connect():
    if 'user_id' in session:
        join_room(session['user_id'])
        emit('system_message', {'message': f"{session['username']} a rejoint le chat"}, broadcast=True)
        update_users()

@socketio.on('disconnect')
def handle_disconnect():
    if 'user_id' in session:
        emit('system_message', {'message': f"{session['username']} a quitté le chat"}, broadcast=True)
        update_users()

@socketio.on('chat_message')
def handle_chat_message(data):
    if 'user_id' not in session:
        return
    
    message = data['message'].strip()
    if message:
        db = get_db()
        db.execute(
            'INSERT INTO messages (user_id, content) VALUES (?, ?)',
            (session['user_id'], message)
        )
        db.commit()
        db.close()
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        emit('chat_message', {
            'username': session['username'],
            'message': message,
            'timestamp': timestamp
        }, broadcast=True, include_self=True)

def update_users():
    db = get_db()
    online_users = db.execute('SELECT username FROM users').fetchall()
    db.close()
    
    emit('update_users', [user['username'] for user in online_users], broadcast=True)

if __name__ == '__main__':
    init_db()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
