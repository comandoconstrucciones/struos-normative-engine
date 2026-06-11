#!/usr/bin/env python3
"""
NSR-10 MCP Server (FastMCP).

Expone 19 tools sobre la API local: NSR-10 Colombia + biblioteca AISC/ACI.

Logs a stderr — stdout es sagrado para JSON-RPC en stdio transport.

Variables de entorno:
  STRUOS_API_URL  default http://127.0.0.1:8100 (struos-api local; Vercel fue retirado)
  STRUOS_API_KEY  opcional; se envía como X-API-Key si está seteada
  MCP_TRANSPORT   stdio (default) | sse | streamable-http
  MCP_HOST        127.0.0.1 (default)
  MCP_PORT        8101 (default)
"""
from __future__ import annotations

import asyncio
import logging
import math
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import httpx
from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("nsr10-mcp")

# Default: API local (struos-api.vercel.app fue retirado y responde 404)
API_URL = os.environ.get("STRUOS_API_URL", "http://127.0.0.1:8100").rstrip("/")
API_KEY = os.environ.get("STRUOS_API_KEY")

_host = os.environ.get("MCP_HOST", "127.0.0.1")
_port = int(os.environ.get("MCP_PORT", "8101"))
mcp = FastMCP("nsr10", host=_host, port=_port)

# --- Coeficientes de importancia NSR-10 Tabla A.2.5-1 ---
_GRUPO_I = {
    "I":   1.00,
    "II":  1.10,
    "III": 1.30,
    "IV":  1.50,
}

# --- HTTP helpers ---

# Timing por llamada a la API — mismo formato que el tool_timing.log del MCP Comando
_TIMING_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tool_timing.log")
_TIMING_LOG_MAX = 5 * 1024 * 1024  # rotación a 5MB


def _log_timing(metodo: str, endpoint: str, dur_s: float, status: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        if os.path.exists(_TIMING_LOG) and os.path.getsize(_TIMING_LOG) > _TIMING_LOG_MAX:
            os.replace(_TIMING_LOG, _TIMING_LOG + ".1")
        with open(_TIMING_LOG, "a") as f:
            f.write(f"[{ts}] {metodo} {endpoint} | {dur_s:.2f}s | {status}\n")
    except Exception as e:
        log.warning("no se pudo escribir timing log: %s", e)
    log.info("timing %s %s %.2fs %s", metodo, endpoint, dur_s, status)


# Cliente compartido — reusa conexiones (keep-alive) en vez de abrir una por llamada
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=httpx.Timeout(60, connect=10))
    return _client


async def _api_get(endpoint: str, params: dict | None = None) -> dict | list:
    headers = {"X-API-Key": API_KEY} if API_KEY else {}
    start = time.perf_counter()
    try:
        resp = await _get_client().get(
            f"{API_URL}{endpoint}", params=params or {}, headers=headers, timeout=30
        )
    except httpx.HTTPError as e:
        _log_timing("GET", endpoint, time.perf_counter() - start, "EXC")
        log.error("API GET %s → %s", endpoint, e)
        return {"error": f"API inaccesible: {e}", "status": 0}
    _log_timing("GET", endpoint, time.perf_counter() - start, str(resp.status_code))
    if resp.status_code == 200:
        return resp.json()
    log.error("API GET %s → %s", endpoint, resp.status_code)
    return {"error": resp.text, "status": resp.status_code}


async def _api_post(endpoint: str, body: dict) -> dict:
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    start = time.perf_counter()
    try:
        resp = await _get_client().post(
            f"{API_URL}{endpoint}", json=body, headers=headers, timeout=60
        )
    except httpx.HTTPError as e:
        _log_timing("POST", endpoint, time.perf_counter() - start, "EXC")
        log.error("API POST %s → %s", endpoint, e)
        return {"error": f"API inaccesible: {e}", "status": 0}
    _log_timing("POST", endpoint, time.perf_counter() - start, str(resp.status_code))
    if resp.status_code == 200:
        return resp.json()
    log.error("API POST %s → %s", endpoint, resp.status_code)
    return {"error": resp.text, "status": resp.status_code}


def _municipio_path(municipio: str) -> str:
    """Escapa el nombre para la URL (tildes, espacios, '/')."""
    return f"/municipios/{quote(municipio, safe='')}"


# --- Fórmulas NSR-10 (inline, sin importar src/) ---

def _round_step(value: float, step: float = 0.05) -> float:
    """Redondea al múltiplo de step más cercano (para tablas Fa/Fv)."""
    return round(round(value / step) * step, 10)

def _calc_sa(T: float, Aa: float, Fa: float, Av: float, Fv: float, I: float) -> float:
    """Sa(T) según NSR-10 A.2.6."""
    T0 = 0.1 * (Av * Fv) / (Aa * Fa)
    Tc = 0.48 * (Av * Fv) / (Aa * Fa)
    TL = 2.4 * Fv
    Sa_plat = 2.5 * Aa * Fa * I
    if T < T0:
        return 2.5 * Aa * Fa * I * (0.4 + 0.6 * T / T0)
    elif T <= Tc:
        return Sa_plat
    elif T <= TL:
        return 1.2 * Av * Fv * I / T
    else:
        return 1.2 * Av * Fv * TL * I / (T ** 2)


# ═══════════════════════════════════════════════════════════════
# TOOLS EXISTENTES (corregidos)
# ═══════════════════════════════════════════════════════════════

