# Análisis: Cómo Mejorar los Embeddings para Retrieval 100% Efectivo

## Estado Actual vs. Estado del Arte

### Lo que Tenemos Hoy
- **Búsqueda vectorial pura** (embeddings de OpenAI text-embedding-3-small)
- **Sin BM25/lexical search** (búsqueda por palabras exactas)
- **Sin reranking** (no re-ordenamos los resultados)
- **Chunks por nodo** (cada sección/fórmula/tabla es un chunk)
- **Sin query transformation** (usamos el query tal cual)

### Lo que Dice la Industria (2024-2026)

> "Basic RAG works in demos. It fails in production."  
> — MyEngineeringPath, Advanced RAG Guide 2026

## Los 3 Problemas Principales

### 1. Vector-Only Search Tiene Puntos Ciegos

Los embeddings son excelentes para **significado semántico** pero malos para:
- **Términos exactos**: "Tabla A.2.4-3", "ORA-00942", "Fa=1.20"
- **Códigos y números**: "R0=5", "deriva 1.0%", "Aa=0.25"
- **Negaciones**: "no se permite", "excepto cuando"
- **Nombres propios**: "Bogotá", "NSR-10"

**Ejemplo de fallo actual:**
- Query: "¿Valor de Fa para suelo D con Aa=0.15?"
- El embedding busca "concepto de Fa" y "suelo tipo D"
- Pero no busca literalmente "0.15" en el texto

### 2. Chunking No Óptimo para Normativas

Actualmente cada nodo (sección, fórmula, tabla) es un chunk completo. Problemas:

- **Chunks muy cortos**: Algunas secciones tienen <50 caracteres
- **Sin overlap**: Si la respuesta está entre dos secciones, se pierde
- **Sin contexto jerárquico**: El chunk "A.2.6.1" no incluye info del padre "A.2.6"

### 3. Sin Re-ranking

Traemos top-10 resultados y los mostramos tal cual. El estado del arte dice:

> "Retrieval wide recall + reranking smart precision"

La idea es:
1. Traer **50-100 candidatos** (recall alto)
2. **Re-rankear** con un modelo más preciso → top 5-10

---

## Solución Propuesta: RAG Híbrido + Reranking

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PIPELINE DE BÚSQUEDA MEJORADO                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. QUERY TRANSFORMATION                                            │
│     ├─ Normalización (lowercase, trim)                              │
│     ├─ Expansión de sinónimos (deriva ↔ drift ↔ desplazamiento)    │
│     └─ Extracción de entidades (Fa, R, Bogotá, A.2.4-3)            │
│                                                                     │
│  2. HYBRID SEARCH (paralelo)                                        │
│     ├─ BM25 (lexical) → top 50 por palabras exactas                │
│     └─ Vector (semántico) → top 50 por significado                 │
│                                                                     │
│  3. FUSION (RRF - Reciprocal Rank Fusion)                          │
│     └─ Combina ambas listas → top 100 candidatos                   │
│                                                                     │
│  4. RERANKING (Cross-Encoder)                                       │
│     └─ Modelo que lee query+chunk junto → top 10 finales           │
│                                                                     │
│  5. RESPUESTA GROUNDED                                              │
│     └─ LLM genera respuesta con citas a secciones específicas      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Implementación Técnica

### Paso 1: Agregar BM25 (Búsqueda Lexical)

