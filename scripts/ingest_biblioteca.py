#!/usr/bin/env python3
"""
Ingesta de biblioteca técnica de Leonardo → Supabase rag_chunks.

Mapea los PDFs en /root/agents/leonardo/docs/ a folders de rag_chunks,
extrae texto con PyMuPDF, genera embeddings con OpenAI, e inserta en Supabase.
Omite archivos ya indexados (basado en filename + folder).

Uso:
    python3 scripts/ingest_biblioteca.py [--dry-run] [--folder FOLDER] [--resume]
"""
import os
import sys
import json
import time
import hashlib
import argparse
import traceback
from pathlib import Path

import fitz  # PyMuPDF
import requests
from openai import OpenAI

# ─── Config ──────────────────────────────────────────────────────────────────

SUPABASE_URL = os.environ.get(
    "STRUOS_SUPABASE_URL",
    "https://vdakfewjadwaczulcmvj.supabase.co",
)
SERVICE_ROLE = os.environ.get(
    "STRUOS_SUPABASE_SERVICE_ROLE",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZkYWtmZXdqYWR3YWN6dWxjbXZqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzQyMzMwMiwiZXhwIjoyMDg4OTk5MzAyfQ.JfyNWc6KQWWsohqRkpqRot_7FAP85TtZkkIhZdvIBTs",
)
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")

HEADERS = {
    "apikey": SERVICE_ROLE,
    "Authorization": f"Bearer {SERVICE_ROLE}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}

EMBEDDING_MODEL = "text-embedding-3-small"
CHUNK_SIZE = 800       # palabras aprox por chunk
CHUNK_OVERLAP = 80     # palabras de solapamiento
BATCH_SIZE = 50        # chunks por inserción
SLEEP_BETWEEN_PDFS = 1.0

DOCS_ROOT = Path("/root/agents/leonardo/docs")

# ─── Mapeo directorio → folder en rag_chunks ─────────────────────────────────

FOLDER_MAP: dict[str, str] = {
    "nsr10":                             "NSR-10",
    "referencia/NSR-10":                 "NSR-10",
    "referencia/AISC/AISC Design Guides": "AISC Design Guides",
    "referencia/AISC":                   "AISC",
    "referencia/ACI":                    "ACI",
    "normas/aci":                        "ACI",
    "referencia/Catálogos":              "Catálogos",
    "referencia/Manuales":               "Manuales",
    "referencia/Normas técnicas":        "Normas técnicas",
    "normas/aashto":                     "AASHTO",
    "normas/aws":                        "AWS",
    "normas/ccp":                        "Codigo Colombiano Puentes",
    "referencia/Codigo Colombiano de Puentes": "Codigo Colombiano Puentes",
    "referencia/Latinoamerica":          "Normas Latinoamerica",
    "referencia/Internacionales":        "Normas Internacionales",
    "referencia/Leyes":                  "Leyes Colombia",
    # Memorias de proyectos propios (descargadas de Drive)
    "drive-sync/C75":                    "Proyectos-C75",
    "drive-sync/AMADEUS-Memorias":       "Proyectos-AMADEUS",
    "drive-sync/Planos":                 "Proyectos-Planos",
}

# Carpetas a omitir (figuras, etc.)
SKIP_DIRS = {"figuras", "__pycache__"}

client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None


def get_folder_for_pdf(pdf_path: Path) -> str:
    """Determina el folder de rag_chunks para un PDF dado su path."""
    rel = pdf_path.relative_to(DOCS_ROOT)
    parts = rel.parts

    # Probar desde la ruta más específica a la más genérica
    for length in range(len(parts) - 1, 0, -1):
        key = "/".join(parts[:length])
        if key in FOLDER_MAP:
            return FOLDER_MAP[key]
        # case-insensitive match
        for map_key, folder in FOLDER_MAP.items():
            if key.lower() == map_key.lower():
                return folder

    return "Referencia"  # fallback


def get_indexed_filenames(folder: str | None = None) -> set[str]:
    """Obtiene los filenames ya indexados en rag_chunks."""
    indexed = set()
    page = 0
    page_size = 1000
    while True:
        params = {
            "select": "filename",
            "limit": page_size,
            "offset": page * page_size,
        }
        if folder:
            params["folder"] = f"eq.{folder}"
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/rag_chunks",
            headers={**HEADERS, "Content-Type": "application/json"},
            params=params,
            timeout=30,
        )
        if not resp.ok:
            print(f"  WARNING: no se pudo obtener indexed list: {resp.status_code}")
            break
        rows = resp.json()
        if not rows:
            break
        for r in rows:
            indexed.add(r["filename"])
        if len(rows) < page_size:
            break
        page += 1
    return indexed


