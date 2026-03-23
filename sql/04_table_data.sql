-- ═══════════════════════════════════════════════════════════════
-- TABLAS RELACIONALES PARA DATOS NSR-10
-- Permite queries directos sobre coeficientes y parámetros
-- ═══════════════════════════════════════════════════════════════

-- Tabla de coeficientes Fa (Tabla A.2.4-3)
CREATE TABLE IF NOT EXISTS nsr10_coef_fa (
    id SERIAL PRIMARY KEY,
    soil_type CHAR(1) NOT NULL,  -- A, B, C, D, E, F
    aa_value DECIMAL(3,2) NOT NULL,  -- Valor de Aa
    fa DECIMAL(3,2),  -- Coeficiente Fa (NULL si requiere estudio especial)
    notes TEXT,
    UNIQUE(soil_type, aa_value)
);

-- Tabla de coeficientes Fv (Tabla A.2.4-4)
CREATE TABLE IF NOT EXISTS nsr10_coef_fv (
    id SERIAL PRIMARY KEY,
    soil_type CHAR(1) NOT NULL,
    av_value DECIMAL(3,2) NOT NULL,
    fv DECIMAL(3,2),
    notes TEXT,
    UNIQUE(soil_type, av_value)
);

-- Parámetros sísmicos por municipio (Apéndice A-4)
CREATE TABLE IF NOT EXISTS nsr10_municipios (
    id SERIAL PRIMARY KEY,
    departamento VARCHAR(100),
    municipio VARCHAR(100) NOT NULL,
    aa DECIMAL(3,2) NOT NULL,
    av DECIMAL(3,2) NOT NULL,
    zona_amenaza VARCHAR(20),  -- Alta, Intermedia, Baja
    UNIQUE(municipio, departamento)
);

-- Coeficiente de importancia (Tabla A.2.5-1)
CREATE TABLE IF NOT EXISTS nsr10_coef_importancia (
    id SERIAL PRIMARY KEY,
    grupo_uso VARCHAR(10) NOT NULL,  -- I, II, III, IV
    descripcion TEXT,
    coef_i DECIMAL(3,2) NOT NULL,
    UNIQUE(grupo_uso)
);

-- Límites de deriva (Tabla A.6.4-1)
CREATE TABLE IF NOT EXISTS nsr10_deriva_limites (
    id SERIAL PRIMARY KEY,
    sistema_estructural VARCHAR(200) NOT NULL,
    deriva_max_pct DECIMAL(4,3) NOT NULL,  -- Como porcentaje (ej: 1.0, 0.5)
    seccion_referencia VARCHAR(20),
    UNIQUE(sistema_estructural)
);

-- Coeficientes de disipación R (Tabla A.3-1 a A.3-7)
CREATE TABLE IF NOT EXISTS nsr10_coef_r (
    id SERIAL PRIMARY KEY,
    sistema VARCHAR(200) NOT NULL,
    material VARCHAR(50),  -- Concreto, Acero, Mampostería, etc.
    capacidad_disipacion VARCHAR(20),  -- DES, DMO, DMI
    r0 DECIMAL(3,1) NOT NULL,
    omega0 DECIMAL(3,1),
    cd DECIMAL(3,1),
    phi_a DECIMAL(3,2),
    phi_c DECIMAL(3,2),
    phi_p DECIMAL(3,2),
    restricciones TEXT,
    UNIQUE(sistema, capacidad_disipacion)
);

-- Combinaciones de carga (B.2.4.2)
CREATE TABLE IF NOT EXISTS nsr10_combinaciones (
    id SERIAL PRIMARY KEY,
    metodo VARCHAR(10) NOT NULL,  -- LRFD, ASD
    numero INT NOT NULL,
    formula TEXT NOT NULL,
    descripcion VARCHAR(100),
    UNIQUE(metodo, numero)
);

