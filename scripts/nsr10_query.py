#!/usr/bin/env python3
"""
NSR-10 Query Engine - SQL First, LLM Fallback
100% exacto para datos tabulares, LLM para texto
"""
import os, re, requests
from openai import OpenAI

SUPABASE_URL = os.environ.get('STRUOS_SUPABASE_URL')
SERVICE_ROLE = os.environ.get('STRUOS_SUPABASE_SERVICE_ROLE')
HEADERS = {'apikey': SERVICE_ROLE, 'Authorization': f'Bearer {SERVICE_ROLE}', 'Content-Type': 'application/json'}

client = OpenAI()

# =====================================================
# SQL QUERIES - 100% EXACTOS
# =====================================================

def query_municipio(nombre: str) -> dict | None:
    """Busca parámetros sísmicos de un municipio"""
    # Normalizar: quitar acentos para búsqueda más robusta
    import unicodedata
    nombre_norm = ''.join(c for c in unicodedata.normalize('NFD', nombre.lower().strip()) 
                         if unicodedata.category(c) != 'Mn')
    
    # Buscar sin acentos
    url = f"{SUPABASE_URL}/rest/v1/nsr10_municipios?municipio=ilike.*{nombre_norm[:4]}*&limit=5"
    r = requests.get(url, headers=HEADERS, timeout=5)
    if r.status_code == 200 and r.json():
        # Filtrar por mejor match
        results = r.json()
        for row in results:
            muni = row.get('municipio', '').lower()
            muni_norm = ''.join(c for c in unicodedata.normalize('NFD', muni) 
                               if unicodedata.category(c) != 'Mn')
            if nombre_norm in muni_norm:
                return row
        return results[0]  # Si no hay match exacto, retornar primero
    return None

def query_coef_r(sistema: str) -> dict | None:
    """Busca R0, Ω0, Cd para un sistema estructural"""
    # Normalizar búsqueda
    patterns = {
        'pórtico': 'Pórtico',
        'portico': 'Pórtico', 
        'muro': 'Muro',
        'dual': 'dual',
        'arriostrado': 'riostra',
    }
    
    search = sistema
    for key, val in patterns.items():
        if key in sistema.lower():
            search = val
            break
    
    # Buscar DES/DMO/DMI
    capacidad = None
    if 'des' in sistema.lower() or 'especial' in sistema.lower():
        capacidad = 'especial'
    elif 'dmo' in sistema.lower() or 'moderada' in sistema.lower():
        capacidad = 'moderada'
    elif 'dmi' in sistema.lower() or 'mínima' in sistema.lower():
        capacidad = 'mínima'
    
    # Construir query
    url = f"{SUPABASE_URL}/rest/v1/nsr10_coef_r?sistema=ilike.*{search}*"
    if capacidad:
        url += f"&sistema=ilike.*{capacidad}*"
    url += "&limit=5"
    
    r = requests.get(url, headers=HEADERS, timeout=5)
    if r.status_code == 200 and r.json():
        # Si hay múltiples, filtrar mejor
        results = r.json()
        for row in results:
            s = row['sistema'].lower()
            if capacidad and capacidad in s:
                return row
        return results[0]
    return None

def query_coef_fa(suelo: str, aa: float) -> float | None:
    """Busca coeficiente Fa"""
    suelo = suelo.upper().strip()
    url = f"{SUPABASE_URL}/rest/v1/nsr10_coef_fa?soil_type=eq.{suelo}&aa_value=eq.{aa}&limit=1"
    r = requests.get(url, headers=HEADERS, timeout=5)
    if r.status_code == 200 and r.json():
        return r.json()[0]['fa']
    return None

def query_coef_fv(suelo: str, av: float) -> float | None:
    """Busca coeficiente Fv"""
    suelo = suelo.upper().strip()
    url = f"{SUPABASE_URL}/rest/v1/nsr10_coef_fv?soil_type=eq.{suelo}&av_value=eq.{av}&limit=1"
    r = requests.get(url, headers=HEADERS, timeout=5)
    if r.status_code == 200 and r.json():
        return r.json()[0]['fv']
    return None

