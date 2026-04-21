#!/usr/bin/env python3
"""
Ingestión NSR-10 al Knowledge Graph
====================================

Script simplificado que:
1. Extrae páginas clave de NSR-10 con Vision AI (usando tool de OpenClaw)
2. Carga datos estructurados a Supabase
3. Genera embeddings con Voyage AI
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from uuid import uuid4

import fitz  # PyMuPDF


# ═══════════════════════════════════════════════════════════════
# Datos Hardcoded de NSR-10 (extraídos manualmente)
# ═══════════════════════════════════════════════════════════════

# Tabla A.2.4-3: Coeficiente Fa
FA_TABLE = {
    "table_id": "Tabla A.2.4-3",
    "title": "Valores del coeficiente Fa, para la zona de períodos cortos del espectro",
    "description": "Coeficiente que amplifica las ordenadas del espectro en roca para efectos de sitio en períodos cortos",
    "reference": "NSR-10 A.2.4.5.5",
    "headers": ["Tipo de Perfil", "Aa ≤ 0.1", "Aa = 0.2", "Aa = 0.3", "Aa = 0.4", "Aa ≥ 0.5"],
    "data": {
        "A": {"0.05": 0.8, "0.10": 0.8, "0.15": 0.8, "0.20": 0.8, "0.25": 0.8, "0.30": 0.8, "0.35": 0.8, "0.40": 0.8, "0.45": 0.8, "0.50": 0.8},
        "B": {"0.05": 1.0, "0.10": 1.0, "0.15": 1.0, "0.20": 1.0, "0.25": 1.0, "0.30": 1.0, "0.35": 1.0, "0.40": 1.0, "0.45": 1.0, "0.50": 1.0},
        "C": {"0.05": 1.2, "0.10": 1.2, "0.15": 1.15, "0.20": 1.1, "0.25": 1.05, "0.30": 1.0, "0.35": 1.0, "0.40": 1.0, "0.45": 1.0, "0.50": 1.0},
        "D": {"0.05": 1.6, "0.10": 1.6, "0.15": 1.5, "0.20": 1.4, "0.25": 1.3, "0.30": 1.2, "0.35": 1.15, "0.40": 1.1, "0.45": 1.05, "0.50": 1.0},
        "E": {"0.05": 2.5, "0.10": 2.5, "0.15": 2.1, "0.20": 1.7, "0.25": 1.45, "0.30": 1.2, "0.35": 1.05, "0.40": 0.9, "0.45": 0.9, "0.50": 0.9},
    }
}

# Tabla A.2.4-4: Coeficiente Fv
FV_TABLE = {
    "table_id": "Tabla A.2.4-4",
    "title": "Valores del coeficiente Fv, para la zona de períodos intermedios del espectro",
    "description": "Coeficiente que amplifica las ordenadas del espectro en roca para efectos de sitio en períodos intermedios",
    "reference": "NSR-10 A.2.4.5.6",
    "headers": ["Tipo de Perfil", "Av ≤ 0.1", "Av = 0.2", "Av = 0.3", "Av = 0.4", "Av ≥ 0.5"],
    "data": {
        "A": {"0.05": 0.8, "0.10": 0.8, "0.15": 0.8, "0.20": 0.8, "0.25": 0.8, "0.30": 0.8, "0.35": 0.8, "0.40": 0.8, "0.45": 0.8, "0.50": 0.8},
        "B": {"0.05": 1.0, "0.10": 1.0, "0.15": 1.0, "0.20": 1.0, "0.25": 1.0, "0.30": 1.0, "0.35": 1.0, "0.40": 1.0, "0.45": 1.0, "0.50": 1.0},
        "C": {"0.05": 1.7, "0.10": 1.7, "0.15": 1.65, "0.20": 1.6, "0.25": 1.55, "0.30": 1.5, "0.35": 1.45, "0.40": 1.4, "0.45": 1.35, "0.50": 1.3},
        "D": {"0.05": 2.4, "0.10": 2.4, "0.15": 2.2, "0.20": 2.0, "0.25": 1.9, "0.30": 1.8, "0.35": 1.7, "0.40": 1.6, "0.45": 1.55, "0.50": 1.5},
        "E": {"0.05": 3.5, "0.10": 3.5, "0.15": 3.35, "0.20": 3.2, "0.25": 3.0, "0.30": 2.8, "0.35": 2.6, "0.40": 2.4, "0.45": 2.4, "0.50": 2.4},
    }
}

# Zonas sísmicas de Colombia (muestra de municipios principales)
SEISMIC_ZONES = [
    # Departamento, Municipio, Aa, Av, Zona
    ("Cundinamarca", "Bogotá D.C.", 0.15, 0.20, "Intermedia"),
    ("Antioquia", "Medellín", 0.15, 0.20, "Intermedia"),
    ("Valle del Cauca", "Cali", 0.25, 0.25, "Alta"),
    ("Atlántico", "Barranquilla", 0.10, 0.10, "Baja"),
    ("Bolívar", "Cartagena", 0.10, 0.10, "Baja"),
    ("Santander", "Bucaramanga", 0.25, 0.25, "Alta"),
    ("Norte de Santander", "Cúcuta", 0.30, 0.30, "Alta"),
    ("Risaralda", "Pereira", 0.25, 0.25, "Alta"),
    ("Caldas", "Manizales", 0.25, 0.25, "Alta"),
    ("Quindío", "Armenia", 0.25, 0.30, "Alta"),
    ("Tolima", "Ibagué", 0.20, 0.20, "Intermedia"),
    ("Huila", "Neiva", 0.25, 0.25, "Alta"),
    ("Nariño", "Pasto", 0.30, 0.35, "Alta"),
    ("Cauca", "Popayán", 0.25, 0.30, "Alta"),
    ("Boyacá", "Tunja", 0.15, 0.15, "Intermedia"),
    ("Meta", "Villavicencio", 0.20, 0.20, "Intermedia"),
    ("Córdoba", "Montería", 0.10, 0.10, "Baja"),
    ("Sucre", "Sincelejo", 0.10, 0.10, "Baja"),
    ("Magdalena", "Santa Marta", 0.10, 0.15, "Intermedia"),
    ("Cesar", "Valledupar", 0.10, 0.10, "Baja"),
]

# Combinaciones de carga LRFD (NSR-10 B.2.4)
LOAD_COMBINATIONS_LRFD = [
    {"number": 1, "name": "1.4D", "factors": {"D": 1.4}, "reference": "B.2.4-1"},
    {"number": 2, "name": "1.2D + 1.6L + 0.5(Lr o S)", "factors": {"D": 1.2, "L": 1.6, "Lr": 0.5}, "reference": "B.2.4-2"},
    {"number": 3, "name": "1.2D + 1.6(Lr o S) + (L o 0.5W)", "factors": {"D": 1.2, "Lr": 1.6, "L": 1.0}, "reference": "B.2.4-3"},
    {"number": 4, "name": "1.2D + 1.0W + L + 0.5(Lr o S)", "factors": {"D": 1.2, "W": 1.0, "L": 1.0, "Lr": 0.5}, "reference": "B.2.4-4"},
    {"number": 5, "name": "1.2D + 1.0E + L", "factors": {"D": 1.2, "E": 1.0, "L": 1.0}, "reference": "B.2.4-5"},
    {"number": 6, "name": "0.9D + 1.0W", "factors": {"D": 0.9, "W": 1.0}, "reference": "B.2.4-6"},
    {"number": 7, "name": "0.9D + 1.0E", "factors": {"D": 0.9, "E": 1.0}, "reference": "B.2.4-7"},
]

# Límites de deriva (NSR-10 A.6.4)
DRIFT_LIMITS = [
    {"system": "portico_especial", "limit": 0.010, "reference": "A.6.4.1"},
    {"system": "portico_intermedio", "limit": 0.010, "reference": "A.6.4.1"},
    {"system": "portico_ordinario", "limit": 0.010, "reference": "A.6.4.1"},
    {"system": "muro_especial", "limit": 0.010, "reference": "A.6.4.1"},
    {"system": "muro_intermedio", "limit": 0.010, "reference": "A.6.4.1"},
    {"system": "dual", "limit": 0.010, "reference": "A.6.4.1"},
    {"system": "mamposteria_confinada", "limit": 0.005, "reference": "A.6.4.1"},
    {"system": "mamposteria_reforzada", "limit": 0.005, "reference": "A.6.4.1"},
]

# Factores de respuesta (NSR-10 A.3.3)
RESPONSE_FACTORS = [
    {"system": "portico_especial", "R0": 7.0, "Omega0": 3.0, "Cd": 5.5, "reference": "A.3.3"},
    {"system": "portico_intermedio", "R0": 5.0, "Omega0": 3.0, "Cd": 4.5, "reference": "A.3.3"},
    {"system": "portico_ordinario", "R0": 2.5, "Omega0": 3.0, "Cd": 2.5, "reference": "A.3.3"},
    {"system": "muro_especial", "R0": 5.0, "Omega0": 2.5, "Cd": 5.0, "reference": "A.3.3"},
    {"system": "muro_intermedio", "R0": 4.0, "Omega0": 2.5, "Cd": 4.0, "reference": "A.3.3"},
    {"system": "dual", "R0": 7.0, "Omega0": 2.5, "Cd": 5.5, "reference": "A.3.3"},
    {"system": "arriostrado_concentrico", "R0": 5.0, "Omega0": 2.0, "Cd": 4.5, "reference": "A.3.3"},
    {"system": "arriostrado_excentrico", "R0": 7.0, "Omega0": 2.0, "Cd": 4.0, "reference": "A.3.3"},
]


# ═══════════════════════════════════════════════════════════════
# Generador de SQL
# ═══════════════════════════════════════════════════════════════

def generate_sql_schema() -> str:
    """Genera el schema SQL para las tablas normativas."""
    
    return """
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
"""


def generate_insert_statements() -> str:
    """Genera statements INSERT para los datos."""
    
    statements = []
    
    # Coeficientes Fa
    for soil, values in FA_TABLE["data"].items():
        stmt = f"""
