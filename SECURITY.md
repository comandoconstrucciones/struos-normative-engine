# Security Notes

## Estado actual (post-hardening 2026-04-21)

Migrations aplicadas en Supabase (proyecto `vdakfewjadwaczulcmvj`):

- `enable_rls_with_public_read_policies` — RLS activado en ~270 tablas
  (`nsr10_*`, `kg_*`, `cc_*`, `rag_chunks*`, `rag_nsr10_vision`,
  `embedding_cache`, `norm_metadata`, `research_*`). Policy `public_read`
  (SELECT TO anon, authenticated USING true). `rag_feedback` además
  tiene policy de INSERT para permitir ratings desde el cliente.
- `fix_function_search_path_mutable` — 11 funciones con
  `search_path = public, extensions, pg_temp` fijado.
- `remove_security_definer_from_rag_feedback_bad` — view recreada con
  `security_invoker = true`.

Advisors de seguridad: **282 → 2** (solo warnings benignos restantes).

## Acciones manuales pendientes (fuera del repo)

El hardening de código cubre la app; lo siguiente requiere acceso a consolas
externas y debe hacerse manualmente:

### 1. Rotar `STRUOS_SUPABASE_SERVICE_ROLE`

El key de `service_role` bypasea RLS y puede estar comprometido si se
commiteó alguna vez en variables de entorno locales.

1. Ir a Supabase Dashboard → Project `vdakfewjadwaczulcmvj` → Settings → API
2. `Reset service_role key`
3. Actualizar en Vercel/Railway:
   - `STRUOS_SUPABASE_SERVICE_ROLE` (nuevo valor)
4. Redeploy

### 2. Usar `anon` key + RLS para endpoints públicos

Los endpoints `/search`, `/municipios/*`, `/coef/*`, `/barras`, `/deriva`
solo hacen SELECT. No necesitan `service_role`.

- En Supabase → Authentication → Policies:
  - Activar RLS en todas las tablas `nsr10_*` y `kg_*`.
  - Crear policy `SELECT` para rol `anon` en cada tabla expuesta.
- Cambiar `HEADERS` en `api/main.py` y `api/index.py` para usar
  la `anon` key en vez de `service_role`.
- Mantener `service_role` solo para scripts de ingestión (`scripts/*`).

### 3. RAG vectorial (ya activo)

pgvector 0.8.0 instalado. Tabla `rag_chunks` con **57,293 chunks** (1536
dims, OpenAI `text-embedding-3-small`). El endpoint `/ask` usa la función
`match_rag_chunks(query_embedding, match_count, folder_filter)` via RPC.

Folders disponibles: `NSR-10`, `AISC Design Guides`, `Catálogos`,
`Manuales`, `Normas técnicas`.

Tabla `rag_chunks_gemini` (32,313 filas) disponible para agregar un segundo
pipeline con embeddings Gemini si se desea comparar calidad.

### 4. Setear variables de entorno en producción

En Vercel (`struos-api.vercel.app`) y Railway (si aplica):

| Variable | Valor recomendado | Obligatoria |
|----------|-------------------|-------------|
| `STRUOS_SUPABASE_URL` | URL del proyecto | Sí |
| `STRUOS_SUPABASE_SERVICE_ROLE` | Solo si usa writes; preferir anon | Sí (hoy) |
| `OPENAI_API_KEY` | Para `/ask` | Solo si se expone `/ask` |
| `STRUOS_API_KEY` | Random largo (32+ chars) | Recomendado |
| `ALLOWED_ORIGINS` | `https://struos-ai.vercel.app,https://chatgpt.com,...` | Recomendado |
| `RATE_LIMIT` | `60/minute` o más estricto | Recomendado |

## Lo que SÍ cubre el código (este commit)

- Sanitización de parámetros ILIKE/FTS (evita pattern injection).
- Whitelist de tablas en `/sql/{table}` (evita scraping arbitrario).
- Validación estricta de enums y rangos (Fa/Fv, capacidad DES/DMO/DMI).
- CORS restringido por defecto a dominios conocidos + `ALLOWED_ORIGINS` env.
- Rate limiting opcional vía `slowapi` (`RATE_LIMIT` env).
- API key opcional vía `X-API-Key` header (`STRUOS_API_KEY` env).
- Cache in-memory de respuestas `/ask` (hash SHA-256).
- `/ask` usa ahora todos los términos significativos, no solo el primero.
- Tests de seguridad y KG integrity en `tests/`.
