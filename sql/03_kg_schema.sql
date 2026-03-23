-- ═══════════════════════════════════════════════════════════════
-- KNOWLEDGE GRAPH TABLES
-- Ejecutar en Supabase SQL Editor
-- ═══════════════════════════════════════════════════════════════

-- Habilitar pgvector si no está
CREATE EXTENSION IF NOT EXISTS vector;

-- Tabla de nodos
CREATE TABLE IF NOT EXISTS kg_nodes (
    id UUID PRIMARY KEY,
    
    -- Tipo y clasificación
    type VARCHAR(50) NOT NULL,  -- NORM, TITLE, CHAPTER, SECTION, TABLE, FORMULA, etc.
    norm_code VARCHAR(20) NOT NULL,  -- NSR-10, ASCE7-22, etc.
    
    -- Jerarquía
    section_path VARCHAR(100),  -- A.2.4.1, Tabla A.2.4-3
    hierarchy_depth INT DEFAULT 0,
    
    -- Contenido
    title TEXT,
    content TEXT,
    content_summary VARCHAR(1000),
    
    -- Para tablas
    table_headers JSONB,
    table_rows JSONB,
    table_sql_ref VARCHAR(100),
    
    -- Para fórmulas
    formula_latex TEXT,
    formula_python TEXT,
    formula_variables JSONB,
    
    -- Para requisitos
    requirement_condition VARCHAR(500),
    requirement_python_func VARCHAR(100),
    
    -- Metadata
    page_start INT,
    page_end INT,
    source_pdf VARCHAR(200),
    
    -- Embedding para búsqueda semántica
    embedding vector(1536),  -- OpenAI text-embedding-3-small
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    
    -- Índice único por normativa y sección
    UNIQUE(norm_code, section_path, type)
);

-- Tabla de aristas
CREATE TABLE IF NOT EXISTS kg_edges (
    id UUID PRIMARY KEY,
    
    source_id UUID NOT NULL REFERENCES kg_nodes(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES kg_nodes(id) ON DELETE CASCADE,
    
    edge_type VARCHAR(50) NOT NULL,  -- CONTAINS, REFERENCES, EQUIVALENT, etc.
    
    metadata JSONB,
    equivalence_score DECIMAL(3, 2),
    verified_by_expert BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ DEFAULT now(),
    
    UNIQUE(source_id, target_id, edge_type)
);

-- ═══════════════════════════════════════════════════════════════
-- ÍNDICES
-- ═══════════════════════════════════════════════════════════════

-- Búsqueda vectorial (HNSW)
CREATE INDEX IF NOT EXISTS idx_kg_nodes_embedding 
    ON kg_nodes USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Full-text search
CREATE INDEX IF NOT EXISTS idx_kg_nodes_content_fts 
    ON kg_nodes USING gin(to_tsvector('spanish', coalesce(title, '') || ' ' || coalesce(content, '')));

-- Búsquedas comunes
CREATE INDEX IF NOT EXISTS idx_kg_nodes_norm_type ON kg_nodes(norm_code, type);
CREATE INDEX IF NOT EXISTS idx_kg_nodes_section ON kg_nodes(norm_code, section_path);

-- Traversal de grafo
CREATE INDEX IF NOT EXISTS idx_kg_edges_source ON kg_edges(source_id, edge_type);
CREATE INDEX IF NOT EXISTS idx_kg_edges_target ON kg_edges(target_id, edge_type);

-- ═══════════════════════════════════════════════════════════════
-- FUNCIONES DE BÚSQUEDA
-- ═══════════════════════════════════════════════════════════════

-- Búsqueda semántica
CREATE OR REPLACE FUNCTION search_kg_semantic(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10,
    filter_norm_code text DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    type varchar,
    section_path varchar,
    title text,
    content text,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        kg_nodes.id,
        kg_nodes.type,
        kg_nodes.section_path,
        kg_nodes.title,
        kg_nodes.content,
        1 - (kg_nodes.embedding <=> query_embedding) AS similarity
    FROM kg_nodes
    WHERE 
        kg_nodes.embedding IS NOT NULL
        AND (filter_norm_code IS NULL OR kg_nodes.norm_code = filter_norm_code)
        AND 1 - (kg_nodes.embedding <=> query_embedding) > match_threshold
    ORDER BY kg_nodes.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Obtener nodos relacionados (1 hop)
CREATE OR REPLACE FUNCTION get_related_nodes(
    node_id uuid,
    edge_types text[] DEFAULT ARRAY['CONTAINS', 'REFERENCES']
)
RETURNS TABLE (
    id uuid,
    type varchar,
    section_path varchar,
    title text,
    edge_type varchar
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT
        n.id,
        n.type,
        n.section_path,
        n.title,
        e.edge_type
    FROM kg_edges e
    JOIN kg_nodes n ON n.id = e.target_id
    WHERE e.source_id = node_id
      AND e.edge_type = ANY(edge_types)
    
    UNION
    
    SELECT DISTINCT
        n.id,
        n.type,
        n.section_path,
        n.title,
        e.edge_type
    FROM kg_edges e
    JOIN kg_nodes n ON n.id = e.source_id
    WHERE e.target_id = node_id
      AND e.edge_type = ANY(edge_types);
END;
$$;
