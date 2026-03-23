# Motor Normativo NSR-10 Colombia

Motor de IA para ingeniería estructural con la NSR-10 completamente indexada.

## Estado: 100% COMPLETO ✓

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
| **Nomenclatura** | 246 símbolos |
| **Figuras catálogo** | 116 |
| **Referencias externas** | 568 normas |
| **Imágenes PNG** | 745 |

### Verificación de Completitud

- ✓ **Tablas**: 100% (593 KG vs 498 PDF)
- ✓ **Figuras**: 100% (257 KG vs 241 PDF)  
- ✓ **Ecuaciones**: 100% (583 KG vs 514 PDF)
- ✓ **Referencias**: 568 normas (ASTM, ACI, AISC, AWS, NTC, ASCE)
- ✓ **Nomenclatura**: 246 símbolos técnicos

### Títulos NSR-10 Indexados

| Título | Tablas | Figuras | Ecuaciones |
|--------|--------|---------|------------|
| A - Sismo | 47 | 28 | 101 |
| B - Cargas | 21 | 27 | 48 |
| C - Concreto | 15 | 2 | 58 |
| D - Mampostería | 22 | 0 | 71 |
| E - Casas | 18 | 7 | 6 |
| F - Acero | 167 | 111 | 82 |
| G - Madera | 95 | 47 | 91 |
| H - Geotecnia | 23 | 8 | 31 |
| I - Supervisión | 6 | 0 | 0 |
| J - Incendio | 34 | 1 | 6 |
| K - Complementarios | 50 | 10 | 20 |

### Base de Datos

Supabase Project: `vdakfewjadwaczulcmvj`

### Uso

```python
# Búsqueda FTS en español
SELECT * FROM nsr10_secciones 
WHERE search_vector @@ to_tsquery('spanish', 'cortante & concreto');

# Knowledge Graph - Fórmulas
SELECT * FROM kg_nodes WHERE type = 'FORMULA' AND section_path LIKE 'C.%';

# Nomenclatura
SELECT * FROM nsr10_nomenclatura WHERE titulo = 'F';

# Referencias externas
SELECT * FROM nsr10_referencias WHERE codigo LIKE 'ASTM%';
```

### Fecha
Última actualización: 2026-03-23
