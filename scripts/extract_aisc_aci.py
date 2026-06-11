#!/usr/bin/env python3
"""
Extractor estructurado de AISC-360-16 y ACI-318-19/25 → Supabase.

Extrae secciones con jerarquía, fórmulas (LaTeX + Python), tablas de propiedades,
y cross-links con NSR-10.  Inserta en las tablas del schema 05_aisc_aci_schema.sql.

Uso:
    python3 scripts/extract_aisc_aci.py [--norm AISC|ACI|ALL] [--dry-run] [--resume]
"""
import os
import re
import sys
import json
import time
import argparse
import traceback
from pathlib import Path

import fitz          # PyMuPDF
import requests

# ─── Config ──────────────────────────────────────────────────────────────────

SUPABASE_URL = os.environ.get(
    "STRUOS_SUPABASE_URL",
    "https://vdakfewjadwaczulcmvj.supabase.co",
)
SERVICE_ROLE = os.environ.get(
    "STRUOS_SUPABASE_SERVICE_ROLE",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZkYWtmZXdqYWR3YWN6dWxjbXZqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzQyMzMwMiwiZXhwIjoyMDg4OTk5MzAyfQ.JfyNWc6KQWWsohqRkpqRot_7FAP85TtZkkIhZdvIBTs",
)

HEADERS = {
    "apikey": SERVICE_ROLE,
    "Authorization": f"Bearer {SERVICE_ROLE}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates,return=minimal",
}

DOCS_ROOT = Path("/root/agents/leonardo/docs")

# ─── Mapeo de fuentes ─────────────────────────────────────────────────────────

SOURCES = {
    "AISC-360-16": {
        "path": DOCS_ROOT / "referencia/AISC/AISC-360-16-Specification-Structural-Steel.pdf",
        "table": "aisc_secciones",
        "norm_code": "AISC-360-16",
        "chapter_pattern": r"^CHAPTER\s+([A-Z])\b",
        "section_pattern": r"^([A-Z]\d+(?:\.\d+[a-z]?)*)[\.\s]+(.+)$",
        "formula_pattern": r"\(Eq\.\s*([A-Z0-9\-\.]+)\)",
    },
    "ACI-318-19": {
        "path": DOCS_ROOT / "referencia/ACI/ACI-318-19-Building-Code-Commentary.pdf",
        "table": "aci_secciones",
        "norm_code": "ACI-318-19",
        "chapter_pattern": r"^CHAPTER\s+(\d+)\b",
        "section_pattern": r"^(\d+\.\d+(?:\.\d+)*)\s+(.+)$",
        "formula_pattern": r"\((\d+\.\d+[a-z]?)\)",
    },
    "ACI-318-25": {
        "path": DOCS_ROOT / "normas/aci/ACI-318-25_Building-Code-Structural-Concrete.pdf",
        "table": "aci_secciones",
        "norm_code": "ACI-318-25",
        "chapter_pattern": r"^CHAPTER\s+(\d+)\b",
        "section_pattern": r"^(\d+\.\d+(?:\.\d+)*)\s+(.+)$",
        "formula_pattern": r"\((\d+\.\d+[a-z]?)\)",
    },
}

# ─── NSR-10 cross-links conocidos (muestra — ampliable) ──────────────────────

