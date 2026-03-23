#!/usr/bin/env python3
"""
Extrae figuras del PDF NSR-10 y las guarda como imágenes individuales.
Usa coordenadas aproximadas basadas en el contenido de cada página.
"""

import fitz  # PyMuPDF
import json
import os
from pathlib import Path
from typing import List, Dict
import re

# Configuración
PDF_PATH = Path("/root/clawd/leonardo/docs/nsr10/NSR-10-Titulo-A.pdf")
EXTRACTED_DIR = Path("/root/clawd/leonardo/projects/normative-engine/extracted/titulo_a")
OUTPUT_DIR = Path("/root/clawd/leonardo/projects/normative-engine/extracted/titulo_a/figures")


def extract_figures_from_pdf():
    """Extrae todas las figuras identificadas del PDF."""
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Cargar lista de figuras desde extracciones
    figures = []
    for f in sorted(EXTRACTED_DIR.glob("page_*.json")):
        with open(f) as file:
            d = json.load(file)
        page_num = d.get("page_number", 0)
        for elem in d.get("elements", []):
            if elem.get("type") == "FIGURE":
                figures.append({
                    "page": page_num,
                    "section": elem.get("section_path", ""),
                    "title": elem.get("title", ""),
                })
    
    print(f"📊 Figuras a extraer: {len(figures)}")
    
    # Abrir PDF
    doc = fitz.open(str(PDF_PATH))
    
    extracted = []
    
    for fig in figures:
        page_num = fig["page"]
        section = fig["section"]
        
        if page_num < 1 or page_num > len(doc):
            print(f"  ⚠️ Página {page_num} fuera de rango")
            continue
        
        page = doc[page_num - 1]  # 0-indexed
        
        # Generar nombre de archivo
        safe_section = re.sub(r'[^\w\-.]', '_', section)
        filename = f"{safe_section}.png"
        filepath = OUTPUT_DIR / filename
        
        # Extraer página completa a alta resolución
        # Luego se puede recortar manualmente o con detección
        mat = fitz.Matrix(2.0, 2.0)  # 2x zoom = ~144 DPI
        pix = page.get_pixmap(matrix=mat)
        
        # Guardar
        pix.save(str(filepath))
        
        print(f"  ✓ {section}: {filepath.name}")
        
        extracted.append({
            "section": section,
            "title": fig["title"],
            "page": page_num,
            "file": str(filepath),
            "filename": filename,
        })
    
    doc.close()
    
    # Guardar índice
    index_path = OUTPUT_DIR / "index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(extracted, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ {len(extracted)} figuras extraídas")
    print(f"📁 Directorio: {OUTPUT_DIR}")
    print(f"📋 Índice: {index_path}")
    
    return extracted


def crop_figure_region(page, figure_title: str):
    """
    Intenta detectar y recortar la región de una figura.
    Busca el texto del título y recorta la región debajo.
    """
    # Buscar texto del título
    text_instances = page.search_for(figure_title[:30])
    
    if text_instances:
        # Tomar primera instancia
        rect = text_instances[0]
        
        # Expandir hacia abajo para capturar la figura
        # Esto es aproximado - figuras suelen estar debajo del título
        page_rect = page.rect
        
        # Crear rectángulo desde el título hasta ~40% de página o siguiente texto
        crop_rect = fitz.Rect(
            0,                      # x0 - todo el ancho
            rect.y0 - 20,           # y0 - un poco arriba del título
            page_rect.width,        # x1 - todo el ancho
            min(rect.y1 + 400, page_rect.height * 0.8)  # y1 - ~400px abajo
        )
        
        return crop_rect
    
    return None


if __name__ == "__main__":
    extract_figures_from_pdf()
