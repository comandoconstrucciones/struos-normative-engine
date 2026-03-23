-- NSR-10 Data Ingestion
-- Generated automatically


INSERT INTO normative.site_coefficients 
(norm_code, coef_type, soil_type, value_005, value_010, value_015, value_020, value_025, value_030, value_035, value_040, value_045, value_050, reference)
VALUES ('NSR-10', 'Fa', 'A', 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 'Tabla A.2.4-3')
ON CONFLICT (norm_code, coef_type, soil_type) DO UPDATE SET
    value_005 = EXCLUDED.value_005, value_010 = EXCLUDED.value_010, value_015 = EXCLUDED.value_015,
    value_020 = EXCLUDED.value_020, value_025 = EXCLUDED.value_025, value_030 = EXCLUDED.value_030,
    value_035 = EXCLUDED.value_035, value_040 = EXCLUDED.value_040, value_045 = EXCLUDED.value_045,
    value_050 = EXCLUDED.value_050;

INSERT INTO normative.site_coefficients 
(norm_code, coef_type, soil_type, value_005, value_010, value_015, value_020, value_025, value_030, value_035, value_040, value_045, value_050, reference)
VALUES ('NSR-10', 'Fa', 'B', 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 'Tabla A.2.4-3')
ON CONFLICT (norm_code, coef_type, soil_type) DO UPDATE SET
    value_005 = EXCLUDED.value_005, value_010 = EXCLUDED.value_010, value_015 = EXCLUDED.value_015,
    value_020 = EXCLUDED.value_020, value_025 = EXCLUDED.value_025, value_030 = EXCLUDED.value_030,
    value_035 = EXCLUDED.value_035, value_040 = EXCLUDED.value_040, value_045 = EXCLUDED.value_045,
    value_050 = EXCLUDED.value_050;

INSERT INTO normative.site_coefficients 
(norm_code, coef_type, soil_type, value_005, value_010, value_015, value_020, value_025, value_030, value_035, value_040, value_045, value_050, reference)
VALUES ('NSR-10', 'Fa', 'C', 1.2, 1.2, 1.15, 1.1, 1.05, 1.0, 1.0, 1.0, 1.0, 1.0, 'Tabla A.2.4-3')
ON CONFLICT (norm_code, coef_type, soil_type) DO UPDATE SET
    value_005 = EXCLUDED.value_005, value_010 = EXCLUDED.value_010, value_015 = EXCLUDED.value_015,
    value_020 = EXCLUDED.value_020, value_025 = EXCLUDED.value_025, value_030 = EXCLUDED.value_030,
    value_035 = EXCLUDED.value_035, value_040 = EXCLUDED.value_040, value_045 = EXCLUDED.value_045,
    value_050 = EXCLUDED.value_050;

INSERT INTO normative.site_coefficients 
(norm_code, coef_type, soil_type, value_005, value_010, value_015, value_020, value_025, value_030, value_035, value_040, value_045, value_050, reference)
VALUES ('NSR-10', 'Fa', 'D', 1.6, 1.6, 1.5, 1.4, 1.3, 1.2, 1.15, 1.1, 1.05, 1.0, 'Tabla A.2.4-3')
ON CONFLICT (norm_code, coef_type, soil_type) DO UPDATE SET
    value_005 = EXCLUDED.value_005, value_010 = EXCLUDED.value_010, value_015 = EXCLUDED.value_015,
    value_020 = EXCLUDED.value_020, value_025 = EXCLUDED.value_025, value_030 = EXCLUDED.value_030,
    value_035 = EXCLUDED.value_035, value_040 = EXCLUDED.value_040, value_045 = EXCLUDED.value_045,
    value_050 = EXCLUDED.value_050;

