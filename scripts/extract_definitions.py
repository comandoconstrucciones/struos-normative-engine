#!/usr/bin/env python3
"""
Extracción especializada de definiciones (A.13) y normas técnicas (A.X.11)
"""
import os
import json
import base64
import google.generativeai as genai
from pathlib import Path

# Configurar Gemini
genai.configure(api_key=os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash')

DEFINITIONS_PROMPT = """Analiza esta página del NSR-10 que contiene DEFINICIONES (Capítulo A.13).

Extrae CADA definición con el formato exacto:
- **término**: El texto en negrilla o antes del guión largo (—)
- **definición**: El texto explicativo después del guión

Retorna JSON array:
[
  {
    "term": "Acabados",
    "definition": "Partes y componentes de una edificación que no hacen parte de la estructura o de su cimentación.",
    "see_also": ["elementos no estructurales"]  // si dice "Véase..."
  },
  ...
]

IMPORTANTE:
- Captura el término EXACTO en negrilla
- Si hay "Véase X" o "Ver X", agrégalo en see_also
- Si el término tiene símbolo (ej: "Aa"), inclúyelo
- No omitas ninguna definición

Retorna SOLO el JSON array, sin explicación."""

NORMAS_PROMPT = """Analiza esta página del NSR-10 que contiene referencias a NORMAS TÉCNICAS.

Extrae CADA norma técnica mencionada:
- NTC (Normas Técnicas Colombianas)
- ASTM (American Society for Testing and Materials)
- ASCE/SEI
- ACI
- ISO
- Otras normas internacionales

Retorna JSON array:
[
  {
    "code": "NTC 1495",
    "title": "Suelos. Ensayo para determinar el contenido de agua de suelos y rocas",
    "equivalent": "ASTM D 2166",
    "section_reference": "A.2.11"
  },
  ...
]

IMPORTANTE:
- Si hay equivalencia NTC ↔ ASTM, incluye ambas
- Captura el título completo de la norma si está disponible
- Identifica la sección NSR-10 donde se menciona

Retorna SOLO el JSON array."""

def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def extract_from_image(image_path, prompt):
    """Extrae contenido de una imagen usando Gemini Vision"""
    try:
        img_data = encode_image(image_path)
        response = model.generate_content([
            prompt,
            {"mime_type": "image/png", "data": img_data}
        ])
        
        text = response.text.strip()
        # Limpiar markdown si existe
        if text.startswith('```'):
            text = text.split('\n', 1)[1]
            if text.endswith('```'):
                text = text[:-3]
            text = text.strip()
        
        return json.loads(text)
    except Exception as e:
        print(f"Error procesando {image_path}: {e}")
        return []

def main():
    # Extraer definiciones (A.13)
    print("=== Extrayendo DEFINICIONES (A.13) ===")
    definitions = []
    
    a13_pages = sorted(Path('/tmp').glob('nsr10_a13-*.png'))
    for page_path in a13_pages:
        page_num = page_path.stem.split('-')[1]
        print(f"  Procesando página {page_num}...")
        
        page_defs = extract_from_image(str(page_path), DEFINITIONS_PROMPT)
        if page_defs:
            for d in page_defs:
                d['source_page'] = int(page_num)
            definitions.extend(page_defs)
    
    print(f"\n  Total definiciones: {len(definitions)}")
    
    # Guardar definiciones
    with open('extracted/definitions_a13.json', 'w', encoding='utf-8') as f:
        json.dump(definitions, f, ensure_ascii=False, indent=2)
    
    # Extraer normas técnicas (A.2.11)
    print("\n=== Extrayendo NORMAS TÉCNICAS (A.2.11) ===")
    normas = []
    
    normas_pages = sorted(Path('/tmp').glob('nsr10_a2_11-*.png'))
    for page_path in normas_pages:
        page_num = page_path.stem.split('-')[1]
        print(f"  Procesando página {page_num}...")
        
        page_normas = extract_from_image(str(page_path), NORMAS_PROMPT)
        if page_normas:
            for n in page_normas:
                n['source_page'] = int(page_num)
            normas.extend(page_normas)
    
    print(f"\n  Total normas: {len(normas)}")
    
    # Guardar normas
    with open('extracted/normas_tecnicas.json', 'w', encoding='utf-8') as f:
        json.dump(normas, f, ensure_ascii=False, indent=2)
    
    # Resumen
    print("\n=== RESUMEN ===")
    print(f"Definiciones extraídas: {len(definitions)}")
    print(f"Normas técnicas extraídas: {len(normas)}")
    print(f"\nArchivos generados:")
    print("  - extracted/definitions_a13.json")
    print("  - extracted/normas_tecnicas.json")

if __name__ == '__main__':
    main()
