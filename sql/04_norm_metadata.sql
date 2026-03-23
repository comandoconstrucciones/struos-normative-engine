-- ============================================
-- TABLA DE METADATOS DE NORMAS
-- ============================================
-- Almacena información completa sobre cada norma:
-- versión, fecha, autor, vigencia, etc.
-- ============================================

CREATE TABLE IF NOT EXISTS norm_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    norm_code VARCHAR(50) UNIQUE NOT NULL,
    
    -- Información básica
    full_title TEXT NOT NULL,
    short_title VARCHAR(255),
    version VARCHAR(50),
    edition VARCHAR(50),
    
    -- Fechas
    publication_date DATE,
    effective_date DATE,
    last_update_date DATE,
    expiration_date DATE,
    
    -- Autoridad
    issuer VARCHAR(255),
    issuing_body VARCHAR(255),
    country VARCHAR(100),
    language VARCHAR(10) DEFAULT 'es',
    
    -- Estado
    status VARCHAR(50) DEFAULT 'vigente',  -- vigente, derogada, en_revision
    supersedes TEXT[],  -- normas anteriores que reemplaza
    superseded_by VARCHAR(255),  -- norma que la reemplaza (si aplica)
    
    -- Legal
    legal_basis TEXT,  -- leyes/decretos que la respaldan
    decree_numbers TEXT[],
    
    -- Alcance
    scope TEXT,
    applicability TEXT,
    
    -- Estructura
    titles JSONB,  -- {code: title, pages: X, chapters: Y, status: completo/parcial}
    total_pages INTEGER,
    
    -- Extracción
    extraction_date TIMESTAMP DEFAULT NOW(),
    extraction_version VARCHAR(20),
    extraction_status VARCHAR(50),  -- parcial, completo
    extraction_notes TEXT,
    
    -- Referencias
    references_norms TEXT[],  -- normas que referencia
    referenced_by TEXT[],  -- normas que la referencian
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_norm_metadata_code ON norm_metadata(norm_code);
CREATE INDEX IF NOT EXISTS idx_norm_metadata_status ON norm_metadata(status);
CREATE INDEX IF NOT EXISTS idx_norm_metadata_country ON norm_metadata(country);

-- Insertar NSR-10
INSERT INTO norm_metadata (
    norm_code,
    full_title,
    short_title,
    version,
    edition,
    publication_date,
    effective_date,
    last_update_date,
    issuer,
    issuing_body,
    country,
    language,
    status,
    supersedes,
    legal_basis,
    decree_numbers,
    scope,
    applicability,
    titles,
    total_pages,
    extraction_date,
    extraction_version,
    extraction_status,
    extraction_notes,
    references_norms
) VALUES (
    'NSR-10',
    'Reglamento Colombiano de Construcción Sismo Resistente',
    'NSR-10',
    '2010 (Actualización 2017)',
    'Primera edición, séptima actualización',
    '2010-03-19',
    '2010-12-15',
    '2017-12-13',
    'Ministerio de Ambiente, Vivienda y Desarrollo Territorial',
    'Comisión Asesora Permanente para el Régimen de Construcciones Sismo Resistentes',
    'Colombia',
    'es',
    'vigente',
    ARRAY['NSR-98', 'Decreto 33 de 1998'],
    'Ley 400 de 1997 - Por la cual se adoptan normas sobre construcciones sismo resistentes',
    ARRAY['Decreto 926 de 2010', 'Decreto 2525 de 2010', 'Decreto 092 de 2011', 'Decreto 340 de 2012', 'Decreto 945 de 2017', 'Decreto 2113 de 2017'],
    'Requisitos mínimos de diseño y construcción sismo resistente para edificaciones en Colombia',
    'Todas las construcciones nuevas y reparaciones/refuerzos de edificaciones existentes en territorio colombiano',
    '[
        {"code": "A", "title": "Requisitos generales de diseño y construcción sismo resistente", "pages": 186, "chapters": 13, "status": "completo"},
        {"code": "B", "title": "Cargas", "pages": 120, "chapters": 6, "status": "pendiente"},
        {"code": "C", "title": "Concreto estructural", "pages": 550, "chapters": 25, "status": "pendiente"},
        {"code": "D", "title": "Mampostería estructural", "pages": 180, "chapters": 10, "status": "pendiente"},
        {"code": "E", "title": "Casas de uno y dos pisos", "pages": 120, "chapters": 8, "status": "pendiente"},
        {"code": "F", "title": "Estructuras metálicas", "pages": 320, "chapters": 12, "status": "pendiente"},
        {"code": "G", "title": "Estructuras de madera y guadua", "pages": 180, "chapters": 10, "status": "pendiente"},
        {"code": "H", "title": "Estudios geotécnicos", "pages": 100, "chapters": 5, "status": "pendiente"},
        {"code": "I", "title": "Supervisión técnica", "pages": 40, "chapters": 3, "status": "pendiente"},
        {"code": "J", "title": "Requisitos de protección contra incendio", "pages": 140, "chapters": 6, "status": "pendiente"},
        {"code": "K", "title": "Requisitos complementarios", "pages": 60, "chapters": 4, "status": "pendiente"}
    ]'::jsonb,
    1996,
    '2026-03-21',
    '1.0',
    'parcial',
    'Título A completamente extraído. Títulos B-K pendientes.',
    ARRAY['ACI 318', 'AISC 360', 'ASCE 7', 'NTC colombianas', 'AWS D1.1', 'ASTM']
) ON CONFLICT (norm_code) DO UPDATE SET
    last_update_date = EXCLUDED.last_update_date,
    extraction_date = EXCLUDED.extraction_date,
    extraction_status = EXCLUDED.extraction_status,
    extraction_notes = EXCLUDED.extraction_notes,
    updated_at = NOW();

-- Vista para consultar estado de extracción
CREATE OR REPLACE VIEW norm_extraction_status AS
SELECT 
    norm_code,
    short_title,
    status as norm_status,
    extraction_status,
    extraction_date,
    total_pages,
    jsonb_array_length(titles) as total_titles,
    (SELECT COUNT(*) FROM jsonb_array_elements(titles) t WHERE t->>'status' = 'completo') as completed_titles,
    last_update_date
FROM norm_metadata;
