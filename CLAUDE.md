# CLAUDE.md

Guía del repo para Claude Code. Información que un agente necesita para ser
útil sin volver a explorar desde cero.

## Qué es esto

Motor normativo **NSR-10 Colombia** (+ otras normas). Indexa el Reglamento
Colombiano de Construcción Sismo Resistente como Knowledge Graph + SQL + RAG
vectorial, y lo expone vía:

- **REST API** (FastAPI, Vercel serverless)
- **MCP server** para Claude Desktop / Claude Code
- **ChatGPT Custom GPT** via OpenAPI action

## Arquitectura

```
PDF NSR-10 → pipeline de extracción (scripts/) → Supabase
                                                      ├── nsr10_* (225+ tablas estructuradas)
                                                      ├── kg_nodes / kg_edges (3109/2488)
                                                      ├── nsr10_secciones (12,789 FTS)
                                                      ├── rag_chunks (57,293 embeddings 1536-dim, OpenAI)
                                                      └── rag_chunks_gemini (32,313 embeddings Gemini)
                                                              ↓
                                                        pgvector 0.8.0
                                                              ↓
                       ┌──────────────────────────────────────┼───────────────────────────────────┐
                                                ↓                                   ↓
                                   api/index.py              mcp_server/server.py
                                   (Vercel + Railway,                   (Claude Desktop /
                                    11 endpoints + /ask RAG)             Claude Code, 8 tools)
```

## Layout del repo

| Path | Propósito |
|------|-----------|
| `api/index.py` | **Única app FastAPI** — usada por Vercel y Railway |
| *(security inlined en `api/index.py` — ver bloque "Security utilities")* | Hardening (ilike_escape, CORS, API-key, rate limit) integrado en el Lambda |
| `vercel.json` (root) | Config Vercel: build `api/index.py`, route all → ahí |
| `Procfile`, `railway.json` (root) | Config Railway: `uvicorn index:app --app-dir api` |
| `mcp_server/server.py` | MCP server para Claude (8 tools). URL y API-key por env |
| `src/nsr10_formulas.py` | Cálculos normativos (espectro, deriva, Vs, T, factor R) |
| `src/normative_package.py` | Interfaz abstracta Requirement/CheckResult (futuro) |
| `scripts/` | Pipeline de extracción activo (extractor, enrich_kg_v2, link_*, load_*) |
| `scripts/legacy/` | 18 scripts obsoletos preservados por referencia histórica |
| `sql/` | Esquemas Postgres del KG y tablas normativas |
| `kg/` | JSON versionados de nodos/edges (solo títulos B, C, D, E — el resto vive en Supabase) |
| `tests/` | 67 tests (fórmulas, API security, KG integrity, /ask mockeado) |
| `web/kg-viewer` | Visualizador del Knowledge Graph |
| `landing/`, `demo/` | Landing `struos-ai.vercel.app` y demo |
| `docs/` | OpenAPI para ChatGPT Action, roadmap, esquema KG |

## Infra externa

- **Supabase**: proyecto `vdakfewjadwaczulcmvj` (Apps), región us-east-1, PG 17
  - Todas las tablas `nsr10_*`, `kg_*`, `rag_chunks*` tienen **RLS activa** con policy `public_read` para `anon, authenticated`.
  - `service_role` sigue bypaseando RLS (para scripts de ingestión).
  - pgvector 0.8.0 instalado. Función SQL `match_rag_chunks(embedding, k, folder)` para el /ask.
- **Vercel team**: `team_FJvXJkFBFkipB46ZV85hnwpt` (Comando Construcciones)
  - `struos-api` (`prj_IRI1TAuugLVKOcjZ12ZIAl6q5wzl`) — la API REST
  - `struos-ai` (`prj_FIQh1wEG36nXfLljdm0HmKLXUdc2`) — landing
  - `struos-landing` (`prj_tpyCQQe6QnAlFuD8k3M7p8uGIZ1J`) — landing alterno
  - `kg-viewer` (`prj_CWzeMQMyZqbzy9he1VzAJ8242L2e`) — visualizador

## Setup local

```bash
cp .env.example .env          # llenar con credenciales (Supabase service_role, OpenAI)
pip install -e ".[dev]"       # instala deps + pytest + ruff
```

## Comandos frecuentes

```bash
# Tests
pytest tests/                                     # 67 tests, <1s

# Lint
ruff check api/ tests/                # estricto en código nuevo
ruff check --fix api/ tests/          # auto-fix

# Dev server local
uvicorn index:app --reload --host 0.0.0.0 --port 8000 --app-dir api

# Probar un endpoint de prod
curl https://struos-api.vercel.app/municipios/Bogota
curl -X POST https://struos-api.vercel.app/ask \
     -H 'content-type: application/json' \
     -d '{"query":"cual es la deriva maxima"}'
```

## Deploy

### Vercel (producción, `struos-api.vercel.app`)

1. **Auto-deploy desde GitHub** (activo desde commit fba133d): cada
   push/merge a `main` dispara un build. `vercel.json` en la raíz le
   dice al builder que compile `api/index.py` con `api/requirements.txt`.
