#!/usr/bin/env python3
"""
Extracción precisa de figuras NSR-10 Título A.
Coordenadas manuales calibradas para cada figura.
"""

import fitz
from pathlib import Path
import re

PDF_PATH = Path("/root/clawd/leonardo/docs/nsr10/NSR-10-Titulo-A.pdf")
OUTPUT_DIR = Path("/root/clawd/leonardo/projects/normative-engine/extracted/titulo_a/figures/precise")

# Coordenadas PRECISAS para cada figura
# Formato: (página_real, x%, y%, ancho%, alto%)
# Las coordenadas son porcentaje de la página
FIGURE_COORDS = {
    # Mapas (páginas completas casi)
    "Figura A.2.3-1": (29, 0.08, 0.12, 0.84, 0.78),   # Mapa zonas sísmicas
    "Figura A.2.3-2": (30, 0.08, 0.12, 0.84, 0.78),   # Mapa Aa
    "Figura A.2.3-3": (31, 0.08, 0.12, 0.84, 0.78),   # Mapa Av
    
    # Gráficas de coeficientes (solo la gráfica + caption)
    "Figura A.2.4-1": (36, 0.02, 0.38, 0.96, 0.38),   # Gráfica Fa
    "Figura A.2.4-2": (37, 0.02, 0.28, 0.96, 0.45),   # Gráfica Fv
    
    # Espectros (gráfica + título, corte justo después del caption)
    "Figura A.2.6-1": (39, 0.02, 0.27, 0.96, 0.34),   # Espectro aceleraciones
    "Figura A.2.6-2": (40, 0.02, 0.22, 0.96, 0.34),   # Espectro velocidades  
    "Figura A.2.6-3": (41, 0.02, 0.22, 0.96, 0.34),   # Espectro desplazamientos
    
    # Factor R (las 4 gráficas + título, sin texto extra)
    "Figura A.2.9-1": (47, 0.02, 0.02, 0.96, 0.48),   # Variación coef R
    
    # Irregularidades (ocupan casi toda la página)
    "Figura A.3-1": (73, 0.05, 0.05, 0.90, 0.88),     # Irregularidades planta
    "Figura A.3-2": (74, 0.05, 0.05, 0.90, 0.88),     # Irregularidades altura
    
    # Separación sísmica (diagrama completo + caption)
    "Figura A.6.5-1": (91, 0.05, 0.43, 0.85, 0.41),   # Separación sísmica
    
    # Mapas adicionales
    "Figura A.10.3-1": (114, 0.08, 0.12, 0.84, 0.78), # Mapa Ae
    "Figura A.12.2-1": (131, 0.08, 0.12, 0.84, 0.78), # Mapa Ad
    
    # Espectro umbral daño (solo gráfica + caption)
    "Figura A.12.3-1": (133, 0.02, 0.25, 0.96, 0.31), # Espectro umbral
    
    # Coef amortiguamiento (solo gráfica + título)
    "Figura A-2.2-1": (157, 0.05, 0.02, 0.90, 0.38),  # Beta cimentación
}


def extract_precise():
    """Extrae figuras con coordenadas precisas."""
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    doc = fitz.open(str(PDF_PATH))
    results = []
    
    print(f"📊 Extrayendo {len(FIGURE_COORDS)} figuras con coordenadas precisas\n")
    
    for fig_id, coords in FIGURE_COORDS.items():
        page_num, x_pct, y_pct, w_pct, h_pct = coords
        
        if page_num < 1 or page_num > len(doc):
            print(f"  ⚠️ {fig_id}: página {page_num} fuera de rango")
            continue
        
        page = doc[page_num - 1]
        rect = page.rect
        
        # Calcular coordenadas absolutas
        x0 = rect.width * x_pct
        y0 = rect.height * y_pct
        x1 = rect.width * (x_pct + w_pct)
        y1 = rect.height * (y_pct + h_pct)
        
        clip = fitz.Rect(x0, y0, x1, y1)
        
        # Extraer a alta resolución (3x = ~216 DPI)
        mat = fitz.Matrix(3.0, 3.0)
        pix = page.get_pixmap(matrix=mat, clip=clip)
        
        # Guardar
        safe_name = re.sub(r'[^\w\-.]', '_', fig_id)
        filename = f"{safe_name}.png"
        filepath = OUTPUT_DIR / filename
        pix.save(str(filepath))
        
        print(f"  ✓ {fig_id}: {pix.width}x{pix.height}px")
        
        results.append({
            "id": fig_id,
            "page": page_num,
            "file": str(filepath),
            "filename": filename,
            "width": pix.width,
            "height": pix.height,
        })
    
    doc.close()
    
    # Guardar índice
    import json
    with open(OUTPUT_DIR / "index.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ {len(results)} figuras extraídas")
    print(f"📁 {OUTPUT_DIR}")
    
    return results


if __name__ == "__main__":
    extract_precise()