INSERT INTO normative.site_coefficients 
(norm_code, coef_type, soil_type, value_005, value_010, value_015, value_020, value_025, value_030, value_035, value_040, value_045, value_050, reference)
VALUES ('NSR-10', 'Fa', 'E', 2.5, 2.5, 2.1, 1.7, 1.45, 1.2, 1.05, 0.9, 0.9, 0.9, 'Tabla A.2.4-3')
ON CONFLICT (norm_code, coef_type, soil_type) DO UPDATE SET
    value_005 = EXCLUDED.value_005, value_010 = EXCLUDED.value_010, value_015 = EXCLUDED.value_015,
    value_020 = EXCLUDED.value_020, value_025 = EXCLUDED.value_025, value_030 = EXCLUDED.value_030,
    value_035 = EXCLUDED.value_035, value_040 = EXCLUDED.value_040, value_045 = EXCLUDED.value_045,
    value_050 = EXCLUDED.value_050;

INSERT INTO normative.site_coefficients 
(norm_code, coef_type, soil_type, value_005, value_010, value_015, value_020, value_025, value_030, value_035, value_040, value_045, value_050, reference)
VALUES ('NSR-10', 'Fv', 'A', 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 'Tabla A.2.4-4')
ON CONFLICT (norm_code, coef_type, soil_type) DO UPDATE SET
    value_005 = EXCLUDED.value_005, value_010 = EXCLUDED.value_010, value_015 = EXCLUDED.value_015,
    value_020 = EXCLUDED.value_020, value_025 = EXCLUDED.value_025, value_030 = EXCLUDED.value_030,
    value_035 = EXCLUDED.value_035, value_040 = EXCLUDED.value_040, value_045 = EXCLUDED.value_045,
    value_050 = EXCLUDED.value_050;

INSERT INTO normative.site_coefficients 
(norm_code, coef_type, soil_type, value_005, value_010, value_015, value_020, value_025, value_030, value_035, value_040, value_045, value_050, reference)
VALUES ('NSR-10', 'Fv', 'B', 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 'Tabla A.2.4-4')
ON CONFLICT (norm_code, coef_type, soil_type) DO UPDATE SET
    value_005 = EXCLUDED.value_005, value_010 = EXCLUDED.value_010, value_015 = EXCLUDED.value_015,
    value_020 = EXCLUDED.value_020, value_025 = EXCLUDED.value_025, value_030 = EXCLUDED.value_030,
    value_035 = EXCLUDED.value_035, value_040 = EXCLUDED.value_040, value_045 = EXCLUDED.value_045,
    value_050 = EXCLUDED.value_050;

INSERT INTO normative.site_coefficients 
(norm_code, coef_type, soil_type, value_005, value_010, value_015, value_020, value_025, value_030, value_035, value_040, value_045, value_050, reference)
VALUES ('NSR-10', 'Fv', 'C', 1.7, 1.7, 1.65, 1.6, 1.55, 1.5, 1.45, 1.4, 1.35, 1.3, 'Tabla A.2.4-4')
ON CONFLICT (norm_code, coef_type, soil_type) DO UPDATE SET
    value_005 = EXCLUDED.value_005, value_010 = EXCLUDED.value_010, value_015 = EXCLUDED.value_015,
    value_020 = EXCLUDED.value_020, value_025 = EXCLUDED.value_025, value_030 = EXCLUDED.value_030,
    value_035 = EXCLUDED.value_035, value_040 = EXCLUDED.value_040, value_045 = EXCLUDED.value_045,
    value_050 = EXCLUDED.value_050;

INSERT INTO normative.site_coefficients 
(norm_code, coef_type, soil_type, value_005, value_010, value_015, value_020, value_025, value_030, value_035, value_040, value_045, value_050, reference)
VALUES ('NSR-10', 'Fv', 'D', 2.4, 2.4, 2.2, 2.0, 1.9, 1.8, 1.7, 1.6, 1.55, 1.5, 'Tabla A.2.4-4')
ON CONFLICT (norm_code, coef_type, soil_type) DO UPDATE SET
    value_005 = EXCLUDED.value_005, value_010 = EXCLUDED.value_010, value_015 = EXCLUDED.value_015,
    value_020 = EXCLUDED.value_020, value_025 = EXCLUDED.value_025, value_030 = EXCLUDED.value_030,
    value_035 = EXCLUDED.value_035, value_040 = EXCLUDED.value_040, value_045 = EXCLUDED.value_045,
    value_050 = EXCLUDED.value_050;