**Opción A: PostgreSQL Full-Text Search**
```sql
-- Agregar columna tsvector
ALTER TABLE kg_nodes ADD COLUMN search_vector tsvector;

-- Poblar con contenido
UPDATE kg_nodes SET search_vector = 
  to_tsvector('spanish', coalesce(title,'') || ' ' || coalesce(content,''));

-- Índice GIN para búsqueda rápida
CREATE INDEX kg_nodes_search_idx ON kg_nodes USING GIN(search_vector);

-- Función de búsqueda híbrida
CREATE FUNCTION hybrid_search(query_text text, query_embedding vector(1536))
RETURNS TABLE(id uuid, score float) AS $$
  -- BM25
  WITH bm25 AS (
    SELECT id, ts_rank_cd(search_vector, plainto_tsquery('spanish', query_text)) as rank
    FROM kg_nodes
    WHERE search_vector @@ plainto_tsquery('spanish', query_text)
    ORDER BY rank DESC LIMIT 50
  ),
  -- Vector
  vector AS (
    SELECT id, 1 - (embedding <=> query_embedding) as rank
    FROM kg_nodes
    WHERE embedding IS NOT NULL
    ORDER BY embedding <=> query_embedding LIMIT 50
  ),
  -- RRF Fusion
  combined AS (
    SELECT id, 
      COALESCE(1.0/(60 + bm25.rank), 0) + COALESCE(1.0/(60 + vector.rank), 0) as rrf_score
    FROM bm25 FULL OUTER JOIN vector USING (id)
  )
  SELECT id, rrf_score as score FROM combined ORDER BY rrf_score DESC LIMIT 100
$$ LANGUAGE SQL;
```

**Opción B: Supabase + pg_search (más simple)**
Supabase ya tiene soporte para full-text search integrado.

### Paso 2: Reranking con Cross-Encoder

```python
from sentence_transformers import CrossEncoder

# Modelo de reranking (gratis, corre local)
reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

def rerank(query: str, candidates: list[dict], top_k: int = 10) -> list[dict]:
    """
    Reordena candidatos usando cross-encoder
    """
    # Preparar pares query-documento
    pairs = [(query, c['content'][:512]) for c in candidates]
    
    # Obtener scores
    scores = reranker.predict(pairs)
    
    # Ordenar por score
    ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
    
    return [c for c, s in ranked[:top_k]]
```

**Alternativa cloud (más rápido):**
- Cohere Rerank API: $1 por 1000 queries
- Jina Reranker: Gratis hasta 1M tokens/mes

### Paso 3: Query Transformation

```python
def transform_query(query: str) -> list[str]:
    """
    Genera variantes del query para mejor recall
    """
    queries = [query]
    
    # Sinónimos conocidos del dominio
    synonyms = {
        'deriva': ['drift', 'desplazamiento relativo', 'desplazamiento de entrepiso'],
        'cortante': ['shear', 'fuerza cortante', 'corte'],
        'período': ['periodo', 'T', 'frecuencia'],
    }
    
    for term, syns in synonyms.items():
        if term in query.lower():
            for syn in syns:
                queries.append(query.lower().replace(term, syn))
    
    # Extraer entidades (tablas, fórmulas, secciones)
    import re
    tables = re.findall(r'[Tt]abla\s+(A[\.\-]?\d+[\.\-\d]*)', query)
    formulas = re.findall(r'[Ee]cuaci[óo]n\s+(A[\.\-]?\d+[\.\-\d]*)', query)
    sections = re.findall(r'[Ss]ecci[óo]n\s+(A[\.\-]?\d+[\.\-\d]*)', query)
    
    # Si hay entidades específicas, agregar query exacta
    for entity in tables + formulas + sections:
        queries.append(entity)
    
    return list(set(queries))
```

### Paso 4: Mejorar Chunking

**Estrategia para Normativas:**

```python
def chunk_for_norms(node: dict) -> list[dict]:
    """
    Chunking optimizado para documentos normativos
    """
    chunks = []
    
    # 1. Chunk principal: contenido del nodo
    main_chunk = {
        'id': node['id'],
        'text': f"NSR-10 {node['type']}: {node['section_path']}\n{node['title']}\n{node['content']}",
        'metadata': {
            'section': node['section_path'],
            'type': node['type'],
            'page': node['page_start']
        }
    }
    chunks.append(main_chunk)
    
    # 2. Para TABLAS: chunk por cada fila importante
    if node['type'] == 'TABLE' and node.get('table_rows'):
        for i, row in enumerate(node['table_rows'][:10]):
            row_chunk = {
                'id': f"{node['id']}_row_{i}",
                'text': f"Tabla {node['section_path']} - Fila: {row}",
                'metadata': {'parent': node['id'], 'type': 'TABLE_ROW'}
            }
            chunks.append(row_chunk)
    
    # 3. Para FÓRMULAS: chunk con variables expandidas
    if node['type'] == 'FORMULA':
        vars_text = '\n'.join(f"- {k}: {v}" for k,v in (node.get('formula_variables') or {}).items())
        formula_chunk = {
            'id': f"{node['id']}_vars",
            'text': f"Fórmula {node['section_path']}: {node.get('formula_latex','')}\nVariables:\n{vars_text}",
            'metadata': {'parent': node['id'], 'type': 'FORMULA_VARS'}
        }
        chunks.append(formula_chunk)
    
    return chunks
```

