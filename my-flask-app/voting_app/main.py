from flask import Flask, render_template_string, request, redirect, url_for, flash, session
import os
import mysql.connector
import bcrypt
import re
import random
from email.mime.text import MIMEText
import smtplib
import time




app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'a_super_secret_key_for_dev') # Used for flash messages and sessions

app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600

# Database connection details from environment variables
DB_HOST = os.getenv('DB_HOST', 'db')
DB_USER = os.getenv('DB_USER', 'user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
DB_NAME = os.getenv('DB_NAME', 'mydatabase')


#Voter_Regestration
Register_Voter="""
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>Register</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background-color: #f0f8ff; color: #333; }
        .container { max-width: 400px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #28a745; }
        form { padding: 15px; border: 1px solid #ccf; border-radius: 5px; background-color: #f7fcff; }
        form input[type="text"], form input[type="email"], form input[type="password"] { width: calc(100% - 22px); padding: 10px; margin-bottom: 10px; border: 1px solid #ccc; border-radius: 4px; }
        form input[type="submit"] { background-color: #28a745; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        form input[type="submit"]:hover { background-color: #218838; }
        .message { background-color: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
        .error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
</head>
<body>
    <div class="container">
        <h1>Voter Register</h1>
          {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
            <div class="{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
        {% endwith %}

        <form method="POST" action="/register">
            <label for="name">Name:</label><br>
            <input type="text" id="name" name="name" required><br><br>
            <label for="email">Email:</label><br>
            <input type="email" id="email" name="email" required><br><br>
            <label for="password">Password:</label><br>
            <input type="password" id="password" name="password" required><br><br>
            <label for="captcha">CAPTCHA: {{ captcha_question }}</label><br>
            <input type="text" id="captcha" name="captcha" required><br><br>
            <input type="submit" value="Register">
        </form>
    </div>
    </body>
</html>
"""


#login section
Login_Voter="""
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>Login</title>
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
        <h1>Voter Login</h1>
        {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
            <div class="message {{ category }}">{{ message }}</div>
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

Voter_OTP="""
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
    <div class="container">
        <h1>OTP Verification</h1>
        {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
            <div class="message {{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
        {% endwith %}

        <form method="POST" action="/verify_otp">
            <label for="otp">Enter OTP sent to your email:</label><br>
            <input type="text" id="otp" name="otp" required><br><br>
            <input type="submit" value="Verify OTP">
        </form>
    </div>
</body>
</html>
"""

    

# HTML templates for rendering
VOTING_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>Cast Your Vote</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background-color: #e0f7fa; color: #333; }
        .container { max-width: 800px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1, h2, h3 { color: #00796b; }
        .message { padding: 10px; margin-bottom: 15px; border-radius: 5px; }
        .message.success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .message.error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .message.info { background-color: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        form { margin-top: 20px; padding: 15px; border: 1px solid #b2ebf2; border-radius: 5px; background-color: #e0f2f7; }
        form select { width: calc(100% - 22px); padding: 10px; margin-bottom: 10px; border: 1px solid #99d; border-radius: 4px; }
        form input[type="submit"] { background-color: #009688; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        form input[type="submit"]:hover { background-color: #00796b; }
        .current-votes { margin-top: 30px; }
        .vote-item { background-color: #f0f0f0; border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; border-radius: 5px; display: flex; justify-content: space-between; align-items: center; }
        .vote-count { font-weight: bold; font-size: 1.2em; color: #00796b; }
        .logout { margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Cast Your Vote</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
            <div class="message {{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
        {% endwith %}

        <h2>Vote Now!</h2>
        <form method="POST" action="/vote">
            <label for="candidate_id">Select Candidate:</label><br>
            <select id="candidate_id" name="candidate_id" required>
                {% if candidates %}
                    {% for candidate in candidates %}
                        <option value="{{ candidate[0] }}">{{ candidate[1] }} ({{ candidate[4] }})</option>
                    {% endfor %}
                {% else %}
                    <option value="">No candidates available</option>
                {% endif %}
            </select><br><br>
            <input type="submit" value="Cast Vote">
        </form>

        <div class="current-votes">
            <h2>Current Vote Counts</h2>
            {% if vote_counts %}
                {% for count in vote_counts %}
                    <div class="vote-item">
                        <span>{{ count[0] }}</span>
                        <span class="vote-count">{{ count[1] }} votes</span>
                    </div>
                {% endfor %}
            {% else %}
                <p>No votes cast yet.</p>
            {% endif %}
        </div>

        <div class="logout">
            <a href="/logout">Logout</a>
        </div>
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
        # Ensure candidates and voters tables exist (they are created by their respective apps)
        # This app will create its own 'votes' table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS votes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                voter_id INT NOT NULL,
                candidate_id INT NOT NULL,
                vote_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (voter_id), # Ensure one vote per voter
                FOREIGN KEY (voter_id) REFERENCES voters(id) ON DELETE CASCADE,
                FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS voters (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                status ENUM('submitted', 'accepted') DEFAULT 'submitted',
                role ENUM('voter') DEFAULT 'voter'
            );
        """)
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
        print(f"Error initializing voting database: {e}")
    finally:
        if conn:
            conn.close()

@app.before_first_request
def before_first_request():
    init_db()

def password_validation(password):
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter."
    if not re.search(r"[0-9]", password):
        return "Password must contain at least one digit."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return "Password must contain at least one special character."
    return True

def captcha_generation():
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    operation = random.choice(['+', '-', '*'])
    if operation == '+':
        answer = num1 + num2
    elif operation == '-':
        answer = num1 - num2
    else:
        answer = num1 * num2
    question = f"What is {num1} {operation} {num2}?"
    return question, answer

# def email_otp(email, otp):
#     msg = MIMEText(f"Your OTP for login is: {otp}. Use within 5 minutes.")
#     msg['Subject'] = 'Voter Login OTP Code'
#     msg['From'] = SMTP_USER
#     msg['To'] = email
#     try:
#         with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
#             server.starttls()
#             server.login(SMTP_USER, SMTP_PASSWORD)
#             server.sendmail(SMTP_USER, [email], msg.as_string())
#             server.quit()
#             return True
#     except Exception as e:
#         print(f"Failed to send OTP to: {e}")
#         return False
    
def audit_log(user_id, action, details, ip_address):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs (user_id, action, details, ip_address)
            VALUES (%s, %s, %s, %s)
        """, (user_id, action, details, ip_address))
        conn.commit()
    except Exception as e:
        print(f"Failed to log audit entry: {e}")
    finally:
        if conn:
            conn.close()

def rate_limitcheck(ip):
    now=time.time()
    if ip in rate_limit:
        count, last_time=rate_limit[ip]
        if now - last_time < Rate_Limitwindow:
            if count >= Max_Ratelimit:
                return False
            rate_limit[ip]=(count+1, last_time)
            return True
        else:
            rate_limit[ip]=(1, now)
            return True
    else:
        rate_limit[ip]=(1, now)
        return True
rate_limit={}
Max_Ratelimit=5
Rate_Limitwindow=360 # 6 minute

# def is_ip_blacklisted(ip):
#     return ip in blacklisted_ips
# blacklisted_ips=set()

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        captcha_response = request.form['captcha']
        captcha_answer = session.get('captcha_answer')

        if not captcha_answer or str(captcha_response) != str(captcha_answer):
            flash("CAPTCHA answer is incorrect. Please try again.", 'error')
            return redirect(url_for('register'))

        password_check = password_validation(password)
        if password_check != True:
            flash(password_check, 'error')
            return redirect(url_for('register'))

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM voters WHERE email = %s", (email,))
            if cursor.fetchone():
                flash("Email already registered. Please use a different email.", 'error')
                return redirect(url_for('register'))

            cursor.execute("INSERT INTO voters (name, email, password) VALUES (%s, %s, %s)", (name, email, hashed_password))
            conn.commit()
            flash("Registration successful! You can now log in.", 'success')
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash(f"Database error: {err}", 'error')
        except Exception as e:
            flash(f"An unexpected error occurred: {e}", 'error')
        finally:
            if conn:
                conn.close()
        return redirect(url_for('register'))
    else:
        captcha_question, captcha_answer = captcha_generation()
        session['captcha_answer'] = captcha_answer
        return render_template_string(Register_Voter, captcha_question=captcha_question)



@app.route('/')
def index():
    conn = None
    candidates = []
    vote_counts = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get candidates
        cursor.execute("SELECT id, name, political_party FROM candidates")
        candidates = cursor.fetchall()

        # Get vote counts
        cursor.execute("""
            SELECT c.name, COUNT(v.id) AS total_votes
            FROM candidates c
            LEFT JOIN votes v ON c.id = v.candidate_id
            GROUP BY c.name
            ORDER BY total_votes DESC;
        """)
        vote_counts = cursor.fetchall()

        return render_template_string(VOTING_TEMPLATE, candidates=candidates, vote_counts=vote_counts, message="Please enter your email and cast your vote!")
    except Exception as e:
        flash(f"Error loading data: {e}", 'error')
        return render_template_string(VOTING_TEMPLATE, candidates=[], vote_counts=[], message=f"Error loading voting data: {e}")
    finally:
        if conn:
            conn.close()

@app.route('/vote', methods=['POST'])
def cast_vote():
    voter_email = request.form['voter_email']
    candidate_id = request.form['candidate_id']
    session['voter_email'] = voter_email # Remember email in session

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(buffered=True) # buffered=True needed for checking rowcount after execute

        # 1. Verify voter exists and get voter_id
        cursor.execute("SELECT id FROM voters WHERE email = %s", (voter_email,))
        voter = cursor.fetchone()
        if not voter:
            flash("Error: Voter not registered. Please register your email first.", 'error')
            return redirect(url_for('index'))
        voter_id = voter[0]

        # 2. Check if voter has already voted
        cursor.execute("SELECT id FROM votes WHERE voter_id = %s", (voter_id,))
        if cursor.fetchone():
            flash("You have already cast your vote!", 'info')
            return redirect(url_for('index'))

        # 3. Verify candidate exists (optional, but good for data integrity)
        cursor.execute("SELECT id FROM candidates WHERE id = %s", (candidate_id,))
        if not cursor.fetchone():
            flash("Error: Invalid candidate selected.", 'error')
            return redirect(url_for('index'))

        # 4. Cast the vote
        cursor.execute("INSERT INTO votes (voter_id, candidate_id) VALUES (%s, %s)", (voter_id, candidate_id))
        conn.commit()
        flash("Your vote has been cast successfully!", 'success')

    except mysql.connector.Error as err:
        flash(f"Database error: {err}", 'error')
        conn.rollback() # Rollback in case of an error
    except Exception as e:
        flash(f"An unexpected error occurred: {e}", 'error')
    finally:
        if conn:
            conn.close()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=2000, debug=True)