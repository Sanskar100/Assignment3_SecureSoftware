from flask import Flask, render_template_string, request, flash
import os
import mysql.connector
from cryptography.fernet import Fernet # Needed for decrypting voter emails

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'another_secret_key_for_db_viewer') # Used for flash messages

# Database connection details from environment variables
DB_HOST = os.getenv('DB_HOST', 'db')
DB_USER = os.getenv('DB_USER', 'user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
DB_NAME = os.getenv('DB_NAME', 'mydatabase')

# Encryption setup (do NOT crash if key is missing; only enable decryption when a valid key is provided)
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
cipher_suite = None
if ENCRYPTION_KEY:
    try:
        cipher_suite = Fernet(ENCRYPTION_KEY.encode())
    except Exception as e:
        # Log the problem and continue without decryption instead of raising
        app.logger.error(f"Invalid ENCRYPTION_KEY provided; disabling decryption. Error: {e}")
        cipher_suite = None
else:
    # don't raise here; the app will show raw/decoded values when cipher is not available
    app.logger.warning("ENCRYPTION_KEY not set. Encrypted fields will not be decrypted.")

# HTML Template for displaying database contents
DB_VIEWER_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>Database Viewer</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background-color: #f8f9fa; color: #343a40; }
        .container { max-width: 1000px; margin: auto; background: white; padding: 25px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        h1 { color: #007bff; text-align: center; margin-bottom: 30px; }
        h2 { color: #28a745; border-bottom: 2px solid #28a745; padding-bottom: 5px; margin-top: 40px; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        th, td { border: 1px solid #dee2e6; padding: 12px; text-align: left; vertical-align: top; word-wrap: break-word; }
        th { background-color: #e9ecef; font-weight: bold; }
        tr:nth-child(even) { background-color: #f8f9fa; }
        .message { padding: 10px; margin-bottom: 15px; border-radius: 5px; }
        .message.success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .message.error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .message.info { background-color: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        pre { background-color: #f0f0f0; padding: 10px; border-radius: 5px; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Database Content Viewer</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
            <div class="message {{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
        {% endwith %}

        {% if tables %}
            {% for table_name, table_data in tables.items() %}
                <h2>Table: `{{ table_name }}`</h2>
                {% if table_data.rows %}
                    <table>
                        <thead>
                            <tr>
                                {% for column in table_data.columns %}
                                    <th>{{ column }}</th>
                                {% endfor %}
                            </tr>
                        </thead>
                        <tbody>
                            {% for row in table_data.rows %}
                                <tr>
                                    {% for item in row %}
                                        <td>{{ item }}</td>
                                    {% endfor %}
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% else %}
                    <p>No data in this table.</p>
                {% endif %}
            {% endfor %}
        {% else %}
            <p>No tables found or error connecting to database.</p>
        {% endif %}
    </div>
</body>
</html>
"""

def decrypt_data(data):
    if data is None:
        return ""
    # If no cipher is configured, return a readable representation (try decoding bytes)
    if cipher_suite is None:
        if isinstance(data, bytes):
            try:
                return data.decode()
            except Exception:
                return repr(data)
        return str(data)

    try:
        # Ensure bytes for Fernet.decrypt
        if isinstance(data, str):
            data_bytes = data.encode()
        elif isinstance(data, bytes):
            data_bytes = data
        else:
            # unknown type; return a readable representation
            return str(data)
        return cipher_suite.decrypt(data_bytes).decode()
    except Exception as e:
        # Don't expose exception details to users; log for debugging
        app.logger.debug(f"Decryption error for data: {e}")
        return "[Decryption Error]"

def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

@app.route('/')
def index():
    conn = None
    cursor = None
    all_tables_data = {}
    try:
        conn = get_db_connection()
        # use a buffered cursor to avoid "Unread result" issues when reusing the same cursor
        cursor = conn.cursor(buffered=True)

        # Get all table names in the database
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]

        for table_name in tables:
            # sanitize table name (remove backticks) then wrap in backticks for SQL
            safe_table = str(table_name).replace('`', '')
            quoted_table = f"`{safe_table}`"

            columns = []
            rows = []
            try:
                # Fetch all data from the table and derive columns from cursor.description
                cursor.execute(f"SELECT * FROM {quoted_table}")
                raw_rows = cursor.fetchall()
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                else:
                    columns = []

                # Process rows, specifically decrypting 'email' if it's the voters table
                processed_rows = []
                for row_tuple in raw_rows:
                    new_row = list(row_tuple) # Convert to list to modify

                    # voters: decrypt email column when present
                    if safe_table == 'voters' and 'email' in columns:
                        email_index = columns.index('email')
                        if email_index < len(new_row):
                            new_row[email_index] = decrypt_data(new_row[email_index])

                    # database_alert: decrypt message column and flash the alert based on severity
                    if safe_table == 'database_alert' and 'message' in columns:
                        msg_index = columns.index('message')
                        if msg_index < len(new_row):
                            # Decrypt or normalize message text
                            decrypted_msg = decrypt_data(new_row[msg_index])
                            new_row[msg_index] = decrypted_msg

                            # Determine severity/category if available
                            severity = None
                            if 'severity' in columns:
                                sev_idx = columns.index('severity')
                                if sev_idx < len(new_row):
                                    try:
                                        severity = str(new_row[sev_idx]).lower()
                                    except Exception:
                                        severity = None

                            # Map severity to flash category
                            if severity in ('critical', 'error', 'danger'):
                                category = 'error'
                            elif severity in ('success', 'ok'):
                                category = 'success'
                            else:
                                category = 'info'

                            # Compose and flash the alert (short and non-sensitive)
                            flash_msg = decrypted_msg if decrypted_msg else "[empty alert message]"
                            flash(flash_msg, category)

                    processed_rows.append(tuple(new_row))

                rows = processed_rows

            except Exception as e:
                app.logger.exception(f"Error reading table '{table_name}': {e}")
                flash(f"Error reading table '{table_name}'. See logs for details.", 'error')
                columns = ["Error"]
                rows = [["Could not load data for this table."]]

            all_tables_data[table_name] = {'columns': columns, 'rows': rows}

        # close cursor if it was created
        if cursor:
            cursor.close()

    except Exception as e:
        app.logger.exception(f"Error connecting to database or fetching tables: {e}")
        flash("Error connecting to database or fetching tables. See logs for details.", 'error')
    finally:
        if conn:
            conn.close()

    return render_template_string(DB_VIEWER_TEMPLATE, tables=all_tables_data, message="Displaying all database tables and data.")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5555, debug=True) # Flask runs on 6000 inside the container