INSERT INTO normative.site_coefficients 
(norm_code, coef_type, soil_type, value_005, value_010, value_015, value_020, value_025, value_030, value_035, value_040, value_045, value_050, reference)
VALUES ('NSR-10', 'Fv', 'E', 3.5, 3.5, 3.35, 3.2, 3.0, 2.8, 2.6, 2.4, 2.4, 2.4, 'Tabla A.2.4-4')
ON CONFLICT (norm_code, coef_type, soil_type) DO UPDATE SET
    value_005 = EXCLUDED.value_005, value_010 = EXCLUDED.value_010, value_015 = EXCLUDED.value_015,
    value_020 = EXCLUDED.value_020, value_025 = EXCLUDED.value_025, value_030 = EXCLUDED.value_030,
    value_035 = EXCLUDED.value_035, value_040 = EXCLUDED.value_040, value_045 = EXCLUDED.value_045,
    value_050 = EXCLUDED.value_050;

INSERT INTO normative.seismic_zones 
(norm_code, department, municipality, Aa, Av, zone_name)
VALUES ('NSR-10', 'Cundinamarca', 'Bogotá D.C.', 0.15, 0.2, 'Intermedia')
ON CONFLICT (norm_code, municipality) DO UPDATE SET
    Aa = EXCLUDED.Aa, Av = EXCLUDED.Av, zone_name = EXCLUDED.zone_name;

INSERT INTO normative.seismic_zones 
(norm_code, department, municipality, Aa, Av, zone_name)
VALUES ('NSR-10', 'Antioquia', 'Medellín', 0.15, 0.2, 'Intermedia')
ON CONFLICT (norm_code, municipality) DO UPDATE SET
    Aa = EXCLUDED.Aa, Av = EXCLUDED.Av, zone_name = EXCLUDED.zone_name;

INSERT INTO normative.seismic_zones 
(norm_code, department, municipality, Aa, Av, zone_name)
VALUES ('NSR-10', 'Valle del Cauca', 'Cali', 0.25, 0.25, 'Alta')
ON CONFLICT (norm_code, municipality) DO UPDATE SET
    Aa = EXCLUDED.Aa, Av = EXCLUDED.Av, zone_name = EXCLUDED.zone_name;

INSERT INTO normative.seismic_zones 
(norm_code, department, municipality, Aa, Av, zone_name)
VALUES ('NSR-10', 'Atlántico', 'Barranquilla', 0.1, 0.1, 'Baja')
ON CONFLICT (norm_code, municipality) DO UPDATE SET
    Aa = EXCLUDED.Aa, Av = EXCLUDED.Av, zone_name = EXCLUDED.zone_name;

INSERT INTO normative.seismic_zones 
(norm_code, department, municipality, Aa, Av, zone_name)
VALUES ('NSR-10', 'Bolívar', 'Cartagena', 0.1, 0.1, 'Baja')
ON CONFLICT (norm_code, municipality) DO UPDATE SET
    Aa = EXCLUDED.Aa, Av = EXCLUDED.Av, zone_name = EXCLUDED.zone_name;

INSERT INTO normative.seismic_zones 
(norm_code, department, municipality, Aa, Av, zone_name)
VALUES ('NSR-10', 'Santander', 'Bucaramanga', 0.25, 0.25, 'Alta')
ON CONFLICT (norm_code, municipality) DO UPDATE SET
    Aa = EXCLUDED.Aa, Av = EXCLUDED.Av, zone_name = EXCLUDED.zone_name;

