from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database import init_db, get_db_connection
from datetime import datetime
import sqlite3
import tensorflow as tf
import numpy as np
import re
from keras_preprocessing.text import Tokenizer
from keras_preprocessing.sequence import pad_sequences
import pickle
import os


os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

init_db()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    model_path = os.path.join(BASE_DIR, 'my_model_1.h5')
    model = tf.keras.models.load_model(model_path)
    print(f"Model loaded successfully from {model_path}")
except FileNotFoundError:
    print(f"Error: Model file '{model_path}' not found. Please ensure the file exists.")
    model = None
except Exception as e:
    print(f"Error loading model: {e}")
    model = None

try:
    tokenizer_path = os.path.join(BASE_DIR, 'tokenizer.pkl')
    with open(tokenizer_path, 'rb') as handle:
        tokenizer = pickle.load(handle)
    print(f"Tokenizer loaded successfully from {tokenizer_path}")
except FileNotFoundError:
    print(f"Error: Tokenizer file '{tokenizer_path}' not found. Please ensure the file exists.")
    tokenizer = None
except Exception as e:
    print(f"Error loading tokenizer: {e}")
    tokenizer = None

MAX_SEQUENCE_LENGTH = 100

def preprocess_text(text):
    if not tokenizer:
        return None
    text = re.sub(r'[^\w\s]', '', text.lower())
    sequence = tokenizer.texts_to_sequences([text])
    padded = pad_sequences(sequence, maxlen=MAX_SEQUENCE_LENGTH)
    return padded

def predict_truth_probability(text):
    if not model:
        print("Model not loaded, returning default probability 1.0")
        return 1.0
    processed_text = preprocess_text(text)
    if processed_text is None:
        print("Processed text is None, returning default probability 1.0")
        return 1.0
    prediction = model.predict(processed_text)
    probability = float(prediction[0][0])
    print(f"Predicted truth probability for '{text}': {probability}")
    return probability

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('chat'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                (name, email, generate_password_hash(password))
            )
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already exists!', 'error')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE email = ?', (email,)
        ).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['name']
            print(f"User logged in: user_id={user['id']}")
            return redirect(url_for('chat'))
        else:
            flash('Invalid email or password!', 'error')
    return render_template('login.html')

@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    messages = conn.execute('''
        SELECT m.content, m.timestamp, u.name as username, m.user_id, m.truth_probability
        FROM messages m
        JOIN users u ON m.user_id = u.id
        ORDER BY m.timestamp
    ''').fetchall()
    conn.close()
    print(f"Rendering chat.html with user_id: {session['user_id']}")
    return render_template('chat.html', 
                         username=session['username'],
                         user_id=session['user_id'],
                         messages=messages)

@app.route('/send_message', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    content = request.form['content']
    truth_probability = predict_truth_probability(content)
    print(f"Storing message with content '{content}' and truth probability {truth_probability}")
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO messages (content, user_id, username, truth_probability) VALUES (?, ?, ?, ?)',
        (content, session['user_id'], session['username'], truth_probability)
    )
    conn.commit()
    conn.close()
    return '', 204

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    if model is None or tokenizer is None:
        print(" WARNING: Model or tokenizer failed to load! Using default predictions.")
    app.run(debug=True, host='0.0.0.0', port=5000)