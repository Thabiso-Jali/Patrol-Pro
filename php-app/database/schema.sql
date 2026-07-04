CREATE DATABASE IF NOT EXISTS patrol_pro CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE patrol_pro;

CREATE TABLE roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(40) NOT NULL UNIQUE
);

CREATE TABLE clients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(160) NOT NULL,
    site_name VARCHAR(160) NOT NULL,
    contact_email VARCHAR(160),
    brand_color VARCHAR(20) DEFAULT '#f472b6',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    role_id INT NOT NULL,
    client_id INT NULL,
    name VARCHAR(160) NOT NULL,
    email VARCHAR(160) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    status ENUM('active','inactive') NOT NULL DEFAULT 'active',
    last_login_at DATETIME NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id),
    FOREIGN KEY (client_id) REFERENCES clients(id),
    INDEX idx_users_status (status)
);

CREATE TABLE guards_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    phone VARCHAR(60),
    badge_number VARCHAR(80) UNIQUE,
    certification VARCHAR(160),
    emergency_contact VARCHAR(160),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE patrol_routes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client_id INT NOT NULL,
    name VARCHAR(160) NOT NULL,
    site_name VARCHAR(160) NOT NULL,
    description TEXT,
    status ENUM('draft','active','paused','completed') NOT NULL DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(id),
    INDEX idx_routes_status (status)
);

CREATE TABLE checkpoints (
    id INT AUTO_INCREMENT PRIMARY KEY,
    route_id INT NOT NULL,
    name VARCHAR(160) NOT NULL,
    checkpoint_code VARCHAR(120) NOT NULL,
    location_label VARCHAR(180),
    sequence_order INT NOT NULL DEFAULT 1,
    expected_interval_minutes INT NOT NULL DEFAULT 30,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (route_id) REFERENCES patrol_routes(id),
    UNIQUE KEY uq_route_checkpoint_code (route_id, checkpoint_code)
);

CREATE TABLE shifts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    guard_user_id INT NOT NULL,
    route_id INT NOT NULL,
    starts_at DATETIME NOT NULL,
    ends_at DATETIME NOT NULL,
    status ENUM('scheduled','active','completed','missed') NOT NULL DEFAULT 'scheduled',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guard_user_id) REFERENCES users(id),
    FOREIGN KEY (route_id) REFERENCES patrol_routes(id),
    INDEX idx_shifts_calendar (starts_at, ends_at)
);

CREATE TABLE patrol_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shift_id INT NOT NULL,
    checkpoint_id INT NOT NULL,
    guard_user_id INT NOT NULL,
    completed_at DATETIME NOT NULL,
    latitude DECIMAL(10,7) NULL,
    longitude DECIMAL(10,7) NULL,
    status ENUM('completed','missed','flagged') NOT NULL DEFAULT 'completed',
    notes TEXT,
    FOREIGN KEY (shift_id) REFERENCES shifts(id),
    FOREIGN KEY (checkpoint_id) REFERENCES checkpoints(id),
    FOREIGN KEY (guard_user_id) REFERENCES users(id),
    INDEX idx_patrol_logs_completed (completed_at)
);

CREATE TABLE incidents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client_id INT NOT NULL,
    route_id INT NULL,
    guard_user_id INT NOT NULL,
    category VARCHAR(80) NOT NULL,
    severity ENUM('low','medium','high','critical') NOT NULL DEFAULT 'medium',
    title VARCHAR(180) NOT NULL,
    notes TEXT,
    evidence_path VARCHAR(255),
    latitude DECIMAL(10,7) NULL,
    longitude DECIMAL(10,7) NULL,
    status ENUM('open','investigating','resolved') NOT NULL DEFAULT 'open',
    reported_at DATETIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(id),
    FOREIGN KEY (route_id) REFERENCES patrol_routes(id),
    FOREIGN KEY (guard_user_id) REFERENCES users(id),
    INDEX idx_incidents_status (status),
    INDEX idx_incidents_reported (reported_at)
);

CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    title VARCHAR(180) NOT NULL,
    body TEXT,
    type VARCHAR(60) NOT NULL,
    read_at DATETIME NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_notifications_read (read_at)
);

CREATE TABLE audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    action VARCHAR(120) NOT NULL,
    entity_type VARCHAR(80) NOT NULL,
    entity_id INT NULL,
    detail TEXT,
    ip_address VARCHAR(80),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_audit_created (created_at)
);

INSERT IGNORE INTO roles (id, name) VALUES
(1, 'Admin'), (2, 'Supervisor'), (3, 'Guard'), (4, 'Client');

INSERT INTO clients (id, name, site_name, contact_email) VALUES
(1, 'Northbank Estates', 'Northbank Business Park', 'client@northbank.example')
ON DUPLICATE KEY UPDATE name = VALUES(name);

INSERT INTO users (id, role_id, client_id, name, email, password_hash) VALUES
(1, 1, NULL, 'Patrol Pro Admin', 'admin@patrolpro.local', '$2y$12$wOiK3nIckLHtRcwzdSyPDeEOXqo3k2HkKxNmnpF.clQlcsOz45vge'),
(2, 3, NULL, 'Jordan Guard', 'guard@patrolpro.local', '$2y$12$wOiK3nIckLHtRcwzdSyPDeEOXqo3k2HkKxNmnpF.clQlcsOz45vge'),
(3, 4, 1, 'Northbank Client', 'client@patrolpro.local', '$2y$12$wOiK3nIckLHtRcwzdSyPDeEOXqo3k2HkKxNmnpF.clQlcsOz45vge')
ON DUPLICATE KEY UPDATE email = VALUES(email);

INSERT INTO guards_profiles (user_id, phone, badge_number, certification, emergency_contact)
VALUES (2, '+44 020 0000 0101', 'PP-1024', 'SIA Licensed', 'Control Room')
ON DUPLICATE KEY UPDATE badge_number = VALUES(badge_number);

INSERT INTO patrol_routes (id, client_id, name, site_name, description, status) VALUES
(1, 1, 'Northbank Night Exterior', 'Northbank Business Park', 'Perimeter doors, car park, loading bay and reception sweep.', 'active')
ON DUPLICATE KEY UPDATE name = VALUES(name);

INSERT INTO checkpoints (route_id, name, checkpoint_code, location_label, sequence_order, expected_interval_minutes) VALUES
(1, 'Main Reception', 'NB-REC-001', 'Reception lobby', 1, 30),
(1, 'Loading Bay', 'NB-LOAD-002', 'Rear service yard', 2, 30),
(1, 'Car Park East', 'NB-PARK-003', 'East car park gate', 3, 30)
ON DUPLICATE KEY UPDATE name = VALUES(name);
