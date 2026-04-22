# Motor Normativo NSR-10 — Struos

API + Knowledge Graph + RAG vectorial para la **NSR-10** (Reglamento
Colombiano de Construcción Sismo Resistente).

Accesible desde navegador, Claude (via MCP), ChatGPT (via Action) y
cualquier cliente HTTP.

| | |
|---|---|
| **API** | https://struos-api.vercel.app |
| **Landing** | https://struos-ai.vercel.app |
| **MCP** | `mcp_server/server.py` (stdio, 8 tools) |
| **DB** | Supabase `vdakfewjadwaczulcmvj` |

---

## Estado

### Normativa indexada (100%)

| | Valor |
|---|---|
| Secciones (FTS) | **12,789** |
| Fórmulas | **558** + 73 sismo + 24 concreto + 8 viento |
| Tablas estructuradas | **225+** |
| Knowledge Graph | **3,109 nodos · 2,488 edges** |
| Figuras | **116** |
| Nomenclatura | **246** símbolos |
| Referencias externas | **568** (ASTM, ACI, AISC, AWS, NTC, ASCE) |

Cubre los 11 títulos **A** (sismo) a **K** (complementarios):

| Título | Tablas | Figuras | Ecuaciones |
|--------|--------|---------|------------|
| A — Sismo | 47 | 28 | 101 |
| B — Cargas | 21 | 27 | 48 |
| C — Concreto | 15 | 2 | 58 |
| D — Mampostería | 22 | 0 | 71 |
| E — Casas de 1-2 pisos | 18 | 7 | 6 |
| F — Acero | 167 | 111 | 82 |
| G — Madera y guadua | 95 | 47 | 91 |
| H — Geotecnia | 23 | 8 | 31 |
| I — Supervisión | 6 | 0 | 0 |
| J — Incendio | 34 | 1 | 6 |
| K — Complementarios | 50 | 10 | 20 |

### RAG vectorial (activo)

- **57,293 chunks** con embeddings OpenAI 1536-dim (`text-embedding-3-small`)
- **32,313 chunks** adicionales con embeddings Gemini
- pgvector 0.8.0 + función SQL `match_rag_chunks` (cosine similarity)
- Folders indexados: `NSR-10`, `AISC Design Guides`, `Catálogos`, `Manuales`, `Normas técnicas`

---

## Endpoints REST

```
GET  /                              info del servicio
GET  /health                        health check
GET  /municipios/{nombre}           Aa, Av, zona sísmica
GET  /coef/fa/{suelo}/{aa}          coeficiente Fa (A.2.4-3)
GET  /coef/fv/{suelo}/{av}          coeficiente Fv (A.2.4-4)
GET  /coef/r?sistema=...            R₀, Ω₀, Cd (A.3-3)
GET  /barras?designacion=...        propiedades de barras (C.3.5.3-1)
GET  /deriva                        derivas máximas (A.6.4-1)
GET  /search?q=...                  FTS en las 12,789 secciones
POST /ask                           RAG vectorial con citas
GET  /ask/folders                   dominios indexados
```

### Ejemplos

```bash
# Parámetros sísmicos de Medellín
curl https://struos-api.vercel.app/municipios/Medellin
# → [{"municipio":"Medellín","departamento":"Antioquia","aa":0.15,"av":0.2,"zona_amenaza":"Intermedia"}]

# Coef Fa para suelo D con Aa=0.25
curl https://struos-api.vercel.app/coef/fa/D/0.25

# Búsqueda full-text
curl "https://struos-api.vercel.app/search?q=cortante+concreto&limit=5"

# Pregunta en lenguaje natural (RAG)
curl -X POST https://struos-api.vercel.app/ask \
  -H 'Content-Type: application/json' \
  -d '{"query":"cuál es la deriva máxima para pórticos de concreto"}'
```

Respuesta de `/ask`:

```json
{
  "question": "...",
  "answer": "Según [1], la deriva máxima es 1.0% de hpi...",
  "folder": "NSR-10",
  "sources": [
    {"n": 1, "filename": "NSR-10-Titulo-A.pdf", "page": 180, "similarity": 0.89, "excerpt": "..."},
    ...
  ]
}
```

---

## Consumo desde Claude (MCP)

**1.** `pip install mcp httpx`

**2.** Agregar a `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) o `~/.config/Claude/claude_desktop_config.json` (Linux):

```json
{
  "mcpServers": {
    "nsr10": {
      "command": "python3",
      "args": ["/ruta/absoluta/a/struos-normative-engine/mcp_server/server.py"],
      "env": {
        "STRUOS_API_URL": "https://struos-api.vercel.app"
      }
    }
  }
}
```

**3.** Reiniciar Claude Desktop. Aparecen 8 tools:

`parametros_sismicos`, `coeficiente_fa`, `coeficiente_fv`, `coeficiente_r`,
`barras_refuerzo`, `deriva_maxima`, `buscar_seccion`, **`preguntar_nsr10`**
(RAG vectorial con citas).

Ver [`mcp_server/README.md`](mcp_server/README.md) para más detalle.

---

## Consumo desde ChatGPT

Usar el OpenAPI schema en [`docs/openapi-chatgpt.json`](docs/openapi-chatgpt.json)
como Custom Action. Instrucciones en [`docs/chatgpt-action.md`](docs/chatgpt-action.md).

---

## Desarrollo

```bash
cp .env.example .env          # credenciales (Supabase, OpenAI, opcional API_KEY)
pip install -e ".[dev]"

pytest tests/                 # 67 tests (<1s)
ruff check api/ tests/

# Dev server local
uvicorn index:app --reload --app-dir api --port 8000
```

Ver [`CLAUDE.md`](CLAUDE.md) — guía detallada para contribuir o extender
(arquitectura, convenciones, gotchas, deploy).

---

## Seguridad

Ver [`SECURITY.md`](SECURITY.md) para el estado de hardening aplicado:

- 282 → 2 Supabase security advisors (RLS activa en todas las tablas públicas)
- Input sanitization, table whitelist, CORS restringido
- Rate limiting opcional (`slowapi`)
- API key opcional (`STRUOS_API_KEY` env)
- Validación estricta de enums (suelo A-F, capacidad DES/DMO/DMI, etc.)

---

## Stack

- **Backend**: Python 3.10+, FastAPI, slowapi
- **DB**: Supabase (Postgres 17), pgvector 0.8.0
- **LLM**: OpenAI (embeddings `text-embedding-3-small`, respuestas `gpt-4o-mini`)
- **Deploy**: Vercel serverless (`struos-api`), Railway (alternativo)
- **CI**: GitHub Actions (py3.10/3.11/3.12 matrix)
- **Protocolos**: MCP (stdio), REST, OpenAPI 3.0

---

## Licencia

Propietario — Comando Construcciones. Contacto: contacto@comandoconstrucciones.com
