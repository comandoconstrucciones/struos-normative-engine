#!/usr/bin/env python3
"""
NSR-10 MCP Server (FastMCP).

Expone 8 tools sobre la API pública https://struos-api.vercel.app para que
Claude (Desktop o Code) consulte la NSR-10 Colombia y otras normas indexadas.

Logs a stderr — stdout es sagrado para JSON-RPC en stdio transport.

Variables de entorno:
  STRUOS_API_URL  default https://struos-api.vercel.app
  STRUOS_API_KEY  opcional; se envía como X-API-Key si está seteada
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

# stdout está reservado para JSON-RPC. Logging a stderr.
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("nsr10-mcp")

API_URL = os.environ.get("STRUOS_API_URL", "https://struos-api.vercel.app").rstrip("/")
API_KEY = os.environ.get("STRUOS_API_KEY")

mcp = FastMCP("nsr10")


async def _api_get(endpoint: str, params: dict | None = None) -> dict | list:
    headers = {"X-API-Key": API_KEY} if API_KEY else {}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{API_URL}{endpoint}", params=params or {}, headers=headers)
        if resp.status_code == 200:
            return resp.json()
        log.error("API GET %s failed: %s %s", endpoint, resp.status_code, resp.text[:200])
        return {"error": resp.text, "status": resp.status_code}


async def _api_post(endpoint: str, body: dict) -> dict:
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(f"{API_URL}{endpoint}", json=body, headers=headers)
        if resp.status_code == 200:
            return resp.json()
        log.error("API POST %s failed: %s %s", endpoint, resp.status_code, resp.text[:200])
        return {"error": resp.text, "status": resp.status_code}


@mcp.tool()
async def parametros_sismicos(municipio: str) -> str:
    """Obtiene parámetros sísmicos (Aa, Av, zona de amenaza) para un municipio colombiano.

    Ej: parametros_sismicos("Bogotá") → Aa=0.15, Av=0.20, zona Intermedia.
    Fuente: NSR-10 Título A, Apéndice A-4.
    """
    data = await _api_get(f"/municipios/{municipio}")
    if isinstance(data, list) and data:
        m = data[0]
        return (
            f"Parámetros sísmicos para {m.get('municipio', municipio)}:\n"
            f"- Departamento: {m.get('departamento', 'N/A')}\n"
            f"- Aa (aceleración pico): {m.get('aa', 'N/A')}\n"
            f"- Av (velocidad pico): {m.get('av', 'N/A')}\n"
            f"- Zona de amenaza sísmica: {m.get('zona_amenaza', 'N/A')}\n\n"
            "Fuente: NSR-10 Título A, Apéndice A-4"
        )
    return f"No se encontró el municipio '{municipio}'. Intenta con el nombre exacto."


@mcp.tool()
async def coeficiente_fa(tipo_suelo: str, aa: float) -> str:
    """Coeficiente de amplificación Fa por tipo de suelo (A-F) y Aa (0.05 a 0.50).

    Fuente: NSR-10 Tabla A.2.4-3.
    """
    tipo = tipo_suelo.upper()
    data = await _api_get(f"/coef/fa/{tipo}/{aa}")
    fa = data.get("fa") if isinstance(data, dict) else None
    if fa is not None:
        return f"Coeficiente Fa:\n- Tipo de suelo: {tipo}\n- Aa: {aa}\n- Fa = {fa}\n\nFuente: NSR-10 Tabla A.2.4-3"
    return f"No se encontró Fa para suelo {tipo} con Aa={aa}. Valores válidos de Aa: 0.05..0.50 en pasos de 0.05"


@mcp.tool()
async def coeficiente_fv(tipo_suelo: str, av: float) -> str:
    """Coeficiente de amplificación Fv por tipo de suelo (A-F) y Av (0.05 a 0.50).

    Fuente: NSR-10 Tabla A.2.4-4.
    """
    tipo = tipo_suelo.upper()
    data = await _api_get(f"/coef/fv/{tipo}/{av}")
    fv = data.get("fv") if isinstance(data, dict) else None
    if fv is not None:
        return f"Coeficiente Fv:\n- Tipo de suelo: {tipo}\n- Av: {av}\n- Fv = {fv}\n\nFuente: NSR-10 Tabla A.2.4-4"
    return f"No se encontró Fv para suelo {tipo} con Av={av}. Valores válidos de Av: 0.05..0.50 en pasos de 0.05"


@mcp.tool()
async def coeficiente_r(sistema: str, capacidad: str | None = None) -> str:
    """R₀, Ω₀, Cd para un sistema estructural (ej: 'pórticos', 'muros', 'dual').

    Opcional capacidad: DES (especial), DMO (moderada), DMI (mínima).
    Fuente: NSR-10 Tabla A.3-3.
    """
    params: dict[str, Any] = {"sistema": sistema}
    if capacidad:
        params["capacidad"] = capacidad
    data = await _api_get("/coef/r", params)
    sistemas = data.get("sistemas") if isinstance(data, dict) else data
    if isinstance(sistemas, list) and sistemas:
        lines = ["Coeficientes de disipación de energía:\n"]
        for item in sistemas[:5]:
            lines.append(f"**{item.get('sistema', 'N/A')}** ({item.get('capacidad_disipacion', 'N/A')}):")
            lines.append(f"  - R₀ = {item.get('r0', 'N/A')}")
            lines.append(f"  - Ω₀ = {item.get('omega0', 'N/A')}")
            lines.append(f"  - Cd = {item.get('cd', 'N/A')}\n")
        lines.append("Fuente: NSR-10 Tabla A.3-3")
        return "\n".join(lines)
    return f"No se encontraron sistemas con '{sistema}'"


@mcp.tool()
async def barras_refuerzo(designacion: str | None = None) -> str:
    """Propiedades de barras corrugadas (diámetro, área, masa).

    Sin argumento → lista todas las barras. Con designación (ej: '5') → filtra.
    Fuente: NSR-10 Tabla C.3.5.3-1.
    """
    params = {"designacion": designacion} if designacion else {}
    data = await _api_get("/barras", params)
    barras = data.get("barras") if isinstance(data, dict) else data
    if isinstance(barras, list) and barras:
        lines = ["Barras de refuerzo:\n"]
        lines.append("| Designación | Ø (mm) | Área (mm²) | Masa (kg/m) |")
        lines.append("|-------------|--------|------------|-------------|")
        for b in barras[:10]:
            lines.append(
                f"| {b.get('designacion', '')} | {b.get('diametro_mm', '')} | "
                f"{b.get('area_mm2', '')} | {b.get('masa_kg_m', '')} |"
            )
        lines.append("\nFuente: NSR-10 Tabla C.3.5.3-1")
        return "\n".join(lines)
    return "No se encontraron barras"


@mcp.tool()
async def deriva_maxima() -> str:
    """Derivas máximas permitidas por sistema estructural (NSR-10 Tabla A.6.4-1)."""
    data = await _api_get("/deriva")
    derivas = data.get("derivas") if isinstance(data, dict) else data
    if isinstance(derivas, list) and derivas:
        lines = ["Derivas máximas permitidas (NSR-10 Tabla A.6.4-1):\n"]
        lines.append("| Sistema estructural | Notas |")
        lines.append("|---------------------|-------|")
        for d in derivas:
            lines.append(f"| {d.get('sistema', '')} | {d.get('notas', '')} |")
        return "\n".join(lines)
    return "Error obteniendo derivas"


@mcp.tool()
async def buscar_seccion(texto: str, limite: int = 10) -> str:
    """Búsqueda full-text en las 12,789 secciones de la NSR-10 (FTS PostgreSQL)."""
    data = await _api_get("/search", {"q": texto, "limit": limite})
    results = data.get("results", []) if isinstance(data, dict) else []
    if results:
        lines = [f"Resultados para '{texto}':\n"]
        for r in results[:5]:
            lines.append(f"**{r.get('titulo', '')} - {r.get('seccion', '')}**")
            lines.append(f"{(r.get('contenido') or '')[:200]}...\n")
        return "\n".join(lines)
    return f"No se encontraron secciones con '{texto}'"


@mcp.tool()
async def preguntar_nsr10(
    pregunta: str,
    folder: str = "NSR-10",
    top_k: int = 8,
) -> str:
    """RAG vectorial: pregunta natural sobre la NSR-10 con citas a fragmentos reales.

    Pipeline: embedding OpenAI → pgvector cosine search sobre 57,293 chunks → LLM cita [1], [2].

    Args:
        pregunta: Pregunta técnica en español.
        folder: Dominio a consultar. Uno de: NSR-10, "AISC Design Guides",
                Catálogos, Manuales, "Normas técnicas". Default NSR-10.
        top_k: Fragmentos a recuperar (1-20). Default 8.
    """
    data = await _api_post("/ask", {"query": pregunta, "folder": folder, "context_limit": top_k})
    if "error" in data:
        return f"Error del API: {data.get('error', '?')} (status {data.get('status', '?')})"

    answer = data.get("answer", "")
    sources = data.get("sources", [])
    lines = [answer, "", "**Fuentes:**"]
    for s in sources:
        lines.append(
            f"- [{s.get('n')}] {s.get('filename', '?')} p.{s.get('page', '?')} "
            f"(similitud {s.get('similarity', 0):.3f})"
        )
    if data.get("cached"):
        lines.append("\n_(respuesta cacheada)_")
    return "\n".join(lines)


def main() -> None:
    log.info("Starting nsr10 MCP server, API=%s, key_set=%s", API_URL, bool(API_KEY))
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