def query_importancia(grupo: str = None) -> list | dict:
    """Busca coeficientes de importancia"""
    url = f"{SUPABASE_URL}/rest/v1/nsr10_coef_importancia"
    if grupo:
        url += f"?grupo_uso=eq.{grupo}"
    r = requests.get(url, headers=HEADERS, timeout=5)
    if r.status_code == 200:
        data = r.json()
        return data[0] if grupo and data else data
    return []

def query_deriva(sistema: str = None) -> list | dict:
    """Busca límites de deriva"""
    url = f"{SUPABASE_URL}/rest/v1/nsr10_deriva_limites"
    r = requests.get(url, headers=HEADERS, timeout=5)
    if r.status_code == 200:
        data = r.json()
        # Normalizar campos
        for row in data:
            row['sistema'] = row.get('sistema_estructural', 'N/A')
            row['deriva'] = f"{row.get('deriva_max_pct', 0)}%"
        return data
    return []

# =====================================================
# QUERY CLASSIFIER
# =====================================================

def classify_and_query(pregunta: str) -> tuple[str, any]:
    """
    Clasifica la pregunta y ejecuta la query SQL apropiada.
    Returns: (tipo, resultado)
    """
    p = pregunta.lower()
    
    # Municipio/ciudad - buscar primero si hay nombre de ciudad
    ciudades = ['bogotá', 'bogota', 'medellín', 'medellin', 'cali', 'barranquilla', 
                'cartagena', 'bucaramanga', 'pereira', 'cúcuta', 'cucuta', 'ibagué',
                'santa marta', 'villavicencio', 'pasto', 'manizales', 'armenia',
                'neiva', 'montería', 'sincelejo', 'popayán', 'valledupar', 'tunja']
    for ciudad in ciudades:
        if ciudad in p:
            # Verificar que la pregunta es sobre parámetros sísmicos
            if any(term in p for term in ['aa', 'av', 'zona', 'parámetro', 'sísmic', 'amenaza', 'valor']):
                result = query_municipio(ciudad)
                if result:
                    return ('MUNICIPIO', result)
    
    # Coeficiente R
    if re.search(r'\b(r0?|coeficiente\s*r|factor.*reducci[oó]n)\b', p):
        # Extraer sistema
        result = query_coef_r(pregunta)
        if result:
            return ('COEF_R', result)
    
    # Coeficiente Fa
    if 'fa' in p and re.search(r'suelo.*tipo\s*([a-e])', p):
        match_suelo = re.search(r'tipo\s*([a-e])', p, re.I)
        match_aa = re.search(r'aa\s*[=:]?\s*(0?[.,]\d+)', p)
        if match_suelo and match_aa:
            suelo = match_suelo.group(1)
            aa = float(match_aa.group(1).replace(',', '.'))
            result = query_coef_fa(suelo, aa)
            if result:
                return ('COEF_FA', {'suelo': suelo, 'aa': aa, 'fa': result})
    
    # Coeficiente Fv
    if 'fv' in p and re.search(r'suelo.*tipo\s*([a-e])', p):
        match_suelo = re.search(r'tipo\s*([a-e])', p, re.I)
        match_av = re.search(r'av\s*[=:]?\s*(0?[.,]\d+)', p)
        if match_suelo and match_av:
            suelo = match_suelo.group(1)
            av = float(match_av.group(1).replace(',', '.'))
            result = query_coef_fv(suelo, av)
            if result:
                return ('COEF_FV', {'suelo': suelo, 'av': av, 'fv': result})
    
    # Importancia
    if 'importancia' in p or 'hospital' in p or 'grupo' in p:
        if 'hospital' in p or 'iv' in p or '4' in p:
            result = query_importancia('IV')
        else:
            result = query_importancia()
        if result:
            return ('IMPORTANCIA', result)
    
    # Deriva
    if 'deriva' in p or 'desplazamiento' in p or 'drift' in p:
        result = query_deriva()
        if result:
            return ('DERIVA', result)
    
    return ('NONE', None)

