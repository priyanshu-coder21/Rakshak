-- Enable PostGIS for spatial data (latitude/longitude mapping)
CREATE EXTENSION IF NOT EXISTS postgis;

-- 1. DistressTickets (The Core Queue)
CREATE TABLE IF NOT EXISTS DistressTickets (
    token_id VARCHAR(50) PRIMARY KEY,
    raw_message TEXT,
    extracted_json JSONB,
    location GEOMETRY(Point, 4326),
    severity INTEGER,
    vulnerability INTEGER,
    wait_time_start TIMESTAMPTZ DEFAULT NOW(),
    vwps_score FLOAT,
    status VARCHAR(20) DEFAULT 'Pending'
);

-- 2. RescueTeams (Resource Management)
CREATE TABLE IF NOT EXISTS RescueTeams (
    team_id VARCHAR(50) PRIMARY KEY,
    current_location GEOMETRY(Point, 4326),
    status VARCHAR(20) DEFAULT 'Available',
    team_capacity INTEGER
);

-- 4. Dispatch_Logs (Audit & Alerts)
CREATE TABLE IF NOT EXISTS Dispatch_Logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_id VARCHAR(50) REFERENCES DistressTickets(token_id),
    team_id VARCHAR(50) REFERENCES RescueTeams(team_id),
    dispatch_time TIMESTAMPTZ DEFAULT NOW(),
    sns_alert_sent BOOLEAN DEFAULT FALSE
);