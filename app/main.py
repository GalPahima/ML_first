import os
import json
import sqlite3
import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'inventory.db')
SETTINGS_PATH = os.path.join(BASE_DIR, 'settings.json')

# Load Settings
with open(SETTINGS_PATH) as f:
    config = json.load(f)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS plants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT,
            size TEXT,
            condition TEXT,
            supply INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def send_telegram_msg(message):
    token = config.get('telegram_token')
    chat_id = config.get('telegram_chat_id')
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {"chat_id": chat_id, "text": message}
        try:
            requests.post(url, data=data)
        except Exception as e:
            print(f"Telegram Error: {e}")

@app.route('/')
def index():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM plants')
    plants = cursor.fetchall()
    conn.close()
    return render_template('index.html', plants=plants, settings=config)

@app.route('/order/<int:plant_id>', methods=['POST'])
def order(plant_id):
    user_name = request.form.get('user_name')
    user_contact = request.form.get('user_contact')
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM plants WHERE id = ?', (plant_id,))
    plant = cursor.fetchone()
    conn.close()

    if plant:
        msg = f"*New Order!*\n\nPlant: {plant[0]}\nCustomer: {user_name}\nContact: {user_contact}"
        send_telegram_msg(msg)
    
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            return "Wrong password!"
    return '''
        <form method="post">
            Password: <input type="password" name="password">
            <input type="submit" value="Login">
        </form>
    '''

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    # Security check: If not logged in, go to login page
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if request.method == 'POST':
        # Adding a new plant
        name = request.form.get('name')
        p_type = request.form.get('type')
        size = request.form.get('size')
        cond = request.form.get('condition')
        supply = request.form.get('supply')
        
        cursor.execute('INSERT INTO plants (name, type, size, condition, supply) VALUES (?,?,?,?,?)',
                       (name, p_type, size, cond, supply))
        conn.commit()
        return redirect(url_for('admin'))

    cursor.execute('SELECT * FROM plants')
    plants = cursor.fetchall()
    conn.close()
    return render_template('admin.html', plants=plants, settings=config)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

@app.route('/delete/<int:plant_id>')
def delete_plant(plant_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM plants WHERE id = ?', (plant_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)