@mcp.tool()
async def parametros_sismicos(municipio: str) -> str:
    """Obtiene parámetros sísmicos (Aa, Av, zona de amenaza) para un municipio colombiano.

    Ej: parametros_sismicos("Bogotá") → Aa=0.15, Av=0.20, zona Intermedia.
    Fuente: NSR-10 Título A, Apéndice A-4.
    """
    data = await _api_get(_municipio_path(municipio))
    if isinstance(data, list) and data:
        m = data[0]
        return (
            f"Parámetros sísmicos — {m.get('municipio', municipio)} ({m.get('departamento', 'N/A')}):\n"
            f"- Aa (aceleración pico): {m.get('aa', 'N/A')}\n"
            f"- Av (velocidad pico):   {m.get('av', 'N/A')}\n"
            f"- Zona de amenaza:       {m.get('zona_amenaza', 'N/A')}\n\n"
            "Fuente: NSR-10 Título A, Apéndice A-4"
        )
    return f"Municipio '{municipio}' no encontrado. Verifica ortografía (ej: 'Medellín', 'Cali')."


@mcp.tool()
async def coeficiente_fa(tipo_suelo: str, aa: float) -> str:
    """Coeficiente de amplificación Fa por tipo de suelo (A-F) y Aa (0.05–0.50).

    Redondea Aa al múltiplo de 0.05 más cercano si no es exacto.
    Fuente: NSR-10 Tabla A.2.4-3.
    """
    tipo = tipo_suelo.upper()
    aa_r = _round_step(aa)
    aa_r = max(0.05, min(0.50, aa_r))
    data = await _api_get(f"/coef/fa/{tipo}/{aa_r}")
    fa = data.get("fa") if isinstance(data, dict) else None
    if fa is not None:
        nota = f" (Aa={aa} redondeado a {aa_r})" if abs(aa - aa_r) > 1e-9 else ""
        return f"Coeficiente Fa:\n- Suelo: {tipo}\n- Aa: {aa_r}{nota}\n- Fa = **{fa}**\n\nFuente: NSR-10 Tabla A.2.4-3"
    return f"No se encontró Fa para suelo {tipo} con Aa={aa_r}. Suelos válidos: A B C D E F."


@mcp.tool()
async def coeficiente_fv(tipo_suelo: str, av: float) -> str:
    """Coeficiente de amplificación Fv por tipo de suelo (A-F) y Av (0.05–0.50).

    Redondea Av al múltiplo de 0.05 más cercano si no es exacto.
    Fuente: NSR-10 Tabla A.2.4-4.
    """
    tipo = tipo_suelo.upper()
    av_r = _round_step(av)
    av_r = max(0.05, min(0.50, av_r))
    data = await _api_get(f"/coef/fv/{tipo}/{av_r}")
    fv = data.get("fv") if isinstance(data, dict) else None
    if fv is not None:
        nota = f" (Av={av} redondeado a {av_r})" if abs(av - av_r) > 1e-9 else ""
        return f"Coeficiente Fv:\n- Suelo: {tipo}\n- Av: {av_r}{nota}\n- Fv = **{fv}**\n\nFuente: NSR-10 Tabla A.2.4-4"
    return f"No se encontró Fv para suelo {tipo} con Av={av_r}. Suelos válidos: A B C D E F."


@mcp.tool()
async def coeficiente_r(sistema: str, capacidad: str | None = None) -> str:
    """R₀, Ω₀, Cd para un sistema estructural (ej: 'pórticos', 'muros', 'dual').

    Opcional capacidad: DES (especial), DMO (moderada), DMI (mínima).
    Fuente: NSR-10 Tabla A.3-3.
    """
    params: dict[str, Any] = {"sistema": sistema}
    if capacidad:
        params["capacidad"] = capacidad.upper()
    data = await _api_get("/coef/r", params)
    sistemas = data.get("sistemas") if isinstance(data, dict) else data
    if isinstance(sistemas, list) and sistemas:
        lines = [f"Coeficientes R para '{sistema}':\n"]
        for item in sistemas[:8]:
            lines.append(f"**{item.get('sistema', 'N/A')}**")
            lines.append(f"  Capacidad: {item.get('capacidad_disipacion', 'N/A')}")
            lines.append(f"  R₀ = {item.get('r0', 'N/A')} | Ω₀ = {item.get('omega0', 'N/A')} | Cd = {item.get('cd', 'N/A')}\n")
        lines.append("Fuente: NSR-10 Tabla A.3-3")
        return "\n".join(lines)
    return f"No se encontraron sistemas con '{sistema}'. Intenta: 'pórtico', 'muro', 'dual', 'mampostería'."


@mcp.tool()
async def barras_refuerzo(designacion: str | None = None) -> str:
    """Propiedades de barras corrugadas (diámetro, área, masa).

    Sin argumento → lista todas. Con designación (ej: '5', '8') → filtra.
    Fuente: NSR-10 Tabla C.3.5.3-1.
    """
    params = {"designacion": designacion} if designacion else {}
    data = await _api_get("/barras", params)
    barras = data.get("barras") if isinstance(data, dict) else data
    if isinstance(barras, list) and barras:
        lines = ["Barras de refuerzo (NSR-10 Tabla C.3.5.3-1):\n"]
        lines.append("| # | Ø (mm) | Área (mm²) | Masa (kg/m) |")
        lines.append("|---|--------|------------|-------------|")
        for b in barras:
            lines.append(
                f"| {b.get('designacion', '')} | {b.get('diametro_mm', '')} | "
                f"{b.get('area_mm2', '')} | {b.get('masa_kg_m', '')} |"
            )
        return "\n".join(lines)
    return "No se encontraron barras. Designaciones válidas: 2 3 4 5 6 7 8 9 10 11 14 18."