NSR10_CROSSLINKS = [
    # NSR-10 adopta AISC-360 con modificaciones
    {"source_norm": "NSR-10", "source_section": "F.1.3",
     "target_norm": "AISC-360-16", "target_section": "A1",
     "link_type": "adopts", "note": "NSR-10 F.1.3 adopta AISC-360-16 con modificaciones sísmicas"},
    {"source_norm": "NSR-10", "source_section": "F.2",
     "target_norm": "AISC-360-16", "target_section": "B",
     "link_type": "adopts", "note": "Clasificación secciones compactas"},
    {"source_norm": "NSR-10", "source_section": "F.3",
     "target_norm": "AISC-360-16", "target_section": "D",
     "link_type": "adopts", "note": "Diseño elementos en tensión"},
    {"source_norm": "NSR-10", "source_section": "F.3",
     "target_norm": "AISC-360-16", "target_section": "E",
     "link_type": "adopts", "note": "Diseño elementos en compresión"},
    {"source_norm": "NSR-10", "source_section": "F.3",
     "target_norm": "AISC-360-16", "target_section": "F",
     "link_type": "adopts", "note": "Diseño vigas en flexión"},
    {"source_norm": "NSR-10", "source_section": "F.3",
     "target_norm": "AISC-360-16", "target_section": "G",
     "link_type": "adopts", "note": "Diseño vigas en corte"},
    {"source_norm": "NSR-10", "source_section": "F.3",
     "target_norm": "AISC-360-16", "target_section": "J",
     "link_type": "adopts", "note": "Diseño conexiones"},
    # ACI cross-links
    {"source_norm": "NSR-10", "source_section": "C.1.3",
     "target_norm": "ACI-318-19", "target_section": "1.1",
     "link_type": "adopts", "note": "NSR-10 C.1 adopta ACI-318 para concreto reforzado"},
    {"source_norm": "NSR-10", "source_section": "C.7",
     "target_norm": "ACI-318-19", "target_section": "22",
     "link_type": "adopts", "note": "Muros estructurales — NSR-10 C.7 ↔ ACI-318-19 Ch.22"},
    {"source_norm": "NSR-10", "source_section": "C.6",
     "target_norm": "ACI-318-19", "target_section": "18",
     "link_type": "modifies", "note": "Marcos resistentes — NSR-10 modifica ACI-318 Ch.18"},
]

# ─── Fórmulas AISC conocidas (LaTeX + Python ejecutable) ─────────────────────

AISC_FORMULAS: list[dict] = [
    {
        "norm_code": "AISC-360-16", "section_id": "D2",
        "formula_id": "Eq. D2-1",
        "description": "Resistencia nominal a tensión (fluencia sección bruta)",
        "latex": r"P_n = F_y \cdot A_g",
        "python_code": (
            "def pn_tension_yield(Fy: float, Ag: float) -> float:\n"
            "    '''Resistencia nominal tensión — fluencia Ag. Unidades consistentes.'''\n"
            "    return Fy * Ag"
        ),
        "variables": {"Fy": "límite elástico, ksi o MPa", "Ag": "área bruta, in² o cm²",
                      "Pn": "resistencia nominal, kip o kN"},
        "units": "kip o kN",
    },
    {
        "norm_code": "AISC-360-16", "section_id": "D2",
        "formula_id": "Eq. D2-2",
        "description": "Resistencia nominal a tensión (fractura sección neta)",
        "latex": r"P_n = F_u \cdot A_e",
        "python_code": (
            "def pn_tension_fracture(Fu: float, Ae: float) -> float:\n"
            "    '''Resistencia nominal tensión — fractura Ae.'''\n"
            "    return Fu * Ae"
        ),
        "variables": {"Fu": "resistencia última, ksi o MPa", "Ae": "área neta efectiva, in² o cm²"},
        "units": "kip o kN",
    },
    {
        "norm_code": "AISC-360-16", "section_id": "E3",
        "formula_id": "Eq. E3-1",
        "description": "Resistencia nominal compresión — pandeo flexional",
        "latex": r"P_n = F_{cr} \cdot A_g",
        "python_code": (
            "import math\n"
            "def pn_compression(Fy: float, Fe: float, Ag: float) -> float:\n"
            "    '''Resistencia compresión — pandeo flexional AISC E3.'''\n"
            "    ratio = Fy / Fe\n"
            "    if ratio <= 2.25:\n"
            "        Fcr = 0.658 ** ratio * Fy\n"
            "    else:\n"
            "        Fcr = 0.877 * Fe\n"
            "    return Fcr * Ag"
        ),
        "variables": {"Fy": "límite elástico, ksi", "Fe": "tensión crítica de Euler, ksi",
                      "Ag": "área bruta, in²", "Fcr": "tensión crítica, ksi"},
        "units": "kip",
    },
    {
        "norm_code": "AISC-360-16", "section_id": "F2",
        "formula_id": "Eq. F2-1",
        "description": "Momento nominal — fluencia (zona 1, sección compacta)",
        "latex": r"M_n = M_p = F_y \cdot Z_x",
        "python_code": (
            "def mn_flexure_compact(Fy: float, Zx: float) -> float:\n"
            "    '''Momento nominal — sección compacta sin LTB.'''\n"
            "    return Fy * Zx"
        ),
        "variables": {"Fy": "límite elástico, ksi", "Zx": "módulo plástico eje X, in³",
                      "Mp": "momento plástico, kip-in"},
        "units": "kip-in",
    },
    {
        "norm_code": "AISC-360-16", "section_id": "J3",
        "formula_id": "Eq. J3-1",
        "description": "Resistencia nominal perno en corte",
        "latex": r"R_n = F_{nv} \cdot A_b",
        "python_code": (
            "def rn_bolt_shear(Fnv: float, Ab: float) -> float:\n"
            "    '''Resistencia nominal perno en corte. Fnv según Tabla J3.2.'''\n"
            "    return Fnv * Ab"
        ),
        "variables": {"Fnv": "resistencia nominal a corte del perno, ksi",
                      "Ab": "área nominal del perno, in²"},
        "units": "kip",
    },
]