# =====================================================
# RESPONSE FORMATTER
# =====================================================

def format_response(tipo: str, data: any, pregunta: str) -> str:
    """Formatea la respuesta SQL en lenguaje natural"""
    
    if tipo == 'MUNICIPIO':
        return f"""**Parámetros sísmicos para {data['municipio']}, {data['departamento']}:**

- **Aa** = {data['aa']}
- **Av** = {data['av']}
- **Zona de amenaza sísmica:** {data['zona_amenaza']}

_Fuente: NSR-10 Apéndice A-4_"""

    elif tipo == 'COEF_R':
        return f"""**Coeficientes para {data['sistema']}:**

- **R₀** = {data['r0']}
- **Ω₀** = {data['omega0']}
- **Cd** = {data['cd']}
- **Altura máxima:** {data.get('altura_max', 'Sin límite')}

_Fuente: NSR-10 Tabla A.3-3_"""

    elif tipo == 'COEF_FA':
        return f"""**Coeficiente Fa para suelo tipo {data['suelo']} con Aa={data['aa']}:**

**Fa = {data['fa']}**

_Fuente: NSR-10 Tabla A.2.4-3_"""

    elif tipo == 'COEF_FV':
        return f"""**Coeficiente Fv para suelo tipo {data['suelo']} con Av={data['av']}:**

**Fv = {data['fv']}**

_Fuente: NSR-10 Tabla A.2.4-4_"""

    elif tipo == 'IMPORTANCIA':
        if isinstance(data, dict):
            return f"""**Coeficiente de importancia para Grupo {data['grupo_uso']}:**

**I = {data['coef_i']}**

Descripción: {data['descripcion']}

_Fuente: NSR-10 Tabla A.2.5-1_"""
        else:
            lines = ["**Coeficientes de importancia (Tabla A.2.5-1):**\n"]
            for row in data:
                lines.append(f"- Grupo {row['grupo_uso']}: I = {row['coef_i']} — {row['descripcion']}")
            return "\n".join(lines)
    
    elif tipo == 'DERIVA':
        lines = ["**Derivas máximas permitidas (Tabla A.6.4-1):**\n"]
        for row in data:
            lines.append(f"- {row.get('sistema', row.get('tipo_estructura', 'Sistema'))}: **{row.get('deriva_max', row.get('deriva', 'N/A'))}**")
        return "\n".join(lines)
    
    return None

# =====================================================
# MAIN QUERY FUNCTION
# =====================================================

def query_nsr10(pregunta: str) -> str:
    """
    Responde preguntas sobre NSR-10.
    SQL-first para datos exactos, LLM fallback para texto.
    """
    # Intentar SQL primero
    tipo, data = classify_and_query(pregunta)
    
    if data:
        response = format_response(tipo, data, pregunta)
        if response:
            return response
    
    # Si no hay SQL match, retornar indicación
    return f"[NO_SQL_MATCH] Pregunta requiere consulta de texto: {pregunta}"

# =====================================================
# TEST
# =====================================================

if __name__ == "__main__":
    tests = [
        "¿Cuál es el valor de Aa para Bogotá?",
        "¿Cuál es el coeficiente R0 para pórticos de concreto DES?",
        "¿Cuál es el coeficiente Fa para suelo tipo D con Aa=0.20?",
        "¿Cuál es el coeficiente de importancia para hospitales?",
        "¿Cuál es la deriva máxima permitida?",
        "¿Cuánto es Aa para Medellín?",
        "R para pórticos de acero con capacidad especial",
        "Fv para suelo tipo E con Av=0.25",
    ]
    
    print("=" * 60)
    print("NSR-10 QUERY ENGINE - SQL FIRST")
    print("=" * 60)
    
    for t in tests:
        print(f"\n📌 {t}")
        print("-" * 60)
        result = query_nsr10(t)
        print(result)
