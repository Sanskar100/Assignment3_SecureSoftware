from flask import Flask, render_template_string, request, redirect, url_for
import os
import mysql.connector

app = Flask(__name__)

# Database connection details from environment variables
DB_HOST = os.getenv('DB_HOST', 'db')
DB_USER = os.getenv('DB_USER', 'user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
DB_NAME = os.getenv('DB_NAME', 'mydatabase')

# HTML templates for rendering
HOME_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>Candidate List</title>
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
    </style>
</head>
<body>
    <div class="container">
        <h1>Candidate List Application</h1>
        <p>{{ message }}</p>
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
            <input type="number" id="age" name="age" required><br><br>
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                sex VARCHAR(50) NOT NULL,
                age INT NOT NULL,
                political_party VARCHAR(255) NOT NULL
            );
        """)
        conn.commit()
        print("Database 'candidates' table checked/created successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")
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
        cursor.execute("SELECT * FROM candidates")
        candidates = cursor.fetchall()
        return render_template_string(HOME_TEMPLATE, candidates=candidates, message="Welcome to the Candidate Management App!")
    except Exception as e:
        return render_template_string(HOME_TEMPLATE, candidates=[], message=f"Error loading candidates: {e}")
    finally:
        if conn:
            conn.close()

@app.route('/add', methods=['POST'])
def add_candidate():
    name = request.form['name']
    sex = request.form['sex']
    age = request.form['age']
    party = request.form['party']

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO candidates (name, sex, age, political_party) VALUES (%s, %s, %s, %s)",
                       (name, sex, age, party))
        conn.commit()
    except Exception as e:
        print(f"Error adding candidate: {e}")
    finally:
        if conn:
            conn.close()
    return redirect(url_for('index'))

@app.route('/delete/<int:candidate_id>', methods=['POST'])
def delete_candidate(candidate_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM candidates WHERE id = %s", (candidate_id,))
        conn.commit()
    except Exception as e:
        print(f"Error deleting candidate: {e}")
    finally:
        if conn:
            conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)