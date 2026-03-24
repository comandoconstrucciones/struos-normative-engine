#!/usr/bin/env python3
"""
NSR-10 API Server — FastAPI for Vercel Serverless
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import os
import requests

# Config
SUPABASE_URL = "https://vdakfewjadwaczulcmvj.supabase.co"
SERVICE_ROLE = os.environ.get('STRUOS_SUPABASE_SERVICE_ROLE', '')

HEADERS = {
    'apikey': SERVICE_ROLE,
    'Authorization': f'Bearer {SERVICE_ROLE}',
    'Content-Type': 'application/json'
}

app = FastAPI(title="NSR-10 API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "service": "NSR-10 Normative Engine",
        "version": "1.0.0",
        "status": "ok",
        "key_set": bool(SERVICE_ROLE),
        "endpoints": ["/municipios/{nombre}", "/coef/fa/{suelo}/{aa}", "/barras", "/deriva", "/coef/r"]
    }

@app.get("/debug")
def debug():
    """Debug endpoint"""
    return {
        "key_length": len(SERVICE_ROLE) if SERVICE_ROLE else 0,
        "key_prefix": SERVICE_ROLE[:10] if SERVICE_ROLE else "EMPTY",
        "url": SUPABASE_URL
    }

@app.get("/municipios/{nombre}")
def get_municipio(nombre: str):
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/nsr10_municipios",
            params={"municipio": f"ilike.*{nombre}*", "select": "municipio,departamento,aa,av,zona_amenaza"},
            headers=HEADERS,
            timeout=10
        )
        return resp.json()
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/coef/fa/{suelo}/{aa}")
def get_fa(suelo: str, aa: float):
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/nsr10_coef_fa",
            params={"soil_type": f"eq.{suelo.upper()}", "aa_value": f"eq.{aa}", "select": "fa"},
            headers=HEADERS,
            timeout=10
        )
        data = resp.json()
        if not data or isinstance(data, dict):
            return {"suelo": suelo, "aa": aa, "fa": None, "raw": data}
        return {"suelo": suelo, "aa": aa, "fa": data[0]["fa"]}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/coef/fv/{suelo}/{av}")
def get_fv(suelo: str, av: float):
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/nsr10_coef_fv",
            params={"soil_type": f"eq.{suelo.upper()}", "av_value": f"eq.{av}", "select": "fv"},
            headers=HEADERS,
            timeout=10
        )
        data = resp.json()
        if not data or isinstance(data, dict):
            return {"suelo": suelo, "av": av, "fv": None, "raw": data}
        return {"suelo": suelo, "av": av, "fv": data[0]["fv"]}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/barras")
def get_barras(designacion: Optional[str] = None):
    try:
        params = {"select": "designacion,diametro_mm,area_mm2,masa_kg_m", "limit": "30"}
        if designacion:
            params["designacion"] = f"ilike.*{designacion}*"
        resp = requests.get(f"{SUPABASE_URL}/rest/v1/nsr10_barras_refuerzo", params=params, headers=HEADERS, timeout=10)
        return resp.json()
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/deriva")
def get_deriva():
    try:
        resp = requests.get(f"{SUPABASE_URL}/rest/v1/nsr10_deriva_max", params={"select": "*"}, headers=HEADERS, timeout=10)
        return resp.json()
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/coef/r")
def get_coef_r(sistema: Optional[str] = None, capacidad: Optional[str] = None):
    try:
        params = {"select": "sistema,capacidad_disipacion,r0,omega0,cd", "limit": "30"}
        if sistema:
            params["sistema"] = f"ilike.*{sistema}*"
        if capacidad:
            params["capacidad_disipacion"] = f"eq.{capacidad}"
        resp = requests.get(f"{SUPABASE_URL}/rest/v1/nsr10_coef_r", params=params, headers=HEADERS, timeout=10)
        return resp.json()
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/search")
def search_fts(q: str, limit: int = 10):
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/nsr10_secciones",
            params={"contenido": f"ilike.*{q}*", "select": "titulo,seccion,contenido", "limit": str(limit)},
            headers=HEADERS,
            timeout=10
        )
        return {"query": q, "results": resp.json()}
    except Exception as e:
        raise HTTPException(500, str(e))
