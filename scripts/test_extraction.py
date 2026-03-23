#!/usr/bin/env python3
"""
Test de extracción de NSR-10 con pocas páginas.
"""

import asyncio
import os
import sys
import json
from pathlib import Path

# Añadir el directorio al path
sys.path.insert(0, str(Path(__file__).parent))

import fitz  # PyMuPDF
import anthropic
import base64

async def test_single_page_extraction():
    """Prueba la extracción de una sola página."""
    
    pdf_path = Path("/root/clawd/leonardo/docs/nsr10/NSR-10-Titulo-A.pdf")
    output_dir = Path("/root/clawd/leonardo/projects/normative-engine/extracted/test")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📄 Abriendo {pdf_path.name}...")
    
    doc = fitz.open(pdf_path)
    print(f"   Total páginas: {len(doc)}")
    
    # Seleccionar páginas interesantes para test
    # Página ~45 tiene tabla de Fa, página ~50 tiene espectro
    test_pages = [44, 45, 50]  # 0-indexed
    
    client = anthropic.Anthropic()
    
    extraction_prompt = """Eres un experto en ingeniería estructural extrayendo contenido de la NSR-10.

Analiza esta página y extrae TODOS los elementos. Responde en JSON:

```json
{
  "page_number": <número>,
  "elements": [
    {
      "type": "SECTION|TABLE|FORMULA|FIGURE|REQUIREMENT|DEFINITION",
      "section_path": "A.2.4.1",
      "title": "Título",
      "content": "Contenido completo...",
      "table_headers": ["Col1", "Col2"],
      "table_rows": [["val1", "val2"]],
      "formula_latex": "S_a = 2.5 A_a F_a I",
      "formula_python": "Sa = 2.5 * Aa * Fa * I",
      "continues_on_next": false,
      "continued_from_prev": false,
      "references": ["Tabla A.2.4-3"]
    }
  ]
}
```

IMPORTANTE:
- Extrae TODO el texto, no resumas
- Para tablas, captura TODAS las filas y columnas
- Identifica fórmulas y escríbelas en LaTeX y Python
- Detecta referencias cruzadas"""
    
    for page_num in test_pages:
        if page_num >= len(doc):
            continue
            
        print(f"\n{'='*50}")
        print(f"📃 Procesando página {page_num + 1}")
        print(f"{'='*50}")
        
        page = doc[page_num]
        
        # Renderizar a imagen
        mat = fitz.Matrix(200 / 72, 200 / 72)  # 200 DPI
        pix = page.get_pixmap(matrix=mat)
        
        # Guardar imagen
        img_path = output_dir / f"page_{page_num + 1:03d}.png"
        pix.save(str(img_path))
        print(f"   ✓ Imagen guardada: {img_path.name}")
        
        # Convertir a base64
        with open(img_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")
        
        # Llamar a Claude
        print(f"   🤖 Llamando a Claude...")
        
        response = client.messages.create(
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
                            "text": extraction_prompt + f"\n\nEsta es la página {page_num + 1} del Título A de la NSR-10."
                        }
                    ],
                }
            ],
        )
        
        text = response.content[0].text
        
        # Extraer JSON
        import re
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = text
        
        try:
            data = json.loads(json_str)
            
            # Guardar extracción
            output_path = output_dir / f"page_{page_num + 1:03d}.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"   ✓ Extracción guardada: {output_path.name}")
            
            # Mostrar resumen
            elements = data.get("elements", [])
            print(f"\n   📊 Elementos extraídos: {len(elements)}")
            
            for elem in elements:
                elem_type = elem.get("type", "?")
                section = elem.get("section_path", "?")
                title = elem.get("title", "")[:50]
                
                print(f"      • [{elem_type}] {section}: {title}")
                
                if elem.get("table_headers"):
                    print(f"        → Tabla con {len(elem.get('table_rows', []))} filas")
                
                if elem.get("formula_latex"):
                    print(f"        → Fórmula: {elem.get('formula_latex')[:60]}")
                    
        except json.JSONDecodeError as e:
            print(f"   ⚠️ Error parseando JSON: {e}")
            
            # Guardar respuesta raw
            raw_path = output_dir / f"page_{page_num + 1:03d}_raw.txt"
            with open(raw_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"   → Respuesta raw guardada en {raw_path.name}")
    
    doc.close()
    
    print(f"\n{'='*50}")
    print("✅ Test completado")
    print(f"{'='*50}")


if __name__ == "__main__":
    asyncio.run(test_single_page_extraction())