-- Coeficiente Cu para periodo (Tabla A.4.2-1)
CREATE TABLE IF NOT EXISTS nsr10_coef_cu (
    id SERIAL PRIMARY KEY,
    aa_threshold DECIMAL(3,2) NOT NULL,
    cu DECIMAL(3,2) NOT NULL,
    UNIQUE(aa_threshold)
);

-- Coeficientes Ct y α para periodo aproximado
CREATE TABLE IF NOT EXISTS nsr10_coef_periodo (
    id SERIAL PRIMARY KEY,
    sistema VARCHAR(200) NOT NULL,
    ct DECIMAL(5,4) NOT NULL,
    alpha DECIMAL(3,2) NOT NULL,
    UNIQUE(sistema)
);

-- ═══════════════════════════════════════════════════════════════
-- DATOS INICIALES
-- ═══════════════════════════════════════════════════════════════

-- Fa (Tabla A.2.4-3)
INSERT INTO nsr10_coef_fa (soil_type, aa_value, fa) VALUES
('A', 0.05, 0.8), ('A', 0.10, 0.8), ('A', 0.15, 0.8), ('A', 0.20, 0.8), ('A', 0.25, 0.8), ('A', 0.30, 0.8), ('A', 0.35, 0.8), ('A', 0.40, 0.8), ('A', 0.45, 0.8), ('A', 0.50, 0.8),
('B', 0.05, 1.0), ('B', 0.10, 1.0), ('B', 0.15, 1.0), ('B', 0.20, 1.0), ('B', 0.25, 1.0), ('B', 0.30, 1.0), ('B', 0.35, 1.0), ('B', 0.40, 1.0), ('B', 0.45, 1.0), ('B', 0.50, 1.0),
('C', 0.05, 1.2), ('C', 0.10, 1.2), ('C', 0.15, 1.1), ('C', 0.20, 1.0), ('C', 0.25, 1.0), ('C', 0.30, 1.0), ('C', 0.35, 1.0), ('C', 0.40, 1.0), ('C', 0.45, 1.0), ('C', 0.50, 1.0),
('D', 0.05, 1.6), ('D', 0.10, 1.4), ('D', 0.15, 1.2), ('D', 0.20, 1.1), ('D', 0.25, 1.0), ('D', 0.30, 1.0), ('D', 0.35, 1.0), ('D', 0.40, 1.0), ('D', 0.45, 1.0), ('D', 0.50, 1.0),
('E', 0.05, 2.5), ('E', 0.10, 1.7), ('E', 0.15, 1.2), ('E', 0.20, 0.9), ('E', 0.25, 0.9), ('E', 0.30, 0.9), ('E', 0.35, 0.9), ('E', 0.40, 0.9), ('E', 0.45, 0.9), ('E', 0.50, 0.9)
ON CONFLICT DO NOTHING;

-- Fv (Tabla A.2.4-4)
INSERT INTO nsr10_coef_fv (soil_type, av_value, fv) VALUES
('A', 0.05, 0.8), ('A', 0.10, 0.8), ('A', 0.15, 0.8), ('A', 0.20, 0.8), ('A', 0.25, 0.8), ('A', 0.30, 0.8), ('A', 0.35, 0.8), ('A', 0.40, 0.8), ('A', 0.45, 0.8), ('A', 0.50, 0.8),
('B', 0.05, 1.0), ('B', 0.10, 1.0), ('B', 0.15, 1.0), ('B', 0.20, 1.0), ('B', 0.25, 1.0), ('B', 0.30, 1.0), ('B', 0.35, 1.0), ('B', 0.40, 1.0), ('B', 0.45, 1.0), ('B', 0.50, 1.0),
('C', 0.05, 1.7), ('C', 0.10, 1.6), ('C', 0.15, 1.5), ('C', 0.20, 1.4), ('C', 0.25, 1.3), ('C', 0.30, 1.3), ('C', 0.35, 1.2), ('C', 0.40, 1.2), ('C', 0.45, 1.2), ('C', 0.50, 1.2),
('D', 0.05, 2.4), ('D', 0.10, 2.0), ('D', 0.15, 1.8), ('D', 0.20, 1.6), ('D', 0.25, 1.5), ('D', 0.30, 1.4), ('D', 0.35, 1.3), ('D', 0.40, 1.2), ('D', 0.45, 1.2), ('D', 0.50, 1.2),
('E', 0.05, 3.5), ('E', 0.10, 3.2), ('E', 0.15, 2.8), ('E', 0.20, 2.4), ('E', 0.25, 2.2), ('E', 0.30, 2.0), ('E', 0.35, 1.8), ('E', 0.40, 1.6), ('E', 0.45, 1.5), ('E', 0.50, 1.4)
ON CONFLICT DO NOTHING;

