#!/usr/bin/env python3
"""
NSR-10 API Server — FastAPI for Vercel Serverless
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import os
import requests
import unicodedata

# Config
SUPABASE_URL = "https://vdakfewjadwaczulcmvj.supabase.co"
SERVICE_ROLE = os.environ.get('STRUOS_SUPABASE_SERVICE_ROLE', '')

HEADERS = {
    'apikey': SERVICE_ROLE,
    'Authorization': f'Bearer {SERVICE_ROLE}',
    'Content-Type': 'application/json'
}

app = FastAPI(title="NSR-10 API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# === UTILIDADES ===

def normalize_text(text: str) -> str:
    """Quita acentos para búsqueda flexible"""
    if not text:
        return ""
    # NFD descompone caracteres (á → a + combining accent)
    normalized = unicodedata.normalize('NFD', text)
    # Filtra combining marks (categoría 'Mn')
    without_accents = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    return without_accents

def search_municipio(nombre: str):
    """Busca municipio con y sin acentos"""
    # Primero buscar exacto
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/nsr10_municipios",
        params={"municipio": f"ilike.*{nombre}*", "select": "municipio,departamento,aa,av,zona_amenaza"},
        headers=HEADERS,
        timeout=10
    )
    data = resp.json()
    
    if data and isinstance(data, list) and len(data) > 0:
        return data
    
    # Si no encuentra, buscar con variantes de acentos
    # Mapeo de caracteres comunes
    ACCENT_MAP = {
        'a': ['á', 'à', 'ä'],
        'e': ['é', 'è', 'ë'],
        'i': ['í', 'ì', 'ï'],
        'o': ['ó', 'ò', 'ö'],
        'u': ['ú', 'ù', 'ü'],
        'n': ['ñ'],
    }
    
    # Generar variantes con acentos
    nombre_lower = nombre.lower()
    variantes = [nombre]
    
    for base, accented_list in ACCENT_MAP.items():
        if base in nombre_lower:
            for accented in accented_list:
                variante = nombre_lower.replace(base, accented)
                variantes.append(variante.title())
    
    # Probar cada variante
    for variante in variantes[1:]:  # Skip la original ya probada
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/nsr10_municipios",
            params={"municipio": f"ilike.*{variante}*", "select": "municipio,departamento,aa,av,zona_amenaza"},
            headers=HEADERS,
            timeout=10
        )
        data = resp.json()
        if data and isinstance(data, list) and len(data) > 0:
            return data
    
    # Última opción: traer todos y filtrar en Python
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/nsr10_municipios",
        params={"select": "municipio,departamento,aa,av,zona_amenaza", "limit": "1200"},
        headers=HEADERS,
        timeout=15
    )
    all_municipios = resp.json()
    
    if isinstance(all_municipios, list):
        nombre_norm = normalize_text(nombre).lower()
        matches = [
            m for m in all_municipios 
            if nombre_norm in normalize_text(m.get('municipio', '')).lower()
        ]
        if matches:
            return matches
    
    return []

# === ENDPOINTS ===

@app.get("/")
def root():
    return {
        "service": "NSR-10 Normative Engine",
        "version": "1.1.0",
        "status": "ok",
        "features": ["búsqueda sin acentos", "7 endpoints"],
        "endpoints": ["/municipios/{nombre}", "/coef/fa/{suelo}/{aa}", "/coef/fv/{suelo}/{av}", "/barras", "/deriva", "/coef/r", "/search"]
    }

@app.get("/municipios/{nombre}")
def get_municipio(nombre: str):
    """Busca municipio - funciona con o sin acentos"""
    try:
        data = search_municipio(nombre)
        return data
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/coef/fa/{suelo}/{aa}")
def get_fa(suelo: str, aa: float):
    """Coeficiente Fa por tipo de suelo y Aa"""
    try:
        suelo_upper = suelo.upper()
        
        # Suelo F requiere estudio específico
        if suelo_upper == 'F':
            return {
                "suelo": "F",
                "aa": aa,
                "fa": None,
                "nota": "Suelo tipo F requiere estudio de sitio específico (NSR-10 A.2.4.4)",
                "referencia": "NSR-10 Tabla A.2.4-3"
            }
        
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/nsr10_coef_fa",
            params={"soil_type": f"eq.{suelo_upper}", "aa_value": f"eq.{aa}", "select": "fa"},
            headers=HEADERS,
            timeout=10
        )
        data = resp.json()
        if not data or isinstance(data, dict):
            return {"suelo": suelo, "aa": aa, "fa": None, "error": "Valor no encontrado. Aa válidos: 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50"}
        return {"suelo": suelo, "aa": aa, "fa": data[0]["fa"], "referencia": "NSR-10 Tabla A.2.4-3"}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/coef/fv/{suelo}/{av}")
def get_fv(suelo: str, av: float):
    """Coeficiente Fv por tipo de suelo y Av"""
    try:
        suelo_upper = suelo.upper()
        
        if suelo_upper == 'F':
            return {
                "suelo": "F",
                "av": av,
                "fv": None,
                "nota": "Suelo tipo F requiere estudio de sitio específico (NSR-10 A.2.4.4)",
                "referencia": "NSR-10 Tabla A.2.4-4"
            }
        
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/nsr10_coef_fv",
            params={"soil_type": f"eq.{suelo_upper}", "av_value": f"eq.{av}", "select": "fv"},
            headers=HEADERS,
            timeout=10
        )
        data = resp.json()
        if not data or isinstance(data, dict):
            return {"suelo": suelo, "av": av, "fv": None, "error": "Valor no encontrado. Av válidos: 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50"}
        return {"suelo": suelo, "av": av, "fv": data[0]["fv"], "referencia": "NSR-10 Tabla A.2.4-4"}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/barras")
def get_barras(designacion: Optional[str] = None):
    """Barras de refuerzo - propiedades"""
    try:
        params = {"select": "designacion,diametro_mm,area_mm2,masa_kg_m", "limit": "30", "order": "diametro_mm"}
        if designacion:
            params["designacion"] = f"ilike.*{designacion}*"
        resp = requests.get(f"{SUPABASE_URL}/rest/v1/nsr10_barras_refuerzo", params=params, headers=HEADERS, timeout=10)
        data = resp.json()
        return {"barras": data, "referencia": "NSR-10 Tabla C.3.5.3-1"}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/deriva")
def get_deriva():
    """Derivas máximas permitidas por sistema estructural"""
    try:
        resp = requests.get(f"{SUPABASE_URL}/rest/v1/nsr10_deriva_max", params={"select": "*"}, headers=HEADERS, timeout=10)
        data = resp.json()
        return {"derivas": data, "referencia": "NSR-10 Tabla A.6.4-1"}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/coef/r")
def get_coef_r(sistema: Optional[str] = None, capacidad: Optional[str] = None):
    """Coeficientes R₀, Ω₀, Cd por sistema estructural"""
    try:
        params = {"select": "sistema,capacidad_disipacion,r0,omega0,cd", "limit": "30"}
        
        if capacidad:
            params["capacidad_disipacion"] = f"eq.{capacidad.upper()}"
        
        if sistema:
            # Primero intentar con el término original (puede tener acentos)
            params["sistema"] = f"ilike.*{sistema}*"
            resp = requests.get(f"{SUPABASE_URL}/rest/v1/nsr10_coef_r", params=params, headers=HEADERS, timeout=10)
            data = resp.json()
            
            # Si no encuentra, traer todos y filtrar en Python
            if not data or len(data) == 0:
                del params["sistema"]
                resp = requests.get(f"{SUPABASE_URL}/rest/v1/nsr10_coef_r", params=params, headers=HEADERS, timeout=10)
                all_data = resp.json()
                
                if isinstance(all_data, list):
                    sistema_norm = normalize_text(sistema).lower()
                    data = [
                        s for s in all_data 
                        if sistema_norm in normalize_text(s.get('sistema', '')).lower()
                    ]
        else:
            resp = requests.get(f"{SUPABASE_URL}/rest/v1/nsr10_coef_r", params=params, headers=HEADERS, timeout=10)
            data = resp.json()
        
        return {"sistemas": data, "referencia": "NSR-10 Tabla A.3-3"}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/search")
def search_fts(q: str, limit: int = 10):
    """Búsqueda Full-Text en secciones de la NSR-10 (12,789 secciones indexadas)"""
    try:
        # Usar FTS con Postgres full-text search
        # El search_vector está indexado con GIN para búsquedas rápidas
        
        # Preparar query para FTS: convertir espacios en AND
        terms = q.strip().split()
        if len(terms) > 1:
            # Múltiples términos: usar websearch_to_tsquery para mejor flexibilidad
            fts_query = ' & '.join(terms)
        else:
            fts_query = terms[0] if terms else q
        
        # PostgREST soporta fts() para búsqueda full-text
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/nsr10_secciones",
            params={
                "search_vector": f"fts(spanish).{fts_query}",
                "select": "seccion,titulo,contenido",
                "limit": str(limit),
                "order": "seccion"
            },
            headers=HEADERS,
            timeout=15
        )
        results = resp.json()
        
        # Si FTS no encuentra, fallback a ILIKE
        if not results or (isinstance(results, list) and len(results) == 0):
            resp = requests.get(
                f"{SUPABASE_URL}/rest/v1/nsr10_secciones",
                params={"contenido": f"ilike.*{q}*", "select": "seccion,titulo,contenido", "limit": str(limit)},
                headers=HEADERS,
                timeout=15
            )
            results = resp.json()
            method = "ilike"
        else:
            method = "fts"
        
        # Truncar contenido para respuesta más ligera
        if isinstance(results, list):
            for r in results:
                if r.get('contenido') and len(r['contenido']) > 300:
                    r['contenido'] = r['contenido'][:300] + '...'
        
        return {
            "query": q,
            "method": method,
            "count": len(results) if isinstance(results, list) else 0,
            "results": results
        }
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/health")
def health():
    """Health check"""
    return {"status": "healthy", "version": "1.1.0"}