@mcp.tool()
async def deriva_maxima() -> str:
    """Derivas máximas permitidas por sistema estructural (NSR-10 Tabla A.6.4-1).

    Retorna el valor numérico de deriva máxima y el porcentaje por sistema.
    """
    data = await _api_get("/deriva")
    derivas = data.get("derivas") if isinstance(data, dict) else data
    if isinstance(derivas, list) and derivas:
        lines = ["Derivas máximas permitidas — NSR-10 Tabla A.6.4-1:\n"]
        lines.append("| Sistema estructural | Δmax | % |")
        lines.append("|---------------------|------|---|")
        for d in derivas:
            dmax = d.get("deriva_max", "N/A")
            try:
                pct = f"{float(dmax)*100:.1f}%"
            except (TypeError, ValueError):
                pct = "N/A"
            lines.append(f"| {d.get('sistema', '')} | {dmax} | {pct} |")
        lines.append("\nΔ = desplazamiento relativo de entrepiso / altura de entrepiso.")
        return "\n".join(lines)
    return "Error obteniendo derivas"


@mcp.tool()
async def buscar_seccion(texto: str, limite: int = 10) -> str:
    """Búsqueda full-text en las 12,789 secciones de la NSR-10.

    Retorna título, número de sección y extracto del contenido.
    """
    lim = max(1, min(limite, 20))
    data = await _api_get("/search", {"q": texto, "limit": lim})
    results = data.get("results", []) if isinstance(data, dict) else []
    if results:
        lines = [f"Resultados NSR-10 para '{texto}' ({len(results)} encontrados):\n"]
        for r in results:
            contenido = (r.get("contenido") or "").strip()
            extracto = contenido[:500] + ("..." if len(contenido) > 500 else "")
            lines.append(f"**{r.get('seccion', '')} — {r.get('titulo', '')}**")
            lines.append(f"{extracto}\n")
        return "\n".join(lines)
    return f"Sin resultados para '{texto}'. Intenta términos más simples (ej: 'deriva', 'cortante', 'refuerzo')."


@mcp.tool()
async def preguntar_nsr10(
    pregunta: str,
    folder: str = "NSR-10",
    top_k: int = 8,
) -> str:
    """RAG vectorial: pregunta en lenguaje natural sobre normas técnicas con citas a fragmentos reales.

    Pipeline: embedding OpenAI → búsqueda coseno en +65,000 chunks → respuesta citada [1][2]...

    Args:
        pregunta: Pregunta técnica en español.
        folder: Dominio donde buscar. Opciones:
            - "NSR-10" (default): reglamento colombiano completo (Títulos A-K)
            - "AISC Design Guides": 36 Design Guides AISC (DG01-DG36)
            - "AISC": especificaciones 360-16, 341, 358
            - "ACI": ACI 318-19 y 318-25 (concreto estructural)
            - "AWS": AWS D1.1-2020 (soldadura estructural)
            - "AASHTO": AASHTO LRFD 2021 (puentes)
            - "Catálogos": Colmena, Steckler, Fajobe, Gerdau
            - "Manuales": SDI, Eurobuild, Superboard, Metaldeck
            - "Normas técnicas": FEMA, ATC-40, ASTM A36/A572, Decreto 523/2010
            - "Normas Latinoamerica": NCh433, E.030 Perú, NTC México, CIRSOC
            - "Normas Internacionales": AS 1170, KDS, SANS, TBDY Turquía
            - "Leyes Colombia": Ley 400, Ley 1796, Decreto 945
            - "Codigo Colombiano Puentes": CCP-14
        top_k: Fragmentos a recuperar (1-20). Default 8.
    """
    top_k = max(1, min(top_k, 20))
    data = await _api_post("/ask", {"query": pregunta, "folder": folder, "context_limit": top_k})
    if "error" in data:
        return f"Error del API: {data.get('error', '?')} (status {data.get('status', '?')})"
    answer = data.get("answer", "")
    sources = data.get("sources", [])
    lines = [answer, "", "**Fuentes:**"]
    for s in sources:
        lines.append(
            f"- [{s.get('n')}] {s.get('filename', '?')} p.{s.get('page', '?')} "
            f"(sim {s.get('similarity', 0):.3f})"
        )
    if data.get("cached"):
        lines.append("\n_(respuesta cacheada)_")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# TOOLS NUEVOS
# ═══════════════════════════════════════════════════════════════

