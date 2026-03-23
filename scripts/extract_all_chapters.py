#!/usr/bin/env python3
"""
Extrae símbolos (nomenclatura A.X.0) y normas técnicas (A.X.11) de todos los capítulos
"""
import os
import json
import base64
import google.generativeai as genai
from pathlib import Path
from collections import defaultdict

genai.configure(api_key=os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash')

SYMBOLS_PROMPT = """Analiza esta página de nomenclatura del NSR-10 (sección A.X.0).

Extrae TODOS los símbolos matemáticos/variables con sus definiciones.
Formato típico: "símbolo = descripción" o "símbolo — descripción"

Retorna JSON array:
[
  {
    "symbol": "Aa",
    "definition": "coeficiente que representa la aceleración horizontal pico efectiva, para diseño",
    "unit": null,
    "reference": "dado en A.2.2"
  },
  {
    "symbol": "Fa",
    "definition": "coeficiente de amplificación que afecta la aceleración en la zona de períodos cortos",
    "unit": null,
    "reference": "ver Tabla A.2.4-3"
  }
]

IMPORTANTE:
- Captura el símbolo EXACTO (con subíndices si los hay: T₀, φₐ, etc.)
- Si hay unidades, extráelas (ej: "m/s", "kPa")
- Si hay referencia a tabla/sección, inclúyela
- No omitas ningún símbolo

Retorna SOLO el JSON array."""

NORMAS_PROMPT = """Analiza esta página del NSR-10 que contiene referencias a NORMAS TÉCNICAS.

Extrae CADA norma técnica mencionada:
- NTC (Normas Técnicas Colombianas)
- ASTM (American Society for Testing and Materials)
- ASCE/SEI
- ACI
- FEMA
- ISO
- AWS
- Otras normas internacionales

Retorna JSON array:
[
  {
    "code": "NTC 1495",
    "title": "Suelos. Ensayo para determinar el contenido de agua",
    "equivalent": "ASTM D 2166",
    "chapter": "A.2"
  }
]

Retorna SOLO el JSON array."""

def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def extract_from_image(image_path, prompt):
    try:
        img_data = encode_image(image_path)
        response = model.generate_content([
            prompt,
            {"mime_type": "image/png", "data": img_data}
        ])
        
        text = response.text.strip()
        if text.startswith('```'):
            text = text.split('\n', 1)[1]
            if text.endswith('```'):
                text = text[:-3]
            text = text.strip()
        
        return json.loads(text)
    except Exception as e:
        print(f"  Error: {e}")
        return []

def main():
    extract_dir = Path('/tmp/nsr10_extract')
    
    # Procesar nomenclatura (símbolos)
    print("=== EXTRAYENDO SÍMBOLOS (A.X.0) ===\n")
    all_symbols = []
    
    symbol_files = sorted([f for f in extract_dir.glob('a*_0-*.png')])
    chapters_done = set()
    
    for img_path in symbol_files:
        # Extraer capítulo del nombre (a2_0, a3_0, etc.)
        chapter = img_path.stem.split('-')[0].replace('_0', '').upper().replace('A', 'A.')
        page = img_path.stem.split('-')[1]
        
        if chapter not in chapters_done:
            print(f"Capítulo {chapter}.0:")
            chapters_done.add(chapter)
        
        print(f"  Página {page}...")
        symbols = extract_from_image(str(img_path), SYMBOLS_PROMPT)
        
        for s in symbols:
            s['chapter'] = chapter
            s['source_page'] = int(page)
        
        all_symbols.extend(symbols)
    
    print(f"\nTotal símbolos extraídos: {len(all_symbols)}")
    
    # Procesar normas técnicas
    print("\n=== EXTRAYENDO NORMAS TÉCNICAS (A.X.11) ===\n")
    all_normas = []
    
    normas_files = sorted([f for f in extract_dir.glob('a*_11-*.png')])
    chapters_done = set()
    
    for img_path in normas_files:
        chapter = img_path.stem.split('-')[0].replace('_11', '').upper().replace('A', 'A.')
        page = img_path.stem.split('-')[1]
        
        if chapter not in chapters_done:
            print(f"Capítulo {chapter}.11:")
            chapters_done.add(chapter)
        
        print(f"  Página {page}...")
        normas = extract_from_image(str(img_path), NORMAS_PROMPT)
        
        for n in normas:
            n['chapter'] = chapter
            n['source_page'] = int(page)
        
        all_normas.extend(normas)
    
    print(f"\nTotal normas extraídas: {len(all_normas)}")
    
    # Guardar resultados
    with open('extracted/symbols_all_chapters.json', 'w', encoding='utf-8') as f:
        json.dump(all_symbols, f, ensure_ascii=False, indent=2)
    
    with open('extracted/normas_all_chapters.json', 'w', encoding='utf-8') as f:
        json.dump(all_normas, f, ensure_ascii=False, indent=2)
    
    # Resumen por capítulo
    print("\n=== RESUMEN POR CAPÍTULO ===\n")
    
    sym_by_ch = defaultdict(list)
    for s in all_symbols:
        sym_by_ch[s['chapter']].append(s)
    
    norm_by_ch = defaultdict(list)
    for n in all_normas:
        norm_by_ch[n['chapter']].append(n)
    
    print("Símbolos:")
    for ch in sorted(sym_by_ch.keys()):
        print(f"  {ch}.0: {len(sym_by_ch[ch])} símbolos")
    
    print("\nNormas técnicas:")
    for ch in sorted(norm_by_ch.keys()):
        print(f"  {ch}.11: {len(norm_by_ch[ch])} normas")
    
    print(f"\nArchivos generados:")
    print("  - extracted/symbols_all_chapters.json")
    print("  - extracted/normas_all_chapters.json")

if __name__ == '__main__':
    main()
