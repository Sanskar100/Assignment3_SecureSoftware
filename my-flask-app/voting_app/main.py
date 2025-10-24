from flask import Flask, render_template_string, request, redirect, url_for, flash, session, send_file
import os
import mysql.connector
import bcrypt
import re
import random
import time
import smtplib
import ssl
from email.message import EmailMessage
from datetime import datetime
import io
import hashlib
import hmac

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'a_super_secret_key_for_dev')  # Used for flash messages and sessions

app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600

# Database connection details from environment variables
DB_HOST = os.getenv('DB_HOST', 'db')
DB_USER = os.getenv('DB_USER', 'user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
DB_NAME = os.getenv('DB_NAME', 'mydatabase')

# SMTP / Email configuration (from env)
SMTP_HOST = os.getenv('SMTP_HOST', '')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
EMAIL_FROM = os.getenv('EMAIL_FROM', SMTP_USER)
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'true').lower() in ('1', 'true', 'yes')

# Voter Registration Template
Register_Voter = """
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
        form input[type="text"], form input[type="email"], form input[type="password"], form input[type="number"], form select { width: calc(100% - 22px); padding: 10px; margin-bottom: 10px; border: 1px solid #ccc; border-radius: 4px; }
        form input[type="submit"] { background-color: #28a745; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        form input[type="submit"]:hover { background-color: #218838; }
        .message { background-color: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
        .error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
        .link { margin-top: 10px; text-align: center; }
    </style>
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
            <label for="age">Age:</label><br>
            <input type="number" id="age" name="age" required min="18"><br><br>
            <label for="sex">Sex:</label><br>
            <select id="sex" name="sex" required>
                <option value="Male">Male</option>
                <option value="Female">Female</option>
                <option value="Other">Other</option>
            </select><br><br>
            <label for="password">Password:</label><br>
            <input type="password" id="password" name="password" required><br><br>
            <label for="captcha">CAPTCHA: {{ captcha_question }} (include '-' if negative, no spaces)</label><br>
            <input type="text" id="captcha" name="captcha" required><br><br>
            <input type="submit" value="Register">
        </form>
        <div class="link">
            <a href="/login">Already a Voter? Login Now</a>
        </div>
    </div>
</body>
</html>
"""

# Login Template
Login_Voter = """
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
        .link { margin-top: 10px; text-align: center; }
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
            <label for="captcha">CAPTCHA: {{ captcha_question }} (include '-' if negative, no spaces)</label><br>
            <input type="text" id="captcha" name="captcha" required><br><br>
            <input type="submit" value="Login">
        </form>
        <div class="link">
            <a href="/register">New Voter? Register Now</a>
        </div>
    </div>
</body>
</html>
"""