-- Coeficiente de importancia (Tabla A.2.5-1)
INSERT INTO nsr10_coef_importancia (grupo_uso, descripcion, coef_i) VALUES
('I', 'Estructuras de ocupación normal', 1.00),
('II', 'Estructuras de ocupación especial', 1.10),
('III', 'Estructuras de atención a la comunidad', 1.25),
('IV', 'Estructuras indispensables', 1.50)
ON CONFLICT DO NOTHING;

-- Límites de deriva (Tabla A.6.4-1)
INSERT INTO nsr10_deriva_limites (sistema_estructural, deriva_max_pct, seccion_referencia) VALUES
('Concreto reforzado, metálicas, madera, mampostería con A.6.4.2.2', 1.0, 'A.6.4.1'),
('Mampostería con requisitos A.6.4.2.3 (muros cortante)', 0.5, 'A.6.4.1.4')
ON CONFLICT DO NOTHING;

-- Combinaciones LRFD (B.2.4.2)
INSERT INTO nsr10_combinaciones (metodo, numero, formula, descripcion) VALUES
('LRFD', 1, '1.4D', 'Solo carga muerta'),
('LRFD', 2, '1.2D + 1.6L + 0.5(Lr o S o R)', 'Gravitacional principal'),
('LRFD', 3, '1.2D + 1.6(Lr o S o R) + (L o 0.5W)', 'Cubierta'),
('LRFD', 4, '1.2D + 1.0W + L + 0.5(Lr o S o R)', 'Viento'),
('LRFD', 5, '1.2D + 1.0E + L + 0.2S', 'Sismo'),
('LRFD', 6, '0.9D + 1.0W', 'Volcamiento viento'),
('LRFD', 7, '0.9D + 1.0E', 'Volcamiento sismo')
ON CONFLICT DO NOTHING;

-- Coeficiente Cu (Tabla A.4.2-1)
INSERT INTO nsr10_coef_cu (aa_threshold, cu) VALUES
(0.10, 1.75),
(0.15, 1.50),
(0.20, 1.40),
(0.25, 1.35),
(0.30, 1.30),
(0.35, 1.28),
(0.40, 1.25),
(0.45, 1.22),
(0.50, 1.20)
ON CONFLICT DO NOTHING;

-- Coeficientes para periodo aproximado (Tabla A.4.2-1)
INSERT INTO nsr10_coef_periodo (sistema, ct, alpha) VALUES
('Pórticos de concreto resistentes a momento', 0.047, 0.9),
('Pórticos de acero resistentes a momento', 0.072, 0.8),
('Pórticos de acero con arriostramientos excéntricos', 0.073, 0.75),
('Pórticos con arriostramientos concéntricos', 0.049, 0.75),
('Otros sistemas estructurales', 0.049, 0.75)
ON CONFLICT DO NOTHING;

-- ═══════════════════════════════════════════════════════════════
-- FUNCIONES DE CONSULTA
-- ═══════════════════════════════════════════════════════════════