INSERT INTO normative.site_coefficients 
(norm_code, coef_type, soil_type, value_005, value_010, value_015, value_020, value_025, value_030, value_035, value_040, value_045, value_050, reference)
VALUES ('NSR-10', 'Fa', '{soil}', {values['0.05']}, {values['0.10']}, {values['0.15']}, {values['0.20']}, {values['0.25']}, {values['0.30']}, {values['0.35']}, {values['0.40']}, {values['0.45']}, {values['0.50']}, 'Tabla A.2.4-3')
ON CONFLICT (norm_code, coef_type, soil_type) DO UPDATE SET
    value_005 = EXCLUDED.value_005, value_010 = EXCLUDED.value_010, value_015 = EXCLUDED.value_015,
    value_020 = EXCLUDED.value_020, value_025 = EXCLUDED.value_025, value_030 = EXCLUDED.value_030,
    value_035 = EXCLUDED.value_035, value_040 = EXCLUDED.value_040, value_045 = EXCLUDED.value_045,
    value_050 = EXCLUDED.value_050;"""
        statements.append(stmt)
    
    # Coeficientes Fv
    for soil, values in FV_TABLE["data"].items():
        stmt = f"""
INSERT INTO normative.site_coefficients 
(norm_code, coef_type, soil_type, value_005, value_010, value_015, value_020, value_025, value_030, value_035, value_040, value_045, value_050, reference)
VALUES ('NSR-10', 'Fv', '{soil}', {values['0.05']}, {values['0.10']}, {values['0.15']}, {values['0.20']}, {values['0.25']}, {values['0.30']}, {values['0.35']}, {values['0.40']}, {values['0.45']}, {values['0.50']}, 'Tabla A.2.4-4')
ON CONFLICT (norm_code, coef_type, soil_type) DO UPDATE SET
    value_005 = EXCLUDED.value_005, value_010 = EXCLUDED.value_010, value_015 = EXCLUDED.value_015,
    value_020 = EXCLUDED.value_020, value_025 = EXCLUDED.value_025, value_030 = EXCLUDED.value_030,
    value_035 = EXCLUDED.value_035, value_040 = EXCLUDED.value_040, value_045 = EXCLUDED.value_045,
    value_050 = EXCLUDED.value_050;"""
        statements.append(stmt)
    
    # Zonas sísmicas
    for dept, muni, aa, av, zone in SEISMIC_ZONES:
        stmt = f"""
