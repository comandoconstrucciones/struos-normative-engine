#!/usr/bin/env python3
"""
Knowledge Graph Builder
=======================

Convierte las extracciones de NSR-10 en nodos y aristas del Knowledge Graph.

Pasos:
1. Cargar extracciones JSON
2. Crear nodos de jerarquía (NORM → TITLE → CHAPTER)
3. Insertar nodos de contenido (SECTION, TABLE, FORMULA, etc.)
4. Crear aristas CONTAINS (jerarquía)
5. Crear aristas REFERENCES (referencias cruzadas)
6. Generar embeddings con Voyage AI
7. Insertar en Supabase
"""

import os
import json
import asyncio
import re
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional, Set, Tuple
from uuid import uuid4
import hashlib

# Embeddings
import voyageai

# Database
from supabase import create_client, Client


@dataclass
class KGNode:
    """Nodo del Knowledge Graph."""
    id: str
    type: str
    norm_code: str
    section_path: Optional[str]
    hierarchy_depth: int
    title: Optional[str]
    content: Optional[str]
    content_summary: Optional[str] = None
    
    # Para tablas
    table_headers: Optional[List[str]] = None
    table_rows: Optional[List[List[str]]] = None
    table_sql_ref: Optional[str] = None
    
    # Para fórmulas
    formula_latex: Optional[str] = None
    formula_python: Optional[str] = None
    formula_variables: Optional[Dict[str, str]] = None
    
    # Para requisitos
    requirement_condition: Optional[str] = None
    requirement_python_func: Optional[str] = None
    
    # Metadata
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    source_pdf: Optional[str] = None
    
    # Embedding (se genera después)
    embedding: Optional[List[float]] = None


@dataclass
class KGEdge:
    """Arista del Knowledge Graph."""
    id: str
    source_id: str
    target_id: str
    edge_type: str
    metadata: Optional[Dict] = None
    equivalence_score: Optional[float] = None
    verified_by_expert: bool = False