INSERT INTO normative.seismic_zones 
(norm_code, department, municipality, Aa, Av, zone_name)
VALUES ('NSR-10', 'Norte de Santander', 'Cúcuta', 0.3, 0.3, 'Alta')
ON CONFLICT (norm_code, municipality) DO UPDATE SET
    Aa = EXCLUDED.Aa, Av = EXCLUDED.Av, zone_name = EXCLUDED.zone_name;

INSERT INTO normative.seismic_zones 
(norm_code, department, municipality, Aa, Av, zone_name)
VALUES ('NSR-10', 'Risaralda', 'Pereira', 0.25, 0.25, 'Alta')
ON CONFLICT (norm_code, municipality) DO UPDATE SET
    Aa = EXCLUDED.Aa, Av = EXCLUDED.Av, zone_name = EXCLUDED.zone_name;

INSERT INTO normative.seismic_zones 
(norm_code, department, municipality, Aa, Av, zone_name)
VALUES ('NSR-10', 'Caldas', 'Manizales', 0.25, 0.25, 'Alta')
ON CONFLICT (norm_code, municipality) DO UPDATE SET
    Aa = EXCLUDED.Aa, Av = EXCLUDED.Av, zone_name = EXCLUDED.zone_name;

INSERT INTO normative.seismic_zones 
(norm_code, department, municipality, Aa, Av, zone_name)
VALUES ('NSR-10', 'Quindío', 'Armenia', 0.25, 0.3, 'Alta')
ON CONFLICT (norm_code, municipality) DO UPDATE SET
    Aa = EXCLUDED.Aa, Av = EXCLUDED.Av, zone_name = EXCLUDED.zone_name;

INSERT INTO normative.seismic_zones 
(norm_code, department, municipality, Aa, Av, zone_name)
VALUES ('NSR-10', 'Tolima', 'Ibagué', 0.2, 0.2, 'Intermedia')
ON CONFLICT (norm_code, municipality) DO UPDATE SET
    Aa = EXCLUDED.Aa, Av = EXCLUDED.Av, zone_name = EXCLUDED.zone_name;

INSERT INTO normative.seismic_zones 
(norm_code, department, municipality, Aa, Av, zone_name)
VALUES ('NSR-10', 'Huila', 'Neiva', 0.25, 0.25, 'Alta')
ON CONFLICT (norm_code, municipality) DO UPDATE SET
    Aa = EXCLUDED.Aa, Av = EXCLUDED.Av, zone_name = EXCLUDED.zone_name;

INSERT INTO normative.seismic_zones 
(norm_code, department, municipality, Aa, Av, zone_name)
VALUES ('NSR-10', 'Nariño', 'Pasto', 0.3, 0.35, 'Alta')
ON CONFLICT (norm_code, municipality) DO UPDATE SET
    Aa = EXCLUDED.Aa, Av = EXCLUDED.Av, zone_name = EXCLUDED.zone_name;

INSERT INTO normative.seismic_zones 
(norm_code, department, municipality, Aa, Av, zone_name)
VALUES ('NSR-10', 'Cauca', 'Popayán', 0.25, 0.3, 'Alta')
ON CONFLICT (norm_code, municipality) DO UPDATE SET
    Aa = EXCLUDED.Aa, Av = EXCLUDED.Av, zone_name = EXCLUDED.zone_name;

INSERT INTO normative.seismic_zones 
(norm_code, department, municipality, Aa, Av, zone_name)
VALUES ('NSR-10', 'Boyacá', 'Tunja', 0.15, 0.15, 'Intermedia')
ON CONFLICT (norm_code, municipality) DO UPDATE SET
    Aa = EXCLUDED.Aa, Av = EXCLUDED.Av, zone_name = EXCLUDED.zone_name;

INSERT INTO normative.seismic_zones 
(norm_code, department, municipality, Aa, Av, zone_name)
VALUES ('NSR-10', 'Meta', 'Villavicencio', 0.2, 0.2, 'Intermedia')
ON CONFLICT (norm_code, municipality) DO UPDATE SET
    Aa = EXCLUDED.Aa, Av = EXCLUDED.Av, zone_name = EXCLUDED.zone_name;

