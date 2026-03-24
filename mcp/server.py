#!/usr/bin/env python3
"""
NSR-10 MCP Server
Model Context Protocol server para consultas de la NSR-10 Colombia
Usa la API pública: https://struos-api.vercel.app
"""
import json
import asyncio
from typing import Any
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Config - API pública (no requiere keys)
API_URL = "https://struos-api.vercel.app"

# Create server
server = Server("nsr10-server")

async def api_get(endpoint: str, params: dict = None) -> dict:
    """Query NSR-10 API"""
    async with httpx.AsyncClient(timeout=30) as client:
        url = f"{API_URL}{endpoint}"
        resp = await client.get(url, params=params or {})
        if resp.status_code == 200:
            return resp.json()
        return {"error": resp.text, "status": resp.status_code}

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
            name="coeficiente_fa",
            description="Obtiene coeficiente Fa según tipo de suelo y valor Aa",
            inputSchema={
                "type": "object",
                "properties": {
                    "tipo_suelo": {"type": "string", "description": "Tipo de suelo: A, B, C, D, E o F"},
                    "aa": {"type": "number", "description": "Valor de Aa (0.05 a 0.50)"}
                },
                "required": ["tipo_suelo", "aa"]
            }
        ),
        Tool(
            name="coeficiente_fv",
            description="Obtiene coeficiente Fv según tipo de suelo y valor Av",
            inputSchema={
                "type": "object",
                "properties": {
                    "tipo_suelo": {"type": "string", "description": "Tipo de suelo: A, B, C, D, E o F"},
                    "av": {"type": "number", "description": "Valor de Av (0.05 a 0.50)"}
                },
                "required": ["tipo_suelo", "av"]
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
            name="barras_refuerzo",
            description="Obtiene propiedades de barras de refuerzo (área, diámetro, peso)",
            inputSchema={
                "type": "object",
                "properties": {
                    "designacion": {"type": "string", "description": "Designación de la barra (ej: No.4, No.5, 5, 16M)"}
                }
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
            name="buscar_seccion",
            description="Busca secciones de la NSR-10 por texto",
            inputSchema={
                "type": "object",
                "properties": {
                    "texto": {"type": "string", "description": "Texto a buscar en las secciones"},
                    "limite": {"type": "integer", "description": "Número máximo de resultados", "default": 10}
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
        data = await api_get(f"/municipios/{municipio}")
        if isinstance(data, list) and data:
            m = data[0]
            result = f"""Parámetros sísmicos para {m.get('municipio', municipio)}:
- Departamento: {m.get('departamento', 'N/A')}
- Aa (aceleración pico): {m.get('aa', 'N/A')}
- Av (velocidad pico): {m.get('av', 'N/A')}
- Zona de amenaza sísmica: {m.get('zona_amenaza', 'N/A')}

Fuente: NSR-10 Título A, Apéndice A-4"""
        else:
            result = f"No se encontró el municipio '{municipio}'. Intenta con el nombre exacto."
        
    elif name == "coeficiente_fa":
        tipo = arguments.get("tipo_suelo", "D").upper()
        aa = arguments.get("aa", 0.25)
        data = await api_get(f"/coef/fa/{tipo}/{aa}")
        fa = data.get("fa")
        if fa:
            result = f"""Coeficiente Fa:
- Tipo de suelo: {tipo}
- Aa: {aa}
- Fa = {fa}

Fuente: NSR-10 Tabla A.2.4-3"""
        else:
            result = f"No se encontró Fa para suelo {tipo} con Aa={aa}. Valores válidos de Aa: 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50"
        
    elif name == "coeficiente_fv":
        tipo = arguments.get("tipo_suelo", "D").upper()
        av = arguments.get("av", 0.25)
        data = await api_get(f"/coef/fv/{tipo}/{av}")
        fv = data.get("fv")
        if fv:
            result = f"""Coeficiente Fv:
- Tipo de suelo: {tipo}
- Av: {av}
- Fv = {fv}

Fuente: NSR-10 Tabla A.2.4-4"""
        else:
            result = f"No se encontró Fv para suelo {tipo} con Av={av}. Valores válidos de Av: 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50"
        
    elif name == "coeficiente_r":
        sistema = arguments.get("sistema", "")
        capacidad = arguments.get("capacidad", "")
        params = {"sistema": sistema}
        if capacidad:
            params["capacidad"] = capacidad
        data = await api_get("/coef/r", params)
        
        if isinstance(data, list) and data:
            lines = ["Coeficientes de disipación de energía:\n"]
            for item in data[:5]:
                lines.append(f"**{item.get('sistema', 'N/A')}** ({item.get('capacidad_disipacion', 'N/A')}):")
                lines.append(f"  - R₀ = {item.get('r0', 'N/A')}")
                lines.append(f"  - Ω₀ = {item.get('omega0', 'N/A')}")
                lines.append(f"  - Cd = {item.get('cd', 'N/A')}\n")
            lines.append("Fuente: NSR-10 Tabla A.3-3")
            result = "\n".join(lines)
        else:
            result = f"No se encontraron sistemas con '{sistema}'"
        
    elif name == "barras_refuerzo":
        designacion = arguments.get("designacion", "")
        params = {"designacion": designacion} if designacion else {}
        data = await api_get("/barras", params)
        
        if isinstance(data, list) and data:
            lines = ["Barras de refuerzo:\n"]
            lines.append("| Designación | Ø (mm) | Área (mm²) | Masa (kg/m) |")
            lines.append("|-------------|--------|------------|-------------|")
            for b in data[:10]:
                lines.append(f"| {b.get('designacion', '')} | {b.get('diametro_mm', '')} | {b.get('area_mm2', '')} | {b.get('masa_kg_m', '')} |")
            lines.append("\nFuente: NSR-10 Tabla C.3.5.3-1")
            result = "\n".join(lines)
        else:
            result = "No se encontraron barras"
        
    elif name == "deriva_maxima":
        data = await api_get("/deriva")
        
        if isinstance(data, list) and data:
            lines = ["Derivas máximas permitidas (NSR-10 Tabla A.6.4-1):\n"]
            lines.append("| Sistema estructural | Deriva máx |")
            lines.append("|---------------------|------------|")
            for d in data:
                lines.append(f"| {d.get('sistema', '')} | {d.get('notas', '')} |")
            result = "\n".join(lines)
        else:
            result = "Error obteniendo derivas"
        
    elif name == "buscar_seccion":
        texto = arguments.get("texto", "")
        limite = arguments.get("limite", 10)
        data = await api_get("/search", {"q": texto, "limit": limite})
        
        results = data.get("results", [])
        if results:
            lines = [f"Resultados para '{texto}':\n"]
            for r in results[:5]:
                lines.append(f"**{r.get('titulo', '')} - {r.get('seccion', '')}**")
                contenido = r.get('contenido', '')[:200]
                lines.append(f"{contenido}...\n")
            result = "\n".join(lines)
        else:
            result = f"No se encontraron secciones con '{texto}'"
        
    else:
        result = f"Herramienta {name} no encontrada"
    
    return [TextContent(type="text", text=result)]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
