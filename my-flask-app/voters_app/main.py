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
        <p>{{ message }}</p>

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
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for voter in voters %}
                <tr>
                    <td>{{ voter[0] }}</td>
                    <td>{{ voter[1] }}</td>
                    <td>{{ voter[2] }}</td>
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
        <p>No voters registered yet. Add one below!</p>
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS voters (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE
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