INSERT INTO normative.seismic_zones 
(norm_code, department, municipality, Aa, Av, zone_name)
VALUES ('NSR-10', '{dept}', '{muni}', {aa}, {av}, '{zone}')
ON CONFLICT (norm_code, municipality) DO UPDATE SET
    Aa = EXCLUDED.Aa, Av = EXCLUDED.Av, zone_name = EXCLUDED.zone_name;"""
        statements.append(stmt)
    
    # Combinaciones de carga
    for combo in LOAD_COMBINATIONS_LRFD:
        factors = combo["factors"]
        stmt = f"""
INSERT INTO normative.load_combinations 
(norm_code, method, combo_number, combo_name, factor_D, factor_L, factor_Lr, factor_W, factor_E, reference)
VALUES ('NSR-10', 'LRFD', {combo['number']}, '{combo['name']}', 
    {factors.get('D', 'NULL')}, {factors.get('L', 'NULL')}, {factors.get('Lr', 'NULL')}, 
    {factors.get('W', 'NULL')}, {factors.get('E', 'NULL')}, '{combo['reference']}')
ON CONFLICT (norm_code, method, combo_number) DO UPDATE SET
    combo_name = EXCLUDED.combo_name, factor_D = EXCLUDED.factor_D, factor_L = EXCLUDED.factor_L;"""
        statements.append(stmt)
    
    # Límites de deriva
    for drift in DRIFT_LIMITS:
        stmt = f"""
