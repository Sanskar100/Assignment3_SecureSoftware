CREATE DATABASE IF NOT EXISTS mydatabase;
USE mydatabase;

-- USERS
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL
);

-- ADMINS
CREATE TABLE IF NOT EXISTS admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('admin') DEFAULT 'admin'
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
    sex ENUM('Male', 'Female', 'Other') NOT NULL,
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

/* New table for database change alerts. Triggers will populate this.
   details is JSON so the application can parse rich structured change info.
*/
-- DATABASE ALERTS
CREATE TABLE IF NOT EXISTS database_alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(128) NOT NULL,
    action VARCHAR(32) NOT NULL,
    details LONGTEXT,
    user_id INT NULL,
    ip_address VARCHAR(45),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_table_action (table_name, action),
    KEY idx_created_at (created_at),
    CONSTRAINT fk_database_alerts_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- INSERT SAMPLE DATA
INSERT INTO users (name) VALUES ('Alice'), ('Bob');

INSERT INTO admins (name, email, password, role)
VALUES ('Admin', 'admin@example.com', '$2b$12$bHbObmkHy4SjgtQNoOCInOEqEuDRC9iarmn57hq8y0jzvhfRDVKwO', 'admin');

INSERT INTO elec_officers (name, email, password, role)
VALUES ('John Doe', 'johndoe@example.com', '$2b$12$osUwZ2HLsWlR.U8ZQYXV9OHF5zrQLNRJFlKD.q0g.nBVOc5R1WYTe', 'elec_officer');

INSERT INTO voters (name, email, password, status, role)
VALUES 
    ('Test User', 'testuser@example.com', '$2b$12$wJ5QZV5KoeqSRanA6kb2uuQB9dWQrMQ5h5xvE80rFoowRC8hYYL26', 'accepted', 'voter');

INSERT INTO candidates (name, sex, age, political_party)
VALUES 
    ('Sarah Connor', 'Female', 35, 'Tech Party'),
    ('Tony Stark', 'Male', 45, 'Innovation Alliance'),
    ('Diana Prince', 'Female', 32, 'Justice League');

INSERT INTO database_alerts (table_name, action, details, user_id, ip_address)
VALUES 
    ('init', 'SEED_DATA', JSON_OBJECT('info', 'Initial sample data inserted'), NULL, NULL);

SELECT * FROM voters;
SELECT * FROM elec_officers;
SELECT * FROM candidates;
SELECT * FROM admins;
SELECT * FROM database_alerts;

/* Triggers to create database_alerts entries for data changes.
   For each table (except audit_logs and database_alerts) we create AFTER INSERT, AFTER UPDATE, AFTER DELETE triggers
   that insert a JSON details object into database_alerts. Modify user_id/ip_address assignment later if you can pass the acting user or IP from the application.
*/

DELIMITER $$

-- USERS
CREATE TRIGGER trg_users_after_insert
AFTER INSERT ON users
FOR EACH ROW
BEGIN
  INSERT INTO database_alerts (table_name, action, details, user_id, ip_address)
  VALUES ('users', 'INSERT', JSON_OBJECT('new', JSON_OBJECT('id', NEW.id, 'name', NEW.name)), NULL, NULL);
END$$

CREATE TRIGGER trg_users_after_update
AFTER UPDATE ON users
FOR EACH ROW
BEGIN
  INSERT INTO database_alerts (table_name, action, details, user_id, ip_address)
  VALUES ('users', 'UPDATE', JSON_OBJECT('old', JSON_OBJECT('id', OLD.id, 'name', OLD.name), 'new', JSON_OBJECT('id', NEW.id, 'name', NEW.name)), NULL, NULL);
END$$

CREATE TRIGGER trg_users_after_delete
AFTER DELETE ON users
FOR EACH ROW
BEGIN
  INSERT INTO database_alerts (table_name, action, details, user_id, ip_address)
  VALUES ('users', 'DELETE', JSON_OBJECT('old', JSON_OBJECT('id', OLD.id, 'name', OLD.name)), NULL, NULL);
END$$