@mcp.tool()
async def espectro_diseno(
    municipio: str,
    tipo_suelo: str,
    grupo_uso: str = "I",
) -> str:
    """Calcula el espectro de diseño sísmico NSR-10 completo para un municipio y tipo de suelo.

    Obtiene Aa/Av del municipio, Fa/Fv de la tabla de suelos, y calcula:
    T0, Tc, TL, Sa en períodos clave (0, 0.1, 0.2, 0.5, 1.0, 1.5, 2.0, 3.0 s).

    Args:
        municipio:  Nombre del municipio colombiano (ej: "Medellín").
        tipo_suelo: Tipo NSR-10 A/B/C/D/E/F (ej: "D").
        grupo_uso:  Grupo de uso I/II/III/IV (default I). Afecta coef. de importancia I.

    Fuente: NSR-10 A.2.6.
    """
    grupo = grupo_uso.upper()
    if grupo not in _GRUPO_I:
        return f"Grupo de uso '{grupo_uso}' inválido. Opciones: I, II, III, IV (Tabla A.2.5-1)."
    I_coef = _GRUPO_I[grupo]
    suelo = tipo_suelo.upper()

    # 1. Parámetros sísmicos del municipio
    mun_data = await _api_get(_municipio_path(municipio))
    if not isinstance(mun_data, list) or not mun_data:
        if isinstance(mun_data, dict) and "error" in mun_data:
            return f"Error consultando la API: {mun_data['error']}"
        return f"Municipio '{municipio}' no encontrado."
    m = mun_data[0]
    if m.get("aa") is None or m.get("av") is None:
        return f"El municipio '{municipio}' no tiene Aa/Av registrados en la base."
    Aa, Av = float(m["aa"]), float(m["av"])
    zona = m.get("zona_amenaza", "N/A")

    # 2. Fa y Fv (en paralelo)
    aa_r = max(0.05, min(0.50, _round_step(Aa)))
    av_r = max(0.05, min(0.50, _round_step(Av)))
    fa_data, fv_data = await asyncio.gather(
        _api_get(f"/coef/fa/{suelo}/{aa_r}"),
        _api_get(f"/coef/fv/{suelo}/{av_r}"),
    )
    Fa = fa_data.get("fa") if isinstance(fa_data, dict) else None
    Fv = fv_data.get("fv") if isinstance(fv_data, dict) else None
    if Fa is None or Fv is None:
        return f"No se encontraron Fa/Fv para suelo {suelo}. Suelos válidos: A B C D E F."

    Fa, Fv = float(Fa), float(Fv)

    # 3. Períodos característicos
    T0 = round(0.1 * (Av * Fv) / (Aa * Fa), 4)
    Tc = round(0.48 * (Av * Fv) / (Aa * Fa), 4)
    TL = round(2.4 * Fv, 4)
    Sa_max = round(2.5 * Aa * Fa * I_coef, 4)

    # 4. Sa en períodos clave
    periodos = [0.0, T0, Tc, 0.5, 1.0, 1.5, 2.0, TL, 3.0]
    periodos = sorted(set(round(t, 3) for t in periodos if t >= 0))

    lines = [
        f"## Espectro de Diseño NSR-10",
        f"**Municipio:** {m.get('municipio', municipio)} | **Zona:** {zona}",
        f"**Suelo:** {suelo} | **Grupo uso:** {grupo} (I = {I_coef})",
        "",
        "### Parámetros sísmicos",
        f"| Parámetro | Valor |",
        f"|-----------|-------|",
        f"| Aa        | {Aa}  |",
        f"| Av        | {Av}  |",
        f"| Fa        | {Fa}  |",
        f"| Fv        | {Fv}  |",
        f"| Aa×Fa     | {round(Aa*Fa, 4)} |",
        f"| Av×Fv     | {round(Av*Fv, 4)} |",
        "",
        "### Períodos característicos",
        f"| Período | Valor (s) |",
        f"|---------|-----------|",
        f"| T0      | {T0}      |",
        f"| Tc      | {Tc}      |",
        f"| TL      | {TL}      |",
        "",
        f"**Sa meseta (T0 a Tc):** {Sa_max} g",
        "",
        "### Sa(T) en períodos clave",
        "| T (s) | Sa (g) | Zona espectro |",
        "|-------|--------|---------------|",
    ]

    for T in periodos:
        Sa = round(_calc_sa(T, Aa, Fa, Av, Fv, I_coef), 4)
        if T < T0:
            zona_esp = "Rampa (0 → T0)"
        elif T <= Tc:
            zona_esp = "Meseta (T0 → Tc)"
        elif T <= TL:
            zona_esp = "Desc. vel. cte (Tc → TL)"
        else:
            zona_esp = "Desc. desp. cte (> TL)"
        lines.append(f"| {T:.3f} | {Sa} | {zona_esp} |")

    lines += ["", "Fuente: NSR-10 A.2.6 — Fórmulas A.2.6-1 a A.2.6-4"]
    return "\n".join(lines)