INSERT INTO normative.seismic_zones 
(norm_code, department, municipality, Aa, Av, zone_name)
VALUES ('NSR-10', 'Córdoba', 'Montería', 0.1, 0.1, 'Baja')
ON CONFLICT (norm_code, municipality) DO UPDATE SET
    Aa = EXCLUDED.Aa, Av = EXCLUDED.Av, zone_name = EXCLUDED.zone_name;

INSERT INTO normative.seismic_zones 
(norm_code, department, municipality, Aa, Av, zone_name)
VALUES ('NSR-10', 'Sucre', 'Sincelejo', 0.1, 0.1, 'Baja')
ON CONFLICT (norm_code, municipality) DO UPDATE SET
    Aa = EXCLUDED.Aa, Av = EXCLUDED.Av, zone_name = EXCLUDED.zone_name;

INSERT INTO normative.seismic_zones 
(norm_code, department, municipality, Aa, Av, zone_name)
VALUES ('NSR-10', 'Magdalena', 'Santa Marta', 0.1, 0.15, 'Intermedia')
ON CONFLICT (norm_code, municipality) DO UPDATE SET
    Aa = EXCLUDED.Aa, Av = EXCLUDED.Av, zone_name = EXCLUDED.zone_name;

INSERT INTO normative.seismic_zones 
(norm_code, department, municipality, Aa, Av, zone_name)
VALUES ('NSR-10', 'Cesar', 'Valledupar', 0.1, 0.1, 'Baja')
ON CONFLICT (norm_code, municipality) DO UPDATE SET
    Aa = EXCLUDED.Aa, Av = EXCLUDED.Av, zone_name = EXCLUDED.zone_name;

INSERT INTO normative.load_combinations 
(norm_code, method, combo_number, combo_name, factor_D, factor_L, factor_Lr, factor_W, factor_E, reference)
VALUES ('NSR-10', 'LRFD', 1, '1.4D', 
    1.4, NULL, NULL, 
    NULL, NULL, 'B.2.4-1')
ON CONFLICT (norm_code, method, combo_number) DO UPDATE SET
    combo_name = EXCLUDED.combo_name, factor_D = EXCLUDED.factor_D, factor_L = EXCLUDED.factor_L;

INSERT INTO normative.load_combinations 
(norm_code, method, combo_number, combo_name, factor_D, factor_L, factor_Lr, factor_W, factor_E, reference)
VALUES ('NSR-10', 'LRFD', 2, '1.2D + 1.6L + 0.5(Lr o S)', 
    1.2, 1.6, 0.5, 
    NULL, NULL, 'B.2.4-2')
ON CONFLICT (norm_code, method, combo_number) DO UPDATE SET
    combo_name = EXCLUDED.combo_name, factor_D = EXCLUDED.factor_D, factor_L = EXCLUDED.factor_L;

INSERT INTO normative.load_combinations 
(norm_code, method, combo_number, combo_name, factor_D, factor_L, factor_Lr, factor_W, factor_E, reference)
VALUES ('NSR-10', 'LRFD', 3, '1.2D + 1.6(Lr o S) + (L o 0.5W)', 
    1.2, 1.0, 1.6, 
    NULL, NULL, 'B.2.4-3')
ON CONFLICT (norm_code, method, combo_number) DO UPDATE SET
    combo_name = EXCLUDED.combo_name, factor_D = EXCLUDED.factor_D, factor_L = EXCLUDED.factor_L;

INSERT INTO normative.load_combinations 
(norm_code, method, combo_number, combo_name, factor_D, factor_L, factor_Lr, factor_W, factor_E, reference)
VALUES ('NSR-10', 'LRFD', 4, '1.2D + 1.0W + L + 0.5(Lr o S)', 
    1.2, 1.0, 0.5, 
    1.0, NULL, 'B.2.4-4')
