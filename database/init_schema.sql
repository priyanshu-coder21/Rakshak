-- Enable extensions for map coordinates and unique IDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS postgis;

-- Create the RescueTeams Table (Available Resources)
CREATE TABLE IF NOT EXISTS RescueTeams (
    team_id VARCHAR(50) PRIMARY KEY,
    current_location GEOMETRY(Point, 4326) NOT NULL, -- PostGIS mapping coordinate
    status VARCHAR(20) DEFAULT 'Available' CHECK (status IN ('Available', 'In_Transit', 'Assigned')),
    team_capacity INTEGER NOT NULL
);

-- Create the DistressTickets Table (The Victims)
CREATE TABLE IF NOT EXISTS DistressTickets (
    token_id VARCHAR(50) PRIMARY KEY, -- Your unique tracking ID
    raw_message TEXT NOT NULL, 
    extracted_json JSONB, -- Stores AI-extracted age and condition[cite: 1]
    location GEOMETRY(Point, 4326) NOT NULL, 
    severity INTEGER DEFAULT 0, 
    vulnerability INTEGER DEFAULT 0, 
    wait_time_start TIMESTAMPTZ DEFAULT NOW(), 
    vwps_score FLOAT DEFAULT 0.0, 
    status VARCHAR(20) DEFAULT 'Pending' CHECK (status IN ('Pending', 'Dispatched', 'Resolved'))
);

-- Create the Dispatch_Logs Table (The Relationship Table)
CREATE TABLE IF NOT EXISTS Dispatch_Logs (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    token_id VARCHAR(50) NOT NULL REFERENCES DistressTickets(token_id), -- Links to the victim[cite: 1]
    team_id VARCHAR(50) NOT NULL REFERENCES RescueTeams(team_id), -- Links to the rescue team[cite: 1]
    dispatch_time TIMESTAMPTZ DEFAULT NOW(),
    sns_alert_sent BOOLEAN DEFAULT FALSE
);



