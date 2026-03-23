# Normative Engine - NSR-10 Colombia

Motor de IA para ingeniería estructural con la NSR-10 completamente indexada.

## Estado: 100% Completado

### Knowledge Graph

| Componente | Cantidad |
|------------|----------|
| **Nodos totales** | 3,109 |
| **Edges** | 2,488 |
| Fórmulas | 583 |
| Tablas | 593 |
| Figuras | 257 |
| Secciones | 706 |
| Definiciones | 219 |

### Datos SQL

| Componente | Cantidad |
|------------|----------|
| **Secciones FTS** | 12,789 |
| **Fórmulas** | 558 |
| **Nomenclatura** | 223 símbolos |
| **Figuras catálogo** | 116 |
| **Referencias externas** | 67 normas |
| **Imágenes PNG** | 745 |

### Títulos NSR-10

- **A** - Requisitos sismo resistente (61 fórmulas)
- **B** - Cargas (48 tablas)
- **C** - Concreto estructural (58 fórmulas)
- **D** - Mampostería estructural (94 fórmulas)
- **E** - Casas 1-2 pisos
- **F** - Estructuras metálicas (167 tablas, 111 figuras)
- **G** - Madera y Guadua (95 tablas)
- **H** - Estudios geotécnicos
- **I** - Supervisión técnica
- **J** - Protección contra incendio
- **K** - Requisitos complementarios

### Base de Datos

Supabase Project: `vdakfewjadwaczulcmvj`

### Uso

```python
# Consulta SQL directa
SELECT * FROM nsr10_barras_refuerzo WHERE numero = 5;

# Búsqueda FTS en español
SELECT * FROM nsr10_secciones 
WHERE search_vector @@ to_tsquery('spanish', 'cortante & concreto');

# Knowledge Graph
SELECT * FROM kg_nodes WHERE type = 'FORMULA' AND section_path LIKE 'C.%';
```

### Estructura

```
normative-engine/
├── scripts/           # API y extracción
├── figuras/           # 745 imágenes PNG
├── sql/               # Esquemas SQL
├── kg/                # Knowledge Graph data
└── README.md
```

### Fecha

Última actualización: 2026-03-23