2. **CLI manual** (respaldo):
   ```bash
   npx vercel --prod
   ```
   `api/.vercel/project.json` ya está linkeado al proyecto correcto.

### Env vars obligatorias en Vercel (Production scope)

| Variable | Para qué |
|----------|----------|
| `STRUOS_SUPABASE_URL` | endpoint de Supabase |
| `STRUOS_SUPABASE_SERVICE_ROLE` | acceso (bypasa RLS) — rotar si se sospecha fuga |
| `OPENAI_API_KEY` | requerido por `/ask` (embeddings + chat) |
| `STRUOS_API_KEY` | opcional; si se setea, exige `X-API-Key` header |
| `ALLOWED_ORIGINS` | lista coma-separada; si no, default conservador |
| `RATE_LIMIT` | ej `60/minute` |
| `EMBEDDING_MODEL` | default `text-embedding-3-small` |

## Endpoints de la API (v1.3.0)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/` | GET | Info del servicio |
| `/health` | GET | Health check |
| `/municipios/{nombre}` | GET | Aa, Av, zona sísmica |
| `/coef/fa/{suelo}/{aa}` | GET | Coef Fa (A.2.4-3) |
| `/coef/fv/{suelo}/{av}` | GET | Coef Fv (A.2.4-4) |
| `/coef/r?sistema=...` | GET | R₀, Ω₀, Cd (A.3-3) |
| `/barras?designacion=...` | GET | Propiedades de barras (C.3.5.3-1) |
| `/deriva` | GET | Derivas máximas (A.6.4-1) |
| `/search?q=...` | GET | FTS en 12,789 secciones |
| `/ask` | POST | **RAG vectorial** con citas |
| `/ask/folders` | GET | Dominios indexados |

Payload de `/ask`:
```json
{ "query": "...", "context_limit": 8, "folder": "NSR-10" }
```

## MCP tools (8)

`parametros_sismicos`, `coeficiente_fa`, `coeficiente_fv`, `coeficiente_r`,
`barras_refuerzo`, `deriva_maxima`, `buscar_seccion`, `preguntar_nsr10`.

Config en `mcp_server/claude_desktop_config.json` (template). Instalar con
`pip install mcp httpx`. Override de URL/API-key vía env `STRUOS_API_URL` y
`STRUOS_API_KEY`.

## CI

`.github/workflows/ci.yml` — matrix py3.10/3.11/3.12:

- `pytest tests/` — 67 tests
- `ruff check api/ tests/` — estricto
- `ruff check src/ mcp_server/` — warn-only (legacy)

## Convenciones

- **Trabajar en branches** `claude/...` y hacer PR a `main`.
- `main` está protegido semánticamente: mergea vía squash; se espera que CI esté verde.
- Para cambios SQL usar `apply_migration` (migración versionada), nunca `execute_sql` para DDL.
- No commitear `.env`, `.vercel/`, PDFs de referencia.
- `scripts/legacy/` es de solo lectura; scripts activos viven en `scripts/`.

## Gotchas conocidos

- **NO renombrar la carpeta `mcp_server/` a `mcp/`**. Python shadowea
  el package oficial `mcp` con carpetas del mismo nombre → ImportError
  al correr el server (`mcp.server is not a package`). Resultado visible:
  Claude Desktop muestra "Couldn't reach the MCP server".
- **Vercel Python serverless empaca solo el archivo entrypoint**. Si
  `api/index.py` hace `from otro_archivo import X`, falla con
  FUNCTION_INVOCATION_FAILED en runtime. Mantener toda la lógica en un
  solo archivo o configurar `includeFiles` en `vercel.json`.
- Las tablas `nsr10_*` tienen RLS activa. Si un cliente usa `anon` key, solo
  puede SELECT (lo cual es suficiente). Los scripts que escriben deben usar
  `service_role`.
- `src/nsr10_formulas.py` usa variables `I`, `R`, `Ct` siguiendo la
  nomenclatura NSR-10 — no renombrar (ruff `E741` ignorado por config).
- El cache de `/ask` es in-memory; en Vercel serverless se pierde entre
  invocations (cada función nueva lo reinicia).
- Dimensión de embeddings: **1536** (OpenAI `text-embedding-3-small`).
  Cambiar a otro modelo requiere regenerar la columna `embedding` de
  `rag_chunks` (57k filas).

## Docs adicionales

- `README.md` — overview para usuarios
- `SECURITY.md` — estado de hardening + follow-ups
- `docs/KNOWLEDGE_GRAPH_SCHEMA.md` — tipos de nodos y aristas
- `docs/MEJORAS_EMBEDDINGS_ANALISIS.md` — análisis de mejoras al RAG
- `docs/COMANDOCALC_ROADMAP.md` — roadmap de la calculadora
- `docs/chatgpt-action.md` — configuración del Custom GPT
- `docs/openapi-chatgpt.json` — spec OpenAPI del API (para ChatGPT Actions)
- `mcp_server/README.md` — cómo instalar el MCP en Claude Desktop