ON CONFLICT (norm_code, method, combo_number) DO UPDATE SET
    combo_name = EXCLUDED.combo_name, factor_D = EXCLUDED.factor_D, factor_L = EXCLUDED.factor_L;

INSERT INTO normative.load_combinations 
(norm_code, method, combo_number, combo_name, factor_D, factor_L, factor_Lr, factor_W, factor_E, reference)
VALUES ('NSR-10', 'LRFD', 5, '1.2D + 1.0E + L', 
    1.2, 1.0, NULL, 
    NULL, 1.0, 'B.2.4-5')
ON CONFLICT (norm_code, method, combo_number) DO UPDATE SET
    combo_name = EXCLUDED.combo_name, factor_D = EXCLUDED.factor_D, factor_L = EXCLUDED.factor_L;

INSERT INTO normative.load_combinations 
(norm_code, method, combo_number, combo_name, factor_D, factor_L, factor_Lr, factor_W, factor_E, reference)
VALUES ('NSR-10', 'LRFD', 6, '0.9D + 1.0W', 
    0.9, NULL, NULL, 
    1.0, NULL, 'B.2.4-6')
ON CONFLICT (norm_code, method, combo_number) DO UPDATE SET
    combo_name = EXCLUDED.combo_name, factor_D = EXCLUDED.factor_D, factor_L = EXCLUDED.factor_L;

INSERT INTO normative.load_combinations 
(norm_code, method, combo_number, combo_name, factor_D, factor_L, factor_Lr, factor_W, factor_E, reference)
VALUES ('NSR-10', 'LRFD', 7, '0.9D + 1.0E', 
    0.9, NULL, NULL, 
    NULL, 1.0, 'B.2.4-7')
ON CONFLICT (norm_code, method, combo_number) DO UPDATE SET
    combo_name = EXCLUDED.combo_name, factor_D = EXCLUDED.factor_D, factor_L = EXCLUDED.factor_L;

INSERT INTO normative.drift_limits 
(norm_code, system_name, drift_limit, reference)
VALUES ('NSR-10', 'portico_especial', 0.01, 'A.6.4.1')
ON CONFLICT (norm_code, system_name) DO UPDATE SET
    drift_limit = EXCLUDED.drift_limit;

INSERT INTO normative.drift_limits 
(norm_code, system_name, drift_limit, reference)
VALUES ('NSR-10', 'portico_intermedio', 0.01, 'A.6.4.1')
ON CONFLICT (norm_code, system_name) DO UPDATE SET
    drift_limit = EXCLUDED.drift_limit;

INSERT INTO normative.drift_limits 
(norm_code, system_name, drift_limit, reference)
VALUES ('NSR-10', 'portico_ordinario', 0.01, 'A.6.4.1')
ON CONFLICT (norm_code, system_name) DO UPDATE SET
    drift_limit = EXCLUDED.drift_limit;

INSERT INTO normative.drift_limits 
(norm_code, system_name, drift_limit, reference)
VALUES ('NSR-10', 'muro_especial', 0.01, 'A.6.4.1')
ON CONFLICT (norm_code, system_name) DO UPDATE SET
    drift_limit = EXCLUDED.drift_limit;

INSERT INTO normative.drift_limits 
(norm_code, system_name, drift_limit, reference)
VALUES ('NSR-10', 'muro_intermedio', 0.01, 'A.6.4.1')
ON CONFLICT (norm_code, system_name) DO UPDATE SET
    drift_limit = EXCLUDED.drift_limit;

INSERT INTO normative.drift_limits 
(norm_code, system_name, drift_limit, reference)
VALUES ('NSR-10', 'dual', 0.01, 'A.6.4.1')
ON CONFLICT (norm_code, system_name) DO UPDATE SET
    drift_limit = EXCLUDED.drift_limit;

