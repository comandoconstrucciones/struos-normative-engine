"""
Tests de la API enfocados en seguridad y validación de entrada.

No golpean Supabase: usan FastAPI TestClient. Para los endpoints que sí hacen
fetch upstream, se mockea `requests.get`.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "vercel-api" / "api"))
sys.path.insert(0, str(ROOT / "api"))


@pytest.fixture(scope="module")
def vercel_client():
    # Import diferido — debe ocurrir DESPUÉS de ajustar sys.path
    import importlib

    sys.path.insert(0, str(ROOT / "vercel-api" / "api"))
    mod = importlib.import_module("index")
    return TestClient(mod.app)


# ====== _security ======

def test_ilike_escape_basic():
    from _security import ilike_escape

    assert ilike_escape("") == ""
    assert ilike_escape("bogota") == "bogota"


def test_ilike_escape_metachars():
    from _security import ilike_escape

    # cada metachar debe quedar escapado con backslash
    assert ilike_escape("*") == r"\*"
    assert ilike_escape("%") == r"\%"
    assert ilike_escape("_") == r"\_"
    assert ilike_escape(",") == r"\,"
    assert ilike_escape("\\") == r"\\"


def test_ilike_escape_mixed():
    from _security import ilike_escape

    assert ilike_escape("50%_off,*") == r"50\%\_off\,\*"


def test_allowed_tables_whitelist():
    from _security import allowed_table

    assert allowed_table("nsr10_secciones")
    assert allowed_table("kg_nodes")
    assert not allowed_table("auth.users")
    assert not allowed_table("pg_catalog.pg_tables")
    assert not allowed_table("")


# ====== CORS ======

def test_cors_origins_default():
    from _security import get_cors_origins

    origins = get_cors_origins()
    assert "*" not in origins
    assert any("struos-ai" in o for o in origins)


def test_cors_origins_from_env(monkeypatch):
    from _security import get_cors_origins

    monkeypatch.setenv("ALLOWED_ORIGINS", "https://a.com, https://b.com")
    origins = get_cors_origins()
    assert origins == ["https://a.com", "https://b.com"]


# ====== Validación de entrada en endpoints (vercel-api) ======

def test_root_ok(vercel_client):
    r = vercel_client.get("/")
    assert r.status_code == 200
    assert "version" in r.json()


def test_health(vercel_client):
    r = vercel_client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_coef_fa_invalid_soil(vercel_client):
    r = vercel_client.get("/coef/fa/X/0.25")
    assert r.status_code == 400


def test_coef_fa_invalid_aa(vercel_client):
    r = vercel_client.get("/coef/fa/D/0.99")
    assert r.status_code == 400


def test_coef_fa_soil_f_returns_note(vercel_client):
    r = vercel_client.get("/coef/fa/F/0.25")
    assert r.status_code == 200
    body = r.json()
    assert body["fa"] is None
    assert "estudio" in body["nota"].lower()


def test_coef_fv_invalid_av(vercel_client):
    r = vercel_client.get("/coef/fv/D/1.0")
    assert r.status_code == 400


def test_coef_r_invalid_capacidad(vercel_client):
    r = vercel_client.get("/coef/r?capacidad=XXX")
    assert r.status_code == 400


def test_search_query_too_short(vercel_client):
    r = vercel_client.get("/search?q=a")
    assert r.status_code == 422  # Query(min_length=2)


def test_search_limit_out_of_range(vercel_client):
    r = vercel_client.get("/search?q=sismo&limit=999")
    assert r.status_code == 422


def test_municipio_too_long(vercel_client):
    r = vercel_client.get("/municipios/" + "a" * 100)
    assert r.status_code == 400


# ====== API key gating opcional ======

# ====== /ask vectorial (vercel-api/api/index.py — módulo canónico) ======

@pytest.fixture(scope="module")
def main_client(monkeypatch_session=None):
    """Fixture del módulo `index` (app unificada, antes duplicada en api/main.py)."""
    import importlib

    sys.path.insert(0, str(ROOT / "vercel-api" / "api"))
    if "index" in sys.modules:
        del sys.modules["index"]
    mod = importlib.import_module("index")
    return mod, TestClient(mod.app)


def test_ask_folders_public(main_client):
    _, client = main_client
    r = client.get("/ask/folders")
    assert r.status_code == 200
    body = r.json()
    assert "NSR-10" in body["folders"]
    assert body["default"] == "NSR-10"


def test_ask_query_validation(main_client):
    _, client = main_client
    r = client.post("/ask", json={"query": "a"})  # muy corto
    assert r.status_code == 422


def test_ask_context_limit_out_of_range(main_client):
    _, client = main_client
    r = client.post("/ask", json={"query": "deriva bogota", "context_limit": 99})
    assert r.status_code == 422


def test_ask_without_openai_key_returns_503(main_client, monkeypatch):
    mod, client = main_client
    monkeypatch.setattr(mod, "_openai_client", None)
    r = client.post("/ask", json={"query": "deriva maxima", "context_limit": 5})
    assert r.status_code == 503


def test_ask_pipeline_with_mocked_rag(main_client):
    """Mockea embed + RPC + LLM para probar el pipeline completo de /ask."""
    mod, client = main_client

    # Mock embedding
    class _Embed:
        def __init__(self, v):
            self.embedding = v

    class _EmbedResp:
        def __init__(self):
            self.data = [_Embed([0.0] * 1536)]

    class _ChatMsg:
        def __init__(self, content):
            self.message = type("M", (), {"content": content})()

    class _ChatResp:
        def __init__(self, text):
            self.choices = [_ChatMsg(text)]

    class _FakeOpenAI:
        embeddings = type(
            "E", (), {"create": staticmethod(lambda model, input: _EmbedResp())}
        )()
        chat = type(
            "C",
            (),
            {
                "completions": type(
                    "CC",
                    (),
                    {
                        "create": staticmethod(
                            lambda **kw: _ChatResp("Según [1], la deriva máxima es 1.0%.")
                        )
                    },
                )()
            },
        )()

    with patch.object(mod, "_openai_client", _FakeOpenAI()), patch.object(
        mod.requests, "post"
    ) as mpost:
        # Simular respuesta de match_rag_chunks
        mpost.return_value.ok = True
        mpost.return_value.status_code = 200
        mpost.return_value.json = lambda: [
            {
                "id": 42,
                "filename": "NSR-10-A.pdf",
                "folder": "NSR-10",
                "page": 180,
                "chunk_text": "A.6.4 Deriva máxima permisible = 1.0% hpi",
                "similarity": 0.89,
            }
        ]
        r = client.post("/ask", json={"query": "cual es la deriva maxima"})

    assert r.status_code == 200
    body = r.json()
    assert "deriva" in body["answer"].lower()
    assert len(body["sources"]) == 1
    assert body["sources"][0]["filename"] == "NSR-10-A.pdf"
    assert body["sources"][0]["page"] == 180
    assert body["sources"][0]["similarity"] == 0.89


def test_ask_empty_rag_results(main_client):
    """Si match_rag_chunks no retorna nada, /ask responde con nota clara."""
    mod, client = main_client

    class _Embed:
        def __init__(self, v):
            self.embedding = v

    class _EmbedResp:
        def __init__(self):
            self.data = [_Embed([0.0] * 1536)]

    class _FakeOpenAI:
        embeddings = type("E", (), {"create": staticmethod(lambda model, input: _EmbedResp())})()
        chat = None  # no debería llamarse

    with patch.object(mod, "_openai_client", _FakeOpenAI()), patch.object(
        mod.requests, "post"
    ) as mpost:
        mpost.return_value.ok = True
        mpost.return_value.json = lambda: []
        r = client.post("/ask", json={"query": "xyzzy nonexistent"})

    assert r.status_code == 200
    body = r.json()
    assert body["sources"] == []
    assert "No encontré" in body["answer"] or "fragmentos" in body["answer"]


def test_api_key_required_when_env_set(monkeypatch):
    import importlib

    monkeypatch.setenv("STRUOS_API_KEY", "secret123")
    # reimportar para releer el env-var — el check lo hace require_api_key en cada request,
    # así que no hace falta reiniciar la app.
    sys.path.insert(0, str(ROOT / "vercel-api" / "api"))
    mod = importlib.import_module("index")
    client = TestClient(mod.app)

    r = client.get("/coef/fa/D/0.25")
    assert r.status_code == 401

    r = client.get("/coef/fa/D/0.25", headers={"X-API-Key": "wrong"})
    assert r.status_code == 401

    # Con la key correcta, pasa la validación (aunque luego falle upstream si
    # no hay service_role — está bien, lo importante es que no sea 401).
    with patch("index.requests.get") as mget:
        mget.return_value.status_code = 200
        mget.return_value.json = lambda: [{"fa": 1.2}]
        mget.return_value.ok = True
        r = client.get(
            "/coef/fa/D/0.25", headers={"X-API-Key": "secret123"}
        )
        assert r.status_code == 200
