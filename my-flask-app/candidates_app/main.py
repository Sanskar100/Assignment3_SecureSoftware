from flask import Flask, render_template_string, request, redirect, url_for, flash, session, Response
import os
import mysql.connector
import bcrypt
import random
import time
import re
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime

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
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 5
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
        .action-buttons { display: flex; gap: 5px; }
        .edit-button { background-color: #ffc107; color: #212529; padding: 5px 10px; border: none; border-radius: 4px; cursor: pointer; }
        .edit-button:hover { background-color: #e0a800; }
        .delete-form { display: inline; }
        .delete-button { background-color: #dc3545; color: white; padding: 5px 10px; border: none; border-radius: 4px; cursor: pointer; }
        .delete-button:hover { background-color: #c82333; }
        .message { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
        .error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
        .logout-link, .nav-link { color: #007bff; text-decoration: none; margin-right: 10px; }
        .logout-link:hover, .nav-link:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Candidate Management Application</h1>
        <p>Welcome, {{ session['admin_name'] }}! 
           <a class="nav-link" href="/manage_voters">Manage Voters</a> |
           <a class="nav-link" href="/manage_elec_officers">Manage Election Officers</a> |
           <a class="nav-link" href="/audit_logs">View Audit Logs</a> |
           <a class="nav-link" href="/export_tally">Download Tally (XML)</a> |
           <a class="logout-link" href="/logout">Logout</a></p>
        {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
            <div class="{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
        {% endwith %}
        {% if edit_candidate %}
        <h2>Edit Candidate (ID: {{ edit_candidate[0] }})</h2>
        <form method="POST" action="/edit/{{ edit_candidate[0] }}">
            <label for="name">Name:</label><br>
            <input type="text" id="name" name="name" value="{{ edit_candidate[1] }}" required><br><br>
            <label for="sex">Sex:</label><br>
            <select id="sex" name="sex" required>
                <option value="Male" {% if edit_candidate[2] == 'Male' %}selected{% endif %}>Male</option>
                <option value="Female" {% if edit_candidate[2] == 'Female' %}selected{% endif %}>Female</option>
                <option value="Other" {% if edit_candidate[2] == 'Other' %}selected{% endif %}>Other</option>
            </select><br><br>
            <label for="age">Age:</label><br>
            <input type="number" id="age" name="age" value="{{ edit_candidate[3] }}" required min="18"><br><br>
            <label for="party">Political Party:</label><br>
            <input type="text" id="party" name="party" value="{{ edit_candidate[4] }}" required><br><br>
            <input type="submit" value="Update Candidate">
            <a href="/" style="margin-left: 10px;">Cancel</a>
        </form>
        {% else %}
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
                    <td class="action-buttons">
                        <form class="delete-form" method="GET" action="/edit/{{ candidate[0] }}">
                            <input type="submit" value="Edit" class="edit-button">
                        </form>
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
        {% endif %}
    </div>
</body>
</html>
"""

VOTERS_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>Voter Management</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }
        .container { max-width: 800px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1, h2 { color: #0056b3; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        form { margin-top: 20px; padding: 15px; border: 1px solid #eee; border-radius: 5px; background-color: #fafafa; }
        form input[type="text"], form input[type="email"], form input[type="password"], form select { width: calc(100% - 22px); padding: 10px; margin-bottom: 10px; border: 1px solid #ccc; border-radius: 4px; }
        form input[type="submit"] { background-color: #007bff; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        form input[type="submit"]:hover { background-color: #0056b3; }
        .action-buttons { display: flex; gap: 5px; }
        .edit-button { background-color: #ffc107; color: #212529; padding: 5px 10px; border: none; border-radius: 4px; cursor: pointer; }
        .edit-button:hover { background-color: #e0a800; }
        .delete-form { display: inline; }
        .delete-button { background-color: #dc3545; color: white; padding: 5px 10px; border: none; border-radius: 4px; cursor: pointer; }
        .delete-button:hover { background-color: #c82333; }
        .message { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
        .error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
        .logout-link, .nav-link { color: #007bff; text-decoration: none; margin-right: 10px; }
        .logout-link:hover, .nav-link:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Voter Management</h1>
        <p>Welcome, {{ session['admin_name'] }}! 
           <a class="nav-link" href="/">Manage Candidates</a> |
           <a class="nav-link" href="/manage_elec_officers">Manage Election Officers</a> |
           <a class="nav-link" href="/audit_logs">View Audit Logs</a> |
           <a class="logout-link" href="/logout">Logout</a></p>
        {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
            <div class="{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
        {% endwith %}
        {% if edit_voter %}
        <h2>Edit Voter (ID: {{ edit_voter[0] }})</h2>
        <form method="POST" action="/edit_voter/{{ edit_voter[0] }}">
            <label for="name">Name:</label><br>
            <input type="text" id="name" name="name" value="{{ edit_voter[1] }}" required><br><br>
            <label for="email">Email:</label><br>
            <input type="email" id="email" name="email" value="{{ edit_voter[2] }}" required><br><br>
            <label for="password">Password (leave blank to keep unchanged):</label><br>
            <input type="password" id="password" name="password"><br><br>
            <label for="status">Status:</label><br>
            <select id="status" name="status" required>
                <option value="submitted" {% if edit_voter[4] == 'submitted' %}selected{% endif %}>Submitted</option>
                <option value="accepted" {% if edit_voter[4] == 'accepted' %}selected{% endif %}>Accepted</option>
            </select><br><br>
            <label for="role">Role:</label><br>
            <select id="role" name="role" required>
                <option value="voter" {% if edit_voter[5] == 'voter' %}selected{% endif %}>Voter</option>
            </select><br><br>
            <input type="submit" value="Update Voter">
            <a href="/manage_voters" style="margin-left: 10px;">Cancel</a>
        </form>
        {% else %}
        <h2>Current Voters</h2>
        {% if voters %}
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Status</th>
                    <th>Role</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for voter in voters %}
                <tr>
                    <td>{{ voter[0] }}</td>
                    <td>{{ voter[1] }}</td>
                    <td>{{ voter[2] }}</td>
                    <td>{{ voter[4] }}</td>
                    <td>{{ voter[5] }}</td>
                    <td class="action-buttons">
                        <form class="delete-form" method="GET" action="/edit_voter/{{ voter[0] }}">
                            <input type="submit" value="Edit" class="edit-button">
                        </form>
                        <form class="delete-form" method="POST" action="/delete_voter/{{ voter[0] }}">
                            <input type="submit" value="Delete" class="delete-button">
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <p>No voters found.</p>
        {% endif %}
        {% endif %}
    </div>
</body>
</html>
"""

ELEC_OFFICERS_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>Election Officer Management</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }
        .container { max-width: 800px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1, h2 { color: #0056b3; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        form { margin-top: 20px; padding: 15px; border: 1px solid #eee; border-radius: 5px; background-color: #fafafa; }
        form input[type="text"], form input[type="email"], form input[type="password"], form select { width: calc(100% - 22px); padding: 10px; margin-bottom: 10px; border: 1px solid #ccc; border-radius: 4px; }
        form input[type="submit"] { background-color: #007bff; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        form input[type="submit"]:hover { background-color: #0056b3; }
        .action-buttons { display: flex; gap: 5px; }
        .edit-button { background-color: #ffc107; color: #212529; padding: 5px 10px; border: none; border-radius: 4px; cursor: pointer; }
        .edit-button:hover { background-color: #e0a800; }
        .delete-form { display: inline; }
        .delete-button { background-color: #dc3545; color: white; padding: 5px 10px; border: none; border-radius: 4px; cursor: pointer; }
        .delete-button:hover { background-color: #c82333; }
        .message { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
        .error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
        .logout-link, .nav-link { color: #007bff; text-decoration: none; margin-right: 10px; }
        .logout-link:hover, .nav-link:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Election Officer Management</h1>
        <p>Welcome, {{ session['admin_name'] }}! 
           <a class="nav-link" href="/">Manage Candidates</a> |
           <a class="nav-link" href="/manage_voters">Manage Voters</a> |
           <a class="nav-link" href="/audit_logs">View Audit Logs</a> |
           <a class="logout-link" href="/logout">Logout</a></p>
        {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
            <div class="{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
        {% endwith %}
        {% if edit_officer %}
        <h2>Edit Election Officer (ID: {{ edit_officer[0] }})</h2>
        <form method="POST" action="/edit_elec_officer/{{ edit_officer[0] }}">
            <label for="name">Name:</label><br>
            <input type="text" id="name" name="name" value="{{ edit_officer[1] }}" required><br><br>
            <label for="email">Email:</label><br>
            <input type="email" id="email" name="email" value="{{ edit_officer[2] }}" required><br><br>
            <label for="password">Password (leave blank to keep unchanged):</label><br>
            <input type="password" id="password" name="password"><br><br>
            <label for="role">Role:</label><br>
            <select id="role" name="role" required>
                <option value="elec_officer" {% if edit_officer[4] == 'elec_officer' %}selected{% endif %}>Election Officer</option>
            </select><br><br>
            <input type="submit" value="Update Election Officer">
            <a href="/manage_elec_officers" style="margin-left: 10px;">Cancel</a>
        </form>
        {% else %}
        <h2>Current Election Officers</h2>
        {% if officers %}
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for officer in officers %}
                <tr>
                    <td>{{ officer[0] }}</td>
                    <td>{{ officer[1] }}</td>
                    <td>{{ officer[2] }}</td>
                    <td>{{ officer[4] }}</td>
                    <td class="action-buttons">
                        <form class="delete-form" method="GET" action="/edit_elec_officer/{{ officer[0] }}">
                            <input type="submit" value="Edit" class="edit-button">
                        </form>
                        <form class="delete-form" method="POST" action="/delete_elec_officer/{{ officer[0] }}">
                            <input type="submit" value="Delete" class="delete-button">
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <p>No election officers found. Add one below!</p>
        {% endif %}

        <h2>Add New Election Officer</h2>
        <form method="POST" action="/add_elec_officer">
            <label for="name">Name:</label><br>
            <input type="text" id="name" name="name" required><br><br>
            <label for="email">Email:</label><br>
            <input type="email" id="email" name="email" required><br><br>
            <label for="password">Password:</label><br>
            <input type="password" id="password" name="password" required><br><br>
            <label for="role">Role:</label><br>
            <select id="role" name="role" required>
                <option value="elec_officer">Election Officer</option>
            </select><br><br>
            <input type="submit" value="Add Election Officer">
        </form>
        {% endif %}
    </div>
</body>
</html>
"""

AUDIT_LOGS_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>Audit Logs</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }
        .container { max-width: 1200px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #0056b3; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
        th { background-color: #f2f2f2; cursor: pointer; }
        th:hover { background-color: #e0e0e0; }
        td { font-size: 14px; }
        th:nth-child(1), td:nth-child(1) { width: 10%; } /* ID */
        th:nth-child(2), td:nth-child(2) { width: 15%; } /* User ID */
        th:nth-child(3), td:nth-child(3) { width: 20%; } /* Action */
        th:nth-child(4), td:nth-child(4) { width: 35%; } /* Details */
        th:nth-child(5), td:nth-child(5) { width: 20%; } /* IP Address */
        th:nth-child(6), td:nth-child(6) { width: 20%; } /* Timestamp */
        .message { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
        .error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
        .logout-link, .nav-link { color: #007bff; text-decoration: none; margin-right: 10px; }
        .logout-link:hover, .nav-link:hover { text-decoration: underline; }
        .pagination { margin-top: 20px; }
        .pagination a { color: #007bff; text-decoration: none; padding: 5px 10px; border: 1px solid #ddd; margin-right: 5px; border-radius: 4px; }
        .pagination a:hover { background-color: #f2f2f2; }
        .pagination .active { background-color: #007bff; color: white; }
    </style>
    <script>
        function sortTable(n) {
            var table = document.querySelector("table");
            var rows, switching = true, i, x, y, shouldSwitch, dir = "asc", switchcount = 0;
            while (switching) {
                switching = false;
                rows = table.rows;
                for (i = 1; i < (rows.length - 1); i++) {
                    shouldSwitch = false;
                    x = rows[i].getElementsByTagName("TD")[n];
                    y = rows[i + 1].getElementsByTagName("TD")[n];
                    var xVal = x.innerHTML.toLowerCase();
                    var yVal = y.innerHTML.toLowerCase();
                    // Handle numeric columns (ID, User ID)
                    if (n === 0 || n === 1) {
                        xVal = parseInt(xVal) || 0;
                        yVal = parseInt(yVal) || 0;
                    }
                    // Handle timestamp column
                    else if (n === 5) {
                        xVal = new Date(xVal).getTime() || 0;
                        yVal = new Date(yVal).getTime() || 0;
                    }
                    if (dir === "asc") {
                        if (xVal > yVal) {
                            shouldSwitch = true;
                            break;
                        }
                    } else if (dir === "desc") {
                        if (xVal < yVal) {
                            shouldSwitch = true;
                            break;
                        }
                    }
                }
                if (shouldSwitch) {
                    rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
                    switching = true;
                    switchcount++;
                } else if (switchcount === 0 && dir === "asc") {
                    dir = "desc";
                    switching = true;
                }
            }
        }
    </script>
</head>
<body>
    <div class="container">
        <h1>Audit Logs</h1>
        <p>Welcome, {{ session['admin_name'] }}! 
           <a class="nav-link" href="/">Manage Candidates</a> |
           <a class="nav-link" href="/manage_voters">Manage Voters</a> |
           <a class="nav-link" href="/manage_elec_officers">Manage Election Officers</a> |
           <a class="logout-link" href="/logout">Logout</a></p>
        {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
            <div class="{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
        {% endwith %}
        <h2>Audit Log Entries</h2>
        {% if logs %}
        <table>
            <thead>
                <tr>
                    <th onclick="sortTable(0)">ID</th>
                    <th onclick="sortTable(1)">User ID</th>
                    <th onclick="sortTable(2)">Action</th>
                    <th onclick="sortTable(3)">Details</th>
                    <th onclick="sortTable(4)">IP Address</th>
                    <th onclick="sortTable(5)">Timestamp</th>
                </tr>
            </thead>
            <tbody>
                {% for log in logs %}
                <tr>
                    <td>{{ log[0] }}</td>
                    <td>{{ log[1] or 'N/A' }}</td>
                    <td>{{ log[2] }}</td>
                    <td>{{ log[3] or 'N/A' }}</td>
                    <td>{{ log[4] }}</td>
                    <td>{{ log[5] }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        <div class="pagination">
            {% if page > 1 %}
            <a href="/audit_logs?page={{ page - 1 }}">Previous</a>
            {% endif %}
            {% for p in range(1, total_pages + 1) %}
            <a href="/audit_logs?page={{ p }}" class="{% if p == page %}active{% endif %}">{{ p }}</a>
            {% endfor %}
            {% if page < total_pages %}
            <a href="/audit_logs?page={{ page + 1 }}">Next</a>
            {% endif %}
        </div>
        {% else %}
        <p>No audit logs found.</p>
        {% endif %}
    </div>
</body>
</html>
"""

#Database utilities
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
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                role ENUM('admin') DEFAULT 'admin'
            );
        """)
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
                password VARCHAR(255) NOT NULL,
                status ENUM('submitted', 'accepted') DEFAULT 'submitted',
                role ENUM('voter') DEFAULT 'voter'
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                sex ENUM('Male', 'Female', 'Other') NOT NULL,
                age INT NOT NULL,
                political_party VARCHAR(255) NOT NULL
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS votes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                voter_id INT NOT NULL,
                candidate_id INT NOT NULL,
                vote_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (voter_id),
                FOREIGN KEY (voter_id) REFERENCES voters(id) ON DELETE CASCADE,
                FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
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

def validate_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)

def validate_password_strength(password):
    if len(password) < 8 or not re.search("[A-Z]", password) or not re.search("[a-z]", password) or not re.search("\d", password) or not re.search("[!@#$%^&*]", password):
        return False
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
                        log_audit(admin_id, 'login_success', ip, details=f"Admin {admin_name} logged in")
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
        log_audit(session['admin_id'], 'view_candidates', request.remote_addr, details=f"Admin {session['admin_name']} viewed candidates")
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

@app.route('/edit/<int:candidate_id>', methods=['GET', 'POST'])
@require_admin_login
def edit_candidate(candidate_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if request.method == 'POST':
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

            if not re.match(r'^[A-Za-z\s]{1,255}$', name):
                flash("Invalid name format. Use letters and spaces only.", 'error')
                return redirect(url_for('index'))
            if not re.match(r'^[A-Za-z\s]{1,255}$', party):
                flash("Invalid political party format. Use letters and spaces only.", 'error')
                return redirect(url_for('index'))
            if sex not in ['Male', 'Female', 'Other']:
                flash("Invalid sex selection", 'error')
                return redirect(url_for('index'))

            cursor.execute("UPDATE candidates SET name = %s, sex = %s, age = %s, political_party = %s WHERE id = %s",
                           (name, sex, age, party, candidate_id))
            conn.commit()
            log_audit(session['admin_id'], 'edit_candidate', request.remote_addr, details=f"Edited candidate ID {candidate_id}: {name}")
            flash("Candidate updated successfully", 'message')
            return redirect(url_for('index'))
        else:
            cursor.execute("SELECT id, name, sex, age, political_party FROM candidates WHERE id = %s", (candidate_id,))
            candidate = cursor.fetchone()
            if candidate:
                log_audit(session['admin_id'], 'view_edit_candidate', request.remote_addr, details=f"Viewing edit form for candidate ID {candidate_id}: {candidate[1]}")
                return render_template_string(HOME_TEMPLATE, edit_candidate=candidate, candidates=[])
            else:
                log_audit(session['admin_id'], 'view_edit_candidate_error', request.remote_addr, details=f"Candidate ID {candidate_id} not found")
                flash("Candidate not found", 'error')
                return redirect(url_for('index'))
    except Exception as e:
        log_audit(session['admin_id'], 'edit_candidate_error', request.remote_addr, details=str(e))
        flash(f"Error editing candidate: {e}", 'error')
        return redirect(url_for('index'))
    finally:
        if conn:
            conn.close()

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

@app.route('/manage_voters')
@require_admin_login
def manage_voters():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, password, status, role FROM voters")
        voters = cursor.fetchall()
        log_audit(session['admin_id'], 'view_voters', request.remote_addr, details=f"Admin {session['admin_name']} viewed voters")
        return render_template_string(VOTERS_TEMPLATE, voters=voters, message="Voter Management")
    except Exception as e:
        log_audit(session['admin_id'], 'view_voters_error', request.remote_addr, details=str(e))
        flash(f"Error loading voters: {e}", 'error')
        return render_template_string(VOTERS_TEMPLATE, voters=[], message=f"Error loading voters: {e}")
    finally:
        if conn:
            conn.close()

@app.route('/edit_voter/<int:voter_id>', methods=['GET', 'POST'])
@require_admin_login
def edit_voter(voter_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if request.method == 'POST':
            name = request.form['name'].strip()
            email = request.form['email'].strip()
            password = request.form['password']
            status = request.form['status']
            role = request.form['role']

            if not re.match(r'^[A-Za-z\s]{1,255}$', name):
                flash("Invalid name format. Use letters and spaces only.", 'error')
                return redirect(url_for('manage_voters'))
            if not validate_email(email):
                flash("Invalid email format.", 'error')
                return redirect(url_for('manage_voters'))
            if password and not validate_password_strength(password):
                flash("Password must be at least 8 characters long and include uppercase, lowercase, numbers, and special characters.", 'error')
                return redirect(url_for('manage_voters'))
            if status not in ['submitted', 'accepted']:
                flash("Invalid status selection.", 'error')
                return redirect(url_for('manage_voters'))
            if role != 'voter':
                flash("Invalid role selection.", 'error')
                return redirect(url_for('manage_voters'))

            if password:
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                cursor.execute("UPDATE voters SET name = %s, email = %s, password = %s, status = %s, role = %s WHERE id = %s",
                               (name, email, hashed_password, status, role, voter_id))
            else:
                cursor.execute("UPDATE voters SET name = %s, email = %s, status = %s, role = %s WHERE id = %s",
                               (name, email, status, role, voter_id))
            conn.commit()
            log_audit(session['admin_id'], 'edit_voter', request.remote_addr, details=f"Edited voter ID {voter_id}: {name}")
            flash("Voter updated successfully", 'message')
            return redirect(url_for('manage_voters'))
        else:
            cursor.execute("SELECT id, name, email, password, status, role FROM voters WHERE id = %s", (voter_id,))
            voter = cursor.fetchone()
            if voter:
                log_audit(session['admin_id'], 'view_edit_voter', request.remote_addr, details=f"Viewing edit form for voter ID {voter_id}: {voter[1]}")
                return render_template_string(VOTERS_TEMPLATE, edit_voter=voter, voters=[])
            else:
                log_audit(session['admin_id'], 'view_edit_voter_error', request.remote_addr, details=f"Voter ID {voter_id} not found")
                flash("Voter not found", 'error')
                return redirect(url_for('manage_voters'))
    except Exception as e:
        log_audit(session['admin_id'], 'edit_voter_error', request.remote_addr, details=str(e))
        flash(f"Error editing voter: {e}", 'error')
        return redirect(url_for('manage_voters'))
    finally:
        if conn:
            conn.close()

@app.route('/delete_voter/<int:voter_id>', methods=['POST'])
@require_admin_login
def delete_voter(voter_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM voters WHERE id = %s", (voter_id,))
        voter = cursor.fetchone()
        if voter:
            cursor.execute("DELETE FROM voters WHERE id = %s", (voter_id,))
            conn.commit()
            log_audit(session['admin_id'], 'delete_voter', request.remote_addr, details=f"Deleted voter ID {voter_id}: {voter[0]}")
            flash("Voter deleted successfully", 'message')
        else:
            flash("Voter not found", 'error')
    except Exception as e:
        log_audit(session['admin_id'], 'delete_voter_error', request.remote_addr, details=str(e))
        flash(f"Error deleting voter: {e}", 'error')
    finally:
        if conn:
            conn.close()
    return redirect(url_for('manage_voters'))

@app.route('/manage_elec_officers')
@require_admin_login
def manage_elec_officers():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, password, role FROM elec_officers")
        officers = cursor.fetchall()
        log_audit(session['admin_id'], 'view_elec_officers', request.remote_addr, details=f"Admin {session['admin_name']} viewed election officers")
        return render_template_string(ELEC_OFFICERS_TEMPLATE, officers=officers, message="Election Officer Management")
    except Exception as e:
        log_audit(session['admin_id'], 'view_elec_officers_error', request.remote_addr, details=str(e))
        flash(f"Error loading election officers: {e}", 'error')
        return render_template_string(ELEC_OFFICERS_TEMPLATE, officers=[], message=f"Error loading election officers: {e}")
    finally:
        if conn:
            conn.close()

@app.route('/add_elec_officer', methods=['POST'])
@require_admin_login
def add_elec_officer():
    name = request.form['name'].strip()
    email = request.form['email'].strip()
    password = request.form['password']
    role = request.form['role']

    if not re.match(r'^[A-Za-z\s]{1,255}$', name):
        flash("Invalid name format. Use letters and spaces only.", 'error')
        return redirect(url_for('manage_elec_officers'))
    if not validate_email(email):
        flash("Invalid email format.", 'error')
        return redirect(url_for('manage_elec_officers'))
    if not validate_password_strength(password):
        flash("Password must be at least 8 characters long and include uppercase, lowercase, numbers, and special characters.", 'error')
        return redirect(url_for('manage_elec_officers'))
    if role != 'elec_officer':
        flash("Invalid role selection.", 'error')
        return redirect(url_for('manage_elec_officers'))

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO elec_officers (name, email, password, role) VALUES (%s, %s, %s, %s)",
                       (name, email, hashed_password, role))
        conn.commit()
        log_audit(session['admin_id'], 'add_elec_officer', request.remote_addr, details=f"Added election officer: {name}")
        flash("Election officer added successfully", 'message')
    except Exception as e:
        log_audit(session['admin_id'], 'add_elec_officer_error', request.remote_addr, details=str(e))
        flash(f"Error adding election officer: {e}", 'error')
    finally:
        if conn:
            conn.close()
    return redirect(url_for('manage_elec_officers'))

@app.route('/edit_elec_officer/<int:officer_id>', methods=['GET', 'POST'])
@require_admin_login
def edit_elec_officer(officer_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if request.method == 'POST':
            name = request.form['name'].strip()
            email = request.form['email'].strip()
            password = request.form['password']
            role = request.form['role']

            if not re.match(r'^[A-Za-z\s]{1,255}$', name):
                flash("Invalid name format. Use letters and spaces only.", 'error')
                return redirect(url_for('manage_elec_officers'))
            if not validate_email(email):
                flash("Invalid email format.", 'error')
                return redirect(url_for('manage_elec_officers'))
            if password and not validate_password_strength(password):
                flash("Password must be at least 8 characters long and include uppercase, lowercase, numbers, and special characters.", 'error')
                return redirect(url_for('manage_elec_officers'))
            if role != 'elec_officer':
                flash("Invalid role selection.", 'error')
                return redirect(url_for('manage_elec_officers'))

            if password:
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                cursor.execute("UPDATE elec_officers SET name = %s, email = %s, password = %s, role = %s WHERE id = %s",
                               (name, email, hashed_password, role, officer_id))
            else:
                cursor.execute("UPDATE elec_officers SET name = %s, email = %s, role = %s WHERE id = %s",
                               (name, email, role, officer_id))
            conn.commit()
            log_audit(session['admin_id'], 'edit_elec_officer', request.remote_addr, details=f"Edited election officer ID {officer_id}: {name}")
            flash("Election officer updated successfully", 'message')
            return redirect(url_for('manage_elec_officers'))
        else:
            cursor.execute("SELECT id, name, email, password, role FROM elec_officers WHERE id = %s", (officer_id,))
            officer = cursor.fetchone()
            if officer:
                log_audit(session['admin_id'], 'view_edit_elec_officer', request.remote_addr, details=f"Viewing edit form for election officer ID {officer_id}: {officer[1]}")
                return render_template_string(ELEC_OFFICERS_TEMPLATE, edit_officer=officer, officers=[])
            else:
                log_audit(session['admin_id'], 'view_edit_elec_officer_error', request.remote_addr, details=f"Election officer ID {officer_id} not found")
                flash("Election officer not found", 'error')
                return redirect(url_for('manage_elec_officers'))
    except Exception as e:
        log_audit(session['admin_id'], 'edit_elec_officer_error', request.remote_addr, details=str(e))
        flash(f"Error editing election officer: {e}", 'error')
        return redirect(url_for('manage_elec_officers'))
    finally:
        if conn:
            conn.close()

@app.route('/delete_elec_officer/<int:officer_id>', methods=['POST'])
@require_admin_login
def delete_elec_officer(officer_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM elec_officers WHERE id = %s", (officer_id,))
        officer = cursor.fetchone()
        if officer:
            cursor.execute("DELETE FROM elec_officers WHERE id = %s", (officer_id,))
            conn.commit()
            log_audit(session['admin_id'], 'delete_elec_officer', request.remote_addr, details=f"Deleted election officer ID {officer_id}: {officer[0]}")
            flash("Election officer deleted successfully", 'message')
        else:
            flash("Election officer not found", 'error')
    except Exception as e:
        log_audit(session['admin_id'], 'delete_elec_officer_error', request.remote_addr, details=str(e))
        flash(f"Error deleting election officer: {e}", 'error')
    finally:
        if conn:
            conn.close()
    return redirect(url_for('manage_elec_officers'))

@app.route('/audit_logs')
@require_admin_login
def audit_logs():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM audit_logs")
        total_logs = cursor.fetchone()[0]
        total_pages = (total_logs + per_page - 1) // per_page

        offset = (page - 1) * per_page
        cursor.execute("""
            SELECT 
                a.id,
                a.user_id,
                a.action,
                a.details,
                a.ip_address,
                a.timestamp
            FROM audit_logs a
            ORDER BY a.timestamp DESC
            LIMIT %s OFFSET %s
        """, (per_page, offset))
        logs = cursor.fetchall()
        log_audit(session['admin_id'], 'view_audit_logs', request.remote_addr, details=f"Admin {session['admin_name']} viewed audit logs")
        return render_template_string(AUDIT_LOGS_TEMPLATE, logs=logs, page=page, total_pages=total_pages)
    except Exception as e:
        log_audit(session['admin_id'], 'view_audit_logs_error', request.remote_addr, details=str(e))
        flash(f"Error loading audit logs: {e}", 'error')
        return render_template_string(AUDIT_LOGS_TEMPLATE, logs=[], page=page, total_pages=1)
    finally:
        if conn:
            conn.close()

@app.route('/logout')
def logout():
    log_audit(session.get('admin_id'), 'logout', request.remote_addr, details=f"Admin {session.get('admin_name', 'Unknown')} logged out")
    session.clear()
    flash("Logged out successfully", 'message')
    return redirect(url_for('login'))

# New route: export tally as XML with checksum
@app.route('/export_tally')
@require_admin_login
def export_tally():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                c.id, c.name,
                COUNT(v.id) AS votes
            FROM candidates c
            LEFT JOIN votes v ON c.id = v.candidate_id
            GROUP BY c.id
            ORDER BY votes DESC, c.id ASC
        """)
        rows = cursor.fetchall()

        # Build XML where each Candidate includes only Name and Votes
        root = ET.Element('Tally')
        candidates_el = ET.SubElement(root, 'Candidates')

        for r in rows:
            cand = ET.SubElement(candidates_el, 'Candidate')
            ET.SubElement(cand, 'Name').text = r[1] or ''
            ET.SubElement(cand, 'Votes').text = str(r[2] or 0)

        # Add blank line (extra newline) between each Candidate element for readability
        # and ensure the Candidates container starts on a new line.
        candidates_el.text = '\n'
        for cand in list(candidates_el):
            # put an extra newline after each candidate to create a blank line between entries
            cand.tail = '\n\n'

        xml_without_checksum = ET.tostring(root, encoding='utf-8', method='xml')
        checksum = hashlib.sha256(xml_without_checksum).hexdigest()

        # Append checksum element
        checksum_el = ET.SubElement(root, 'Checksum')
        checksum_el.text = checksum
        # ensure the checksum sits on its own line after the Candidates section
        checksum_el.tail = '\n'

        final_xml = ET.tostring(root, encoding='utf-8', method='xml')

        filename = f"tally_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.xml"
        log_audit(session['admin_id'], 'export_tally', request.remote_addr, details=f"Exported tally, checksum={checksum}")

        return Response(final_xml, mimetype='application/xml', headers={
            "Content-Disposition": f"attachment; filename={filename}"
        })
    except Exception as e:
        log_audit(session.get('admin_id'), 'export_tally_error', request.remote_addr, details=str(e))
        flash(f"Error exporting tally: {e}", 'error')
        return redirect(url_for('index'))
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)