def extract_text_chunks(pdf_path: Path) -> list[dict]:
    """Extrae chunks de texto de un PDF. Retorna lista de {page, chunk_start, text}."""
    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        print(f"  ERROR abriendo PDF: {e}")
        return []

    chunks = []
    all_words = []  # (word, page_num)

    for page_num in range(len(doc)):
        try:
            page = doc[page_num]
            text = page.get_text("text")
            words = text.split()
            all_words.extend((w, page_num + 1) for w in words)
        except Exception:
            continue

    doc.close()

    if not all_words:
        return []

    # Chunking por palabras con overlap
    i = 0
    while i < len(all_words):
        end = min(i + CHUNK_SIZE, len(all_words))
        chunk_words = [w for w, _ in all_words[i:end]]
        chunk_text = " ".join(chunk_words)

        # Página del inicio del chunk
        page_num = all_words[i][1]

        # Saltar chunks demasiado cortos (encabezados, etc.)
        if len(chunk_words) < 30:
            i += CHUNK_SIZE - CHUNK_OVERLAP
            continue

        chunks.append({
            "page": page_num,
            "chunk_start": i,
            "chunk_text": chunk_text,
        })
        i += CHUNK_SIZE - CHUNK_OVERLAP

    return chunks


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Genera embeddings para una lista de textos."""
    if not client:
        raise RuntimeError("OPENAI_API_KEY no configurado")
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [e.embedding for e in resp.data]


def insert_chunks(filename: str, folder: str, chunks: list[dict]) -> int:
    """Inserta chunks en rag_chunks. Retorna número insertado."""
    inserted = 0

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]

        # Generar embeddings para el batch
        texts = [c["chunk_text"] for c in batch]
        try:
            embeddings = embed_texts(texts)
        except Exception as e:
            print(f"  ERROR embedding batch {i//BATCH_SIZE}: {e}")
            time.sleep(2)
            continue

        rows = [
            {
                "filename": filename,
                "folder": folder,
                "page": c["page"],
                "chunk_start": c["chunk_start"],
                "chunk_text": c["chunk_text"],
                "embedding": emb,
            }
            for c, emb in zip(batch, embeddings)
        ]

        resp = requests.post(
            f"{SUPABASE_URL}/rest/v1/rag_chunks",
            headers=HEADERS,
            json=rows,
            timeout=60,
        )
        if resp.ok:
            inserted += len(rows)
        else:
            print(f"  ERROR insert: {resp.status_code} {resp.text[:200]}")

        time.sleep(0.3)

    return inserted


def find_all_pdfs() -> list[Path]:
    """Encuentra todos los PDFs en la biblioteca de Leonardo."""
    pdfs = []
    for pdf in sorted(DOCS_ROOT.rglob("*.pdf")):
        # Omitir carpetas excluidas
        if any(skip in pdf.parts for skip in SKIP_DIRS):
            continue
        pdfs.append(pdf)
    return pdfs


def main():
    parser = argparse.ArgumentParser(description="Ingestar biblioteca Leonardo → Supabase")
    parser.add_argument("--dry-run", action="store_true", help="No insertar, solo mostrar qué haría")
    parser.add_argument("--folder", help="Filtrar por folder específico (ej: 'AISC Design Guides')")
    parser.add_argument("--force", action="store_true", help="Re-indexar aunque ya exista")
    parser.add_argument("--list", action="store_true", help="Solo listar PDFs y sus folders")
    args = parser.parse_args()

    if not OPENAI_KEY and not args.dry_run and not args.list:
        print("ERROR: OPENAI_API_KEY requerido para generar embeddings")
        sys.exit(1)

    pdfs = find_all_pdfs()
    print(f"\n{'=' * 60}")
    print(f"  Biblioteca Leonardo — {len(pdfs)} PDFs encontrados")
    print(f"{'=' * 60}\n")

    # Obtener ya indexados
    if not args.force and not args.dry_run and not args.list:
        print("Consultando Supabase para evitar re-indexar...")
        indexed = get_indexed_filenames()
        print(f"  {len(indexed)} filenames ya en rag_chunks\n")
    else:
        indexed = set()

    total_chunks = 0
    total_pdfs = 0
    skipped = 0

    for pdf_path in pdfs:
        folder = get_folder_for_pdf(pdf_path)

        # Filtro por folder si se especificó
        if args.folder and folder.lower() != args.folder.lower():
            continue

        filename = pdf_path.name

        if args.list:
            print(f"  [{folder}] {filename}")
            continue

        # Verificar si ya está indexado
        if filename in indexed and not args.force:
            print(f"  SKIP (ya indexado): {filename}")
            skipped += 1
            continue

        print(f"  ► [{folder}] {filename}")

        if args.dry_run:
            print(f"    DRY-RUN: extraería chunks")
            total_pdfs += 1
            continue

        # Extraer chunks
        chunks = extract_text_chunks(pdf_path)
        if not chunks:
            print(f"    WARNING: sin texto extraíble")
            continue

        print(f"    {len(chunks)} chunks → insertando...")

        # Insertar
        n = insert_chunks(filename, folder, chunks)
        print(f"    ✓ {n} chunks insertados")
        total_chunks += n
        total_pdfs += 1

        time.sleep(SLEEP_BETWEEN_PDFS)

    print(f"\n{'=' * 60}")
    print(f"  RESUMEN:")
    print(f"  PDFs procesados : {total_pdfs}")
    print(f"  PDFs omitidos   : {skipped}")
    print(f"  Chunks insertados: {total_chunks}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
