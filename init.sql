CREATE DATABASE IF NOT EXISTS mydatabase;
USE mydatabase;

-- USERS
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL
);

-- ELECTION OFFICERS
CREATE TABLE IF NOT EXISTS elec_officers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('elec_officer') DEFAULT 'elec_officer'
);

-- VOTERS
CREATE TABLE IF NOT EXISTS voters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    status ENUM('submitted', 'accepted') DEFAULT 'submitted',
    role ENUM('voter') DEFAULT 'voter'
);

-- CANDIDATES
CREATE TABLE IF NOT EXISTS candidates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    age INT NOT NULL,
    political_party VARCHAR(255) NOT NULL
);

-- VOTES
CREATE TABLE IF NOT EXISTS votes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    voter_id INT NOT NULL,
    candidate_id INT NOT NULL,
    vote_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (voter_id),
    FOREIGN KEY (voter_id) REFERENCES voters(id) ON DELETE CASCADE,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
);

-- AUDIT LOGS
CREATE TABLE IF NOT EXISTS audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    action VARCHAR(255),
    details TEXT,
    ip_address VARCHAR(45),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- INSERT SAMPLE DATA
INSERT INTO users (name) VALUES ('Alice'), ('Bob');

INSERT INTO elec_officers (name, email, password, role)
VALUES ('John Doe', 'johndoe@example.com', '$2b$12$osUwZ2HLsWlR.U8ZQYXV9OHF5zrQLNRJFlKD.q0g.nBVOc5R1WYTe', 'elec_officer');

INSERT INTO voters (name, email, password, status, role)
VALUES 
    ('Test User', 'testuser@example.com', '$2b$12$wJ5QZV5KoeqSRanA6kb2uuQB9dWQrMQ5h5xvE80rFoowRC8hYYL26', 'accepted', 'voter');

INSERT INTO candidates (name, age, political_party)
VALUES 
    ('Sarah Connor', 35, 'Tech Party'),
    ('Tony Stark', 45, 'Innovation Alliance'),
    ('Diana Prince', 32, 'Justice League');

SELECT * FROM voters;
SELECT * FROM elec_officers;
SELECT * FROM candidates;