# Voting Template
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
        .welcome { color: #00796b; font-size: 1.2em; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Cast Your Vote</h1>
        <p class="welcome">Welcome: {{ voter_name }}</p>

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
                        <!-- Show candidate name and party so user can identify who to vote for -->
                        <option value="{{ candidate[0] }}">Candidate {{ loop.index }} — {{ candidate[1] }} ({{ candidate[3] }})</option>
                    {% endfor %}
                {% else %}
                    <option value="">No candidates available</option>
                {% endif %}
            </select><br><br>
            <input type="submit" value="Cast Vote">
        </form>

        <!-- Removed public display of current vote counts per request -->

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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                age INT NOT NULL,
                political_party VARCHAR(255) NOT NULL
            );
        """)
        # Create voters table if not exists
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
        # Add age and sex columns if not exist
        cursor.execute("SHOW COLUMNS FROM voters LIKE 'age'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE voters ADD COLUMN age INT NOT NULL")
        cursor.execute("SHOW COLUMNS FROM voters LIKE 'sex'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE voters ADD COLUMN sex ENUM('Male', 'Female', 'Other') NOT NULL")

        # Votes table migration / creation:
        # - Add voter_hash (VARCHAR) and ensure unique index on it.
        # - Drop strict FOREIGN KEY on voter_id (so numeric id isn't required to be stored).
        # - Keep candidate_id FK.
        cursor.execute("CREATE TABLE IF NOT EXISTS votes (id INT AUTO_INCREMENT PRIMARY KEY) ENGINE=InnoDB;")
        # Ensure voter_hash column exists
        cursor.execute("SHOW COLUMNS FROM votes LIKE 'voter_hash'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE votes ADD COLUMN voter_hash VARCHAR(255) NULL")
        # Ensure candidate_id column exists
        cursor.execute("SHOW COLUMNS FROM votes LIKE 'candidate_id'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE votes ADD COLUMN candidate_id INT NULL")
        # Ensure vote_time column exists
        cursor.execute("SHOW COLUMNS FROM votes LIKE 'vote_time'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE votes ADD COLUMN vote_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        # Remove unique index on voter_id if it exists (we'll enforce uniqueness on voter_hash)
        try:
            cursor.execute("SHOW INDEX FROM votes WHERE Column_name = 'voter_id' AND Non_unique = 0")
            idx = cursor.fetchone()
            if idx:
                # index name in result is at position 2 (Key_name) for SHOW INDEX
                idx_name = idx[2]
                cursor.execute(f"ALTER TABLE votes DROP INDEX `{idx_name}`")
        except Exception:
            pass
        # Drop foreign key constraint on voter_id if exists
        try:
            cursor.execute("""
                SELECT CONSTRAINT_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'votes' AND REFERENCED_TABLE_NAME = 'voters' AND COLUMN_NAME = 'voter_id'
            """, (DB_NAME,))
            fk = cursor.fetchone()
            if fk:
                fk_name = fk[0]
                cursor.execute(f"ALTER TABLE votes DROP FOREIGN KEY `{fk_name}`")
                # allow voter_id to be NULL if present
                cursor.execute("SHOW COLUMNS FROM votes LIKE 'voter_id'")
                if cursor.fetchone():
                    cursor.execute("ALTER TABLE votes MODIFY COLUMN voter_id INT NULL")
        except Exception:
            pass
        # Ensure unique index on voter_hash so each voter_hash can only vote once
        try:
            cursor.execute("SHOW INDEX FROM votes WHERE Column_name = 'voter_hash' AND Non_unique = 0")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE votes ADD UNIQUE INDEX ux_votes_voter_hash (voter_hash(64))")
        except Exception:
            # Some MySQL variants don't permit prefix index on long fields in the same way; fall back to full column unique if possible
            try:
                cursor.execute("ALTER TABLE votes ADD UNIQUE (voter_hash)")
            except Exception:
                pass
        # Ensure candidate_id foreign key exists (re-create if missing)
        try:
            cursor.execute("""
                SELECT CONSTRAINT_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'votes' AND REFERENCED_TABLE_NAME = 'candidates' AND COLUMN_NAME = 'candidate_id'
            """, (DB_NAME,))
            fk_cand = cursor.fetchone()
            if not fk_cand:
                # Add an index then a foreign key constraint (safe even if column already indexed)
                try:
                    cursor.execute("ALTER TABLE votes ADD INDEX idx_votes_candidate_id (candidate_id)")
                except Exception:
                    pass
                try:
                    cursor.execute("ALTER TABLE votes ADD CONSTRAINT fk_votes_candidate FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE")
                except Exception:
                    pass
        except Exception:
            pass

        # Create audit_logs table if not exists
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
        print("Database tables checked/created/migrated successfully.")
    except Exception as e:
        print(f"Error initializing voting database: {e}")
    finally:
        if conn:
            conn.close()

rate_limit = {}
Max_Ratelimit = 5
Rate_Limitwindow = 360
blacklisted_ips = set()

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
    elif operation == '*':
        answer = num1 * num2
    else:  # For '-', ensure non-negative by swapping if needed
        if num1 < num2:
            num1, num2 = num2, num1  # Swap to make num1 >= num2
        answer = num1 - num2
    question = f"What is {num1} {operation} {num2}?"
    return question, answer

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

# New: helper to send vote confirmation emails
def send_vote_confirmation_email(recipient_email, voter_name, candidate_name, voter_id=None, ip_address=None):
    # Simplified wrapper for a vote confirmation using the generic sender
    subject = "Vote Confirmation"
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    body = f"""Hello {voter_name},

