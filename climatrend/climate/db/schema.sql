-- =====================================================================
-- ClimaTrend Climate & Environmental Intelligence Schema (SQLite DDL)
-- Unified database supporting Regional Climatology, Early-Warnings,
-- Shared Alerts Engine, Carbon Footprint, Risk & Infrastructure Planning.
-- =====================================================================

PRAGMA foreign_keys = ON;

-- 1. Monitored Regions
CREATE TABLE IF NOT EXISTS regions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    country TEXT DEFAULT 'Unknown',
    elevation REAL DEFAULT 0.0,
    bounding_box TEXT,
    baseline_computed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Regional Climatology Baselines (Day-of-Year & Monthly)
CREATE TABLE IF NOT EXISTS climatology_baselines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region_id INTEGER NOT NULL REFERENCES regions(id) ON DELETE CASCADE,
    day_of_year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    metric TEXT NOT NULL,
    mean REAL NOT NULL,
    std REAL NOT NULL,
    p5 REAL NOT NULL,
    p10 REAL NOT NULL,
    p50 REAL NOT NULL,
    p90 REAL NOT NULL,
    p95 REAL NOT NULL,
    p99 REAL NOT NULL,
    sample_years INTEGER DEFAULT 30,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(region_id, day_of_year, metric)
);

CREATE INDEX IF NOT EXISTS idx_baselines_lookup 
ON climatology_baselines(region_id, day_of_year, metric);

-- 3. Extreme Event Indices (xclim / Climatological Trends)
CREATE TABLE IF NOT EXISTS extreme_indices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region_id INTEGER NOT NULL REFERENCES regions(id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    heatwave_days INTEGER DEFAULT 0,
    consecutive_dry_days INTEGER DEFAULT 0,
    heavy_rain_days_20mm INTEGER DEFAULT 0,
    heavy_rain_days_50mm INTEGER DEFAULT 0,
    cold_spell_days INTEGER DEFAULT 0,
    max_daily_precip_mm REAL DEFAULT 0.0,
    trend_slope REAL,
    trend_p_value REAL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(region_id, year)
);

-- 4. Statistical Return Periods (GEV / Gumbel fit)
CREATE TABLE IF NOT EXISTS return_periods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region_id INTEGER NOT NULL REFERENCES regions(id) ON DELETE CASCADE,
    metric TEXT NOT NULL,
    return_period_years INTEGER NOT NULL,
    threshold_value REAL NOT NULL,
    distribution_type TEXT DEFAULT 'GEV',
    params_json TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(region_id, metric, return_period_years)
);

-- 5. Alert Rules (Config-driven for Features 6 and 7)
CREATE TABLE IF NOT EXISTS alert_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_name TEXT NOT NULL UNIQUE,
    hazard_type TEXT NOT NULL,
    condition_type TEXT NOT NULL,
    threshold_config TEXT NOT NULL,
    severity TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. User Alert Subscriptions
CREATE TABLE IF NOT EXISTS alert_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT 'user_default',
    region_id INTEGER REFERENCES regions(id) ON DELETE CASCADE,
    latitude REAL,
    longitude REAL,
    radius_km REAL DEFAULT 50.0,
    hazard_types TEXT NOT NULL DEFAULT '["all"]',
    min_severity TEXT NOT NULL DEFAULT 'Advisory',
    channels TEXT NOT NULL DEFAULT '["in_app"]',
    destination TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. SHARED ALERT LOG TABLE (Features 6 & 7 Unified Engine)
CREATE TABLE IF NOT EXISTS alert_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    region_id INTEGER REFERENCES regions(id) ON DELETE SET NULL,
    hazard_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    historical_context TEXT,
    latitude REAL,
    longitude REAL,
    source TEXT NOT NULL,
    forecast_value REAL,
    normal_value REAL,
    sent_channels TEXT DEFAULT '["in_app"]',
    status TEXT DEFAULT 'active',
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_alert_log_region ON alert_log(region_id, status);
CREATE INDEX IF NOT EXISTS idx_alert_log_detected ON alert_log(detected_at DESC);

-- 8. Backtest & Calibration Results
CREATE TABLE IF NOT EXISTS backtest_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region_id INTEGER NOT NULL REFERENCES regions(id) ON DELETE CASCADE,
    hazard_type TEXT NOT NULL,
    test_period_start TEXT NOT NULL,
    test_period_end TEXT NOT NULL,
    hit_rate REAL NOT NULL,
    false_alarm_rate REAL NOT NULL,
    lead_time_hours REAL NOT NULL,
    total_events INTEGER NOT NULL,
    calibrated_thresholds TEXT,
    report_markdown TEXT,
    evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. Carbon Footprint Activities (Feature 1)
CREATE TABLE IF NOT EXISTS carbon_activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT 'user_default',
    activity_date TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    co2e_kg REAL NOT NULL,
    is_anomaly INTEGER DEFAULT 0,
    anomaly_score REAL DEFAULT 0.0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_carbon_user_date ON carbon_activities(user_id, activity_date);

-- 10. Environmental Readings (Feature 2)
CREATE TABLE IF NOT EXISTS environmental_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_name TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    timestamp TEXT NOT NULL,
    aqi INTEGER,
    pm2_5 REAL,
    pm10 REAL,
    no2 REAL,
    o3 REAL,
    co REAL,
    source TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(latitude, longitude, timestamp, source)
);

-- 11. Climate Risk Scores (Feature 3)
CREATE TABLE IF NOT EXISTS climate_risk_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region_id INTEGER REFERENCES regions(id) ON DELETE CASCADE,
    assessment_date TEXT NOT NULL,
    hazard_type TEXT NOT NULL,
    hazard_score REAL NOT NULL,
    exposure_score REAL NOT NULL,
    vulnerability_score REAL NOT NULL,
    total_risk REAL NOT NULL,
    risk_level TEXT NOT NULL,
    explanations_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 12. Infrastructure Assets (Feature 5)
CREATE TABLE IF NOT EXISTS infrastructure_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT 'user_default',
    name TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    elevation_m REAL DEFAULT 0.0,
    flood_exposure_score REAL DEFAULT 0.0,
    heat_exposure_score REAL DEFAULT 0.0,
    fire_exposure_score REAL DEFAULT 0.0,
    vulnerability_score REAL DEFAULT 0.0,
    priority_rank INTEGER DEFAULT 0,
    resilience_measures TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