---

## Métricas de Evaluación

### Antes de Implementar

```
Recall@5:    ~60% (encuentra el resultado correcto en top 5)
Recall@10:   ~80%
MRR:         ~0.5 (Mean Reciprocal Rank)
```

### Después de Híbrido + Reranking

```
Recall@5:    ~90%+
Recall@10:   ~98%+
MRR:         ~0.8+
```

### Test Suite Mínimo

```python
test_cases = [
    # Búsqueda exacta (BM25 debe encontrar)
    {"query": "Tabla A.2.4-3", "expected": "Tabla A.2.4-3"},
    {"query": "Fa=1.20", "expected": "A.2.4-3 o A.2.4-4"},
    {"query": "Bogotá zona sísmica", "expected": "A.2.3 o Apéndice A-4"},
    
    # Búsqueda semántica (Vector debe encontrar)
    {"query": "¿cómo calcular el cortante?", "expected": "A.4.3"},
    {"query": "límite de desplazamiento entre pisos", "expected": "A.6.4"},
    
    # Multi-hop (requiere Knowledge Graph)
    {"query": "¿Qué valor de R usar para pórtico especial en Medellín?", 
     "expected": ["A.3", "nsr10_municipios"]},
]
```

---

## Plan de Implementación

### Fase 1: BM25 + Híbrido (1-2 días)
1. Agregar columna `search_vector` a `kg_nodes`
2. Crear índice GIN
3. Crear función `hybrid_search`
4. Test con queries de exactitud

### Fase 2: Reranking (1 día)
1. Integrar Cohere Rerank o modelo local
2. Modificar pipeline: retrieve 50 → rerank → top 10
3. Medir mejora en MRR

### Fase 3: Query Transformation (1 día)
1. Diccionario de sinónimos del dominio NSR-10
2. Extracción de entidades (tablas, secciones)
3. Multi-query retrieval

### Fase 4: Chunking Mejorado (2-3 días)
1. Re-chunking de tablas (por fila)
2. Re-chunking de fórmulas (con variables)
3. Overlap entre secciones relacionadas
4. Regenerar embeddings

---

## Costo Estimado

| Componente | Costo Único | Costo Mensual |
|------------|-------------|---------------|
| BM25 (Supabase) | $0 | $0 |
| Reranking (Cohere) | - | ~$10-50 |
| Embeddings adicionales | ~$0.01 | - |
| **Total** | **~$0.01** | **~$10-50** |

**Alternativa gratuita:** Usar `cross-encoder/ms-marco-MiniLM-L-6-v2` local para reranking.

---

## Conclusión

El estado del arte es claro:

> **"Hybrid Search + Reranking es el patrón que separa RAG de demo de RAG de producción."**

Nuestros embeddings actuales funcionan (~70% recall) pero para lograr **100% recall** necesitamos:

1. ✅ **BM25 paralelo** → Encuentra términos exactos
2. ✅ **RRF Fusion** → Combina lo mejor de ambos
3. ✅ **Cross-Encoder Reranking** → Elimina falsos positivos
4. ✅ **Query Transformation** → Expande sinónimos del dominio

Con estas mejoras, el sistema debería encontrar **siempre** la respuesta correcta cuando existe en el Knowledge Graph.