This is a confirmation that your vote was received.

Voter ID: {voter_id or 'N/A'}
Candidate: {candidate_name}
Time: {timestamp}

If you did not cast this vote, please contact the election administrators immediately.

Regards,
Voting System
"""
    return send_system_email(recipient_email, subject, body, user_id=voter_id, ip_address=ip_address, tag='vote_confirmation')

def send_system_email(recipient_email, subject, body, user_id=None, ip_address=None, tag='system'):
    """
    Robust email sender:
    - Uses configured SMTP_HOST/SMTP_PORT with optional STARTTLS or SSL.
    - If no SMTP_HOST configured, attempts localhost (port 25).
    - If delivery is not possible, prints email to stdout as a fallback (and still audits).
    Returns True if email was "sent" (or printed), False on fatal failure.
    """
    global SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_USE_TLS, EMAIL_FROM

    # Ensure a sensible From address
    if not EMAIL_FROM:
        EMAIL_FROM = SMTP_USER or 'no-reply@example.com'

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = EMAIL_FROM
    msg['To'] = recipient_email
    msg.set_content(body)

    # Try configured SMTP
    try:
        if SMTP_HOST:
            # Prefer TLS upgrade when requested
            if EMAIL_USE_TLS:
                with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
                    server.ehlo()
                    try:
                        server.starttls(context=ssl.create_default_context())
                        server.ehlo()
                    except Exception as e:
                        # If STARTTLS fails, continue and try without it (but log)
                        print(f"Warning: STARTTLS failed: {e}")
                    # Login only if credentials provided
                    if SMTP_USER and SMTP_PASSWORD:
                        server.login(SMTP_USER, SMTP_PASSWORD)
                    server.send_message(msg)
            else:
                # If using SSL port (commonly 465) prefer SMTP_SSL
                if SMTP_PORT == 465:
                    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ssl.create_default_context(), timeout=10) as server:
                        if SMTP_USER and SMTP_PASSWORD:
                            server.login(SMTP_USER, SMTP_PASSWORD)
                        server.send_message(msg)
                else:
                    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
                        if SMTP_USER and SMTP_PASSWORD:
                            server.login(SMTP_USER, SMTP_PASSWORD)
                        server.send_message(msg)
            audit_log(user_id, f'email_sent_{tag}', f'Email sent to {recipient_email} via {SMTP_HOST}:{SMTP_PORT}', ip_address)
            return True
        else:
            # Try localhost (no auth)
            try:
                with smtplib.SMTP('localhost', 25, timeout=10) as server:
                    server.send_message(msg)
                audit_log(user_id, f'email_sent_{tag}', f'Email sent to {recipient_email} via localhost', ip_address)
                return True
            except Exception as e_local:
                # As last resort, print the email to stdout so it's available in logs
                print("SMTP not configured and localhost send failed. Printing email to stdout as fallback.")
                print("----- EMAIL START -----")
                print(f"To: {recipient_email}")
                print(f"Subject: {subject}")
                print(body)
                print("----- EMAIL END -----")
                audit_log(user_id, f'email_printed_{tag}', f'Email printed to console for {recipient_email}: {e_local}', ip_address)
                return True
    except Exception as e:
        print(f"Failed to send email to {recipient_email}: {e}")
        audit_log(user_id, f'email_failed_{tag}', f'Failed to send email to {recipient_email}: {e}', ip_address)
        return False

# New helper: create an in-memory text receipt for download
def make_vote_receipt_bytes(voter_name, candidate_name, voter_id=None, ip_address=None):
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    # Mask the voter identifier so numeric id is not directly revealed; if it's a long hash use short prefix
    masked_identifier = 'N/A'
    if voter_id:
        s = str(voter_id)
        if len(s) >= 16:  # likely a hash
            masked_identifier = f"{s[:8]}...{s[-4:]}"
        else:
            # If numeric, do not include raw id; instead include hashed short form
            try:
                masked_identifier = make_voter_hash(s)[:12]
            except Exception:
                masked_identifier = 'masked'
    receipt_text = f"""Vote Receipt