# ─── Fórmulas ACI conocidas ───────────────────────────────────────────────────

ACI_FORMULAS: list[dict] = [
    {
        "norm_code": "ACI-318-19", "section_id": "22.5.1.1",
        "formula_id": "(22-1)",
        "description": "Resistencia nominal a cortante en vigas sin refuerzo transversal",
        "latex": r"V_n = V_c = \left[8\lambda(\rho_w)^{1/3}\sqrt{f'_c} + N_u/6A_g\right] b_w d",
        "python_code": (
            "import math\n"
            "def vc_beam_no_stirrups(lamb: float, rho_w: float, fc: float,\n"
            "                        Nu: float, Ag: float, bw: float, d: float) -> float:\n"
            "    '''Cortante nominal viga sin estribos ACI-318-19 Ec.(22-1). Unidades SI (MPa, mm, N).'''\n"
            "    return (8 * lamb * rho_w**(1/3) * math.sqrt(fc) + Nu / (6 * Ag)) * bw * d"
        ),
        "variables": {"lamb": "factor liviana (1.0 normal)", "rho_w": "As/(bw·d)",
                      "fc": "f'c MPa", "Nu": "fuerza axial N (+ compresión)",
                      "Ag": "área bruta mm²", "bw": "ancho alma mm", "d": "peralte efectivo mm"},
        "units": "N",
    },
    {
        "norm_code": "ACI-318-19", "section_id": "22.4.2.1",
        "formula_id": "(22-2)",
        "description": "Resistencia nominal a compresión de columna espiral",
        "latex": r"P_n = 0.85 f'_c (A_g - A_{st}) + f_y A_{st}",
        "python_code": (
            "def pn_column_spiral(fc: float, Ag: float, Ast: float, fy: float) -> float:\n"
            "    '''Resistencia axial nominal columna espiral ACI.'''\n"
            "    return 0.85 * fc * (Ag - Ast) + fy * Ast"
        ),
        "variables": {"fc": "f'c MPa", "Ag": "área bruta mm²",
                      "Ast": "área total refuerzo longitudinal mm²", "fy": "fy MPa"},
        "units": "N",
    },
    {
        "norm_code": "ACI-318-19", "section_id": "22.2.2",
        "formula_id": "(22-3)",
        "description": "Momento nominal sección rectangular (bloque rectangular Whitney)",
        "latex": r"M_n = A_s f_y \left(d - \frac{a}{2}\right),\quad a = \frac{A_s f_y}{0.85 f'_c b}",
        "python_code": (
            "def mn_beam_rect(As: float, fy: float, d: float, fc: float, b: float) -> float:\n"
            "    '''Momento nominal viga rect. ACI bloque Whitney.'''\n"
            "    a = As * fy / (0.85 * fc * b)\n"
            "    return As * fy * (d - a / 2)"
        ),
        "variables": {"As": "área refuerzo traccionado mm²", "fy": "fy MPa",
                      "d": "peralte efectivo mm", "fc": "f'c MPa",
                      "b": "ancho a compresión mm", "a": "profundidad bloque compresión mm"},
        "units": "N·mm",
    },
]


