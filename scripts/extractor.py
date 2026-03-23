#!/usr/bin/env python3
"""
NSR-10 Extraction Pipeline
==========================

Extrae contenido estructurado de los PDFs de NSR-10 usando Vision AI.

Pipeline:
1. Rasterizar PDF → imágenes PNG
2. Extraer contenido con Vision AI (Claude/Gemini)
3. Merge de elementos multi-página
4. Clasificar nodos
5. Detectar referencias cruzadas
6. Generar embeddings e insertar en Knowledge Graph
"""

import os
import json
import asyncio
import re
import base64
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from enum import Enum
import hashlib

# PDF processing
import fitz  # PyMuPDF
from PIL import Image
import io

# AI clients
import anthropic
import google.generativeai as genai

# Database
from supabase import create_client, Client


class NodeType(Enum):
    NORM = "NORM"
    TITLE = "TITLE"
    CHAPTER = "CHAPTER"
    SECTION = "SECTION"
    TABLE = "TABLE"
    FORMULA = "FORMULA"
    FIGURE = "FIGURE"
    DEFINITION = "DEFINITION"
    REQUIREMENT = "REQUIREMENT"
    EXAMPLE = "EXAMPLE"
    COMMENTARY = "COMMENTARY"


@dataclass
class ExtractedElement:
    """Elemento extraído de una página."""
    type: str
    section_path: Optional[str]
    title: Optional[str]
    content: str
    
    # Para tablas
    table_headers: Optional[List[str]] = None
    table_rows: Optional[List[List[str]]] = None
    
    # Para fórmulas
    formula_latex: Optional[str] = None
    formula_python: Optional[str] = None
    formula_variables: Optional[Dict[str, str]] = None
    
    # Para requisitos
    requirement_condition: Optional[str] = None
    
    # Metadata
    page_start: int = 0
    page_end: int = 0
    continues_on_next: bool = False
    continued_from_prev: bool = False
    
    # Referencias detectadas
    references: Optional[List[str]] = None


@dataclass
class PageExtraction:
    """Resultado de extracción de una página."""
    page_number: int
    elements: List[ExtractedElement]
    raw_text: str
    has_table_continuation: bool = False
    has_section_continuation: bool = False