Voter: {voter_name}
Voter Identifier: {masked_identifier}
Candidate: {candidate_name}
Time: {timestamp}
IP: {ip_address or 'N/A'}

This is an official receipt for your vote.
"""
    buf = io.BytesIO()
    buf.write(receipt_text.encode('utf-8'))
    buf.seek(0)
    filename_safe = (str(voter_id)[:8] if voter_id else 'unknown')
    filename = f"vote_receipt_{filename_safe}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.txt"
    return buf, filename

def rate_limitcheck(ip):
    now = time.time()
    if ip in rate_limit:
        count, last_time = rate_limit[ip]
        if now - last_time < Rate_Limitwindow:
            if count >= Max_Ratelimit:
                return False
            rate_limit[ip] = (count + 1, last_time)
            return True
        else:
            rate_limit[ip] = (1, now)
            return True
    else:
        rate_limit[ip] = (1, now)
        return True

def is_ip_blacklisted(ip):
    return ip in blacklisted_ips

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        age = request.form['age']
        sex = request.form['sex']
        password = request.form['password']
        captcha_response = request.form['captcha'].strip()
        captcha_answer = session.get('captcha_answer')

        print(f"Register attempt: email={email}, captcha_response='{captcha_response}', captcha_answer={captcha_answer}")

        if not captcha_answer or str(captcha_response) != str(captcha_answer):
            flash("CAPTCHA answer is incorrect. Please try again.", 'error')
            print(f"Register failed for {email}: CAPTCHA incorrect")
            return redirect(url_for('register'))

        try:
            age_int = int(age)
            if age_int < 18:
                flash("You must be at least 18 years old to register.", 'error')
                print(f"Register failed for {email}: Underage")
                return redirect(url_for('register'))
        except ValueError:
            flash("Invalid age provided.", 'error')
            print(f"Register failed for {email}: Invalid age")
            return redirect(url_for('register'))

        password_check = password_validation(password)
        if password_check != True:
            flash(password_check, 'error')
            print(f"Register failed for {email}: {password_check}")
            return redirect(url_for('register'))

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM voters WHERE email = %s", (email,))
            if cursor.fetchone():
                flash("Email already registered. Please use a different email.", 'error')
                print(f"Register failed for {email}: Email already registered")
                return redirect(url_for('register'))

            cursor.execute("INSERT INTO voters (name, email, age, sex, password) VALUES (%s, %s, %s, %s, %s)", (name, email, age_int, sex, hashed_password))
            conn.commit()
            flash("Registration successful! You can now log in.", 'success')
            print(f"Registration successful for {email}")

            # Send a system-generated registration email (best-effort, won't block user)
            try:
                subject = "Welcome to the Voting System"
                body = f"""Hello {name},

Thank you for registering as a voter.

Your account has been created and is pending approval by the election administrators. You will receive another email when your account is approved.

If you did not register, please contact support.

