#!/usr/bin/env python3
import os, json, requests
import google.generativeai as genai

genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash')

SUPABASE_URL = os.environ.get('STRUOS_SUPABASE_URL')
SERVICE_ROLE = os.environ.get('STRUOS_SUPABASE_SERVICE_ROLE')
HEADERS = {'apikey': SERVICE_ROLE, 'Authorization': f'Bearer {SERVICE_ROLE}', 'Content-Type': 'application/json'}

def regenerate(latex, section):
    prompt = f"""Convierte esta fórmula LaTeX NSR-10 a Python ejecutable:
LaTeX: {latex}
Sección: {section}

Genera función Python con def calc_SECCION(...): que calcule y retorne el resultado.
SOLO código Python, sin explicación."""
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if '```python' in text:
            text = text.split('```python')[1].split('```')[0]
        elif '```' in text:
            text = text.split('```')[1].split('```')[0]
        text = text.strip()
        compile(text, '<string>', 'exec')
        return text
    except:
        return None

# Obtener fórmulas con Python inválido
url = f"{SUPABASE_URL}/rest/v1/kg_nodes?type=eq.FORMULA&select=id,section_path,formula_latex,formula_python"
formulas = requests.get(url, headers=HEADERS).json()

to_fix = []
for f in formulas:
    py = f.get('formula_python', '')
    if py:
        try:
            compile(py, '<string>', 'exec')
        except:
            to_fix.append(f)

print(f"Fórmulas pendientes: {len(to_fix)}")

fixed = 0
for i, f in enumerate(to_fix):
    section = f.get('section_path', 'N/A')
    latex = f.get('formula_latex', '')
    
    print(f"  [{i+1}/{len(to_fix)}] {section}...")
    new_py = regenerate(latex, section)
    
    if new_py:
        update_url = f"{SUPABASE_URL}/rest/v1/kg_nodes?id=eq.{f['id']}"
        r = requests.patch(update_url, headers=HEADERS, json={'formula_python': new_py})
        if r.status_code in [200, 204]:
            fixed += 1

print(f"\nRegeneradas: {fixed}/{len(to_fix)}")