class KnowledgeGraphBuilder:
    """Construye el Knowledge Graph desde extracciones."""
    
    # Jerarquía de la NSR-10
    TITLE_NAMES = {
        "A": "Requisitos Generales de Diseño y Construcción Sismo Resistente",
        "B": "Cargas",
        "C": "Concreto Estructural",
        "D": "Mampostería Estructural",
        "E": "Casas de Uno y Dos Pisos",
        "F": "Estructuras Metálicas",
        "G": "Estructuras de Madera y Guadua",
        "H": "Estudios Geotécnicos",
        "I": "Supervisión Técnica",
        "J": "Requisitos de Protección Contra Incendio",
        "K": "Requisitos Complementarios",
    }
    
    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        voyage_api_key: Optional[str] = None
    ):
        # Supabase
        self.supabase_url = supabase_url or os.environ.get("SUPABASE_URL")
        self.supabase_key = supabase_key or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        
        if self.supabase_url and self.supabase_key:
            self.db = create_client(self.supabase_url, self.supabase_key)
        else:
            self.db = None
            print("⚠️ Supabase no configurado, solo se generarán archivos locales")
        
        # Voyage AI
        self.voyage_key = voyage_api_key or os.environ.get("VOYAGE_API_KEY")
        if self.voyage_key:
            self.voyage = voyageai.Client(api_key=self.voyage_key)
        else:
            self.voyage = None
            print("⚠️ Voyage AI no configurado, no se generarán embeddings")
        
        # Storage
        self.nodes: Dict[str, KGNode] = {}
        self.edges: List[KGEdge] = []
        
        # Índice para búsqueda rápida por section_path
        self.section_index: Dict[str, str] = {}  # section_path → node_id
    
    def _generate_id(self, content: str) -> str:
        """Genera ID único basado en contenido."""
        return str(uuid4())
    
    def _get_hierarchy_depth(self, section_path: str) -> int:
        """Calcula la profundidad jerárquica."""
        if not section_path:
            return 0
        
        # Contar puntos y guiones
        parts = re.split(r'[.\-]', section_path)
        return len(parts)
    
    def _get_parent_section(self, section_path: str) -> Optional[str]:
        """Obtiene la sección padre."""
        if not section_path or '.' not in section_path:
            return None
        
        # A.2.4.1 → A.2.4
        # Tabla A.2.4-3 → A.2.4
        
        # Para tablas/figuras: "Tabla A.2.4-3" → "A.2.4"
        if section_path.startswith(("Tabla", "Figura", "R-")):
            match = re.search(r'([A-K]\.\d+\.?\d*)', section_path)
            if match:
                return match.group(1)
        
        # Para secciones normales
        parts = section_path.rsplit('.', 1)
        if len(parts) > 1:
            return parts[0]
        
        return None
    
    def _summarize_content(self, content: str, max_length: int = 500) -> str:
        """Genera resumen del contenido."""
        if not content:
            return ""
        
        # Tomar primeras oraciones hasta max_length
        sentences = re.split(r'(?<=[.!?])\s+', content)
        summary = ""
        
        for sentence in sentences:
            if len(summary) + len(sentence) > max_length:
                break
            summary += sentence + " "
        
        return summary.strip()
    
    # ═══════════════════════════════════════════════════════════════
    # PASO 1: Crear Nodos de Jerarquía
    # ═══════════════════════════════════════════════════════════════
    
    def create_hierarchy_nodes(self, norm_code: str = "NSR-10", title_code: str = "A"):
        """Crea nodos NORM y TITLE."""
        
        print("🏗️ Creando nodos de jerarquía...")
        
        # Nodo raíz: NORM
        norm_id = self._generate_id(norm_code)
        norm_node = KGNode(
            id=norm_id,
            type="NORM",
            norm_code=norm_code,
            section_path=None,
            hierarchy_depth=0,
            title=f"{norm_code} - Reglamento Colombiano de Construcción Sismo Resistente",
            content=f"Norma Sismo Resistente de Colombia {norm_code}. Reglamenta las condiciones mínimas para el diseño y construcción de edificaciones.",
        )
        self.nodes[norm_id] = norm_node
        self.section_index[norm_code] = norm_id
        
        # Nodo TITLE
        title_id = self._generate_id(f"{norm_code}-{title_code}")
        title_name = self.TITLE_NAMES.get(title_code, f"Título {title_code}")
        
        title_node = KGNode(
            id=title_id,
            type="TITLE",
            norm_code=norm_code,
            section_path=title_code,
            hierarchy_depth=1,
            title=f"Título {title_code} — {title_name}",
            content=f"Título {title_code} de la {norm_code}: {title_name}",
        )
        self.nodes[title_id] = title_node
        self.section_index[title_code] = title_id
        
        # Edge: NORM → TITLE
        self.edges.append(KGEdge(
            id=self._generate_id(f"{norm_id}-{title_id}"),
            source_id=norm_id,
            target_id=title_id,
            edge_type="CONTAINS"
        ))
        
        print(f"  ✓ Nodo NORM: {norm_code}")
        print(f"  ✓ Nodo TITLE: {title_code}")
    
    # ═══════════════════════════════════════════════════════════════
    # PASO 2: Procesar Extracciones
    # ═══════════════════════════════════════════════════════════════
    
    def process_extractions(self, extractions_path: Path, norm_code: str = "NSR-10"):
        """Procesa archivo de extracciones y crea nodos."""
        
        print(f"📄 Procesando {extractions_path}...")
        
        with open(extractions_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        title_code = data.get("title_code", "A")
        source_pdf = data.get("source_pdf", "")
        elements = data.get("elements", [])
        
        # Crear jerarquía base
        self.create_hierarchy_nodes(norm_code, title_code)
        
        # Crear nodos intermedios (CHAPTER) y de contenido
        chapters_created: Set[str] = set()
        
        for elem in elements:
            section_path = elem.get("section_path")
            
            if not section_path:
                continue
            
            # Crear chapters intermedios si no existen
            self._ensure_chapter_hierarchy(section_path, norm_code, title_code, chapters_created)
            
            # Crear nodo del elemento
            node = self._create_node_from_element(elem, norm_code, source_pdf)
            
            if node:
                self.nodes[node.id] = node
                self.section_index[section_path] = node.id
                
                # Crear edge CONTAINS desde el padre
                parent_section = self._get_parent_section(section_path)
                if parent_section and parent_section in self.section_index:
                    self.edges.append(KGEdge(
                        id=self._generate_id(f"{self.section_index[parent_section]}-{node.id}"),
                        source_id=self.section_index[parent_section],
                        target_id=node.id,
                        edge_type="CONTAINS"
                    ))
        
        print(f"  ✓ {len(self.nodes)} nodos creados")
        print(f"  ✓ {len(chapters_created)} capítulos intermedios")
    
    def _ensure_chapter_hierarchy(
        self,
        section_path: str,
        norm_code: str,
        title_code: str,
        chapters_created: Set[str]
    ):
        """Asegura que existan los nodos de capítulo intermedios."""
        
        # Extraer partes de la sección
        # A.2.4.1 → ["A", "2", "4", "1"]
        
        # Para secciones normales
        if section_path.startswith(title_code):
            parts = section_path.split('.')
            
            # Crear A.2, A.2.4, etc.
            for i in range(2, len(parts)):
                chapter_path = '.'.join(parts[:i])
                
                if chapter_path not in self.section_index and chapter_path not in chapters_created:
                    # Crear nodo CHAPTER
                    chapter_id = self._generate_id(chapter_path)
                    
                    chapter_node = KGNode(
                        id=chapter_id,
                        type="CHAPTER",
                        norm_code=norm_code,
                        section_path=chapter_path,
                        hierarchy_depth=i,
                        title=f"Capítulo {chapter_path}",
                        content=None,  # Se llenará si encontramos contenido
                    )
                    
                    self.nodes[chapter_id] = chapter_node
                    self.section_index[chapter_path] = chapter_id
                    chapters_created.add(chapter_path)
                    
                    # Edge desde padre
                    parent_path = '.'.join(parts[:i-1]) if i > 2 else title_code
                    if parent_path in self.section_index:
                        self.edges.append(KGEdge(
                            id=self._generate_id(f"{self.section_index[parent_path]}-{chapter_id}"),
                            source_id=self.section_index[parent_path],
                            target_id=chapter_id,
                            edge_type="CONTAINS"
                        ))
    
    def _create_node_from_element(
        self,
        elem: Dict,
        norm_code: str,
        source_pdf: str
    ) -> Optional[KGNode]:
        """Crea un KGNode desde un elemento extraído."""
        
        elem_type = elem.get("type", "SECTION")
        section_path = elem.get("section_path")
        
        if not section_path:
            return None
        
        node = KGNode(
            id=self._generate_id(f"{norm_code}-{section_path}"),
            type=elem_type,
            norm_code=norm_code,
            section_path=section_path,
            hierarchy_depth=self._get_hierarchy_depth(section_path),
            title=elem.get("title"),
            content=elem.get("content"),
            content_summary=self._summarize_content(elem.get("content", "")),
            
            # Tablas
            table_headers=elem.get("table_headers"),
            table_rows=elem.get("table_rows"),
            
            # Fórmulas
            formula_latex=elem.get("formula_latex"),
            formula_python=elem.get("formula_python"),
            formula_variables=elem.get("formula_variables"),
            
            # Requisitos
            requirement_condition=elem.get("requirement_condition"),
            
            # Metadata
            page_start=elem.get("page_start"),
            page_end=elem.get("page_end"),
            source_pdf=source_pdf,
        )
        
        return node
    
    # ═══════════════════════════════════════════════════════════════
    # PASO 3: Crear Aristas REFERENCES
    # ═══════════════════════════════════════════════════════════════
    
    def create_reference_edges(self, extractions_path: Path):
        """Crea aristas REFERENCES basadas en referencias detectadas."""
        
        print("🔗 Creando aristas REFERENCES...")
        
        with open(extractions_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        ref_count = 0
        
        for elem in data.get("elements", []):
            source_path = elem.get("section_path")
            references = elem.get("references", [])
            
            if not source_path or source_path not in self.section_index:
                continue
            
            source_id = self.section_index[source_path]
            
            for ref in references:
                # Buscar el nodo referenciado
                target_id = self.section_index.get(ref)
                
                if target_id and target_id != source_id:
                    # Crear edge REFERENCES
                    self.edges.append(KGEdge(
                        id=self._generate_id(f"ref-{source_id}-{target_id}"),
                        source_id=source_id,
                        target_id=target_id,
                        edge_type="REFERENCES"
                    ))
                    ref_count += 1
        
        print(f"  ✓ {ref_count} aristas REFERENCES creadas")
    
    # ═══════════════════════════════════════════════════════════════
    # PASO 4: Generar Embeddings
    # ═══════════════════════════════════════════════════════════════
    
    async def generate_embeddings(self, batch_size: int = 50):
        """Genera embeddings para todos los nodos con contenido."""
        
        if not self.voyage:
            print("⚠️ Voyage AI no configurado, saltando embeddings")
            return
        
        print("🧠 Generando embeddings...")
        
        # Filtrar nodos con contenido para embeddear
        nodes_to_embed = []
        for node in self.nodes.values():
            text = self._get_embedding_text(node)
            if text and len(text) > 10:
                nodes_to_embed.append((node, text))
        
        print(f"  → {len(nodes_to_embed)} nodos a embeddear")
        
        # Procesar en batches
        for i in range(0, len(nodes_to_embed), batch_size):
            batch = nodes_to_embed[i:i + batch_size]
            texts = [t for _, t in batch]
            
            try:
                result = self.voyage.embed(texts, model="voyage-3")
                
                for j, embedding in enumerate(result.embeddings):
                    batch[j][0].embedding = embedding
                
                print(f"  ✓ {min(i + batch_size, len(nodes_to_embed))}/{len(nodes_to_embed)}")
                
            except Exception as e:
                print(f"  ⚠️ Error en batch {i}: {e}")
            
            await asyncio.sleep(0.5)  # Rate limiting
        
        embedded_count = sum(1 for n in self.nodes.values() if n.embedding)
        print(f"  ✓ {embedded_count} embeddings generados")
    
    def _get_embedding_text(self, node: KGNode) -> str:
        """Obtiene el texto a embeddear para un nodo."""
        
        parts = []
        
        if node.title:
            parts.append(node.title)
        
        if node.content:
            parts.append(node.content)
        
        # Para tablas, incluir descripción
        if node.type == "TABLE" and node.table_headers:
            parts.append(f"Tabla con columnas: {', '.join(node.table_headers)}")
        
        # Para fórmulas, incluir la fórmula
        if node.type == "FORMULA":
            if node.formula_latex:
                parts.append(f"Fórmula: {node.formula_latex}")
            if node.formula_python:
                parts.append(f"Python: {node.formula_python}")
        
        # Para requisitos, incluir condición
        if node.type == "REQUIREMENT" and node.requirement_condition:
            parts.append(f"Condición: {node.requirement_condition}")
        
        return " ".join(parts)
    
    # ═══════════════════════════════════════════════════════════════
    # PASO 5: Guardar / Insertar
    # ═══════════════════════════════════════════════════════════════
    
    def save_to_json(self, output_dir: Path):
        """Guarda nodos y aristas en archivos JSON."""
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Guardar nodos
        nodes_data = []
        for node in self.nodes.values():
            node_dict = asdict(node)
            # Convertir embedding a lista si existe
            if node_dict.get("embedding"):
                node_dict["embedding"] = list(node_dict["embedding"])
            nodes_data.append(node_dict)
        
        nodes_path = output_dir / "kg_nodes.json"
        with open(nodes_path, "w", encoding="utf-8") as f:
            json.dump(nodes_data, f, ensure_ascii=False, indent=2)
        
        # Guardar aristas
        edges_data = [asdict(e) for e in self.edges]
        edges_path = output_dir / "kg_edges.json"
        with open(edges_path, "w", encoding="utf-8") as f:
            json.dump(edges_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Guardado:")
        print(f"  → {nodes_path} ({len(nodes_data)} nodos)")
        print(f"  → {edges_path} ({len(edges_data)} aristas)")
    
    async def insert_to_supabase(self, batch_size: int = 100):
        """Inserta nodos y aristas en Supabase."""
        
        if not self.db:
            print("⚠️ Supabase no configurado")
            return
        
        print("📤 Insertando en Supabase...")
        
        # Insertar nodos
        nodes_data = []
        for node in self.nodes.values():
            node_dict = {
                "id": node.id,
                "type": node.type,
                "norm_code": node.norm_code,
                "section_path": node.section_path,
                "hierarchy_depth": node.hierarchy_depth,
                "title": node.title,
                "content": node.content,
                "content_summary": node.content_summary,
                "table_headers": node.table_headers,
                "table_rows": node.table_rows,
                "table_sql_ref": node.table_sql_ref,
                "formula_latex": node.formula_latex,
                "formula_python": node.formula_python,
                "formula_variables": node.formula_variables,
                "requirement_condition": node.requirement_condition,
                "requirement_python_func": node.requirement_python_func,
                "page_start": node.page_start,
                "page_end": node.page_end,
                "source_pdf": node.source_pdf,
                "embedding": node.embedding,
            }
            nodes_data.append(node_dict)
        
        # Batch insert nodos
        for i in range(0, len(nodes_data), batch_size):
            batch = nodes_data[i:i + batch_size]
            try:
                self.db.table("kg_nodes").upsert(batch).execute()
                print(f"  ✓ Nodos: {min(i + batch_size, len(nodes_data))}/{len(nodes_data)}")
            except Exception as e:
                print(f"  ⚠️ Error insertando nodos: {e}")
        
        # Insertar aristas
        edges_data = []
        for edge in self.edges:
            edges_data.append({
                "id": edge.id,
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "edge_type": edge.edge_type,
                "metadata": edge.metadata,
                "equivalence_score": edge.equivalence_score,
                "verified_by_expert": edge.verified_by_expert,
            })
        
        for i in range(0, len(edges_data), batch_size):
            batch = edges_data[i:i + batch_size]
            try:
                self.db.table("kg_edges").upsert(batch).execute()
                print(f"  ✓ Aristas: {min(i + batch_size, len(edges_data))}/{len(edges_data)}")
            except Exception as e:
                print(f"  ⚠️ Error insertando aristas: {e}")
        
        print("  ✓ Inserción completada")
    
    # ═══════════════════════════════════════════════════════════════
    # Pipeline Completo
    # ═══════════════════════════════════════════════════════════════
    
    async def build(
        self,
        extractions_path: Path,
        output_dir: Path,
        norm_code: str = "NSR-10",
        generate_embeddings: bool = True,
        insert_to_db: bool = False
    ):
        """Ejecuta el pipeline completo de construcción del KG."""
        
        print(f"\n{'='*60}")
        print(f"🏗️ Knowledge Graph Builder")
        print(f"{'='*60}\n")
        
        # Paso 1-2: Procesar extracciones
        self.process_extractions(extractions_path, norm_code)
        
        # Paso 3: Referencias
        self.create_reference_edges(extractions_path)
        
        # Paso 4: Embeddings
        if generate_embeddings:
            await self.generate_embeddings()
        
        # Paso 5: Guardar
        self.save_to_json(output_dir)
        
        if insert_to_db:
            await self.insert_to_supabase()
        
        # Resumen
        print(f"\n{'='*60}")
        print("📊 Resumen del Knowledge Graph")
        print(f"{'='*60}")
        
        by_type = {}
        for node in self.nodes.values():
            by_type[node.type] = by_type.get(node.type, 0) + 1
        
        print("\nNodos por tipo:")
        for t, count in sorted(by_type.items()):
            print(f"  {t}: {count}")
        
        edge_types = {}
        for edge in self.edges:
            edge_types[edge.edge_type] = edge_types.get(edge.edge_type, 0) + 1
        
        print("\nAristas por tipo:")
        for t, count in sorted(edge_types.items()):
            print(f"  {t}: {count}")
        
        print(f"\nTotal: {len(self.nodes)} nodos, {len(self.edges)} aristas")
        print(f"{'='*60}\n")


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Construye Knowledge Graph desde extracciones")
    parser.add_argument("extractions", help="Ruta al archivo JSON de extracciones")
    parser.add_argument("--output", "-o", default="./kg_output", help="Directorio de salida")
    parser.add_argument("--norm", default="NSR-10", help="Código de normativa")
    parser.add_argument("--no-embeddings", action="store_true", help="No generar embeddings")
    parser.add_argument("--insert-db", action="store_true", help="Insertar en Supabase")
    
    args = parser.parse_args()
    
    builder = KnowledgeGraphBuilder()
    
    await builder.build(
        extractions_path=Path(args.extractions),
        output_dir=Path(args.output),
        norm_code=args.norm,
        generate_embeddings=not args.no_embeddings,
        insert_to_db=args.insert_db
    )


if __name__ == "__main__":
    asyncio.run(main())
