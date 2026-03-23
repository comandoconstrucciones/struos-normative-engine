# Esquema del Knowledge Graph — NSR-10

## Tipos de Nodos

| Tipo | Descripción | Campos Clave |
|------|-------------|--------------|
| SECTION | Sección del documento | title, content |
| FORMULA | Ecuación matemática | formula_latex, formula_python, formula_variables |
| SYMBOL | Variable de nomenclatura | title (símbolo), content (definición) |
| DEFINITION | Término del glosario | title (término), content (definición) |
| TABLE | Tabla de datos | table_headers, table_rows, table_sql_ref |
| FIGURE | Figura/gráfico | source_pdf (URL imagen) |
| EXTERNAL_REF | Norma externa citada | title (código), content (título completo) |

## Tipos de Aristas

| Tipo | Fuente → Destino | Descripción |
|------|------------------|-------------|
| CONTAINS | SECTION → SECTION/FORMULA/TABLE | Jerarquía |
| CITES | SECTION → EXTERNAL_REF | Cita norma |
| EQUIVALENT | EXTERNAL_REF ↔ EXTERNAL_REF | NTC ↔ ASTM |
| **USES_SYMBOL** | FORMULA → SYMBOL | Fórmula usa símbolo |
| **DEFINED_IN** | SYMBOL → SECTION | Símbolo definido en |
| **REFERENCES** | SECTION → SECTION | "Véase A.X.X" |
| **APPLIES_TO** | TABLE → FORMULA | Tabla da datos a fórmula |

## Ejemplo: Fórmula A.2.4-3

```
N̄ch = ds / Σ(di/Ni)

├── USES_SYMBOL → ds
├── USES_SYMBOL → di  
├── USES_SYMBOL → Ni
├── USES_SYMBOL → m
├── CITES → ASTM D 1586
└── DEFINED_IN → A.2.4.3
```
