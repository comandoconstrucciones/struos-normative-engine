#!/usr/bin/env python3
"""
Test de extracción de NSR-10 - Versión 2 con mejor manejo de errores.
"""

import asyncio
import os
import sys
import json
from pathlib import Path

import fitz  # PyMuPDF
import anthropic
import base64

async def test_extraction():
    """Prueba la extracción de una página."""
    
    pdf_path = Path("/root/clawd/leonardo/docs/nsr10/NSR-10-Titulo-A.pdf")
    output_dir = Path("/root/clawd/leonardo/projects/normative-engine/extracted/test")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📄 Abriendo {pdf_path.name}...")
    
    doc = fitz.open(pdf_path)
    print(f"   Total páginas: {len(doc)}")
    
    # Probar página 45 (que tiene tablas de Fa/Fv)
    page_num = 44  # 0-indexed = página 45
    
    page = doc[page_num]
    
    # Renderizar a imagen con menor resolución
    mat = fitz.Matrix(150 / 72, 150 / 72)  # 150 DPI (más pequeño)
    pix = page.get_pixmap(matrix=mat)
    
    # Guardar imagen
    img_path = output_dir / f"test_page.png"
    pix.save(str(img_path))
    
    # Verificar tamaño
    img_size = img_path.stat().st_size
    print(f"   ✓ Imagen: {img_path.name} ({img_size / 1024:.1f} KB)")
    
    # Leer como base64
    with open(img_path, "rb") as f:
        image_bytes = f.read()
    
    image_data = base64.standard_b64encode(image_bytes).decode("utf-8")
    print(f"   ✓ Base64 length: {len(image_data)} chars")
    
    doc.close()
    
    # Prompt simplificado
    prompt = """Analiza esta página de la NSR-10 (normativa sísmica de Colombia).

Extrae el contenido en formato JSON con esta estructura:

{
  "page_number": 45,
  "elements": [
    {
      "type": "TABLE",
      "section_path": "Tabla A.2.4-3",
      "title": "Valores del coeficiente Fa",
      "table_headers": ["Tipo de perfil", "Aa <= 0.05", "Aa = 0.10", ...],
      "table_rows": [
        ["A", "0.8", "0.8", ...],
        ["B", "1.0", "1.0", ...]
      ]
    }
  ]
}

Extrae TODAS las tablas, secciones, y fórmulas que veas. Para las tablas, incluye TODOS los valores."""

    print(f"\n   🤖 Llamando a Claude...")
    
    try:
        client = anthropic.Anthropic()
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
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
                            "text": prompt
                        }
                    ],
                }
            ],
        )
        
        text = response.content[0].text
        print(f"\n   ✓ Respuesta recibida ({len(text)} chars)")
        
        # Guardar respuesta
        output_path = output_dir / "test_response.txt"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
        
        print(f"   ✓ Guardada en {output_path.name}")
        
        # Intentar parsear JSON
        import re
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            data = json.loads(json_str)
            
            json_path = output_dir / "test_extraction.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"   ✓ JSON guardado: {json_path.name}")
            
            # Mostrar resumen
            elements = data.get("elements", [])
            print(f"\n   📊 Elementos: {len(elements)}")
            for elem in elements:
                print(f"      • [{elem.get('type')}] {elem.get('section_path')}: {elem.get('title', '')[:40]}")
        
    except anthropic.BadRequestError as e:
        print(f"\n   ❌ Error de API: {e}")
        print(f"   → Mensaje: {e.message}")
        
    except Exception as e:
        print(f"\n   ❌ Error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(test_extraction())
