-- ═══════════════════════════════════════════════════════════════
-- AISC + ACI STRUCTURED TABLES — Fase 2
-- ═══════════════════════════════════════════════════════════════

-- ─── AISC secciones ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.aisc_secciones (
    id              SERIAL PRIMARY KEY,
    norm_code       VARCHAR(30)  NOT NULL DEFAULT 'AISC-360-16',
    chapter         VARCHAR(10),          -- 'B', 'C', 'D', ...
    section_id      VARCHAR(30)  NOT NULL, -- 'B4', 'B4.1', 'B4.1a'
    parent_id       VARCHAR(30),          -- FK lógico a section_id padre
    title           TEXT,
    body            TEXT,                 -- texto completo de la sección
    page_start      INT,
    page_end        INT,
    has_formula     BOOLEAN DEFAULT FALSE,
    has_table       BOOLEAN DEFAULT FALSE,
    level           SMALLINT DEFAULT 1,   -- 1=Chapter, 2=Section, 3=Subsection
    source_file     VARCHAR(200),
    created_at      TIMESTAMPTZ DEFAULT now(),
    tsv             TSVECTOR GENERATED ALWAYS AS (
                        to_tsvector('english', coalesce(title,'') || ' ' || coalesce(body,''))
                    ) STORED,
    UNIQUE(norm_code, section_id)
);

CREATE INDEX IF NOT EXISTS idx_aisc_secciones_tsv    ON public.aisc_secciones USING GIN(tsv);
CREATE INDEX IF NOT EXISTS idx_aisc_secciones_norm   ON public.aisc_secciones (norm_code);
CREATE INDEX IF NOT EXISTS idx_aisc_secciones_chap   ON public.aisc_secciones (chapter);
CREATE INDEX IF NOT EXISTS idx_aisc_secciones_parent ON public.aisc_secciones (parent_id);

-- ─── ACI secciones ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.aci_secciones (
    id              SERIAL PRIMARY KEY,
    norm_code       VARCHAR(30)  NOT NULL DEFAULT 'ACI-318-19',
    chapter         VARCHAR(10),          -- '1','2','22',...
    section_id      VARCHAR(30)  NOT NULL, -- '22.5', '22.5.1', '22.5.1.1'
    parent_id       VARCHAR(30),
    title           TEXT,
    body            TEXT,
    page_start      INT,
    page_end        INT,
    has_formula     BOOLEAN DEFAULT FALSE,
    has_table       BOOLEAN DEFAULT FALSE,
    level           SMALLINT DEFAULT 1,
    source_file     VARCHAR(200),
    created_at      TIMESTAMPTZ DEFAULT now(),
    tsv             TSVECTOR GENERATED ALWAYS AS (
                        to_tsvector('english', coalesce(title,'') || ' ' || coalesce(body,''))
                    ) STORED,
    UNIQUE(norm_code, section_id)
);

CREATE INDEX IF NOT EXISTS idx_aci_secciones_tsv    ON public.aci_secciones USING GIN(tsv);
CREATE INDEX IF NOT EXISTS idx_aci_secciones_norm   ON public.aci_secciones (norm_code);
CREATE INDEX IF NOT EXISTS idx_aci_secciones_chap   ON public.aci_secciones (chapter);
CREATE INDEX IF NOT EXISTS idx_aci_secciones_parent ON public.aci_secciones (parent_id);

-- ─── Fórmulas estructuradas ──────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.norm_formulas (
    id              SERIAL PRIMARY KEY,
    norm_code       VARCHAR(30)  NOT NULL,   -- 'AISC-360-16', 'ACI-318-19', 'NSR-10'
    section_id      VARCHAR(30),
    formula_id      VARCHAR(50),             -- 'Eq. B4-1', '(22-1)'
    description     TEXT,
    latex           TEXT,                    -- representación LaTeX
    python_code     TEXT,                    -- función Python ejecutable
    variables       JSONB,                   -- {"Mn": "momento nominal", "phi": "factor resistencia"}
    units           VARCHAR(50),             -- 'kN·m', 'MPa', 'kip-in'
    page            INT,
    source_file     VARCHAR(200),
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_norm_formulas_norm    ON public.norm_formulas (norm_code);
CREATE INDEX IF NOT EXISTS idx_norm_formulas_section ON public.norm_formulas (section_id);

-- ─── Cross-links entre normas ─────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.norm_crosslinks (
    id              SERIAL PRIMARY KEY,
    source_norm     VARCHAR(30) NOT NULL,    -- 'NSR-10'
    source_section  VARCHAR(50),
    target_norm     VARCHAR(30) NOT NULL,    -- 'AISC-360-16'
    target_section  VARCHAR(50),
    link_type       VARCHAR(30),             -- 'adopts', 'modifies', 'references', 'equivalent'
    note            TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_crosslinks_source ON public.norm_crosslinks (source_norm, source_section);
CREATE INDEX IF NOT EXISTS idx_crosslinks_target ON public.norm_crosslinks (target_norm, target_section);

-- ─── Tablas de propiedades estructuradas (acero / concreto) ──────────────────

CREATE TABLE IF NOT EXISTS public.norm_property_tables (
    id              SERIAL PRIMARY KEY,
    norm_code       VARCHAR(30) NOT NULL,
    table_id        VARCHAR(50),             -- 'Table B4.1b', 'Table 20.2.1.3.1'
    section_id      VARCHAR(30),
    title           TEXT,
    data            JSONB,                   -- datos de la tabla en JSON
    page            INT,
    source_file     VARCHAR(200),
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_prop_tables_norm ON public.norm_property_tables (norm_code);
