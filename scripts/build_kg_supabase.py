#!/usr/bin/env python3
"""
Construye el Knowledge Graph desde las extracciones y lo carga a Supabase.
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime
from uuid import uuid4
from typing import List, Dict, Optional
import re

from supabase import create_client, Client
import openai

# Configuración
EXTRACTED_DIR = Path("/root/clawd/leonardo/projects/normative-engine/extracted/titulo_a")
NORM_CODE = "NSR-10"
TITLE_CODE = "A"

# Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

# OpenAI para embeddings
openai.api_key = os.environ.get("OPENAI_API_KEY")


def get_embedding(text: str) -> List[float]:
    """Genera embedding usando OpenAI."""
    if not text or len(text.strip()) < 10:
        return None
    
    # Truncar a 8000 caracteres
    text = text[:8000]
    
    try:
        response = openai.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"  ⚠️ Error embedding: {e}")
        return None


def create_supabase_schema(db: Client):
    """Crea las tablas del Knowledge Graph si no existen."""
    
    # El schema se crea via SQL en Supabase Dashboard
    # Aquí solo verificamos que existan
    
    try:
        db.table("kg_nodes").select("id").limit(1).execute()
        print("  ✓ Tabla kg_nodes existe")
    except Exception as e:
        print(f"  ⚠️ Tabla kg_nodes no existe. Crear manualmente.")
        print(f"    Error: {e}")
        return False
    
    try:
        db.table("kg_edges").select("id").limit(1).execute()
        print("  ✓ Tabla kg_edges existe")
    except Exception as e:
        print(f"  ⚠️ Tabla kg_edges no existe. Crear manualmente.")
        return False
    
    return True


def load_extractions() -> List[Dict]:
    """Carga todas las extracciones."""
    
    all_elements = []
    
    for f in sorted(EXTRACTED_DIR.glob("page_*.json")):
        with open(f, "r", encoding="utf-8") as file:
            data = json.load(file)
        
        page_num = data.get("page_number", 0)
        
        for elem in data.get("elements", []):
            elem["_page"] = page_num
            elem["_source_file"] = f.name
            all_elements.append(elem)
    
    return all_elements


def build_nodes(elements: List[Dict]) -> List[Dict]:
    """Construye nodos del Knowledge Graph."""
    
    nodes = []
    seen_sections = set()
    
    # Nodo raíz: NORM
    norm_id = str(uuid4())
    nodes.append({
        "id": norm_id,
        "type": "NORM",
        "norm_code": NORM_CODE,
        "section_path": None,
        "hierarchy_depth": 0,
        "title": f"{NORM_CODE} - Reglamento Colombiano de Construcción Sismo Resistente",
        "content": "Norma Sismo Resistente de Colombia. Reglamenta condiciones mínimas para diseño y construcción de edificaciones nuevas e intervención de existentes.",
    })
    
    # Nodo TITLE
    title_id = str(uuid4())
    nodes.append({
        "id": title_id,
        "type": "TITLE",
        "norm_code": NORM_CODE,
        "section_path": TITLE_CODE,
        "hierarchy_depth": 1,
        "title": f"Título {TITLE_CODE} — Requisitos Generales de Diseño y Construcción Sismo Resistente",
        "content": "Requisitos generales de diseño sismo resistente, zonificación sísmica, espectros, sistemas estructurales, análisis, derivas.",
        "_parent_id": norm_id,
    })
    
    # Procesar elementos extraídos
    for elem in elements:
        section_path = elem.get("section_path")
        elem_type = elem.get("type", "SECTION")
        
        # Saltar elementos sin section_path válido
        if not section_path:
            continue
        
        # Limpiar section_path
        section_path = section_path.strip()
        
        # Evitar duplicados
        key = f"{elem_type}:{section_path}"
        if key in seen_sections:
            continue
        seen_sections.add(key)
        
        # Determinar profundidad
        if elem_type in ("TABLE", "FIGURE"):
            depth = 4
        elif elem_type == "FORMULA":
            depth = 5
        else:
            depth = section_path.count('.') + 2
        
        # Construir contenido para embedding
        content_parts = []
        if elem.get("title"):
            content_parts.append(elem.get("title"))
        if elem.get("content"):
            content_parts.append(elem.get("content"))
        if elem_type == "TABLE" and elem.get("table_headers"):
            content_parts.append(f"Tabla con columnas: {', '.join(elem.get('table_headers', []))}")
        if elem_type == "FORMULA" and elem.get("formula_latex"):
            content_parts.append(f"Fórmula: {elem.get('formula_latex')}")
        
        content = " ".join(content_parts)
        
        node = {
            "id": str(uuid4()),
            "type": elem_type,
            "norm_code": NORM_CODE,
            "section_path": section_path,
            "hierarchy_depth": depth,
            "title": elem.get("title"),
            "content": content[:5000] if content else None,
            "content_summary": content[:500] if content else None,
            "table_headers": elem.get("table_headers"),
            "table_rows": elem.get("table_rows"),
            "formula_latex": elem.get("formula_latex"),
            "formula_python": elem.get("formula_python"),
            "formula_variables": elem.get("formula_variables"),
            "page_start": elem.get("_page"),
            "page_end": elem.get("_page"),
            "source_pdf": f"NSR-10-Titulo-{TITLE_CODE}.pdf",
            "_references": elem.get("references", []),
        }
        
        nodes.append(node)
    
    return nodes


def build_edges(nodes: List[Dict]) -> List[Dict]:
    """Construye aristas del Knowledge Graph."""
    
    edges = []
    
    # Índice de section_path → node_id
    section_index = {}
    for node in nodes:
        if node.get("section_path"):
            section_index[node["section_path"]] = node["id"]
    
    # Aristas CONTAINS (jerarquía)
    for node in nodes:
        section_path = node.get("section_path")
        if not section_path:
            continue
        
        # Buscar padre
        parent_path = None
        
        if node["type"] == "TITLE":
            # TITLE → NORM
            parent_id = [n["id"] for n in nodes if n["type"] == "NORM"][0]
            edges.append({
                "id": str(uuid4()),
                "source_id": parent_id,
                "target_id": node["id"],
                "edge_type": "CONTAINS",
            })
            continue
        
        # Para tablas/figuras: Tabla A.2.4-3 → A.2.4
        if node["type"] in ("TABLE", "FIGURE"):
            match = re.search(r'([A-K]\.\d+\.?\d*)', section_path)
            if match:
                parent_path = match.group(1)
        
        # Para secciones: A.2.4.1 → A.2.4
        elif '.' in section_path:
            parts = section_path.rsplit('.', 1)
            if len(parts) > 1:
                parent_path = parts[0]
        
        # Para capítulos: A.2 → A
        elif section_path.startswith(TITLE_CODE):
            parent_path = TITLE_CODE
        
        if parent_path and parent_path in section_index:
            edges.append({
                "id": str(uuid4()),
                "source_id": section_index[parent_path],
                "target_id": node["id"],
                "edge_type": "CONTAINS",
            })
    
    # Aristas REFERENCES
    for node in nodes:
        refs = node.get("_references", [])
        source_id = node["id"]
        
        for ref in refs:
            # Buscar el nodo referenciado
            ref_clean = ref.strip()
            
            # Buscar en índice
            target_id = section_index.get(ref_clean)
            
            # Buscar parcial
            if not target_id:
                for sp, nid in section_index.items():
                    if ref_clean in sp or sp in ref_clean:
                        target_id = nid
                        break
            
            if target_id and target_id != source_id:
                edges.append({
                    "id": str(uuid4()),
                    "source_id": source_id,
                    "target_id": target_id,
                    "edge_type": "REFERENCES",
                })
    
    return edges


def generate_embeddings(nodes: List[Dict], batch_size: int = 20):
    """Genera embeddings para los nodos."""
    
    print(f"\n🧠 Generando embeddings...")
    
    nodes_with_content = [n for n in nodes if n.get("content") and len(n.get("content", "")) > 20]
    
    total = len(nodes_with_content)
    embedded = 0
    
    for i in range(0, total, batch_size):
        batch = nodes_with_content[i:i + batch_size]
        
        for node in batch:
            embedding = get_embedding(node.get("content", ""))
            if embedding:
                node["embedding"] = embedding
                embedded += 1
        
        print(f"  ✓ {min(i + batch_size, total)}/{total} embeddings")
    
    print(f"  Total: {embedded} embeddings generados")


def insert_to_supabase(db: Client, nodes: List[Dict], edges: List[Dict]):
    """Inserta nodos y aristas en Supabase."""
    
    print(f"\n📤 Insertando en Supabase...")
    
    # Preparar nodos (quitar campos internos)
    nodes_clean = []
    for node in nodes:
        n = {k: v for k, v in node.items() if not k.startswith("_")}
        nodes_clean.append(n)
    
    # Insertar nodos en batches
    batch_size = 50
    for i in range(0, len(nodes_clean), batch_size):
        batch = nodes_clean[i:i + batch_size]
        try:
            db.table("kg_nodes").upsert(batch, on_conflict="id").execute()
            print(f"  ✓ Nodos: {min(i + batch_size, len(nodes_clean))}/{len(nodes_clean)}")
        except Exception as e:
            print(f"  ⚠️ Error nodos batch {i}: {e}")
    
    # Insertar aristas
    for i in range(0, len(edges), batch_size):
        batch = edges[i:i + batch_size]
        try:
            db.table("kg_edges").upsert(batch, on_conflict="id").execute()
            print(f"  ✓ Aristas: {min(i + batch_size, len(edges))}/{len(edges)}")
        except Exception as e:
            print(f"  ⚠️ Error aristas batch {i}: {e}")


def main():
    print(f"\n{'='*60}")
    print(f"🏗️ Knowledge Graph Builder - NSR-10 Título {TITLE_CODE}")
    print(f"{'='*60}")
    print(f"Inicio: {datetime.now().strftime('%H:%M:%S')}\n")
    
    # Conectar Supabase
    print("📡 Conectando a Supabase...")
    db = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Verificar tablas
    if not create_supabase_schema(db):
        print("\n❌ Crear tablas manualmente primero. Ver sql/kg_schema.sql")
        sys.exit(1)
    
    # Cargar extracciones
    print(f"\n📄 Cargando extracciones de {EXTRACTED_DIR}...")
    elements = load_extractions()
    print(f"  ✓ {len(elements)} elementos cargados")
    
    # Construir nodos
    print(f"\n🔧 Construyendo nodos...")
    nodes = build_nodes(elements)
    print(f"  ✓ {len(nodes)} nodos creados")
    
    # Construir aristas
    print(f"\n🔗 Construyendo aristas...")
    edges = build_edges(nodes)
    print(f"  ✓ {len(edges)} aristas creadas")
    
    # Generar embeddings
    generate_embeddings(nodes)
    
    # Insertar en Supabase
    insert_to_supabase(db, nodes, edges)
    
    # Resumen
    print(f"\n{'='*60}")
    print(f"✅ Knowledge Graph Completado")
    print(f"{'='*60}")
    print(f"  Nodos: {len(nodes)}")
    print(f"  Aristas: {len(edges)}")
    print(f"  Embeddings: {sum(1 for n in nodes if n.get('embedding'))}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