# ─── Helpers Supabase ─────────────────────────────────────────────────────────

def sb_upsert(table: str, rows: list[dict], dry_run: bool = False) -> int:
    if not rows:
        return 0
    if dry_run:
        print(f"    DRY-RUN → {len(rows)} filas en {table}")
        return len(rows)
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=HEADERS,
        json=rows,
        timeout=60,
    )
    if not resp.ok:
        print(f"  ERROR upsert {table}: {resp.status_code} {resp.text[:300]}")
        return 0
    return len(rows)


def sb_upsert_crosslinks(links: list[dict], dry_run: bool = False) -> int:
    return sb_upsert("norm_crosslinks", links, dry_run)


def sb_upsert_formulas(formulas: list[dict], dry_run: bool = False) -> int:
    return sb_upsert("norm_formulas", formulas, dry_run)


def sb_upsert_secciones(table: str, rows: list[dict], dry_run: bool = False) -> int:
    # Deduplicar por (norm_code, section_id) — el parser puede emitir la misma sección dos veces
    seen: set[tuple] = set()
    unique_rows = []
    for r in rows:
        key = (r["norm_code"], r["section_id"])
        if key not in seen:
            seen.add(key)
            unique_rows.append(r)

    if len(unique_rows) < len(rows):
        print(f"  dedup: {len(rows)} → {len(unique_rows)} filas únicas")

    # Insertar en batches de 200 para evitar errores de payload
    batch_size = 200
    total = 0
    for i in range(0, len(unique_rows), batch_size):
        batch = unique_rows[i : i + batch_size]
        n = sb_upsert(table, batch, dry_run)
        total += n
    return total


# ─── Extracción de texto por sección ─────────────────────────────────────────