-- ADMINS
CREATE TRIGGER trg_admins_after_insert
AFTER INSERT ON admins
FOR EACH ROW
BEGIN
  INSERT INTO database_alerts (table_name, action, details, user_id, ip_address)
  VALUES ('admins', 'INSERT', JSON_OBJECT('new', JSON_OBJECT('id', NEW.id, 'name', NEW.name, 'email', NEW.email, 'role', NEW.role)), NULL, NULL);
END$$

CREATE TRIGGER trg_admins_after_update
AFTER UPDATE ON admins
FOR EACH ROW
BEGIN
  INSERT INTO database_alerts (table_name, action, details, user_id, ip_address)
  VALUES ('admins', 'UPDATE', JSON_OBJECT('old', JSON_OBJECT('id', OLD.id, 'name', OLD.name, 'email', OLD.email, 'role', OLD.role), 'new', JSON_OBJECT('id', NEW.id, 'name', NEW.name, 'email', NEW.email, 'role', NEW.role)), NULL, NULL);
END$$

CREATE TRIGGER trg_admins_after_delete
AFTER DELETE ON admins
FOR EACH ROW
BEGIN
  INSERT INTO database_alerts (table_name, action, details, user_id, ip_address)
  VALUES ('admins', 'DELETE', JSON_OBJECT('old', JSON_OBJECT('id', OLD.id, 'name', OLD.name, 'email', OLD.email, 'role', OLD.role)), NULL, NULL);
END$$

-- ELECTION OFFICERS
CREATE TRIGGER trg_elec_officers_after_insert
AFTER INSERT ON elec_officers
FOR EACH ROW
BEGIN
  INSERT INTO database_alerts (table_name, action, details, user_id, ip_address)
  VALUES ('elec_officers', 'INSERT', JSON_OBJECT('new', JSON_OBJECT('id', NEW.id, 'name', NEW.name, 'email', NEW.email, 'role', NEW.role)), NULL, NULL);
END$$

CREATE TRIGGER trg_elec_officers_after_update
AFTER UPDATE ON elec_officers
FOR EACH ROW
BEGIN
  INSERT INTO database_alerts (table_name, action, details, user_id, ip_address)
  VALUES ('elec_officers', 'UPDATE', JSON_OBJECT('old', JSON_OBJECT('id', OLD.id, 'name', OLD.name, 'email', OLD.email, 'role', OLD.role), 'new', JSON_OBJECT('id', NEW.id, 'name', NEW.name, 'email', NEW.email, 'role', NEW.role)), NULL, NULL);
END$$

CREATE TRIGGER trg_elec_officers_after_delete
AFTER DELETE ON elec_officers
FOR EACH ROW
BEGIN
  INSERT INTO database_alerts (table_name, action, details, user_id, ip_address)
  VALUES ('elec_officers', 'DELETE', JSON_OBJECT('old', JSON_OBJECT('id', OLD.id, 'name', OLD.name, 'email', OLD.email, 'role', OLD.role)), NULL, NULL);
END$$

-- VOTERS
CREATE TRIGGER trg_voters_after_insert
AFTER INSERT ON voters
FOR EACH ROW
BEGIN
  INSERT INTO database_alerts (table_name, action, details, user_id, ip_address)
  VALUES ('voters', 'INSERT', JSON_OBJECT('new', JSON_OBJECT('id', NEW.id, 'name', NEW.name, 'email', NEW.email, 'status', NEW.status, 'role', NEW.role)), NULL, NULL);
END$$

CREATE TRIGGER trg_voters_after_update
AFTER UPDATE ON voters
FOR EACH ROW
BEGIN
  INSERT INTO database_alerts (table_name, action, details, user_id, ip_address)
  VALUES ('voters', 'UPDATE', JSON_OBJECT('old', JSON_OBJECT('id', OLD.id, 'name', OLD.name, 'email', OLD.email, 'status', OLD.status, 'role', OLD.role), 'new', JSON_OBJECT('id', NEW.id, 'name', NEW.name, 'email', NEW.email, 'status', NEW.status, 'role', NEW.role)), NULL, NULL);
END$$