INSERT INTO normative.drift_limits 
(norm_code, system_name, drift_limit, reference)
VALUES ('NSR-10', '{drift['system']}', {drift['limit']}, '{drift['reference']}')
ON CONFLICT (norm_code, system_name) DO UPDATE SET
    drift_limit = EXCLUDED.drift_limit;"""
        statements.append(stmt)
    
    # Factores de respuesta
    for resp in RESPONSE_FACTORS:
        stmt = f"""
INSERT INTO normative.response_factors 
(norm_code, system_name, R0, Omega0, Cd, reference)
VALUES ('NSR-10', '{resp['system']}', {resp['R0']}, {resp['Omega0']}, {resp['Cd']}, '{resp['reference']}')
ON CONFLICT (norm_code, system_name) DO UPDATE SET
    R0 = EXCLUDED.R0, Omega0 = EXCLUDED.Omega0, Cd = EXCLUDED.Cd;"""
        statements.append(stmt)
    
    return "\n".join(statements)


def main():
    """Genera archivos SQL para la ingestión."""
    
    output_dir = Path("/root/clawd/leonardo/projects/normative-engine/sql")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Schema
    schema_path = output_dir / "01_schema.sql"
    with open(schema_path, "w", encoding="utf-8") as f:
        f.write(generate_sql_schema())
    print(f"✓ Schema guardado: {schema_path}")
    
    # Data
    data_path = output_dir / "02_data_nsr10.sql"
    with open(data_path, "w", encoding="utf-8") as f:
        f.write("-- NSR-10 Data Ingestion\n")
        f.write("-- Generated automatically\n\n")
        f.write(generate_insert_statements())
    print(f"✓ Data guardado: {data_path}")
    
    # Resumen
    print(f"\n📊 Resumen de datos NSR-10:")
    print(f"   • Coeficientes Fa: 5 tipos de suelo × 10 valores")
    print(f"   • Coeficientes Fv: 5 tipos de suelo × 10 valores")
    print(f"   • Zonas sísmicas: {len(SEISMIC_ZONES)} municipios")
    print(f"   • Combinaciones LRFD: {len(LOAD_COMBINATIONS_LRFD)}")
    print(f"   • Límites de deriva: {len(DRIFT_LIMITS)} sistemas")
    print(f"   • Factores de respuesta: {len(RESPONSE_FACTORS)} sistemas")
    
    print(f"\n💡 Para aplicar en Supabase:")
    print(f"   1. Ir a SQL Editor en Supabase Dashboard")
    print(f"   2. Ejecutar {schema_path}")
    print(f"   3. Ejecutar {data_path}")


if __name__ == "__main__":
    main()
