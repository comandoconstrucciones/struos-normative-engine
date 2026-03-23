#!/usr/bin/env python3
"""Extrae las tablas faltantes"""
import os, json, base64, uuid, requests
import google.generativeai as genai

genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash')

SUPABASE_URL = os.environ.get('STRUOS_SUPABASE_URL')
SERVICE_ROLE = os.environ.get('STRUOS_SUPABASE_SERVICE_ROLE')
HEADERS = {'apikey': SERVICE_ROLE, 'Authorization': f'Bearer {SERVICE_ROLE}', 'Content-Type': 'application/json'}

TABLE_PROMPT = """Extrae la tabla de esta imagen del NSR-10.

Retorna JSON con:
{
  "table_id": "A.X.X-X",
  "title": "Título de la tabla",
  "headers": ["Col1", "Col2", ...],
  "rows": [
    ["val1", "val2", ...],
    ...
  ]
}

Extrae TODOS los datos de la tabla, incluyendo valores numéricos exactos.
Retorna SOLO el JSON."""

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def extract_table(img_path):
    try:
        img_data = encode_image(img_path)
        response = model.generate_content([
            TABLE_PROMPT,
            {"mime_type": "image/png", "data": img_data}
        ])
        text = response.text.strip()
        if '```' in text:
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
            text = text.split('```')[0]
        return json.loads(text.strip())
    except Exception as e:
        print(f"  Error: {e}")
        return None

def insert_table(table_data, page):
    """Inserta tabla en el KG"""
    node = {
        'id': str(uuid.uuid4()),
        'norm_code': 'NSR-10',
        'section_path': f"Tabla {table_data['table_id']}",
        'type': 'TABLE',
        'title': table_data.get('title', ''),
        'table_headers': table_data.get('headers', []),
        'table_rows': table_data.get('rows', []),
        'page_start': page
    }
    
    url = f"{SUPABASE_URL}/rest/v1/kg_nodes"
    r = requests.post(url, headers=HEADERS, json=[node])
    return r.status_code in [200, 201]

# Procesar imágenes
tables_to_process = [
    ('/tmp/tabla_a25-028.png', 28),
    ('/tmp/tabla_a103-113.png', 113),
    ('/tmp/tabla_a122-131.png', 131),
]

for img_path, page in tables_to_process:
    print(f"Procesando {img_path}...")
    table = extract_table(img_path)
    
    if table:
        print(f"  Tabla: {table.get('table_id', 'N/A')}")
        print(f"  Título: {table.get('title', 'N/A')[:50]}")
        print(f"  Filas: {len(table.get('rows', []))}")
        
        if insert_table(table, page):
            print("  ✓ Insertada")
        else:
            print("  ✗ Error al insertar")
    else:
        print("  ✗ No se pudo extraer")
