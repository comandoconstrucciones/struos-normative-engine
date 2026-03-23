#!/usr/bin/env python3
"""
Regenera fórmulas Python ejecutables a partir del LaTeX
"""
import os
import json
import requests
import google.generativeai as genai

genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash')

SUPABASE_URL = os.environ.get('STRUOS_SUPABASE_URL')
SERVICE_ROLE = os.environ.get('STRUOS_SUPABASE_SERVICE_ROLE')
HEADERS = {
    'apikey': SERVICE_ROLE,
    'Authorization': f'Bearer {SERVICE_ROLE}',
    'Content-Type': 'application/json'
}

FORMULA_PROMPT = """Convierte esta fórmula LaTeX de la NSR-10 a código Python ejecutable.

LaTeX: {latex}
Variables: {variables}
Sección: {section}

Genera una función Python que:
1. Reciba los parámetros necesarios
2. Calcule y retorne el resultado
3. Use nombres de variables claros
4. Incluya docstring con la referencia NSR-10

Ejemplo de formato esperado:
```python
def calc_Sa(T, Aa, Fv, I, T0, TL):
    \"\"\"
    Calcula la aceleración espectral Sa según NSR-10 A.2.6.1
    
    Args:
        T: Período fundamental (s)
        Aa: Coeficiente de aceleración
        Fv: Coeficiente de amplificación
        I: Factor de importancia
        T0: Período inicial
        TL: Período largo
    
    Returns:
        Sa: Aceleración espectral (fracción de g)
    \"\"\"
    if T < T0:
        Sa = 2.5 * Aa * Fv * I * (0.4 + 0.6 * T / T0)
    elif T <= TL:
        Sa = 2.5 * Aa * Fv * I
    else:
        Sa = 1.2 * Aa * Fv * I * TL / T
    return Sa
```

Retorna SOLO el código Python, sin explicación adicional."""

def regenerate_formula(formula_data):
    """Regenera una fórmula con Python ejecutable"""
    latex = formula_data.get('formula_latex', '')
    variables = formula_data.get('formula_variables', {})
    section = formula_data.get('section_path', '')
    
    prompt = FORMULA_PROMPT.format(
        latex=latex,
        variables=json.dumps(variables) if variables else "{}",
        section=section
    )
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Limpiar código
        if '```python' in text:
            text = text.split('```python')[1].split('```')[0]
        elif '```' in text:
            text = text.split('```')[1].split('```')[0]
        
        text = text.strip()
        
        # Verificar que es Python válido
        compile(text, '<string>', 'exec')
        return text
    except SyntaxError:
        return None
    except Exception as e:
        print(f"  Error: {e}")
        return None

def main():
    # Obtener fórmulas del KG
    print("Obteniendo fórmulas del KG...")
    url = f"{SUPABASE_URL}/rest/v1/kg_nodes?type=eq.FORMULA&select=id,section_path,formula_latex,formula_variables,formula_python"
    r = requests.get(url, headers=HEADERS)
    formulas = r.json()
    
    print(f"Total fórmulas: {len(formulas)}")
    
    # Filtrar las que tienen Python inválido
    to_fix = []
    for f in formulas:
        py = f.get('formula_python', '')
        if py:
            try:
                compile(py, '<string>', 'exec')
            except:
                to_fix.append(f)
        else:
            to_fix.append(f)
    
    print(f"Fórmulas a regenerar: {len(to_fix)}")
    
    # Regenerar
    fixed = 0
    for i, f in enumerate(to_fix[:20]):  # Limitar a 20 por ahora
        section = f.get('section_path', 'N/A')
        print(f"  [{i+1}/{len(to_fix[:20])}] {section}...")
        
        new_python = regenerate_formula(f)
        if new_python:
            # Actualizar en Supabase
            update_url = f"{SUPABASE_URL}/rest/v1/kg_nodes?id=eq.{f['id']}"
            r = requests.patch(update_url, headers=HEADERS, json={'formula_python': new_python})
            if r.status_code in [200, 204]:
                fixed += 1
    
    print(f"\n=== RESUMEN ===")
    print(f"Fórmulas regeneradas: {fixed}")

if __name__ == '__main__':
    main()