Regards,
Voting System
"""
                send_system_email(email, subject, body, user_id=None, ip_address=request.remote_addr, tag='registration')
            except Exception as ee:
                print(f"Failed to send registration email to {email}: {ee}")
                audit_log(None, 'email_registration_failed', f'Failed to send registration email to {email}: {ee}', request.remote_addr)

            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash(f"Database error: {err}", 'error')
            print(f"Register failed for {email}: Database error - {err}")
        except Exception as e:
            flash(f"An unexpected error occurred: {e}", 'error')
            print(f"Register failed for {email}: Unexpected error - {e}")
        finally:
            if conn:
                conn.close()
        return redirect(url_for('register'))
    else:
        captcha_question, captcha_answer = captcha_generation()
        session['captcha_answer'] = captcha_answer
        return render_template_string(Register_Voter, captcha_question=captcha_question)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        captcha_response = request.form['captcha'].strip()
        captcha_answer = session.get('captcha_answer')
        ip_address = request.remote_addr
        print(f"Login attempt: email={email}, captcha_response='{captcha_response}', captcha_answer={captcha_answer}")

        if not rate_limitcheck(ip_address):
            flash("Too many login attempts. Please try again later.", 'error')
            print(f"Login failed for {email}: Rate limit triggered")
            return redirect(url_for('login'))

        if not captcha_answer or str(captcha_response) != str(captcha_answer):
            flash("CAPTCHA answer is incorrect. Please try again.", 'error')
            print(f"Login failed for {email}: CAPTCHA incorrect")
            return redirect(url_for('login'))

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, password, status, role FROM voters WHERE email = %s", (email,))
            voter = cursor.fetchone()
            if voter:
                voter_id, voter_name, hashed_password, status, role = voter
                if bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')):
                    if status == 'accepted' and role == 'voter':
                        session['voter_id'] = voter_id
                        session['voter_name'] = voter_name
                        audit_log(voter_id, 'login_success', 'Voter logged in successfully', ip_address)
                        flash("Login successful!", 'success')
                        print(f"Login successful for {email}")
                        return redirect(url_for('index'))
                    else:
                        flash("Account not approved or invalid role.", 'error')
                        print(f"Login failed for {email}: Account not approved or invalid role (status={status}, role={role})")
                else:
                    audit_log(None, 'failed_login', 'Invalid password', ip_address)
                    flash("Invalid credentials.", 'error')
                    print(f"Login failed for {email}: Invalid password")
            else:
                audit_log(None, 'failed_login', 'Invalid email', ip_address)
                flash("Invalid credentials.", 'error')
                print(f"Login failed for {email}: Invalid email")
        except Exception as e:
            flash(str(e), 'error')
            print(f"Login failed for {email}: Exception - {e}")
        finally:
            if conn:
                conn.close()
        return redirect(url_for('login'))
    else:
        captcha_question, captcha_answer = captcha_generation()
        session['captcha_answer'] = captcha_answer
        return render_template_string(Login_Voter, captcha_question=captcha_question)

@app.route('/logout')
def logout():
    audit_log(session.get('voter_id'), 'logout', 'User logged out', request.remote_addr)
    session.clear()
    flash("Logged out successfully.", 'success')
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'voter_id' not in session:
        flash("Please log in to access the voting page.", 'error')
        return redirect(url_for('login'))
    
    conn = None
    candidates = []
    vote_counts = []  # intentionally empty — do not show vote counts publicly
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get candidates (used to populate the hidden/generic dropdown)
        cursor.execute("SELECT id, name, age, political_party FROM candidates")
        candidates = cursor.fetchall()

        # Do not query or compute vote totals here — removed per request

        return render_template_string(VOTING_TEMPLATE, candidates=candidates, vote_counts=vote_counts, voter_name=session.get('voter_name', 'Voter'))
    except Exception as e:
        flash(f"Error loading data: {e}", 'error')
        return render_template_string(VOTING_TEMPLATE, candidates=[], vote_counts=[], voter_name=session.get('voter_name', 'Voter'))
    finally:
        if conn:
            conn.close()

@app.route('/vote', methods=['POST'])
def vote():
    if 'voter_id' not in session:
        flash("Please log in to access the voting page.", 'error')
        return redirect(url_for('login'))
    
    candidate_id = request.form['candidate_id']
    voter_id = session['voter_id']

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Create deterministic hash for this voter (so DB stores non-reversible token)
        voter_hash = make_voter_hash(voter_id)

        # 1. Check if voter has already voted by checking voter_hash uniqueness
        cursor.execute("SELECT id FROM votes WHERE voter_hash = %s", (voter_hash,))
        if cursor.fetchone():
            flash("You have already cast your vote!", 'info')
            return redirect(url_for('index'))
          
        cursor.execute("SELECT id, name FROM candidates WHERE id = %s", (candidate_id,))
        candidate_row = cursor.fetchone()
        if not candidate_row:
            flash("Error: Invalid candidate selected.", 'error')
            return redirect(url_for('index'))

        candidate_name = candidate_row[1]

        # 3. Cast the vote storing only voter_hash (not the plain numeric voter_id)
        cursor.execute("INSERT INTO votes (voter_hash, candidate_id) VALUES (%s, %s)", (voter_hash, candidate_id))
        conn.commit()
        flash("Your vote has been cast successfully!", 'success')

        # Instead of sending an email, generate a downloadable receipt and return it
        try:
            # Fetch voter's name for the receipt (best-effort)
            cursor.execute("SELECT name FROM voters WHERE id = %s", (voter_id,))
            voter_row = cursor.fetchone()
            voter_name = (voter_row[0] if voter_row else session.get('voter_name', 'Voter'))

            # Use the voter_hash (masked) rather than raw numeric id in receipt
            buf, filename = make_vote_receipt_bytes(voter_name, candidate_name, voter_id=voter_hash, ip_address=request.remote_addr)
            audit_log(voter_id, 'receipt_generated', f'Receipt generated for vote for {candidate_name}', request.remote_addr)
            # Return the receipt as a downloadable file (text)
            return send_file(buf, as_attachment=True, download_name=filename, mimetype='text/plain')
        except Exception as e:
            # Log but keep user experience (redirect) if download failed
            print(f"Failed to generate/download receipt: {e}")
            audit_log(voter_id, 'receipt_generation_failed', f'Failed to generate receipt: {e}', request.remote_addr)

    except Exception as e:
        flash(f"An unexpected error occurred: {e}", 'error')
    finally:
        if conn:
            conn.close()
    return redirect(url_for('index'))

# New: secret for hashing voter ids (use a strong secret in prod via env)
VOTE_HASH_SECRET = os.getenv('VOTE_HASH_SECRET', 'default_dev_vote_secret')

# New helper: deterministic HMAC-based voter hash (so same voter -> same hash, but not reversible without secret)
def make_voter_hash(voter_id):
    # ensure string input
    msg = str(voter_id).encode('utf-8')
    key = VOTE_HASH_SECRET.encode('utf-8')
    return hmac.new(key, msg, hashlib.sha256).hexdigest()

def wait_for_db(max_retries=60, retry_delay=2):
    retries = 0
    while retries < max_retries:
        try:
            conn = get_db_connection()
            conn.close()
            print("DB connection successful.")
            init_db()  # Call init_db() here, after confirming the DB is ready
            return True
        except mysql.connector.Error as err:
            print(f"DB not ready yet: {err}. Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            retries += 1
    print("Failed to connect to DB after max retries.")
    return False

if __name__ == '__main__':
    if not wait_for_db():
        exit(1)  # Exit if DB never becomes ready
    app.run(host='0.0.0.0', port=2000, debug=True)
VOTE_HASH_SECRET = os.getenv('VOTE_HASH_SECRET', 'default_dev_vote_secret')

# New helper: deterministic HMAC-based voter hash (so same voter -> same hash, but not reversible without secret)
def make_voter_hash(voter_id):
    # ensure string input
    msg = str(voter_id).encode('utf-8')
    key = VOTE_HASH_SECRET.encode('utf-8')
    return hmac.new(key, msg, hashlib.sha256).hexdigest()

def wait_for_db(max_retries=60, retry_delay=2):
    retries = 0
    while retries < max_retries:
        try:
            conn = get_db_connection()
            conn.close()
            print("DB connection successful.")
            init_db()  # Call init_db() here, after confirming the DB is ready
            return True
        except mysql.connector.Error as err:
            print(f"DB not ready yet: {err}. Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            retries += 1
    print("Failed to connect to DB after max retries.")
    return False

if __name__ == '__main__':
    if not wait_for_db():
        exit(1)  # Exit if DB never becomes ready
    app.run(host='0.0.0.0', port=2000, debug=True)
