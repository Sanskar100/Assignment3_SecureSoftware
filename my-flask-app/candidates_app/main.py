from flask import Flask, render_template_string, request, redirect, url_for, flash, session
import os
import mysql.connector
import bcrypt
import random
import time
import re

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'a_super_secret_key_for_dev')
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  

# Database configurations
DB_HOST = os.getenv('DB_HOST', 'db')
DB_USER = os.getenv('DB_USER', 'user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
DB_NAME = os.getenv('DB_NAME', 'mydatabase')

# Security configurations
BLACKLISTED_IPS = []
RATE_LIMIT_WINDOW = 60  # 1-minute window
RATE_LIMIT_MAX = 5  # Max 5 attempts per window
rate_limit_dict = {}

# HTML templates
LOGIN_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>Admin Login</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }
        .container { max-width: 400px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #0056b3; }
        form { padding: 15px; border: 1px solid #eee; border-radius: 5px; background-color: #fafafa; }
        form input[type="email"], form input[type="password"], form input[type="text"] { width: calc(100% - 22px); padding: 10px; margin-bottom: 10px; border: 1px solid #ccc; border-radius: 4px; }
        form input[type="submit"] { background-color: #007bff; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        form input[type="submit"]:hover { background-color: #0056b3; }
        .message { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
        .error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Admin Login</h1>
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

HOME_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>Candidate Management</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }
        .container { max-width: 800px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1, h2 { color: #0056b3; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        form { margin-top: 20px; padding: 15px; border: 1px solid #eee; border-radius: 5px; background-color: #fafafa; }
        form input[type="text"], form input[type="number"], form select { width: calc(100% - 22px); padding: 10px; margin-bottom: 10px; border: 1px solid #ccc; border-radius: 4px; }
        form input[type="submit"] { background-color: #007bff; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        form input[type="submit"]:hover { background-color: #0056b3; }
        .delete-form { display: inline; }
        .delete-button { background-color: #dc3545; color: white; padding: 5px 10px; border: none; border-radius: 4px; cursor: pointer; }
        .delete-button:hover { background-color: #c82333; }
        .message { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
        .error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
        .logout-link { color: #007bff; text-decoration: none; }
        .logout-link:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Candidate Management Application</h1>
        <p>Welcome, {{ session['admin_name'] }}! <a class="logout-link" href="/logout">Logout</a></p>
        {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
            <div class="{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
        {% endwith %}
        <h2>Current Candidates</h2>
        {% if candidates %}
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Sex</th>
                    <th>Age</th>
                    <th>Political Party</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for candidate in candidates %}
                <tr>
                    <td>{{ candidate[0] }}</td>
                    <td>{{ candidate[1] }}</td>
                    <td>{{ candidate[2] }}</td>
                    <td>{{ candidate[3] }}</td>
                    <td>{{ candidate[4] }}</td>
                    <td>
                        <form class="delete-form" method="POST" action="/delete/{{ candidate[0] }}">
                            <input type="submit" value="Delete" class="delete-button">
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <p>No candidates found. Add one below!</p>
        {% endif %}

        <h2>Add New Candidate</h2>
        <form method="POST" action="/add">
            <label for="name">Name:</label><br>
            <input type="text" id="name" name="name" required><br><br>
            <label for="sex">Sex:</label><br>
            <select id="sex" name="sex" required>
                <option value="Male">Male</option>
                <option value="Female">Female</option>
                <option value="Other">Other</option>
            </select><br><br>
            <label for="age">Age:</label><br>
            <input type="number" id="age" name="age" required min="18"><br><br>
            <label for="party">Political Party:</label><br>
            <input type="text" id="party" name="party" required><br><br>
            <input type="submit" value="Add Candidate">
        </form>
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
        # Ensure candidates table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                sex ENUM('Male', 'Female', 'Other') NOT NULL,
                age INT NOT NULL,
                political_party VARCHAR(255) NOT NULL
            );
        """)
        # Ensure admins table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                role ENUM('admin') DEFAULT 'admin'
            );
        """)
        # Ensure audit_logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                action VARCHAR(255),
                details TEXT,
                ip_address VARCHAR(45),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        print("Database tables checked/created successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")
    finally:
        if conn:
            conn.close()

def require_admin_login(f):
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash("Please log in as an admin to access this page", 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def generate_captcha():
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    operation = random.choice(['+', '-'])
    question = f"What is {num1} {operation} {num2}?"
    answer = num1 + num2 if operation == '+' else num1 - num2
    return question, str(answer)

def log_audit(user_id, action, ip, details=''):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO audit_logs (user_id, action, ip_address, details) VALUES (%s, %s, %s, %s)", 
                       (user_id, action, ip, details))
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

@app.before_request
def before_first_request():
    init_db()

@app.route('/login', methods=['GET', 'POST'])
def login():
    ip = request.remote_addr
    if is_ip_blacklisted(ip) or not check_rate_limit(ip):
        log_audit(None, 'access_denied', ip, details="Rate limit or blacklist violation")
        flash("Access denied due to rate limit or blacklist", 'error')
        return render_template_string(LOGIN_TEMPLATE, captcha_question="")
    
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password']
        captcha_response = request.form['captcha']
        captcha_answer = session.get('captcha_answer')
        
        if captcha_response != captcha_answer:
            log_audit(None, 'failed_login', ip, details="Incorrect CAPTCHA")
            flash("CAPTCHA incorrect. Please try again.", 'error')
            captcha_question, captcha_answer = generate_captcha()
            session['captcha_answer'] = captcha_answer
            return render_template_string(LOGIN_TEMPLATE, captcha_question=captcha_question)

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, password, role FROM admins WHERE email = %s", (email,))
            admin = cursor.fetchone()
            if admin:
                admin_id, admin_name, hashed_password, role = admin
                if bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')):
                    if role == 'admin':
                        session['admin_id'] = admin_id
                        session['admin_name'] = admin_name
                        log_audit(admin_id, 'login_success', ip)
                        flash("Login successful", 'message')
                        return redirect(url_for('index'))
                    else:
                        log_audit(admin_id, 'failed_login_role', ip, details=f"Invalid role for {email}")
                        flash("Invalid admin role", 'error')
                else:
                    log_audit(None, 'failed_login_password', ip, details=f"Invalid password for {email}")
                    flash("Invalid credentials", 'error')
            else:
                log_audit(None, 'failed_login_email', ip, details=f"Invalid email {email}")
                flash("Invalid credentials", 'error')
            captcha_question, captcha_answer = generate_captcha()
            session['captcha_answer'] = captcha_answer
            return render_template_string(LOGIN_TEMPLATE, captcha_question=captcha_question)
        except Exception as e:
            log_audit(None, 'failed_login_error', ip, details=str(e))
            flash(f"Error: {e}", 'error')
            captcha_question, captcha_answer = generate_captcha()
            session['captcha_answer'] = captcha_answer
            return render_template_string(LOGIN_TEMPLATE, captcha_question=captcha_question)
        finally:
            if conn:
                conn.close()
    else:
        captcha_question, captcha_answer = generate_captcha()
        session['captcha_answer'] = captcha_answer
        return render_template_string(LOGIN_TEMPLATE, captcha_question=captcha_question)

@app.route('/')
@require_admin_login
def index():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, sex, age, political_party FROM candidates")
        candidates = cursor.fetchall()
        log_audit(session['admin_id'], 'view_candidates', request.remote_addr)
        return render_template_string(HOME_TEMPLATE, candidates=candidates, message="Welcome to the Candidate Management App!")
    except Exception as e:
        log_audit(session['admin_id'], 'view_candidates_error', request.remote_addr, details=str(e))
        flash(f"Error loading candidates: {e}", 'error')
        return render_template_string(HOME_TEMPLATE, candidates=[], message=f"Error loading candidates: {e}")
    finally:
        if conn:
            conn.close()

@app.route('/add', methods=['POST'])
@require_admin_login
def add_candidate():
    name = request.form['name'].strip()
    sex = request.form['sex']
    try:
        age = int(request.form['age'])
        if age < 18:
            flash("Age must be at least 18", 'error')
            return redirect(url_for('index'))
    except ValueError:
        flash("Invalid age format", 'error')
        return redirect(url_for('index'))
    party = request.form['party'].strip()

    # Input validation
    if not re.match(r'^[A-Za-z\s]{1,255}$', name):
        flash("Invalid name format. Use letters and spaces only.", 'error')
        return redirect(url_for('index'))
    if not re.match(r'^[A-Za-z\s]{1,255}$', party):
        flash("Invalid political party format. Use letters and spaces only.", 'error')
        return redirect(url_for('index'))
    if sex not in ['Male', 'Female', 'Other']:
        flash("Invalid sex selection", 'error')
        return redirect(url_for('index'))

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO candidates (name, sex, age, political_party) VALUES (%s, %s, %s, %s)",
                       (name, sex, age, party))
        conn.commit()
        log_audit(session['admin_id'], 'add_candidate', request.remote_addr, details=f"Added candidate: {name}")
        flash("Candidate added successfully", 'message')
    except Exception as e:
        log_audit(session['admin_id'], 'add_candidate_error', request.remote_addr, details=str(e))
        flash(f"Error adding candidate: {e}", 'error')
    finally:
        if conn:
            conn.close()
    return redirect(url_for('index'))

@app.route('/delete/<int:candidate_id>', methods=['POST'])
@require_admin_login
def delete_candidate(candidate_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM candidates WHERE id = %s", (candidate_id,))
        candidate = cursor.fetchone()
        if candidate:
            cursor.execute("DELETE FROM candidates WHERE id = %s", (candidate_id,))
            conn.commit()
            log_audit(session['admin_id'], 'delete_candidate', request.remote_addr, details=f"Deleted candidate ID {candidate_id}: {candidate[0]}")
            flash("Candidate deleted successfully", 'message')
        else:
            flash("Candidate not found", 'error')
    except Exception as e:
        log_audit(session['admin_id'], 'delete_candidate_error', request.remote_addr, details=str(e))
        flash(f"Error deleting candidate: {e}", 'error')
    finally:
        if conn:
            conn.close()
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    log_audit(session.get('admin_id'), 'logout', request.remote_addr)
    session.clear()
    flash("Logged out successfully", 'message')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)