#!/usr/bin/env python3
"""
NSR-10 MCP Server
Model Context Protocol server para consultas de la NSR-10 Colombia
"""
import os
import json
import asyncio
from typing import Any
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Config
SUPABASE_URL = os.environ.get('STRUOS_SUPABASE_URL')
SUPABASE_KEY = os.environ.get('STRUOS_SUPABASE_SERVICE_ROLE')

HEADERS = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json'
}

# Create server
server = Server("nsr10-server")

async def query_supabase(table: str, params: dict = None) -> list:
    """Query Supabase REST API"""
    async with httpx.AsyncClient() as client:
        url = f"{SUPABASE_URL}/rest/v1/{table}"
        resp = await client.get(url, params=params or {}, headers=HEADERS)
        if resp.status_code == 200:
            return resp.json()
        return {"error": resp.text}

@server.list_tools()
async def list_tools() -> list[Tool]:
    """Lista de herramientas disponibles"""
    return [
        Tool(
            name="parametros_sismicos",
            description="Obtiene parámetros sísmicos (Aa, Av, zona) para un municipio de Colombia",
            inputSchema={
                "type": "object",
                "properties": {
                    "municipio": {"type": "string", "description": "Nombre del municipio (ej: Bogotá, Medellín, Cali)"}
                },
                "required": ["municipio"]
            }
        ),
        Tool(
            name="coeficiente_sitio",
            description="Obtiene coeficientes Fa y Fv según tipo de suelo y valores Aa/Av",
            inputSchema={
                "type": "object",
                "properties": {
                    "tipo_suelo": {"type": "string", "description": "Tipo de suelo: A, B, C, D, E o F"},
                    "aa": {"type": "number", "description": "Valor de Aa (0.05 a 0.50)"},
                    "av": {"type": "number", "description": "Valor de Av (0.05 a 0.50)"}
                },
                "required": ["tipo_suelo", "aa", "av"]
            }
        ),
        Tool(
            name="coeficiente_r",
            description="Obtiene coeficientes R₀, Ω₀ y Cd para un sistema estructural",
            inputSchema={
                "type": "object",
                "properties": {
                    "sistema": {"type": "string", "description": "Descripción del sistema (ej: pórticos, muros, dual)"},
                    "capacidad": {"type": "string", "enum": ["DES", "DMO", "DMI"], "description": "Capacidad de disipación"}
                },
                "required": ["sistema"]
            }
        ),
        Tool(
            name="coeficiente_importancia",
            description="Obtiene el coeficiente de importancia I según el grupo de uso",
            inputSchema={
                "type": "object",
                "properties": {
                    "grupo": {"type": "string", "enum": ["I", "II", "III", "IV"], "description": "Grupo de uso de la edificación"}
                },
                "required": ["grupo"]
            }
        ),
        Tool(
            name="barras_refuerzo",
            description="Obtiene propiedades de barras de refuerzo (área, diámetro, peso)",
            inputSchema={
                "type": "object",
                "properties": {
                    "designacion": {"type": "string", "description": "Designación de la barra (ej: No.4, No.5, 16M)"}
                },
                "required": ["designacion"]
            }
        ),
        Tool(
            name="cargas_vivas",
            description="Obtiene cargas vivas según uso de la edificación",
            inputSchema={
                "type": "object",
                "properties": {
                    "uso": {"type": "string", "description": "Tipo de uso (ej: oficinas, residencial, educativo, hospitalario)"}
                },
                "required": ["uso"]
            }
        ),
        Tool(
            name="deriva_maxima",
            description="Obtiene la deriva máxima permitida según el sistema estructural",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="recubrimientos",
            description="Obtiene recubrimientos mínimos para elementos de concreto",
            inputSchema={
                "type": "object",
                "properties": {
                    "elemento": {"type": "string", "description": "Tipo de elemento (vigas, columnas, losas, etc.)"}
                }
            }
        ),
        Tool(
            name="perfiles_acero",
            description="Obtiene propiedades de perfiles de acero estructural",
            inputSchema={
                "type": "object",
                "properties": {
                    "perfil": {"type": "string", "description": "Designación del perfil (ej: W12x40, W8x31)"}
                },
                "required": ["perfil"]
            }
        ),
        Tool(
            name="consulta_sql",
            description="Consulta directa a cualquier tabla de la NSR-10. Tablas disponibles: nsr10_municipios, nsr10_coef_fa, nsr10_coef_fv, nsr10_coef_r, nsr10_coef_importancia, nsr10_barras_refuerzo, nsr10_cargas_vivas, nsr10_cargas_muertas, nsr10_recubrimientos, nsr10_deriva_max, nsr10_acero_perfiles, nsr10_madera_esfuerzos_adm, nsr10_guadua_propiedades, nsr10_geotecnia_fs, nsr10_incendio_resistencia_elementos, y 240+ más",
            inputSchema={
                "type": "object",
                "properties": {
                    "tabla": {"type": "string", "description": "Nombre de la tabla (ej: nsr10_municipios)"},
                    "filtros": {"type": "string", "description": "Filtros en formato Supabase (ej: municipio=eq.Bogotá)"},
                    "limite": {"type": "integer", "description": "Número máximo de resultados", "default": 20}
                },
                "required": ["tabla"]
            }
        ),
        Tool(
            name="buscar_seccion",
            description="Busca secciones de la NSR-10 por texto",
            inputSchema={
                "type": "object",
                "properties": {
                    "texto": {"type": "string", "description": "Texto a buscar en las secciones"},
                    "titulo": {"type": "string", "description": "Filtrar por título (A, B, C, D, E, F, G, H, I, J, K)"}
                },
                "required": ["texto"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Ejecuta una herramienta"""
    
    if name == "parametros_sismicos":
        municipio = arguments.get("municipio", "")
        data = await query_supabase("nsr10_municipios", {
            "municipio": f"ilike.*{municipio}*",
            "select": "municipio,departamento,aa,av,zona_amenaza"
        })
        result = json.dumps(data, indent=2, ensure_ascii=False)
        
    elif name == "coeficiente_sitio":
        tipo = arguments.get("tipo_suelo", "").upper()
        aa = arguments.get("aa", 0.25)
        av = arguments.get("av", 0.25)
        
        fa_data = await query_supabase("nsr10_coef_fa", {
            "soil_type": f"eq.{tipo}",
            "aa_value": f"eq.{aa}",
            "select": "fa"
        })
        fv_data = await query_supabase("nsr10_coef_fv", {
            "soil_type": f"eq.{tipo}",
            "av_value": f"eq.{av}",
            "select": "fv"
        })
        
        fa = fa_data[0]["fa"] if fa_data and isinstance(fa_data, list) else "No encontrado"
        fv = fv_data[0]["fv"] if fv_data and isinstance(fv_data, list) else "No encontrado"
        
        result = json.dumps({"tipo_suelo": tipo, "Aa": aa, "Av": av, "Fa": fa, "Fv": fv}, indent=2)
        
    elif name == "coeficiente_r":
        sistema = arguments.get("sistema", "")
        capacidad = arguments.get("capacidad", "")
        
        params = {"sistema": f"ilike.*{sistema}*", "select": "sistema,capacidad_disipacion,r0,omega0,cd"}
        if capacidad:
            params["capacidad_disipacion"] = f"eq.{capacidad}"
            
        data = await query_supabase("nsr10_coef_r", params)
        result = json.dumps(data, indent=2, ensure_ascii=False)
        
    elif name == "coeficiente_importancia":
        grupo = arguments.get("grupo", "")
        data = await query_supabase("nsr10_coef_importancia", {
            "grupo_uso": f"eq.{grupo}",
            "select": "*"
        })
        if not data:
            data = await query_supabase("nsr10_coef_importancia", {"select": "*"})
        result = json.dumps(data, indent=2, ensure_ascii=False)
        
    elif name == "barras_refuerzo":
        designacion = arguments.get("designacion", "")
        data = await query_supabase("nsr10_barras_refuerzo", {
            "designacion": f"ilike.*{designacion}*",
            "select": "designacion,diametro_mm,area_mm2,masa_kg_m,tabla_ref"
        })
        result = json.dumps(data, indent=2, ensure_ascii=False)
        
    elif name == "cargas_vivas":
        uso = arguments.get("uso", "")
        data = await query_supabase("nsr10_cargas_vivas", {
            "or": f"(categoria.ilike.*{uso}*,uso.ilike.*{uso}*)",
            "select": "categoria,uso,carga_kn_m2,tabla_ref",
            "limit": "20"
        })
        result = json.dumps(data, indent=2, ensure_ascii=False)
        
    elif name == "deriva_maxima":
        data = await query_supabase("nsr10_deriva_max", {"select": "*"})
        result = json.dumps(data, indent=2, ensure_ascii=False)
        
    elif name == "recubrimientos":
        elemento = arguments.get("elemento", "")
        params = {"select": "condicion,recubrimiento_reforzado_mm,recubrimiento_preesforzado_mm,tabla_ref"}
        if elemento:
            params["condicion"] = f"ilike.*{elemento}*"
        data = await query_supabase("nsr10_recubrimientos", params)
        result = json.dumps(data, indent=2, ensure_ascii=False)
        
    elif name == "perfiles_acero":
        perfil = arguments.get("perfil", "")
        data = await query_supabase("nsr10_acero_perfiles", {
            "designacion": f"ilike.*{perfil}*",
            "select": "*"
        })
        result = json.dumps(data, indent=2, ensure_ascii=False)
        
    elif name == "consulta_sql":
        tabla = arguments.get("tabla", "")
        filtros = arguments.get("filtros", "")
        limite = arguments.get("limite", 20)
        
        params = {"select": "*", "limit": str(limite)}
        if filtros:
            for filtro in filtros.split("&"):
                if "=" in filtro:
                    key, value = filtro.split("=", 1)
                    params[key] = value
                    
        data = await query_supabase(tabla, params)
        result = json.dumps(data, indent=2, ensure_ascii=False)
        
    elif name == "buscar_seccion":
        texto = arguments.get("texto", "")
        titulo = arguments.get("titulo", "")
        
        params = {
            "contenido": f"ilike.*{texto}*",
            "select": "titulo,seccion,contenido",
            "limit": "10"
        }
        if titulo:
            params["titulo"] = f"eq.{titulo}"
            
        data = await query_supabase("nsr10_secciones", params)
        result = json.dumps(data, indent=2, ensure_ascii=False)
        
    else:
        result = json.dumps({"error": f"Herramienta {name} no encontrada"})
    
    return [TextContent(type="text", text=result)]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
