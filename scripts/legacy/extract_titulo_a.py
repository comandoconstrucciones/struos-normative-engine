#!/usr/bin/env python3
"""
Extracción completa del Título A de NSR-10 usando Gemini.
"""

import os
import sys
import json
import time
import asyncio
from pathlib import Path
from datetime import datetime

import fitz  # PyMuPDF
import google.generativeai as genai
from PIL import Image
import io

# Configurar Gemini
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

OUTPUT_DIR = Path("/root/clawd/leonardo/projects/normative-engine/extracted/titulo_a")
PDF_PATH = Path("/root/clawd/leonardo/docs/nsr10/NSR-10-Titulo-A.pdf")

EXTRACTION_PROMPT = """Analiza esta página de la NSR-10 (Norma Sismo Resistente de Colombia, Título A).

Extrae TODO el contenido en formato JSON estructurado:

```json
{
  "page_number": <número>,
  "elements": [
    {
      "type": "SECTION",
      "section_path": "A.2.4.1",
      "title": "Título de la sección",
      "content": "Texto completo de la sección..."
    },
    {
      "type": "TABLE",
      "section_path": "Tabla A.2.4-3",
      "title": "Título de la tabla",
      "table_headers": ["Col1", "Col2", "Col3"],
      "table_rows": [["val1", "val2", "val3"], ...]
    },
    {
      "type": "FORMULA",
      "section_path": "A.2.6",
      "formula_latex": "S_a = 2.5 \\cdot A_a \\cdot F_a \\cdot I",
      "formula_python": "Sa = 2.5 * Aa * Fa * I",
      "formula_variables": {"Aa": "Tabla A.2.3-2", "Fa": "Tabla A.2.4-3"}
    },
    {
      "type": "FIGURE",
      "section_path": "Figura A.2.6-1",
      "title": "Título de la figura",
      "content": "Descripción de lo que muestra la figura"
    },
    {
      "type": "REQUIREMENT",
      "section_path": "A.6.4.1",
      "content": "La deriva máxima no debe exceder...",
      "requirement_condition": "drift <= 0.01"
    }
  ],
  "references": ["A.2.4", "Tabla A.2.4-3"],
  "continues_on_next": false,
  "continued_from_prev": false
}
```

REGLAS:
- Extrae TODO el texto visible, no resumas
- Para tablas: captura TODOS los valores de TODAS las filas y columnas
- Identifica el número de sección exacto (A.2.4.1, etc.)
- Detecta si el contenido continúa en la siguiente página
- Lista todas las referencias cruzadas mencionadas
- Si hay fórmulas, escríbelas en LaTeX y Python"""


def extract_page_gemini(model, image_path: Path, page_num: int) -> dict:
    """Extrae contenido de una página usando Gemini."""
    
    img = Image.open(image_path)
    
    try:
        response = model.generate_content([
            EXTRACTION_PROMPT + f"\n\nEsta es la página {page_num}.",
            img
        ])
        
        text = response.text
        
        # Extraer JSON
        import re
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = text
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {
                "page_number": page_num,
                "elements": [],
                "raw_text": text,
                "parse_error": True
            }
            
    except Exception as e:
        return {
            "page_number": page_num,
            "elements": [],
            "error": str(e)
        }


def main():
    print(f"\n{'='*60}")
    print(f"📚 Extracción NSR-10 Título A con Gemini")
    print(f"{'='*60}")
    print(f"Inicio: {datetime.now().strftime('%H:%M:%S')}\n")
    
    # Crear directorio de salida
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    images_dir = OUTPUT_DIR / "images"
    images_dir.mkdir(exist_ok=True)
    
    # Abrir PDF
    doc = fitz.open(PDF_PATH)
    total_pages = len(doc)
    print(f"📄 PDF: {PDF_PATH.name} ({total_pages} páginas)\n")
    
    # Inicializar Gemini
    model = genai.GenerativeModel("gemini-2.0-flash")
    
    # Extraer todas las páginas
    all_extractions = []
    errors = []
    
    start_time = time.time()
    
    for page_num in range(total_pages):
        page = doc[page_num]
        
        # Renderizar página
        mat = fitz.Matrix(150 / 72, 150 / 72)  # 150 DPI
        pix = page.get_pixmap(matrix=mat)
        
        img_path = images_dir / f"page_{page_num + 1:03d}.png"
        pix.save(str(img_path))
        
        # Extraer con Gemini
        result = extract_page_gemini(model, img_path, page_num + 1)
        all_extractions.append(result)
        
        # Guardar extracción individual
        json_path = OUTPUT_DIR / f"page_{page_num + 1:03d}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # Tracking
        elements_count = len(result.get("elements", []))
        has_error = "error" in result or result.get("parse_error")
        
        if has_error:
            errors.append(page_num + 1)
            status = "⚠️"
        else:
            status = "✓"
        
        # Progress
        elapsed = time.time() - start_time
        pages_done = page_num + 1
        rate = pages_done / elapsed if elapsed > 0 else 0
        eta = (total_pages - pages_done) / rate if rate > 0 else 0
        
        print(f"  {status} Página {page_num + 1:3d}/{total_pages} | {elements_count:2d} elementos | {rate:.1f} pág/s | ETA: {eta/60:.1f} min")
        
        # Rate limiting (evitar 429)
        time.sleep(0.5)
    
    doc.close()
    
    # Guardar extracción completa
    complete_path = OUTPUT_DIR / "complete_extraction.json"
    with open(complete_path, "w", encoding="utf-8") as f:
        json.dump({
            "norm_code": "NSR-10",
            "title_code": "A",
            "total_pages": total_pages,
            "extraction_date": datetime.now().isoformat(),
            "pages": all_extractions
        }, f, ensure_ascii=False, indent=2)
    
    # Resumen
    total_elements = sum(len(p.get("elements", [])) for p in all_extractions)
    elapsed_total = time.time() - start_time
    
    print(f"\n{'='*60}")
    print(f"📊 Extracción Completada")
    print(f"{'='*60}")
    print(f"  Páginas: {total_pages}")
    print(f"  Elementos: {total_elements}")
    print(f"  Errores: {len(errors)}")
    print(f"  Tiempo: {elapsed_total/60:.1f} minutos")
    print(f"  Output: {complete_path}")
    
    if errors:
        print(f"  Páginas con error: {errors[:10]}{'...' if len(errors) > 10 else ''}")
    
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
