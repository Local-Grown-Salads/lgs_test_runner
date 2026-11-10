-- Agronomist SDK Test Database Schema
-- This creates the minimal schema required for testing the SDK

-- Create the api schema (PostgREST exposes this)
CREATE SCHEMA IF NOT EXISTS api;

-- Anonymous role for PostgREST
CREATE ROLE anon NOLOGIN;
GRANT USAGE ON SCHEMA api TO anon;

-- =============================================================================
-- fetch_product_assembly_db_view
-- Used by: assembly.get_product_by(product_id)
-- =============================================================================
CREATE TABLE api.product_assembly (
    product_id TEXT PRIMARY KEY,
    product_name TEXT,
    assembly_line TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE VIEW api.fetch_product_assembly_db_view AS
SELECT * FROM api.product_assembly;

GRANT SELECT ON api.fetch_product_assembly_db_view TO anon;

-- Seed test data
INSERT INTO api.product_assembly (product_id, product_name, assembly_line, status) VALUES
    ('TEST-001', 'Test Product 1', 'Line A', 'active'),
    ('TEST-002', 'Test Product 2', 'Line B', 'active'),
    ('TEST-003', 'Test Product 3', 'Line A', 'inactive');

-- =============================================================================
-- fetch_inspector_db_view
-- Used by: inspector.get_inspection_data(), inspector.get_expected_configuration()
-- =============================================================================
CREATE TABLE api.inspector_config (
    id SERIAL PRIMARY KEY,
    grow_formula_id TEXT NOT NULL,
    day_number INTEGER NOT NULL,
    time_segment_id TEXT NOT NULL,
    start_time TEXT,
    end_time TEXT,
    environment_formula_name TEXT,
    expected_ph NUMERIC,
    min_ph NUMERIC,
    max_ph NUMERIC,
    expected_air_temperature_c NUMERIC,
    min_air_temperature_c NUMERIC,
    max_air_temperature_c NUMERIC,
    is_light_on BOOLEAN,
    UNIQUE(grow_formula_id, day_number, time_segment_id)
);

CREATE VIEW api.fetch_inspector_db_view AS
SELECT * FROM api.inspector_config;

GRANT SELECT ON api.fetch_inspector_db_view TO anon;

-- Seed test data
INSERT INTO api.inspector_config (
    grow_formula_id, day_number, time_segment_id,
    start_time, end_time, environment_formula_name,
    expected_ph, min_ph, max_ph,
    expected_air_temperature_c, min_air_temperature_c, max_air_temperature_c,
    is_light_on
) VALUES
    ('FORMULA-001', 1, 'MORNING', '06:00', '12:00', 'Standard Grow', 6.5, 6.0, 7.0, 24.0, 22.0, 26.0, true),
    ('FORMULA-001', 1, 'AFTERNOON', '12:00', '18:00', 'Standard Grow', 6.5, 6.0, 7.0, 26.0, 24.0, 28.0, true),
    ('FORMULA-001', 1, 'NIGHT', '18:00', '06:00', 'Standard Grow', 6.5, 6.0, 7.0, 20.0, 18.0, 22.0, false);