class NSR10Extractor:
    """Extractor de NSR-10 usando Vision AI."""
    
    def __init__(
        self,
        pdf_path: str,
        output_dir: str,
        vision_model: str = "claude",  # "claude" o "gemini"
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None
    ):
        self.pdf_path = Path(pdf_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.vision_model = vision_model
        self.norm_code = "NSR-10"
        
        # Detectar título del documento
        self.title_code = self._detect_title()
        
        # Inicializar clientes
        if vision_model == "claude":
            self.client = anthropic.Anthropic()
        else:
            genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
            self.client = genai.GenerativeModel("gemini-2.0-flash")
        
        # Supabase (opcional)
        if supabase_url and supabase_key:
            self.db = create_client(supabase_url, supabase_key)
        else:
            self.db = None
        
        # Cache de extracciones
        self.extractions: List[PageExtraction] = []
        self.merged_elements: List[ExtractedElement] = []
    
    def _detect_title(self) -> str:
        """Detecta el título del documento (A, B, C, etc.)."""
        filename = self.pdf_path.stem.lower()
        
        titles = {
            "titulo-a": "A", "titulo_a": "A",
            "titulo-b": "B", "titulo_b": "B",
            "titulo-c": "C", "titulo_c": "C",
            "titulo-d": "D", "titulo_d": "D",
            "titulo-e": "E", "titulo_e": "E",
            "titulo-f": "F", "titulo_f": "F",
            "titulo-g": "G", "titulo_g": "G",
            "titulo-h": "H", "titulo_h": "H",
            "titulo-i": "I", "titulo_i": "I",
            "titulo-j": "J", "titulo_j": "J",
            "titulo-k": "K", "titulo_k": "K",
        }
        
        for pattern, code in titles.items():
            if pattern in filename:
                return code
        
        return "A"  # Default
    
    # ═══════════════════════════════════════════════════════════════
    # PASO 1: Rasterización
    # ═══════════════════════════════════════════════════════════════
    
    def rasterize_pdf(self, dpi: int = 200, start_page: int = 0, end_page: int = None) -> List[Path]:
        """Convierte páginas del PDF a imágenes PNG."""
        
        print(f"📄 Rasterizando {self.pdf_path.name}...")
        
        doc = fitz.open(self.pdf_path)
        total_pages = len(doc)
        
        if end_page is None:
            end_page = total_pages
        
        image_paths = []
        images_dir = self.output_dir / "images"
        images_dir.mkdir(exist_ok=True)
        
        for page_num in range(start_page, min(end_page, total_pages)):
            page = doc[page_num]
            
            # Renderizar a imagen
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            
            # Guardar como PNG
            img_path = images_dir / f"page_{page_num + 1:03d}.png"
            pix.save(str(img_path))
            image_paths.append(img_path)
            
            if (page_num + 1) % 10 == 0:
                print(f"  ✓ {page_num + 1}/{end_page} páginas")
        
        doc.close()
        print(f"  ✓ {len(image_paths)} imágenes generadas")
        
        return image_paths
    
    # ═══════════════════════════════════════════════════════════════
    # PASO 2: Extracción con Vision AI
    # ═══════════════════════════════════════════════════════════════
    
    def _get_extraction_prompt(self) -> str:
        """Prompt para extracción estructurada."""
        
        return """Eres un experto en ingeniería estructural extrayendo contenido de la NSR-10 (Norma Sismo Resistente de Colombia).

Analiza esta página y extrae TODOS los elementos estructurados. Para cada elemento, identifica:

1. **SECTION**: Secciones numeradas (A.2.4, A.2.4.1, etc.)
   - section_path: el número de sección exacto
   - title: el título de la sección
   - content: el texto completo de la sección

2. **TABLE**: Tablas con datos
   - section_path: el número de tabla (ej: "Tabla A.2.4-3")
   - title: el título de la tabla
   - table_headers: lista de encabezados de columnas
   - table_rows: lista de filas, cada fila es lista de celdas
   - IMPORTANTE: Si la tabla continúa en la siguiente página, indica continues_on_next: true

3. **FORMULA**: Ecuaciones matemáticas
   - section_path: sección donde aparece
   - formula_latex: la fórmula en LaTeX
   - formula_python: la fórmula como código Python
   - formula_variables: diccionario {variable: "descripción o sección donde se define"}

4. **FIGURE**: Figuras y gráficas
   - section_path: número de figura (ej: "Figura A.2.6-1")
   - title: título/caption de la figura
   - content: descripción de lo que muestra

5. **REQUIREMENT**: Requisitos verificables (límites, condiciones)
   - section_path: sección donde aparece
   - content: el texto del requisito
   - requirement_condition: la condición expresada como código (ej: "drift <= 0.01")

6. **DEFINITION**: Definiciones de términos técnicos
   - section_path: sección donde aparece
   - title: el término definido
   - content: la definición

7. **COMMENTARY**: Comentarios (secciones que empiezan con R-)
   - section_path: número del comentario (ej: "R-A.2.4")
   - content: el texto del comentario

REGLAS IMPORTANTES:
- Extrae TODO el texto visible, no resumas
- Preserva la numeración exacta de secciones
- Para tablas, captura TODAS las filas y columnas
- Detecta si un elemento continúa de la página anterior (continued_from_prev)
- Detecta si un elemento continúa en la siguiente página (continues_on_next)
- Identifica referencias cruzadas: "ver Tabla X", "según sección Y", etc.

Responde en JSON con este formato:
```json
{
  "page_number": <número>,
  "elements": [
    {
      "type": "SECTION|TABLE|FORMULA|FIGURE|REQUIREMENT|DEFINITION|COMMENTARY",
      "section_path": "A.2.4.1",
      "title": "Título del elemento",
      "content": "Contenido completo...",
      "table_headers": ["Col1", "Col2"],  // solo para TABLE
      "table_rows": [["val1", "val2"]],   // solo para TABLE
      "formula_latex": "S_a = 2.5 A_a F_a I",  // solo para FORMULA
      "formula_python": "Sa = 2.5 * Aa * Fa * I",  // solo para FORMULA
      "formula_variables": {"Aa": "Tabla A.2.3-1"},  // solo para FORMULA
      "requirement_condition": "drift <= 0.01",  // solo para REQUIREMENT
      "continues_on_next": false,
      "continued_from_prev": false,
      "references": ["Tabla A.2.4-3", "A.3.3"]
    }
  ],
  "has_table_continuation": false,
  "has_section_continuation": false
}
```"""
    
    async def extract_page_claude(self, image_path: Path, page_num: int) -> PageExtraction:
        """Extrae contenido de una página usando Claude."""
        
        # Leer imagen y convertir a base64
        with open(image_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")
        
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": self._get_extraction_prompt() + f"\n\nEsta es la página {page_num}."
                        }
                    ],
                }
            ],
        )
        
        # Parsear respuesta JSON
        text = response.content[0].text
        
        # Extraer JSON del response
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Intentar parsear directamente
            json_str = text
        
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            print(f"  ⚠️ Error parseando JSON de página {page_num}")
            data = {"elements": [], "page_number": page_num}
        
        # Convertir a objetos
        elements = []
        for elem in data.get("elements", []):
            elements.append(ExtractedElement(
                type=elem.get("type", "SECTION"),
                section_path=elem.get("section_path"),
                title=elem.get("title"),
                content=elem.get("content", ""),
                table_headers=elem.get("table_headers"),
                table_rows=elem.get("table_rows"),
                formula_latex=elem.get("formula_latex"),
                formula_python=elem.get("formula_python"),
                formula_variables=elem.get("formula_variables"),
                requirement_condition=elem.get("requirement_condition"),
                page_start=page_num,
                page_end=page_num,
                continues_on_next=elem.get("continues_on_next", False),
                continued_from_prev=elem.get("continued_from_prev", False),
                references=elem.get("references"),
            ))
        
        return PageExtraction(
            page_number=page_num,
            elements=elements,
            raw_text=text,
            has_table_continuation=data.get("has_table_continuation", False),
            has_section_continuation=data.get("has_section_continuation", False),
        )
    
    async def extract_page_gemini(self, image_path: Path, page_num: int) -> PageExtraction:
        """Extrae contenido de una página usando Gemini."""
        
        # Cargar imagen
        img = Image.open(image_path)
        
        response = self.client.generate_content([
            self._get_extraction_prompt() + f"\n\nEsta es la página {page_num}.",
            img
        ])
        
        text = response.text
        
        # Extraer JSON
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = text
        
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            print(f"  ⚠️ Error parseando JSON de página {page_num}")
            data = {"elements": [], "page_number": page_num}
        
        # Convertir a objetos (mismo código que Claude)
        elements = []
        for elem in data.get("elements", []):
            elements.append(ExtractedElement(
                type=elem.get("type", "SECTION"),
                section_path=elem.get("section_path"),
                title=elem.get("title"),
                content=elem.get("content", ""),
                table_headers=elem.get("table_headers"),
                table_rows=elem.get("table_rows"),
                formula_latex=elem.get("formula_latex"),
                formula_python=elem.get("formula_python"),
                formula_variables=elem.get("formula_variables"),
                requirement_condition=elem.get("requirement_condition"),
                page_start=page_num,
                page_end=page_num,
                continues_on_next=elem.get("continues_on_next", False),
                continued_from_prev=elem.get("continued_from_prev", False),
                references=elem.get("references"),
            ))
        
        return PageExtraction(
            page_number=page_num,
            elements=elements,
            raw_text=text,
            has_table_continuation=data.get("has_table_continuation", False),
            has_section_continuation=data.get("has_section_continuation", False),
        )
    
    async def extract_pages(
        self,
        image_paths: List[Path],
        batch_size: int = 5,
        delay_seconds: float = 1.0
    ) -> List[PageExtraction]:
        """Extrae contenido de múltiples páginas."""
        
        print(f"🔍 Extrayendo contenido con {self.vision_model}...")
        
        extractions = []
        
        for i in range(0, len(image_paths), batch_size):
            batch = image_paths[i:i + batch_size]
            
            tasks = []
            for img_path in batch:
                page_num = int(img_path.stem.split("_")[1])
                
                if self.vision_model == "claude":
                    tasks.append(self.extract_page_claude(img_path, page_num))
                else:
                    tasks.append(self.extract_page_gemini(img_path, page_num))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    print(f"  ⚠️ Error: {result}")
                else:
                    extractions.append(result)
            
            print(f"  ✓ {min(i + batch_size, len(image_paths))}/{len(image_paths)} páginas")
            
            # Rate limiting
            await asyncio.sleep(delay_seconds)
        
        self.extractions = extractions
        return extractions
    
    # ═══════════════════════════════════════════════════════════════
    # PASO 3: Merge de Elementos Multi-Página
    # ═══════════════════════════════════════════════════════════════
    
    def merge_elements(self) -> List[ExtractedElement]:
        """Une elementos que se extienden a través de múltiples páginas."""
        
        print("🔗 Merging elementos multi-página...")
        
        all_elements = []
        pending_merge: Optional[ExtractedElement] = None
        
        for extraction in sorted(self.extractions, key=lambda x: x.page_number):
            for element in extraction.elements:
                
                # ¿Este elemento continúa del anterior?
                if element.continued_from_prev and pending_merge:
                    # Merge
                    if element.type == "TABLE" and pending_merge.type == "TABLE":
                        # Unir filas de tabla
                        if element.table_rows:
                            pending_merge.table_rows = (pending_merge.table_rows or []) + element.table_rows
                        pending_merge.page_end = element.page_start
                    else:
                        # Unir contenido de texto
                        pending_merge.content += "\n" + element.content
                        pending_merge.page_end = element.page_start
                    
                    # ¿Continúa en la siguiente?
                    if not element.continues_on_next:
                        all_elements.append(pending_merge)
                        pending_merge = None
                
                # ¿Este elemento continúa en la siguiente?
                elif element.continues_on_next:
                    pending_merge = element
                
                else:
                    # Elemento completo
                    all_elements.append(element)
        
        # Si quedó algo pendiente
        if pending_merge:
            all_elements.append(pending_merge)
        
        self.merged_elements = all_elements
        print(f"  ✓ {len(all_elements)} elementos después de merge")
        
        return all_elements
    
    # ═══════════════════════════════════════════════════════════════
    # PASO 4: Detección de Referencias
    # ═══════════════════════════════════════════════════════════════
    
    def detect_references(self, element: ExtractedElement) -> List[Tuple[str, str]]:
        """Detecta referencias cruzadas en el contenido."""
        
        references = []
        text = element.content or ""
        
        # Patrones de referencia
        patterns = [
            # Tablas: "Tabla A.2.4-3", "tabla A.2.4-3"
            (r'[Tt]abla\s+([A-K]\.\d+\.?\d*-\d+)', 'TABLE'),
            
            # Figuras: "Figura A.2.6-1"
            (r'[Ff]igura\s+([A-K]\.\d+\.?\d*-\d+)', 'FIGURE'),
            
            # Secciones: "sección A.3.3", "A.3.3.1"
            (r'[Ss]ecci[oó]n\s+([A-K]\.\d+\.?\d*\.?\d*)', 'SECTION'),
            (r'(?<!\w)([A-K]\.\d+\.\d+\.?\d*)(?!\w)', 'SECTION'),
            
            # Capítulos: "Capítulo A.2"
            (r'[Cc]ap[ií]tulo\s+([A-K]\.\d+)', 'CHAPTER'),
            
            # Ecuaciones: "Ecuación A.2.4-1"
            (r'[Ee]cuaci[oó]n\s+([A-K]\.\d+\.?\d*-\d+)', 'FORMULA'),
            
            # Comentarios: "R-A.2.4"
            (r'(R-[A-K]\.\d+\.?\d*)', 'COMMENTARY'),
        ]
        
        for pattern, ref_type in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # No auto-referenciarse
                if match != element.section_path:
                    references.append((match, ref_type))
        
        return list(set(references))  # Deduplicar
    
    def enrich_references(self):
        """Añade referencias detectadas a todos los elementos."""
        
        print("🔗 Detectando referencias cruzadas...")
        
        for element in self.merged_elements:
            refs = self.detect_references(element)
            element.references = [r[0] for r in refs]
        
        total_refs = sum(len(e.references or []) for e in self.merged_elements)
        print(f"  ✓ {total_refs} referencias detectadas")
    
    # ═══════════════════════════════════════════════════════════════
    # PASO 5: Guardar Resultados
    # ═══════════════════════════════════════════════════════════════
    
    def save_extractions(self, filename: str = "extracted.json"):
        """Guarda las extracciones en JSON."""
        
        output_path = self.output_dir / filename
        
        data = {
            "norm_code": self.norm_code,
            "title_code": self.title_code,
            "source_pdf": str(self.pdf_path),
            "total_elements": len(self.merged_elements),
            "elements": [asdict(e) for e in self.merged_elements]
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Guardado en {output_path}")
        return output_path
    
    def save_by_type(self):
        """Guarda elementos separados por tipo."""
        
        by_type: Dict[str, List[ExtractedElement]] = {}
        
        for element in self.merged_elements:
            if element.type not in by_type:
                by_type[element.type] = []
            by_type[element.type].append(element)
        
        for elem_type, elements in by_type.items():
            output_path = self.output_dir / f"{elem_type.lower()}s.json"
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump([asdict(e) for e in elements], f, ensure_ascii=False, indent=2)
            
            print(f"  ✓ {len(elements)} {elem_type}s → {output_path.name}")
    
    # ═══════════════════════════════════════════════════════════════
    # Pipeline Completo
    # ═══════════════════════════════════════════════════════════════
    
    async def run(
        self,
        start_page: int = 0,
        end_page: int = None,
        dpi: int = 200,
        batch_size: int = 5
    ):
        """Ejecuta el pipeline completo de extracción."""
        
        print(f"\n{'='*60}")
        print(f"📚 Extracción NSR-10 Título {self.title_code}")
        print(f"{'='*60}\n")
        
        # Paso 1: Rasterizar
        image_paths = self.rasterize_pdf(dpi=dpi, start_page=start_page, end_page=end_page)
        
        # Paso 2: Extraer con Vision AI
        await self.extract_pages(image_paths, batch_size=batch_size)
        
        # Paso 3: Merge
        self.merge_elements()
        
        # Paso 4: Referencias
        self.enrich_references()
        
        # Paso 5: Guardar
        self.save_extractions()
        self.save_by_type()
        
        # Resumen
        print(f"\n{'='*60}")
        print("📊 Resumen de Extracción")
        print(f"{'='*60}")
        
        by_type = {}
        for e in self.merged_elements:
            by_type[e.type] = by_type.get(e.type, 0) + 1
        
        for t, count in sorted(by_type.items()):
            print(f"  {t}: {count}")
        
        print(f"\n  Total: {len(self.merged_elements)} elementos")
        print(f"{'='*60}\n")
        
        return self.merged_elements


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Extrae contenido de NSR-10")
    parser.add_argument("pdf_path", help="Ruta al PDF")
    parser.add_argument("--output", "-o", default="./extracted", help="Directorio de salida")
    parser.add_argument("--model", "-m", default="claude", choices=["claude", "gemini"])
    parser.add_argument("--start", type=int, default=0, help="Página inicial (0-indexed)")
    parser.add_argument("--end", type=int, default=None, help="Página final")
    parser.add_argument("--dpi", type=int, default=200, help="DPI para rasterización")
    parser.add_argument("--batch", type=int, default=5, help="Batch size para extracción")
    
    args = parser.parse_args()
    
    extractor = NSR10Extractor(
        pdf_path=args.pdf_path,
        output_dir=args.output,
        vision_model=args.model
    )
    
    await extractor.run(
        start_page=args.start,
        end_page=args.end,
        dpi=args.dpi,
        batch_size=args.batch
    )


if __name__ == "__main__":
    asyncio.run(main())
