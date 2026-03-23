#!/usr/bin/env python3
"""
Recorta las figuras extraídas para quedarse solo con la imagen.
Usa detección de bordes y análisis de contenido.
"""

import fitz  # PyMuPDF
import json
from pathlib import Path
from PIL import Image
import re

PDF_PATH = Path("/root/clawd/leonardo/docs/nsr10/NSR-10-Titulo-A.pdf")
OUTPUT_DIR = Path("/root/clawd/leonardo/projects/normative-engine/extracted/titulo_a/figures")

# Mapeo manual de figuras a regiones aproximadas (x, y, w, h) en porcentaje de página
# Estas son las figuras más importantes
FIGURE_REGIONS = {
    "Figura A.2.3-1": (0.05, 0.15, 0.90, 0.75),  # Mapa zonas sísmicas
    "Figura A.2.3-2": (0.05, 0.15, 0.90, 0.75),  # Mapa Aa
    "Figura A.2.3-3": (0.05, 0.15, 0.90, 0.75),  # Mapa Av
    "Figura A.2.4-1": (0.05, 0.20, 0.90, 0.60),  # Gráfica Fa
    "Figura A.2.4-2": (0.05, 0.20, 0.90, 0.60),  # Gráfica Fv
    "Figura A.2.6-1": (0.05, 0.15, 0.90, 0.70),  # Espectro aceleraciones
    "Figura A.2.6-2": (0.05, 0.15, 0.90, 0.70),  # Espectro velocidades
    "Figura A.2.6-3": (0.05, 0.15, 0.90, 0.70),  # Espectro desplazamientos
    "Figura A.2.9-1": (0.05, 0.20, 0.90, 0.60),  # Factor R
    "Figura A.3-1": (0.05, 0.10, 0.90, 0.80),    # Irregularidades planta
    "Figura A.3-2": (0.05, 0.10, 0.90, 0.80),    # Irregularidades altura
    "Figura A.6.5-1": (0.10, 0.25, 0.80, 0.50),  # Separación sísmica
    "Figura A.10.3-1": (0.05, 0.15, 0.90, 0.75), # Mapa Ae
    "Figura A.12.2-1": (0.05, 0.15, 0.90, 0.75), # Mapa Ad
    "Figura A.12.3-1": (0.05, 0.20, 0.90, 0.60), # Espectro umbral daño
    "Figura A-2.2-1": (0.05, 0.20, 0.90, 0.60),  # Coef amortiguamiento
}

def crop_figures():
    """Recorta las figuras usando regiones predefinidas."""
    
    # Cargar índice
    index_path = OUTPUT_DIR / "index.json"
    with open(index_path) as f:
        figures = json.load(f)
    
    doc = fitz.open(str(PDF_PATH))
    
    cropped_dir = OUTPUT_DIR / "cropped"
    cropped_dir.mkdir(exist_ok=True)
    
    results = []
    
    for fig in figures:
        section = fig["section"]
        page_num = fig["page"]
        
        if page_num < 1 or page_num > len(doc):
            continue
        
        page = doc[page_num - 1]
        page_rect = page.rect
        
        # Obtener región (usar predefinida o default)
        region = FIGURE_REGIONS.get(section, (0.05, 0.15, 0.90, 0.70))
        
        # Calcular rectángulo de recorte
        x0 = page_rect.width * region[0]
        y0 = page_rect.height * region[1]
        x1 = page_rect.width * (region[0] + region[2])
        y1 = page_rect.height * (region[1] + region[3])
        
        clip = fitz.Rect(x0, y0, x1, y1)
        
        # Extraer a alta resolución
        mat = fitz.Matrix(3.0, 3.0)  # 3x zoom = ~216 DPI
        pix = page.get_pixmap(matrix=mat, clip=clip)
        
        # Guardar
        safe_section = re.sub(r'[^\w\-.]', '_', section)
        filename = f"{safe_section}_cropped.png"
        filepath = cropped_dir / filename
        pix.save(str(filepath))
        
        print(f"  ✓ {section}: {filepath.name}")
        
        results.append({
            "section": section,
            "title": fig["title"],
            "page": page_num,
            "file": str(filepath),
            "filename": filename,
            "width": pix.width,
            "height": pix.height,
        })
    
    doc.close()
    
    # Guardar índice actualizado
    cropped_index = cropped_dir / "index.json"
    with open(cropped_index, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ {len(results)} figuras recortadas")
    print(f"📁 Directorio: {cropped_dir}")
    
    return results


if __name__ == "__main__":
    crop_figures()
