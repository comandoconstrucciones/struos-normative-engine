#!/usr/bin/env python3
"""
Extrae la sección REFERENCIAS completa con títulos de normas
"""
import os, json, re, requests, uuid, base64
import google.generativeai as genai

genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash')

SUPABASE_URL = os.environ.get('STRUOS_SUPABASE_URL')
SERVICE_ROLE = os.environ.get('STRUOS_SUPABASE_SERVICE_ROLE')
HEADERS = {'apikey': SERVICE_ROLE, 'Authorization': f'Bearer {SERVICE_ROLE}', 'Content-Type': 'application/json'}

REF_PROMPT = """Analiza esta página de REFERENCIAS del NSR-10.

Extrae CADA referencia bibliográfica con:
- Código de la norma (ATC 40, FEMA 356, ASCE/SEI 31-03, etc.)
- Título completo
- Año
- Organización/Editor

Retorna JSON array:
[
  {
    "code": "ATC 40",
    "title": "Seismic Evaluation and Retrofit of Concrete Buildings",
    "year": "1996",
    "organization": "Applied Technology Council, Seismic Safety Commission, State of California"
  },
  ...
]

Retorna SOLO el JSON array."""

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def extract_refs(img_path):
    try:
        img_data = encode_image(img_path)
        response = model.generate_content([
            REF_PROMPT,
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
        return []

# Extraer página de referencias (página 153 aprox)
import subprocess
subprocess.run(['pdftoppm', '-png', '-f', '153', '-l', '154', 
                '/root/clawd/leonardo/docs/nsr10/NSR-10-Titulo-A.pdf', 
                '/tmp/nsr10_refs'], capture_output=True)

# Procesar
print("Extrayendo referencias completas...")
all_refs = []
for img in ['/tmp/nsr10_refs-153.png', '/tmp/nsr10_refs-154.png']:
    import os.path
    if os.path.exists(img):
        print(f"  {img}...")
        refs = extract_refs(img)
        all_refs.extend(refs)

print(f"\nReferencias extraídas: {len(all_refs)}")

# Insertar en KG
nodes = []
for ref in all_refs:
    code = ref.get('code', '')
    if not code:
        continue
    
    code_slug = code.replace(' ', '_').replace('/', '_').replace('-', '_')
    
    nodes.append({
        'id': str(uuid.uuid4()),
        'norm_code': 'EXTERNAL',
        'section_path': f"BIBREF.{code_slug}",
        'type': 'EXTERNAL_REF',
        'title': code,
        'content': ref.get('title', ''),
        'content_summary': f"{ref.get('organization', '')} ({ref.get('year', '')})"
    })

print(f"Nodos a insertar: {len(nodes)}")

if nodes:
    url = f"{SUPABASE_URL}/rest/v1/kg_nodes"
    r = requests.post(url, headers=HEADERS, json=nodes)
    if r.status_code in [200, 201]:
        print(f"  ✓ Insertados: {len(nodes)}")
    else:
        print(f"  Error: {r.text[:100]}")

# Mostrar lo que encontramos
print("\nReferencias encontradas:")
for ref in all_refs:
    print(f"  • {ref.get('code', 'N/A')}: {ref.get('title', '')[:50]}...")
