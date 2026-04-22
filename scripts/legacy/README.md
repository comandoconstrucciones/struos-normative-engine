# Scripts legacy

Esta carpeta contiene scripts de uno-solo-uso del pipeline de ingestión
y versiones anteriores de búsqueda/API que quedaron reemplazadas.

No se ejecutan en el pipeline actual; se preservan como referencia histórica.

## Contenido

| Archivo | Reemplazado por / Estado |
|---------|--------------------------|
| `api_server.py` | `api/main.py` (producción) |
| `nsr10_api.py` | `api/index.py` |
| `search_v3.py`, `search_v4.py`, `search_v5.py` | `search_production.py` |
| `enrich_kg.py` | `enrich_kg_v2.py` |
| `extract_titulo_a.py`, `extract_kg_titulo_b.py`, `extract_kg_titulo_c.py` | One-shot por título (ya ejecutado) |
| `test_extraction.py`, `test_extraction_v2.py` | Pruebas ad-hoc del pipeline |
| `regenerate_remaining.py` | One-shot de regeneración |
| `fix_empty_tables.py`, `fix_unaccent_search.py` | One-shots de parcheo |
| `build_kg_supabase.py`, `ingest_nsr10.py` | Bootstrap inicial (ya ejecutado) |
| `advanced_search.py`, `create_advanced_edges.py` | One-shots |

## Reactivar un script

```bash
cd scripts/legacy
python3 <archivo>.py
```

Antes, verificar que las variables de entorno y el esquema SQL de Supabase
sigan siendo compatibles con el código (puede haber deriva).