-- Obtener Fa para suelo y Aa (con interpolación)
CREATE OR REPLACE FUNCTION get_fa(p_soil CHAR(1), p_aa DECIMAL)
RETURNS DECIMAL
LANGUAGE plpgsql
AS $$
DECLARE
    v_fa DECIMAL;
    v_aa_low DECIMAL;
    v_aa_high DECIMAL;
    v_fa_low DECIMAL;
    v_fa_high DECIMAL;
BEGIN
    -- Buscar valor exacto
    SELECT fa INTO v_fa FROM nsr10_coef_fa 
    WHERE soil_type = p_soil AND aa_value = p_aa;
    
    IF FOUND THEN RETURN v_fa; END IF;
    
    -- Interpolar
    SELECT aa_value, fa INTO v_aa_low, v_fa_low 
    FROM nsr10_coef_fa 
    WHERE soil_type = p_soil AND aa_value < p_aa 
    ORDER BY aa_value DESC LIMIT 1;
    
    SELECT aa_value, fa INTO v_aa_high, v_fa_high 
    FROM nsr10_coef_fa 
    WHERE soil_type = p_soil AND aa_value > p_aa 
    ORDER BY aa_value ASC LIMIT 1;
    
    IF v_aa_low IS NULL THEN RETURN v_fa_high; END IF;
    IF v_aa_high IS NULL THEN RETURN v_fa_low; END IF;
    
    -- Interpolación lineal
    RETURN v_fa_low + (v_fa_high - v_fa_low) * (p_aa - v_aa_low) / (v_aa_high - v_aa_low);
END;
$$;

-- Obtener Fv para suelo y Av
CREATE OR REPLACE FUNCTION get_fv(p_soil CHAR(1), p_av DECIMAL)
RETURNS DECIMAL
LANGUAGE plpgsql
AS $$
DECLARE
    v_fv DECIMAL;
    v_av_low DECIMAL;
    v_av_high DECIMAL;
    v_fv_low DECIMAL;
    v_fv_high DECIMAL;
BEGIN
    SELECT fv INTO v_fv FROM nsr10_coef_fv 
    WHERE soil_type = p_soil AND av_value = p_av;
    
    IF FOUND THEN RETURN v_fv; END IF;
    
    SELECT av_value, fv INTO v_av_low, v_fv_low 
    FROM nsr10_coef_fv 
    WHERE soil_type = p_soil AND av_value < p_av 
    ORDER BY av_value DESC LIMIT 1;
    
    SELECT av_value, fv INTO v_av_high, v_fv_high 
    FROM nsr10_coef_fv 
    WHERE soil_type = p_soil AND av_value > p_av 
    ORDER BY av_value ASC LIMIT 1;
    
    IF v_av_low IS NULL THEN RETURN v_fv_high; END IF;
    IF v_av_high IS NULL THEN RETURN v_fv_low; END IF;
    
    RETURN v_fv_low + (v_fv_high - v_fv_low) * (p_av - v_av_low) / (v_av_high - v_av_low);
END;
$$;

-- Obtener todos los parámetros sísmicos para un municipio
CREATE OR REPLACE FUNCTION get_parametros_sismicos(p_municipio TEXT, p_suelo CHAR(1) DEFAULT 'D')
RETURNS TABLE (
    municipio VARCHAR,
    aa DECIMAL,
    av DECIMAL,
    fa DECIMAL,
    fv DECIMAL,
    zona VARCHAR
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_aa DECIMAL;
    v_av DECIMAL;
BEGIN
    -- Buscar municipio
    SELECT m.aa, m.av, m.zona_amenaza INTO v_aa, v_av, zona
    FROM nsr10_municipios m
    WHERE LOWER(m.municipio) LIKE '%' || LOWER(p_municipio) || '%'
    LIMIT 1;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Municipio % no encontrado', p_municipio;
    END IF;
    
    municipio := p_municipio;
    aa := v_aa;
    av := v_av;
    fa := get_fa(p_suelo, v_aa);
    fv := get_fv(p_suelo, v_av);
    
    RETURN NEXT;
END;
$$;
