"""
Tests de integridad del Knowledge Graph (archivos JSON versionados en kg/).

Falla si:
- Hay edges que apuntan a nodos inexistentes (dentro del mismo título).
- Hay nodos duplicados por id.
- Faltan campos obligatorios.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

KG_DIR = Path(__file__).resolve().parent.parent / "kg"

# Las aristas pueden apuntar a nodos raíz "titulo_X" definidos implícitamente
# en el conjunto de datos (no están dentro del archivo nodes_*).
IMPLICIT_ROOT_NODES = {"titulo_a", "titulo_b", "titulo_c", "titulo_d", "titulo_e",
                       "titulo_f", "titulo_g", "titulo_h", "titulo_i", "titulo_j",
                       "titulo_k"}


def _titulos() -> list[str]:
    nodes_files = sorted(KG_DIR.glob("nodes_titulo_*.json"))
    return [f.stem.replace("nodes_titulo_", "") for f in nodes_files]


@pytest.mark.parametrize("titulo", _titulos())
def test_nodes_unique_ids(titulo: str):
    nodes = json.loads((KG_DIR / f"nodes_titulo_{titulo}.json").read_text())
    ids = [n["id"] for n in nodes]
    assert len(ids) == len(set(ids)), f"IDs duplicados en título {titulo}"


@pytest.mark.parametrize("titulo", _titulos())
def test_nodes_required_fields(titulo: str):
    nodes = json.loads((KG_DIR / f"nodes_titulo_{titulo}.json").read_text())
    for n in nodes:
        assert "id" in n and n["id"], f"nodo sin id en {titulo}: {n}"
        assert "tipo" in n, f"nodo {n['id']} sin tipo"
        assert "label" in n, f"nodo {n['id']} sin label"


@pytest.mark.parametrize("titulo", _titulos())
def test_edges_reference_existing_nodes(titulo: str):
    edges_path = KG_DIR / f"edges_titulo_{titulo}.json"
    if not edges_path.exists():
        pytest.skip(f"Sin edges para {titulo}")
    nodes = json.loads((KG_DIR / f"nodes_titulo_{titulo}.json").read_text())
    edges = json.loads(edges_path.read_text())

    node_ids = {n["id"] for n in nodes} | IMPLICIT_ROOT_NODES

    orphans = []
    for e in edges:
        src, tgt = e.get("source"), e.get("target")
        if src not in node_ids:
            orphans.append(("source", src, e))
        if tgt not in node_ids:
            orphans.append(("target", tgt, e))

    assert not orphans, f"Edges apuntan a nodos inexistentes en {titulo}: {orphans[:5]}"


@pytest.mark.parametrize("titulo", _titulos())
def test_edges_required_fields(titulo: str):
    edges_path = KG_DIR / f"edges_titulo_{titulo}.json"
    if not edges_path.exists():
        pytest.skip(f"Sin edges para {titulo}")
    edges = json.loads(edges_path.read_text())
    for e in edges:
        assert "source" in e and e["source"], f"edge sin source en {titulo}"
        assert "target" in e and e["target"], f"edge sin target en {titulo}"
        assert "relation" in e and e["relation"], f"edge sin relation en {titulo}"
