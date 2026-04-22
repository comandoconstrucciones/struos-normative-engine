# NSR-10 MCP Server

Motor normativo de ingeniería estructural Colombia para Model Context Protocol.
Implementado con **FastMCP** (API oficial recomendada por modelcontextprotocol.io).

## Instalación rápida

Opción A — con **uv** (recomendado por MCP docs):
```bash
# Instalar uv si no lo tienes: https://docs.astral.sh/uv/
uv sync --project mcp    # instala mcp + httpx en un venv local
```

Opción B — con pip clásico:
```bash
pip install mcp httpx
```

## Configuración Claude Desktop

Archivo: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)
o `~/.config/Claude/claude_desktop_config.json` (Linux).

**Con uv (recomendado)**:
```json
{
  "mcpServers": {
    "nsr10": {
      "command": "uv",
      "args": [
        "--directory",
        "/ruta/absoluta/a/struos-normative-engine/mcp",
        "run",
        "server.py"
      ],
      "env": {
        "STRUOS_API_URL": "https://struos-api.vercel.app"
      }
    }
  }
}
```

**Con python3 (si no usas uv)**:
```json
{
  "mcpServers": {
    "nsr10": {
      "command": "python3",
      "args": ["/ruta/absoluta/a/struos-normative-engine/mcp/server.py"],
      "env": {
        "STRUOS_API_URL": "https://struos-api.vercel.app"
      }
    }
  }
}
```

Después reiniciar Claude Desktop (quit completo, no cerrar ventana).

## Claude Code (CLI)

```bash
claude mcp add nsr10 -- python3 /ruta/absoluta/a/struos-normative-engine/mcp/server.py
# verificar
claude mcp list     # nsr10: ✓ Connected
```

## Debugging con MCP Inspector

```bash
npx @modelcontextprotocol/inspector uv --directory /ruta/a/mcp run server.py
```

UI web interactiva para probar tools, ver schemas y logs.

## Herramientas disponibles (8)

| Tool | Descripción |
|------|-------------|
| `parametros_sismicos(municipio)` | Aa, Av, zona de amenaza por municipio |
| `coeficiente_fa(tipo_suelo, aa)` | Coef Fa (Tabla A.2.4-3) |
| `coeficiente_fv(tipo_suelo, av)` | Coef Fv (Tabla A.2.4-4) |
| `coeficiente_r(sistema, capacidad?)` | R₀, Ω₀, Cd (Tabla A.3-3) |
| `barras_refuerzo(designacion?)` | Propiedades de barras (Ø, área, masa) |
| `deriva_maxima()` | Derivas máximas (Tabla A.6.4-1) |
| `buscar_seccion(texto, limite?)` | Búsqueda FTS en 12,789 secciones |
| **`preguntar_nsr10(pregunta, folder?, top_k?)`** | **RAG vectorial**: natural language con citas |

## Ejemplos en Claude

```
"¿Cuáles son los parámetros sísmicos para Bogotá?"
→ usa parametros_sismicos(municipio="Bogotá")

"Dame el coeficiente Fa para suelo tipo D con Aa=0.25"
→ usa coeficiente_fa(tipo_suelo="D", aa=0.25)

"¿Cuál es el R para pórticos especiales de concreto?"
→ usa coeficiente_r(sistema="pórticos", capacidad="DES")

"¿Cuál es la deriva máxima para pórticos de concreto según NSR-10?"
→ usa preguntar_nsr10(pregunta="...") y responde citando [1], [2]
  con filename + página + similitud coseno
```

## Variables de entorno

| Variable | Default | Uso |
|----------|---------|-----|
| `STRUOS_API_URL` | `https://struos-api.vercel.app` | Self-hosting o staging |
| `STRUOS_API_KEY` | (vacío) | Si el API exige `X-API-Key`, incluir |

## API REST subyacente

```bash
curl https://struos-api.vercel.app/municipios/Bogotá
curl https://struos-api.vercel.app/coef/fa/D/0.25
curl -X POST https://struos-api.vercel.app/ask \
  -H 'content-type: application/json' \
  -d '{"query":"deriva maxima","folder":"NSR-10"}'
```

## Links

- **Landing**: https://struos-ai.vercel.app
- **API**: https://struos-api.vercel.app
- **GitHub**: https://github.com/comandoconstrucciones/struos-normative-engine
- **MCP Docs**: https://modelcontextprotocol.io/docs/develop/build-server