def extract_sections_from_pdf(cfg: dict) -> list[dict]:
    """Extrae secciones jerárquicas de un PDF normativo."""
    pdf_path = cfg["path"]
    norm_code = cfg["norm_code"]
    section_re = re.compile(cfg["section_pattern"], re.MULTILINE)
    chapter_re = re.compile(cfg["chapter_pattern"], re.MULTILINE)

    if not pdf_path.exists():
        print(f"  SKIP: no existe {pdf_path}")
        return []

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        print(f"  ERROR abriendo {pdf_path.name}: {e}")
        return []

    sections: list[dict] = []
    current_section: dict | None = None
    current_chapter = ""

    print(f"  Escaneando {doc.page_count} páginas de {pdf_path.name}...")

    for page_num in range(min(doc.page_count, 800)):
        try:
            page = doc[page_num]
            text = page.get_text("text")
        except Exception:
            continue

        for line in text.splitlines():
            line_s = line.strip()
            if not line_s:
                continue

            # Detectar capítulo
            chap_m = chapter_re.match(line_s)
            if chap_m:
                current_chapter = chap_m.group(1)
                continue

            # Detectar sección
            sec_m = section_re.match(line_s)
            if sec_m:
                sec_id = sec_m.group(1)
                sec_title = sec_m.group(2).strip()

                # Guardar sección anterior
                if current_section:
                    sections.append(current_section)

                # Determinar nivel
                dots = sec_id.count(".")
                level = dots + 2 if dots > 0 else 2

                # Determinar parent
                if dots > 0:
                    parent_id = sec_id.rsplit(".", 1)[0]
                else:
                    parent_id = current_chapter if current_chapter else None

                current_section = {
                    "norm_code": norm_code,
                    "chapter": current_chapter or sec_id[0] if sec_id else None,
                    "section_id": sec_id,
                    "parent_id": parent_id,
                    "title": sec_title[:500],
                    "body": "",
                    "page_start": page_num + 1,
                    "page_end": page_num + 1,
                    "level": level,
                    "has_formula": False,
                    "has_table": False,
                    "source_file": pdf_path.name,
                }
            else:
                # Acumular texto en sección actual
                if current_section:
                    current_section["body"] = (current_section["body"] + " " + line_s).strip()
                    current_section["page_end"] = page_num + 1
                    if "Eq." in line_s or re.search(r"\(\d+\.\d+", line_s):
                        current_section["has_formula"] = True
                    if "Table" in line_s or "Tabla" in line_s:
                        current_section["has_table"] = True
                    # Limitar body a 4000 chars
                    if len(current_section["body"]) > 4000:
                        current_section["body"] = current_section["body"][:4000]

    if current_section:
        sections.append(current_section)

    doc.close()
    print(f"  {len(sections)} secciones extraídas de {pdf_path.name}")
    return sections


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Extractor estructurado AISC + ACI → Supabase")
    parser.add_argument("--norm", default="ALL", choices=["AISC", "ACI", "ALL"],
                        help="Norma a procesar")
    parser.add_argument("--dry-run", action="store_true", help="No insertar, solo mostrar")
    parser.add_argument("--skip-sections", action="store_true", help="Omitir extracción de secciones")
    parser.add_argument("--skip-formulas", action="store_true", help="Omitir fórmulas")
    parser.add_argument("--skip-crosslinks", action="store_true", help="Omitir cross-links")
    args = parser.parse_args()

    print(f"\n{'=' * 60}")
    print(f"  Extractor Estructurado AISC + ACI — Fase 2")
    print(f"  Norma: {args.norm}  |  dry-run: {args.dry_run}")
    print(f"{'=' * 60}\n")

    total_sections = 0
    total_formulas = 0
    total_crosslinks = 0

    # ── Secciones ──────────────────────────────────────────────────────────────
    if not args.skip_sections:
        for key, cfg in SOURCES.items():
            if args.norm == "AISC" and not key.startswith("AISC"):
                continue
            if args.norm == "ACI" and not key.startswith("ACI"):
                continue

            print(f"\n► Procesando {key}...")
            sections = extract_sections_from_pdf(cfg)

            if sections:
                n = sb_upsert_secciones(cfg["table"], sections, args.dry_run)
                total_sections += n
                print(f"  ✓ {n} secciones upserted en {cfg['table']}")

            time.sleep(0.5)

    # ── Fórmulas ───────────────────────────────────────────────────────────────
    if not args.skip_formulas:
        formulas = []
        if args.norm in ("AISC", "ALL"):
            formulas.extend(AISC_FORMULAS)
        if args.norm in ("ACI", "ALL"):
            formulas.extend(ACI_FORMULAS)

        if formulas:
            print(f"\n► Insertando {len(formulas)} fórmulas estructuradas...")
            n = sb_upsert_formulas(formulas, args.dry_run)
            total_formulas += n
            print(f"  ✓ {n} fórmulas upserted en norm_formulas")

    # ── Cross-links ────────────────────────────────────────────────────────────
    if not args.skip_crosslinks:
        links = NSR10_CROSSLINKS
        if args.norm == "AISC":
            links = [l for l in links if l["target_norm"].startswith("AISC")]
        elif args.norm == "ACI":
            links = [l for l in links if l["target_norm"].startswith("ACI")]

        print(f"\n► Insertando {len(links)} cross-links NSR-10 ↔ AISC/ACI...")
        n = sb_upsert_crosslinks(links, args.dry_run)
        total_crosslinks += n
        print(f"  ✓ {n} cross-links upserted en norm_crosslinks")

    print(f"\n{'=' * 60}")
    print(f"  RESUMEN Fase 2:")
    print(f"  Secciones insertadas : {total_sections}")
    print(f"  Fórmulas insertadas  : {total_formulas}")
    print(f"  Cross-links insertados: {total_crosslinks}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
