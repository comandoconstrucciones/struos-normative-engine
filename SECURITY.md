# Security Notes

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
- Cambiar `HEADERS` en `api/main.py` y `vercel-api/api/index.py` para usar
  la `anon` key en vez de `service_role`.
- Mantener `service_role` solo para scripts de ingestión (`scripts/*`).

### 3. Configurar pgvector para RAG vectorial

El endpoint `/ask` actualmente usa keyword-matching. Para RAG real:

```sql
-- En Supabase SQL Editor:
CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE nsr10_secciones
  ADD COLUMN IF NOT EXISTS embedding vector(1536);

CREATE INDEX IF NOT EXISTS nsr10_secciones_embedding_idx
  ON nsr10_secciones USING hnsw (embedding vector_cosine_ops);
```

Luego poblar con `scripts/embedding_cache.py` (OpenAI `text-embedding-3-small`).

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
