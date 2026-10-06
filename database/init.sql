-- Combined schema for local development.
-- Runs automatically when the docker-compose postgres container is created for the first time.

CREATE TYPE policy_type_enum AS ENUM ('auto', 'health', 'life', 'home', 'travel');

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    dob DATE,
    risk_profile JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE providers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    country VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE policies (
    id SERIAL PRIMARY KEY,
    provider_id INT NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
    policy_type policy_type_enum NOT NULL,
    title VARCHAR(255) NOT NULL,
    coverage JSONB,
    premium NUMERIC,
    term_months INT,
    deductible NUMERIC,
    tnc_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE userpolicies (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    policy_id INTEGER NOT NULL REFERENCES policies(id) ON DELETE CASCADE,
    policy_number VARCHAR(50) UNIQUE NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    premium NUMERIC(12,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    auto_renew BOOLEAN DEFAULT FALSE
);

CREATE TABLE claims (
    id SERIAL PRIMARY KEY,
    user_policy_id INTEGER NOT NULL REFERENCES userpolicies(id) ON DELETE CASCADE,
    claim_number VARCHAR(50) UNIQUE NOT NULL,
    claim_type VARCHAR(100) NOT NULL,
    incident_date DATE NOT NULL,
    amount_claimed NUMERIC(12,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE claimdocuments (
    id SERIAL PRIMARY KEY,
    claim_id INTEGER NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    file_url TEXT NOT NULL,
    doc_type VARCHAR(100),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE fraudflags (
    id SERIAL PRIMARY KEY,
    claim_id INTEGER REFERENCES claims(id) ON DELETE CASCADE,
    rule_code VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE recommendations (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    policy_id INT NOT NULL REFERENCES policies(id) ON DELETE CASCADE,
    score NUMERIC,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE adminlogs (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER NOT NULL REFERENCES users(id),
    action TEXT NOT NULL,
    target_type VARCHAR NOT NULL,
    target_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed data so the Policies / Compare pages show something immediately.
INSERT INTO providers (name, country) VALUES
    ('SecureLife Insurance', 'India'),
    ('TrustGuard General', 'India'),
    ('SafeHaven Assurance', 'India');

INSERT INTO policies (provider_id, policy_type, title, coverage, premium, term_months, deductible, tnc_url) VALUES
    (1, 'health', 'FamilyCare Health Plan', '{"hospitalization": true, "opd": false}', 8500, 12, 5000, ''),
    (2, 'health', 'Comprehensive Health Shield', '{"hospitalization": true, "opd": true}', 12000, 12, 3000, ''),
    (1, 'travel', 'Domestic Travel Cover', '{"trip_cancellation": true}', 1500, 3, 500, ''),
    (2, 'travel', 'International Travel Plus', '{"trip_cancellation": true, "medical": true}', 4500, 6, 1000, ''),
    (3, 'life', 'Term Life Secure', '{"payout": "lumpsum"}', 6000, 240, 0, ''),
    (1, 'life', 'Life Cover with Savings', '{"payout": "lumpsum", "savings": true}', 9500, 180, 0, ''),
    (2, 'auto', 'Private Car Comprehensive', '{"roadside_assistance": true}', 7000, 12, 2000, ''),
    (3, 'auto', 'Two-Wheeler Accident Cover', '{"accident_cover": true}', 2000, 12, 500, ''),
    (1, 'home', 'HomeSafe Structure Plan', '{"structure": true}', 5000, 12, 2500, ''),
    (3, 'home', 'Complete Home Protection', '{"structure": true, "contents": true}', 8000, 12, 3000, '');