@mcp.tool()
async def cortante_basal(
    municipio: str,
    tipo_suelo: str,
    sistema: str,
    T: float,
    W: float,
    grupo_uso: str = "I",
    capacidad: str = "DES",
) -> str:
    """Calcula el cortante basal de diseño sísmico V = Sa(T) × I / R₀ × W.

    Obtiene automáticamente Aa, Av, Fa, Fv y R₀ del sistema estructural.

    Args:
        municipio:  Municipio colombiano (ej: "Bogotá").
        tipo_suelo: Tipo de suelo A/B/C/D/E/F.
        sistema:    Sistema estructural (ej: "pórtico", "muro", "dual").
        T:          Período fundamental de la estructura en segundos.
        W:          Peso sísmico total de la estructura en kN.
        grupo_uso:  Grupo de uso I/II/III/IV (default I).
        capacidad:  DES (especial), DMO (moderada), DMI (mínima). Default DES.

    Fuente: NSR-10 A.2.6 + A.3.3 + A.4.3.
    """
    grupo = grupo_uso.upper()
    if grupo not in _GRUPO_I:
        return f"Grupo de uso '{grupo_uso}' inválido. Opciones: I, II, III, IV (Tabla A.2.5-1)."
    I_coef = _GRUPO_I[grupo]
    suelo = tipo_suelo.upper()

    # 1. Parámetros sísmicos
    mun_data = await _api_get(_municipio_path(municipio))
    if not isinstance(mun_data, list) or not mun_data:
        if isinstance(mun_data, dict) and "error" in mun_data:
            return f"Error consultando la API: {mun_data['error']}"
        return f"Municipio '{municipio}' no encontrado."
    m = mun_data[0]
    if m.get("aa") is None or m.get("av") is None:
        return f"El municipio '{municipio}' no tiene Aa/Av registrados en la base."
    Aa, Av = float(m["aa"]), float(m["av"])

    # 2. Fa, Fv y coeficiente R (en paralelo)
    aa_r = max(0.05, min(0.50, _round_step(Aa)))
    av_r = max(0.05, min(0.50, _round_step(Av)))
    fa_data, fv_data, r_data = await asyncio.gather(
        _api_get(f"/coef/fa/{suelo}/{aa_r}"),
        _api_get(f"/coef/fv/{suelo}/{av_r}"),
        _api_get("/coef/r", {"sistema": sistema, "capacidad": capacidad.upper()}),
    )
    Fa = fa_data.get("fa") if isinstance(fa_data, dict) else None
    Fv = fv_data.get("fv") if isinstance(fv_data, dict) else None
    if Fa is None or Fv is None:
        return f"No se encontraron Fa/Fv para suelo {suelo}."
    Fa, Fv = float(Fa), float(Fv)

    # 3. Coeficiente R
    sistemas = r_data.get("sistemas") if isinstance(r_data, dict) else r_data
    if not isinstance(sistemas, list) or not sistemas:
        return f"Sistema '{sistema}' no encontrado. Intenta: 'pórtico', 'muro', 'dual'."
    s = sistemas[0]
    R0 = float(s.get("r0", 1))
    Omega0 = float(s.get("omega0", 1))
    Cd = float(s.get("cd", 1))
    nombre_sistema = s.get("sistema", sistema)

    # 4. Sa(T) y cortante
    Sa = _calc_sa(T, Aa, Fa, Av, Fv, I_coef)
    Cs = Sa / R0                        # coef. sísmico de diseño
    V = Cs * W                          # cortante basal (kN)

    # Mínimo NSR-10 A.4.3: Cs_min = 0.044 × Aa × Fa × I
    Cs_min = 0.044 * Aa * Fa * I_coef
    V_min = Cs_min * W
    gobernante = "mínimo NSR-10" if Cs < Cs_min else "espectro"
    Cs_final = max(Cs, Cs_min)
    V_final = Cs_final * W

    T0 = round(0.1 * (Av * Fv) / (Aa * Fa), 4)
    Tc = round(0.48 * (Av * Fv) / (Aa * Fa), 4)

    lines = [
        f"## Cortante Basal de Diseño — NSR-10",
        f"**Municipio:** {m.get('municipio', municipio)} | **Suelo:** {suelo} | **Grupo:** {grupo}",
        "",
        "### Datos de entrada",
        f"| Parámetro | Valor |",
        f"|-----------|-------|",
        f"| Aa        | {Aa}  |",
        f"| Av        | {Av}  |",
        f"| Fa        | {Fa}  |",
        f"| Fv        | {Fv}  |",
        f"| T0        | {T0} s |",
        f"| Tc        | {Tc} s |",
        f"| I (grupo {grupo}) | {I_coef} |",
        "",
        "### Sistema estructural",
        f"**{nombre_sistema}**",
        f"- R₀ = {R0} | Ω₀ = {Omega0} | Cd = {Cd}",
        "",
        "### Cálculo cortante basal",
        f"| | Valor |",
        f"|---|-------|",
        f"| T (período) | {T} s |",
        f"| Sa(T) | {round(Sa, 4)} g |",
        f"| Cs = Sa/R₀ | {round(Cs, 5)} |",
        f"| Cs_min (0.044·Aa·Fa·I) | {round(Cs_min, 5)} |",
        f"| **Cs gobernante ({gobernante})** | **{round(Cs_final, 5)}** |",
        f"| W | {W} kN |",
        f"| **V = Cs × W** | **{round(V_final, 2)} kN** |",
        "",
        "Fuente: NSR-10 A.2.6, A.3.3, A.4.3",
    ]
    return "\n".join(lines)


