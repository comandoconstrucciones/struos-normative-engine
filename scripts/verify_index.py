#!/usr/bin/env python3
"""
Extrae el índice del Título A y verifica contra el KG
"""
import os
import json
import base64
import google.generativeai as genai
from pathlib import Path

genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash')

INDEX_PROMPT = """Analiza esta página del ÍNDICE del NSR-10 Título A.

Extrae TODAS las entradas del índice con el formato:
- Tablas (ej: "Tabla A.2.4-1")
- Figuras (ej: "Figura A.2.3-1")
- Fórmulas/Ecuaciones si se mencionan

Retorna JSON:
{
  "tables": [
    {"id": "A.2.4-1", "title": "Clasificación de los perfiles de suelo"},
    ...
  ],
  "figures": [
    {"id": "A.2.3-1", "title": "Zonas de Amenaza Sísmica"},
    ...
  ],
  "formulas": [
    {"id": "A.2.6-1", "title": "Espectro de diseño"},
    ...
  ]
}

Solo incluye elementos que aparezcan en esta página del índice.
Retorna SOLO el JSON."""

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def extract_index(image_path):
    try:
        img_data = encode_image(image_path)
        response = model.generate_content([
            INDEX_PROMPT,
            {"mime_type": "image/png", "data": img_data}
        ])
        text = response.text.strip()
        if text.startswith('```'):
            text = text.split('\n', 1)[1]
            if text.endswith('```'):
                text = text[:-3]
        return json.loads(text)
    except Exception as e:
        print(f"  Error: {e}")
        return {"tables": [], "figures": [], "formulas": []}

def main():
    all_tables = []
    all_figures = []
    all_formulas = []
    
    print("Extrayendo índice de tablas y figuras...")
    
    # Procesar páginas 3-10 (donde está el índice de tablas/figuras)
    for i in range(3, 11):
        img_path = f"/tmp/nsr10_indice-{i:03d}.png"
        if not Path(img_path).exists():
            continue
        
        print(f"  Página {i}...")
        result = extract_index(img_path)
        
        all_tables.extend(result.get('tables', []))
        all_figures.extend(result.get('figures', []))
        all_formulas.extend(result.get('formulas', []))
    
    # Eliminar duplicados
    tables = {t['id']: t for t in all_tables}.values()
    figures = {f['id']: f for f in all_figures}.values()
    formulas = {f['id']: f for f in all_formulas}.values()
    
    index = {
        'tables': list(tables),
        'figures': list(figures),
        'formulas': list(formulas)
    }
    
    with open('extracted/titulo_a_index.json', 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    
    print(f"\n=== ÍNDICE EXTRAÍDO ===")
    print(f"Tablas: {len(index['tables'])}")
    print(f"Figuras: {len(index['figures'])}")
    print(f"Fórmulas: {len(index['formulas'])}")
    
    # Listar
    print("\nTABLAS:")
    for t in sorted(index['tables'], key=lambda x: x['id']):
        print(f"  {t['id']}: {t['title'][:50]}")
    
    print("\nFIGURAS:")
    for f in sorted(index['figures'], key=lambda x: x['id']):
        print(f"  {f['id']}: {f['title'][:50]}")

if __name__ == '__main__':
    main()
