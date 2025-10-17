from flask import Flask, render_template_string, request, redirect, url_for, flash, session
import os
import mysql.connector
import bcrypt
import random
import time
import smtplib
from email.mime.text import MIMEText
import re


app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'a_super_secret_key_for_dev')
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600

# Database and SMTP configurations
DB_HOST = os.getenv('DB_HOST', 'db')
DB_USER = os.getenv('DB_USER', 'user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
DB_NAME = os.getenv('DB_NAME', 'mydatabase')
SMTP_SERVER = 'smtp.example.com'
SMTP_PORT = 587
SMTP_USER = 'your_email@example.com'
SMTP_PASSWORD = 'your_password'
BLACKLISTED_IPS = []
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 5
rate_limit_dict = {}

ELEC_OFFICER_LOGIN_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>Election Officer Login</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background-color: #f0f8ff; color: #333; }
        .container { max-width: 400px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #28a745; }
        form { padding: 15px; border: 1px solid #ccf; border-radius: 5px; background-color: #f7fcff; }
        form input[type="email"], form input[type="password"], form input[type="text"] { width: calc(100% - 22px); padding: 10px; margin-bottom: 10px; border: 1px solid #ccc; border-radius: 4px; }
        form input[type="submit"] { background-color: #28a745; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        form input[type="submit"]:hover { background-color: #218838; }
        .message { background-color: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
        .error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Election Officer Login</h1>
        {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
            <div class="{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
        {% endwith %}
        <form method="POST" action="/login">
            <label for="email">Email:</label><br>
            <input type="email" id="email" name="email" required><br><br>
            <label for="password">Password:</label><br>
            <input type="password" id="password" name="password" required><br><br>
            <label for="captcha">CAPTCHA: {{ captcha_question }}</label><br>
            <input type="text" id="captcha" name="captcha" required><br><br>
            <input type="submit" value="Login">
        </form>
    </div>
</body>
</html>
"""
ELEC_OFFICER_OTP_TEMPLATE="""
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>OTP Verification</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background-color: #f0f8ff; color: #333; }
        .container { max-width: 400px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #28a745; }
        form { padding: 15px; border: 1px solid #ccf; border-radius: 5px; background-color: #f7fcff; }
        form input[type="text"] { width: calc(100% - 22px); padding: 10px; margin-bottom: 10px; border: 1px solid #ccc; border-radius: 4px; }
        form input[type="submit"] { background-color: #28a745; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        form input[type="submit"]:hover { background-color: #218838; }
        .message { background-color: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
        .error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
    </style>
</head>
<body>
    div class="container">
        <h1>Election Officer OTP Verification</h1>
        {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
            <div class="{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
        {% endwith %}
        <form method="POST" action="/verify_otp">
            <label for="otp">Enter OTP:</label><br>
            <input type="text" id="otp" name="otp" required><br><br>
            <input type="submit" value="Verify">
        </form>
    </div>
</body>
</html>
"""

# HTML templates for rendering
VOTERS_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>Voter Registration</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background-color: #f0f8ff; color: #333; }
        .container { max-width: 800px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1, h2 { color: #28a745; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #e6ffe6; }
        form { margin-top: 20px; padding: 15px; border: 1px solid #ccf; border-radius: 5px; background-color: #f7fcff; }
        form input[type="text"], form input[type="email"] { width: calc(100% - 22px); padding: 10px; margin-bottom: 10px; border: 1px solid #ccc; border-radius: 4px; }
        form input[type="submit"] { background-color: #28a745; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        form input[type="submit"]:hover { background-color: #218838; }
        .action-buttons { display: flex; gap: 5px; }
        .edit-button { background-color: #ffc107; color: #212529; padding: 5px 10px; border: none; border-radius: 4px; cursor: pointer; }
        .edit-button:hover { background-color: #e0a800; }
        .delete-form { display: inline; }
        .delete-button { background-color: #dc3545; color: white; padding: 5px 10px; border: none; border-radius: 4px; cursor: pointer; }
        .delete-button:hover { background-color: #c82333; }
        .message { background-color: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Voter Registration Application</h1>
        <p>Welcome, {{ session['elec_officer_name'] }}! <a class="logout-link" href="/logout">Logout</a></p>
        {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
            <div class="{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
        {% endwith %}
        {% if edit_voter %}
        <h2>Edit Voter (ID: {{ edit_voter[0] }})</h2>
        <form method="POST" action="/edit/{{ edit_voter[0] }}">
            <label for="name">Name:</label><br>
            <input type="text" id="name" name="name" value="{{ edit_voter[1] }}" required><br><br>
            <label for="email">Email:</label><br>
            <input type="email" id="email" name="email" value="{{ edit_voter[2] }}" required><br><br>
            <input type="submit" value="Update Voter">
            <a href="/" style="margin-left: 10px;">Cancel</a>
        </form>
        {% else %}
        <h2>Current Registered Voters</h2>
        {% if voters %}
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for voter in voters %}
                <tr>
                    <td>{{ voter[0] }}</td>
                    <td>{{ voter[1] }}</td>
                    <td>{{ voter[2] }}</td>
                    <td>{{ voter[3] }}</td>
                    <td class="action-buttons">
                        <form class="delete-form" method="GET" action="/edit/{{ voter[0] }}">
                            <input type="submit" value="Edit" class="edit-button">
                        </form>
                        <form class="delete-form" method="POST" action="/delete/{{ voter[0] }}">
                            <input type="submit" value="Delete" class="delete-button">
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <p>No voters registered yet. Add one below</p>
        {% endif %}

        <h2>Register New Voter</h2>
        <form method="POST" action="/add">
            <label for="name">Name:</label><br>
            <input type="text" id="name" name="name" required><br><br>
            <label for="email">Email:</label><br>
            <input type="email" id="email" name="email" required><br><br>
            <input type="submit" value="Register Voter">
        </form>
        {% endif %}
    </div>
</body>
</html>
"""

def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

def init_db():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Election officers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS elec_officers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                role ENUM('elec_officer') DEFAULT 'elec_officer'
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS voters (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                status ENUM('submitted', 'accepted', 'rejected') DEFAULT 'submitted'
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                action VARCHAR(255),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip VARCHAR(45),
                details TEXT
            );
        """)
        conn.commit()
        print("Database 'voters' table checked/created successfully.")
    except Exception as e:
        print(f"Error initializing voters database: {e}")
    finally:
        if conn:
            conn.close()

@app.before_request
def before_first_request():
    init_db()

def validate_password_strength(password):
    if len(password) < 8 or not re.search("[A-Z]", password) or not re.search("[a-z]", password) or not re.search("\d", password) or not re.search("[!@#$%^&*]", password):
        return False
    return True

def generate_captcha():
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    operation = random.choice(['+', '-'])
    question = f"What is {num1} {operation} {num2}?"
    answer = num1 + num2 if operation == '+' else num1 - num2
    return question, str(answer)

def send_otp(email, otp):
    msg = MIMEText(f"Your Election Officer OTP is {otp}")
    msg['Subject'] = 'Election Officer Login OTP'
    msg['From'] = SMTP_USER
    msg['To'] = email
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending OTP: {e}")
        return False
def log_audit(user_id, action, ip, details=''):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO audit_logs (user_id, action, ip, details) VALUES (%s, %s, %s, %s)", (user_id, action, ip, details))
        conn.commit()
    except Exception as e:
        print(f"Error logging audit: {e}")
    finally:
        if conn:
            conn.close()
def is_ip_blacklisted(ip):
    return ip in BLACKLISTED_IPS

def check_rate_limit(ip):
    now = time.time()
    if ip in rate_limit_dict:
        count, last_time = rate_limit_dict[ip]
        if now - last_time < RATE_LIMIT_WINDOW:
            if count >= RATE_LIMIT_MAX:
                return False
            rate_limit_dict[ip] = (count + 1, last_time)
            return True
        rate_limit_dict[ip] = (1, now)
        return True
    rate_limit_dict[ip] = (1, now)
    return True

@app.route('/login', methods=['GET', 'POST'])
def elec_officer_login():
    ip = request.remote_addr
    if is_ip_blacklisted(ip) or not check_rate_limit(ip):
        log_audit(None, 'access_denied', ip, details="Rate limit or blacklist violation")
        flash("Access denied due to rate limit or blacklist", 'error')
        return render_template_string(ELEC_OFFICER_LOGIN_TEMPLATE, captcha_question="")
    
    captcha_question, captcha_answer = generate_captcha()
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password']
        captcha_response = request.form['captcha']

        if captcha_response != captcha_answer:
            flash("CAPTCHA incorrect. Please try again.", 'error')
            log_audit(None, 'failed_login', ip, details="Incorrect CAPTCHA")
            return render_template_string(ELEC_OFFICER_LOGIN_TEMPLATE, captcha_question=captcha_question)

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, password FROM elec_officers WHERE email = %s", (email,))
            officer = cursor.fetchone()
            if officer:
                officer_id, officer_name, hashed_password, role = officer
                if bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')):
                    if role == 'elec_officer':
                        otp = str(random.randint(100000, 999999))
                        session['otp'] = otp
                        session['otp_expiry'] = time.time() + 300  # 5 minutes
                        session['pending_elec_officer_id'] = officer_id
                        session['pending_elec_officer_name'] = officer_name
                        if send_otp(email, otp):
                            log_audit(officer_id, 'otp_sent', ip)
                            return redirect(url_for('verify_otp'))
                        else:
                            log_audit(officer_id, 'otp_failed', ip, details="Failed to send OTP")
                            flash("Failed to send OTP", 'error')
                            return render_template_string(ELEC_OFFICER_LOGIN_TEMPLATE, captcha_question=captcha_question)
                    else:
                        log_audit(officer_id, 'failed_login_role', ip, details=f"Invalid role for {email}")
                        flash("Invalid election officer role", 'error')
                        return render_template_string(ELEC_OFFICER_LOGIN_TEMPLATE, captcha_question=captcha_question)
                else:
                    log_audit(None, 'failed_login_password', ip, details=f"Invalid password for {email}")
                    flash("Invalid credentials", 'error')
                    return render_template_string(ELEC_OFFICER_LOGIN_TEMPLATE, captcha_question=captcha_question)
            else:
                log_audit(None, 'failed_login_email', ip, details=f"Invalid email {email}")
                flash("Invalid credentials", 'error')
                return render_template_string(ELEC_OFFICER_LOGIN_TEMPLATE, captcha_question=captcha_question)
        except Exception as e:
            log_audit(None, 'failed_login_error', ip, details=str(e))
            flash(f"Error: {e}", 'error')
            return render_template_string(ELEC_OFFICER_LOGIN_TEMPLATE, captcha_question=captcha_question)
        finally:
            if conn:
                conn.close()

    return render_template_string(ELEC_OFFICER_LOGIN_TEMPLATE, captcha_question=captcha_question)

@app.route('/')
def index():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM voters")
        voters = cursor.fetchall()
        return render_template_string(VOTERS_TEMPLATE, voters=voters, message="Welcome to the Voter Registration App!")
    except Exception as e:
        return render_template_string(VOTERS_TEMPLATE, voters=[], message=f"Error loading voters: {e}")
    finally:
        if conn:
            conn.close()

@app.route('/add', methods=['POST'])
def add_voter():
    name = request.form['name']
    email = request.form['email']

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO voters (name, email) VALUES (%s, %s)", (name, email))
        conn.commit()
    except Exception as e:
        print(f"Error adding voter: {e}")
    finally:
        if conn:
            conn.close()
    return redirect(url_for('index'))

@app.route('/edit/<int:voter_id>', methods=['GET', 'POST'])
def edit_voter(voter_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if request.method == 'POST':
            name = request.form['name']
            email = request.form['email']
            cursor.execute("UPDATE voters SET name = %s, email = %s WHERE id = %s", (name, email, voter_id))
            conn.commit()
            return redirect(url_for('index'))
        else: # GET request to show edit form
            cursor.execute("SELECT * FROM voters WHERE id = %s", (voter_id,))
            voter = cursor.fetchone()
            if voter:
                return render_template_string(VOTERS_TEMPLATE, edit_voter=voter, message=f"Editing Voter ID: {voter_id}")
            else:
                return redirect(url_for('index'))
    except Exception as e:
        print(f"Error editing voter: {e}")
        return redirect(url_for('index'))
    finally:
        if conn:
            conn.close()

@app.route('/delete/<int:voter_id>', methods=['POST'])
def delete_voter(voter_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM voters WHERE id = %s", (voter_id,))
        conn.commit()
    except Exception as e:
        print(f"Error deleting voter: {e}")
    finally:
        if conn:
            conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4000, debug=True)