@mcp.tool()
async def verificar_deriva(
    sistema: str,
    deriva_calculada: float,
) -> str:
    """Verifica si la deriva de entrepiso calculada cumple NSR-10 Tabla A.6.4-1.

    Args:
        sistema:          Descripción del sistema (ej: "concreto", "mampostería", "madera").
        deriva_calculada: Deriva calculada como fracción (ej: 0.008 para 0.8%).

    Fuente: NSR-10 A.6.4.1.
    """
    data = await _api_get("/deriva")
    derivas = data.get("derivas") if isinstance(data, dict) else data
    if not isinstance(derivas, list):
        return "Error obteniendo tabla de derivas."

    # Buscar la fila más relevante por coincidencia de texto
    # (solo filas con deriva_max numérica y > 0 — evita float(None) y división por cero)
    sys_lower = sistema.lower()
    candidatos = []
    for d in derivas:
        try:
            dmax_val = float(d.get("deriva_max"))
        except (TypeError, ValueError):
            continue
        if dmax_val <= 0:
            continue
        nombre = (d.get("sistema") or "").lower()
        score = sum(1 for w in sys_lower.split() if w in nombre)
        candidatos.append((score, d))
    candidatos.sort(key=lambda x: -x[0])
    if not candidatos:
        return "La tabla de derivas no trajo filas con valores numéricos."

    lines = [f"## Verificación de Deriva — NSR-10 A.6.4.1"]
    lines.append(f"**Deriva calculada:** {deriva_calculada:.4f} ({deriva_calculada*100:.2f}%)\n")
    lines.append("### Resultado por sistema:")

    for score, d in candidatos[:3]:
        dmax = float(d["deriva_max"])
        cumple = deriva_calculada <= dmax
        estado = "✅ CUMPLE" if cumple else "❌ NO CUMPLE"
        margen = abs(dmax - deriva_calculada) / dmax * 100
        rel = "margen disponible" if cumple else "exceso"
        lines.append(
            f"\n**{d.get('sistema', '')}**\n"
            f"- Δmax = {dmax} ({dmax*100:.1f}%)\n"
            f"- {estado} — {rel}: {margen:.1f}%"
        )

    lines.append("\nFuente: NSR-10 Tabla A.6.4-1")
    return "\n".join(lines)


@mcp.tool()
async def cargas_vivas(uso: str | None = None, categoria: str | None = None) -> str:
    """Cargas vivas mínimas de diseño por uso y categoría — NSR-10 Tabla B.4.2.1-1.

    Args:
        uso:       Uso del espacio (ej: "Apartamentos", "Oficinas", "Bodegas").
        categoria: Categoría de ocupación (ej: "Residencial", "Comercio", "Fábricas").

    Sin argumentos → lista todas las cargas (32 filas).
    Fuente: NSR-10 Título B, Tabla B.4.2.1-1.
    """
    params: dict = {}
    if uso:
        params["uso"] = uso
    if categoria:
        params["categoria"] = categoria
    data = await _api_get("/cargas-vivas", params)
    cargas = data.get("cargas") if isinstance(data, dict) else data
    if not isinstance(cargas, list) or not cargas:
        return f"No se encontraron cargas para uso='{uso}' categoria='{categoria}'. Categorías: Residencial, Oficinas, Comercio, Reunión, Educativos, Institucional, Almacenamiento, Fábricas, Garajes, Coliseos y Estadios."
    lines = ["Cargas vivas mínimas — NSR-10 Tabla B.4.2.1-1:\n"]
    lines.append("| Categoría | Uso | kN/m² | kgf/m² |")
    lines.append("|-----------|-----|-------|--------|")
    for c in cargas:
        nota = f" ¹" if c.get("notas") else ""
        lines.append(
            f"| {c.get('categoria', '')} | {c.get('uso', '')}{nota} | "
            f"{c.get('carga_kn_m2', '')} | {c.get('carga_kgf_m2', '')} |"
        )
    notas = [c.get("notas") for c in cargas if c.get("notas")]
    if notas:
        lines.append(f"\n¹ {notas[0]}")
    lines.append("\nFuente: NSR-10 B.4.2.1 — Tabla B.4.2.1-1")
    return "\n".join(lines)


@mcp.tool()
async def perfiles_acero(tipo: str | None = None, designacion: str | None = None) -> str:
    """Propiedades geométricas de perfiles de acero estructural (Ix, Sx, Zx, A, W, rx).

    Args:
        tipo:        Tipo de perfil. Opciones: W, C, L, HSS (tubular cuadrado/rectangular),
                     tubular_round, T, plate. Ej: "W" para vigas de alma llena.
        designacion: Designación del perfil (ej: "W10x22", "HSS4x4x1/4", "C150x12.2").

    Sin argumentos → lista todos los perfiles disponibles.
    """
    params: dict = {}
    if tipo:
        params["tipo"] = tipo
    if designacion:
        params["designacion"] = designacion
    data = await _api_get("/perfiles", params)
    perfiles = data.get("perfiles") if isinstance(data, dict) else data
    if not isinstance(perfiles, list) or not perfiles:
        return f"No se encontraron perfiles para tipo='{tipo}' designacion='{designacion}'."
    lines = [f"Perfiles de acero — {len(perfiles)} encontrados:\n"]
    lines.append("| Perfil | A (cm²) | W (kg/m) | Ix (cm⁴) | Sx (cm³) | Zx (cm³) | rx (cm) |")
    lines.append("|--------|---------|----------|----------|----------|----------|---------|")
    for p in perfiles[:20]:
        lines.append(
            f"| {p.get('designation', '')} | {p.get('area', '')} | {p.get('weight', '')} | "
            f"{p.get('ix', '')} | {p.get('sx', '')} | {p.get('zx', '')} | {p.get('rx', '')} |"
        )
    if len(perfiles) > 20:
        lines.append(f"\n_(mostrando 20 de {len(perfiles)} — especifica tipo o designación para filtrar)_")
    return "\n".join(lines)