INSERT INTO normative.drift_limits 
(norm_code, system_name, drift_limit, reference)
VALUES ('NSR-10', 'mamposteria_confinada', 0.005, 'A.6.4.1')
ON CONFLICT (norm_code, system_name) DO UPDATE SET
    drift_limit = EXCLUDED.drift_limit;

INSERT INTO normative.drift_limits 
(norm_code, system_name, drift_limit, reference)
VALUES ('NSR-10', 'mamposteria_reforzada', 0.005, 'A.6.4.1')
ON CONFLICT (norm_code, system_name) DO UPDATE SET
    drift_limit = EXCLUDED.drift_limit;

INSERT INTO normative.response_factors 
(norm_code, system_name, R0, Omega0, Cd, reference)
VALUES ('NSR-10', 'portico_especial', 7.0, 3.0, 5.5, 'A.3.3')
ON CONFLICT (norm_code, system_name) DO UPDATE SET
    R0 = EXCLUDED.R0, Omega0 = EXCLUDED.Omega0, Cd = EXCLUDED.Cd;

INSERT INTO normative.response_factors 
(norm_code, system_name, R0, Omega0, Cd, reference)
VALUES ('NSR-10', 'portico_intermedio', 5.0, 3.0, 4.5, 'A.3.3')
ON CONFLICT (norm_code, system_name) DO UPDATE SET
    R0 = EXCLUDED.R0, Omega0 = EXCLUDED.Omega0, Cd = EXCLUDED.Cd;

INSERT INTO normative.response_factors 
(norm_code, system_name, R0, Omega0, Cd, reference)
VALUES ('NSR-10', 'portico_ordinario', 2.5, 3.0, 2.5, 'A.3.3')
ON CONFLICT (norm_code, system_name) DO UPDATE SET
    R0 = EXCLUDED.R0, Omega0 = EXCLUDED.Omega0, Cd = EXCLUDED.Cd;

INSERT INTO normative.response_factors 
(norm_code, system_name, R0, Omega0, Cd, reference)
VALUES ('NSR-10', 'muro_especial', 5.0, 2.5, 5.0, 'A.3.3')
ON CONFLICT (norm_code, system_name) DO UPDATE SET
    R0 = EXCLUDED.R0, Omega0 = EXCLUDED.Omega0, Cd = EXCLUDED.Cd;

INSERT INTO normative.response_factors 
(norm_code, system_name, R0, Omega0, Cd, reference)
VALUES ('NSR-10', 'muro_intermedio', 4.0, 2.5, 4.0, 'A.3.3')
ON CONFLICT (norm_code, system_name) DO UPDATE SET
    R0 = EXCLUDED.R0, Omega0 = EXCLUDED.Omega0, Cd = EXCLUDED.Cd;

INSERT INTO normative.response_factors 
(norm_code, system_name, R0, Omega0, Cd, reference)
VALUES ('NSR-10', 'dual', 7.0, 2.5, 5.5, 'A.3.3')
ON CONFLICT (norm_code, system_name) DO UPDATE SET
    R0 = EXCLUDED.R0, Omega0 = EXCLUDED.Omega0, Cd = EXCLUDED.Cd;

INSERT INTO normative.response_factors 
(norm_code, system_name, R0, Omega0, Cd, reference)
VALUES ('NSR-10', 'arriostrado_concentrico', 5.0, 2.0, 4.5, 'A.3.3')
ON CONFLICT (norm_code, system_name) DO UPDATE SET
    R0 = EXCLUDED.R0, Omega0 = EXCLUDED.Omega0, Cd = EXCLUDED.Cd;

INSERT INTO normative.response_factors 
(norm_code, system_name, R0, Omega0, Cd, reference)
VALUES ('NSR-10', 'arriostrado_excentrico', 7.0, 2.0, 4.0, 'A.3.3')
ON CONFLICT (norm_code, system_name) DO UPDATE SET
    R0 = EXCLUDED.R0, Omega0 = EXCLUDED.Omega0, Cd = EXCLUDED.Cd;