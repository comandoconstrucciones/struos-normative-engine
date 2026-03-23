
-- ═══════════════════════════════════════════════════════════════
-- NORMATIVE ENGINE TABLES - NSR-10
-- ═══════════════════════════════════════════════════════════════

-- Schema
CREATE SCHEMA IF NOT EXISTS normative;

-- Coeficientes de sitio (Fa, Fv)
CREATE TABLE IF NOT EXISTS normative.site_coefficients (
    id SERIAL PRIMARY KEY,
    norm_code VARCHAR(20) NOT NULL DEFAULT 'NSR-10',
    coef_type VARCHAR(2) NOT NULL,  -- 'Fa' o 'Fv'
    soil_type VARCHAR(2) NOT NULL,  -- 'A', 'B', 'C', 'D', 'E'
    
    value_005 DECIMAL(4, 3),
    value_010 DECIMAL(4, 3),
    value_015 DECIMAL(4, 3),
    value_020 DECIMAL(4, 3),
    value_025 DECIMAL(4, 3),
    value_030 DECIMAL(4, 3),
    value_035 DECIMAL(4, 3),
    value_040 DECIMAL(4, 3),
    value_045 DECIMAL(4, 3),
    value_050 DECIMAL(4, 3),
    
    reference VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT now(),
    
    UNIQUE(norm_code, coef_type, soil_type)
);

-- Zonas sísmicas
CREATE TABLE IF NOT EXISTS normative.seismic_zones (
    id SERIAL PRIMARY KEY,
    norm_code VARCHAR(20) NOT NULL DEFAULT 'NSR-10',
    country_code VARCHAR(3) DEFAULT 'COL',
    department VARCHAR(100),
    municipality VARCHAR(100),
    
    Aa DECIMAL(4, 3),
    Av DECIMAL(4, 3),
    zone_name VARCHAR(50),
    
    lat DECIMAL(10, 6),
    lon DECIMAL(10, 6),
    
    created_at TIMESTAMPTZ DEFAULT now(),
    
    UNIQUE(norm_code, municipality)
);

-- Combinaciones de carga
CREATE TABLE IF NOT EXISTS normative.load_combinations (
    id SERIAL PRIMARY KEY,
    norm_code VARCHAR(20) NOT NULL DEFAULT 'NSR-10',
    method VARCHAR(10) NOT NULL,  -- 'LRFD' o 'ASD'
    combo_number INT,
    combo_name VARCHAR(100),
    
    factor_D DECIMAL(3, 2),
    factor_L DECIMAL(3, 2),
    factor_Lr DECIMAL(3, 2),
    factor_S DECIMAL(3, 2),
    factor_W DECIMAL(3, 2),
    factor_E DECIMAL(3, 2),
    
    reference VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT now(),
    
    UNIQUE(norm_code, method, combo_number)
);

-- Límites de deriva
CREATE TABLE IF NOT EXISTS normative.drift_limits (
    id SERIAL PRIMARY KEY,
    norm_code VARCHAR(20) NOT NULL DEFAULT 'NSR-10',
    system_name VARCHAR(100),
    
    drift_limit DECIMAL(5, 4),
    
    reference VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT now(),
    
    UNIQUE(norm_code, system_name)
);

-- Factores de respuesta
CREATE TABLE IF NOT EXISTS normative.response_factors (
    id SERIAL PRIMARY KEY,
    norm_code VARCHAR(20) NOT NULL DEFAULT 'NSR-10',
    system_name VARCHAR(100),
    
    R0 DECIMAL(4, 2),
    Omega0 DECIMAL(4, 2),
    Cd DECIMAL(4, 2),
    
    reference VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT now(),
    
    UNIQUE(norm_code, system_name)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_seismic_zones_municipality 
    ON normative.seismic_zones (municipality);
CREATE INDEX IF NOT EXISTS idx_site_coef_lookup 
    ON normative.site_coefficients (norm_code, coef_type, soil_type);