@mcp.tool()
async def periodo_fundamental(
    sistema: str,
    n_pisos: int,
    hn_m: float | None = None,
) -> str:
    """Período fundamental empírico de la estructura — NSR-10 A.4.2.

    Calcula T usando el método aproximado (A.4.2-1) según sistema estructural.
    Si se provee hn_m (altura total en metros), usa esa altura; si no, estima 3 m/piso.

    Args:
        sistema:  Sistema estructural. Opciones:
                  "portico_concreto"  → Ct=0.047, α=0.9
                  "portico_acero"     → Ct=0.072, α=0.8
                  "muro_concreto"     → Ct=0.049, α=0.75
                  "muro_mamposteria"  → Ct=0.049, α=0.75
                  "dual"              → Ct=0.047, α=0.9 (como pórtico concreto)
        n_pisos:  Número de pisos de la estructura.
        hn_m:     Altura total sobre la base en metros (opcional; si None → 3 m × n_pisos).

    Fuente: NSR-10 A.4.2.2 — Ecuación A.4.2-1.
    """
    if n_pisos < 1:
        return "n_pisos debe ser ≥ 1."
    if hn_m is not None and hn_m <= 0:
        return "hn_m debe ser > 0 (altura total en metros)."
    SISTEMAS: dict[str, dict] = {
        "portico_concreto":  {"Ct": 0.047, "alpha": 0.90, "nombre": "Pórtico de concreto reforzado"},
        "portico_acero":     {"Ct": 0.072, "alpha": 0.80, "nombre": "Pórtico de acero"},
        "muro_concreto":     {"Ct": 0.049, "alpha": 0.75, "nombre": "Muros de concreto"},
        "muro_mamposteria":  {"Ct": 0.049, "alpha": 0.75, "nombre": "Muros de mampostería"},
        "dual":              {"Ct": 0.047, "alpha": 0.90, "nombre": "Sistema dual"},
    }
    key = sistema.lower().replace(" ", "_").replace("-", "_")
    # fuzzy match
    if key not in SISTEMAS:
        for k in SISTEMAS:
            if key in k or k in key:
                key = k
                break
        else:
            return (
                f"Sistema '{sistema}' no reconocido.\n"
                "Opciones: portico_concreto, portico_acero, muro_concreto, muro_mamposteria, dual"
            )

    s = SISTEMAS[key]
    Ct = s["Ct"]
    alpha = s["alpha"]
    hn = hn_m if hn_m else n_pisos * 3.0
    T = round(Ct * (hn ** alpha), 3)

    # Upper bound: 1.2 × Ta si se usa análisis completo (solo referencia)
    T_upper = round(1.2 * T, 3)

    lines = [
        "## Período Fundamental — NSR-10 A.4.2",
        f"**Sistema:** {s['nombre']}",
        "",
        "### Parámetros",
        f"| Parámetro | Valor |",
        f"|-----------|-------|",
        f"| Ct        | {Ct}  |",
        f"| α         | {alpha} |",
        f"| hn        | {hn} m ({n_pisos} pisos × {hn/n_pisos:.1f} m/piso) |",
        "",
        "### Resultado",
        f"**Ta = Ct × hn^α = {Ct} × {hn}^{alpha} = {T} s**",
        "",
        f"Límite superior (si se usa análisis completo): T ≤ 1.2 × Ta = **{T_upper} s**",
        "",
        "Fuente: NSR-10 A.4.2.2 — Ecuación A.4.2-1",
    ]
    return "\n".join(lines)


@mcp.tool()
async def separacion_sismica(
    delta1_cm: float,
    delta2_cm: float,
    h_cm: float | None = None,
) -> str:
    """Separación sísmica mínima entre estructuras adyacentes — NSR-10 A.6.5.

    La separación mínima es la suma de los desplazamientos horizontales máximos
    de ambas estructuras en el nivel de separación.

    Args:
        delta1_cm: Desplazamiento máximo de la estructura 1 en el nivel de separación (cm).
        delta2_cm: Desplazamiento máximo de la estructura 2 (o límite de lote) en cm.
                   Usar 0 si la estructura 2 es rígida o es el límite del lote.
        h_cm:      Altura del piso en cm (opcional; se usa para verificar % de altura).

    Fuente: NSR-10 A.6.5.1.
    """
    sep_min = round(math.sqrt(delta1_cm**2 + delta2_cm**2), 2)  # SRSS (NSR-10 A.6.5.1)
    sep_min_abs = round(delta1_cm + delta2_cm, 2)                # suma directa (conservador)

    lines = [
        "## Separación Sísmica — NSR-10 A.6.5",
        "",
        "### Datos de entrada",
        f"| | Valor |",
        f"|---|-------|",
        f"| δ₁ (despl. estructura 1) | {delta1_cm} cm |",
        f"| δ₂ (despl. estructura 2) | {delta2_cm} cm |",
        "",
        "### Separación mínima",
        f"| Método | Separación |",
        f"|--------|-----------|",
        f"| SRSS: √(δ₁² + δ₂²)  | **{sep_min} cm** |",
        f"| Suma directa: δ₁ + δ₂ | {sep_min_abs} cm |",
    ]

    if h_cm:
        pct = round(sep_min / h_cm * 100, 2)
        lines.append(f"| % de altura de piso hn | {pct}% |")

    lines += [
        "",
        "**Separación de diseño recomendada (SRSS):** Use la raíz cuadrada de la suma de cuadrados.",
        "La suma directa es el método conservador; NSR-10 A.6.5.1 permite SRSS.",
        "",
        "Fuente: NSR-10 A.6.5.1",
    ]
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# BIBLIOTECA NORMATIVA AISC / ACI (endpoints v1.5.0)
# ═══════════════════════════════════════════════════════════════