CREATE TRIGGER trg_voters_after_delete
AFTER DELETE ON voters
FOR EACH ROW
BEGIN
  INSERT INTO database_alerts (table_name, action, details, user_id, ip_address)
  VALUES ('voters', 'DELETE', JSON_OBJECT('old', JSON_OBJECT('id', OLD.id, 'name', OLD.name, 'email', OLD.email, 'status', OLD.status, 'role', OLD.role)), NULL, NULL);
END$$

-- CANDIDATES
CREATE TRIGGER trg_candidates_after_insert
AFTER INSERT ON candidates
FOR EACH ROW
BEGIN
  INSERT INTO database_alerts (table_name, action, details, user_id, ip_address)
  VALUES ('candidates', 'INSERT', JSON_OBJECT('new', JSON_OBJECT('id', NEW.id, 'name', NEW.name, 'sex', NEW.sex, 'age', NEW.age, 'political_party', NEW.political_party)), NULL, NULL);
END$$

CREATE TRIGGER trg_candidates_after_update
AFTER UPDATE ON candidates
FOR EACH ROW
BEGIN
  INSERT INTO database_alerts (table_name, action, details, user_id, ip_address)
  VALUES ('candidates', 'UPDATE', JSON_OBJECT('old', JSON_OBJECT('id', OLD.id, 'name', OLD.name, 'sex', OLD.sex, 'age', OLD.age, 'political_party', OLD.political_party), 'new', JSON_OBJECT('id', NEW.id, 'name', NEW.name, 'sex', NEW.sex, 'age', NEW.age, 'political_party', NEW.political_party)), NULL, NULL);
END$$

CREATE TRIGGER trg_candidates_after_delete
AFTER DELETE ON candidates
FOR EACH ROW
BEGIN
  INSERT INTO database_alerts (table_name, action, details, user_id, ip_address)
  VALUES ('candidates', 'DELETE', JSON_OBJECT('old', JSON_OBJECT('id', OLD.id, 'name', OLD.name, 'sex', OLD.sex, 'age', OLD.age, 'political_party', OLD.political_party)), NULL, NULL);
END$$

-- VOTES
CREATE TRIGGER trg_votes_after_insert
AFTER INSERT ON votes
FOR EACH ROW
BEGIN
  INSERT INTO database_alerts (table_name, action, details, user_id, ip_address)
  VALUES ('votes', 'INSERT', JSON_OBJECT('new', JSON_OBJECT('id', NEW.id, 'voter_id', NEW.voter_id, 'candidate_id', NEW.candidate_id, 'vote_time', DATE_FORMAT(NEW.vote_time, '%Y-%m-%d %H:%i:%s'))), NULL, NULL);
END$$

CREATE TRIGGER trg_votes_after_update
AFTER UPDATE ON votes
FOR EACH ROW
BEGIN
  INSERT INTO database_alerts (table_name, action, details, user_id, ip_address)
  VALUES ('votes', 'UPDATE', JSON_OBJECT('old', JSON_OBJECT('id', OLD.id, 'voter_id', OLD.voter_id, 'candidate_id', OLD.candidate_id, 'vote_time', DATE_FORMAT(OLD.vote_time, '%Y-%m-%d %H:%i:%s')), 'new', JSON_OBJECT('id', NEW.id, 'voter_id', NEW.voter_id, 'candidate_id', NEW.candidate_id, 'vote_time', DATE_FORMAT(NEW.vote_time, '%Y-%m-%d %H:%i:%s'))), NULL, NULL);
END$$

CREATE TRIGGER trg_votes_after_delete
AFTER DELETE ON votes
FOR EACH ROW
BEGIN
  INSERT INTO database_alerts (table_name, action, details, user_id, ip_address)
  VALUES ('votes', 'DELETE', JSON_OBJECT('old', JSON_OBJECT('id', OLD.id, 'voter_id', OLD.voter_id, 'candidate_id', OLD.candidate_id, 'vote_time', DATE_FORMAT(OLD.vote_time, '%Y-%m-%d %H:%i:%s'))), NULL, NULL);
END$$

DELIMITER ;