@mcp.tool()
async def buscar_aisc(texto: str, norma: str = "AISC-360-16", capitulo: str | None = None, limite: int = 10) -> str:
    """Búsqueda full-text en las especificaciones AISC (acero estructural).

    Args:
        texto:    Términos de búsqueda en inglés (ej: "shear strength", "bolted connections").
        norma:    AISC-360-16 (default), AISC-341-10 (sísmico) o AISC-358-16 (conexiones precalificadas).
        capitulo: Filtrar por capítulo (ej: "F", "J"). Opcional.
        limite:   Máximo de resultados (1-50). Default 10.
    """
    params: dict[str, Any] = {"q": texto, "norm": norma, "limit": max(1, min(limite, 50))}
    if capitulo:
        params["chapter"] = capitulo
    data = await _api_get("/aisc/search", params)
    return _format_norm_results(data, texto, norma)


@mcp.tool()
async def buscar_aci(texto: str, norma: str = "ACI-318-19", capitulo: str | None = None, limite: int = 10) -> str:
    """Búsqueda full-text en ACI 318 (concreto estructural).

    Args:
        texto:    Términos de búsqueda en inglés (ej: "development length", "punching shear").
        norma:    ACI-318-19 (default) o ACI-318-25.
        capitulo: Filtrar por capítulo (ej: "25"). Opcional.
        limite:   Máximo de resultados (1-50). Default 10.
    """
    params: dict[str, Any] = {"q": texto, "norm": norma, "limit": max(1, min(limite, 50))}
    if capitulo:
        params["chapter"] = capitulo
    data = await _api_get("/aci/search", params)
    return _format_norm_results(data, texto, norma)


def _format_norm_results(data: dict | list, texto: str, norma: str) -> str:
    if not isinstance(data, dict) or "results" not in data:
        err = data.get("error", "respuesta inesperada") if isinstance(data, dict) else "respuesta inesperada"
        return f"Error consultando {norma}: {err}"
    results = data["results"]
    if not results:
        return f"Sin resultados en {norma} para '{texto}'. Usa términos en inglés."
    lines = [f"Resultados {norma} para '{texto}' ({len(results)}):\n"]
    for r in results:
        extras = []
        if r.get("has_formula"):
            extras.append("fórmulas")
        if r.get("has_table"):
            extras.append("tablas")
        tag = f" _[{', '.join(extras)}]_" if extras else ""
        lines.append(f"**{r.get('section_id', '')} — {r.get('title', '')}** (p.{r.get('page_start', '?')}){tag}")
        body = (r.get("body") or "").strip()
        if body:
            lines.append(f"{body}\n")
    return "\n".join(lines)


@mcp.tool()
async def formulas_norma(norma: str | None = None, seccion: str | None = None, limite: int = 20) -> str:
    """Fórmulas estructuradas de normas con LaTeX y código Python ejecutable.

    Cubre AISC, ACI y NSR-10. Cada fórmula incluye variables, unidades y página.

    Args:
        norma:   Filtrar por norma (ej: "ACI-318-19", "AISC-360-16", "NSR-10"). Opcional.
        seccion: Filtrar por sección, búsqueda parcial (ej: "22.2"). Opcional.
        limite:  Máximo de fórmulas (1-100). Default 20.
    """
    params: dict[str, Any] = {"limit": max(1, min(limite, 100))}
    if norma:
        params["norm"] = norma
    if seccion:
        params["section"] = seccion
    data = await _api_get("/norm/formulas", params)
    formulas = data.get("formulas") if isinstance(data, dict) else None
    if not formulas:
        return f"Sin fórmulas para norma='{norma}' seccion='{seccion}'."
    lines = [f"Fórmulas normativas ({len(formulas)}):\n"]
    for f in formulas:
        lines.append(f"**{f.get('norm_code', '')} {f.get('section_id', '')} {f.get('formula_id', '')}** — {f.get('description', '')}")
        if f.get("latex"):
            lines.append(f"  LaTeX: `{f['latex']}`")
        if f.get("python_code"):
            lines.append(f"```python\n{f['python_code']}\n```")
        if f.get("units"):
            lines.append(f"  Unidades: {f['units']}")
        lines.append("")
    return "\n".join(lines)


@mcp.tool()
async def crosslinks_normas(origen: str | None = None, destino: str | None = None, limite: int = 50) -> str:
    """Equivalencias y referencias cruzadas entre normas: NSR-10 ↔ AISC ↔ ACI.

    Muestra qué sección de una norma adopta, modifica o referencia a otra.

    Args:
        origen:  Norma origen (ej: "NSR-10"). Opcional.
        destino: Norma destino (ej: "ACI-318-19"). Opcional.
        limite:  Máximo de cross-links (1-200). Default 50.
    """
    params: dict[str, Any] = {"limit": max(1, min(limite, 200))}
    if origen:
        params["source"] = origen
    if destino:
        params["target"] = destino
    data = await _api_get("/norm/crosslinks", params)
    links = data.get("crosslinks") if isinstance(data, dict) else None
    if not links:
        return f"Sin cross-links para origen='{origen}' destino='{destino}'."
    lines = [f"Cross-links entre normas ({len(links)}):\n"]
    lines.append("| Origen | Destino | Tipo | Nota |")
    lines.append("|--------|---------|------|------|")
    for li in links:
        lines.append(
            f"| {li.get('source_norm', '')} {li.get('source_section', '')} "
            f"| {li.get('target_norm', '')} {li.get('target_section', '')} "
            f"| {li.get('link_type', '')} | {li.get('note', '')} |"
        )
    return "\n".join(lines)


def main() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    log.info("Starting nsr10 MCP server v2, transport=%s API=%s", transport, API_URL)
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
