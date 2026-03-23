# Normative Engine - NSR-10

Motor normativo para ingeniería estructural con la NSR-10 de Colombia completamente indexada.

## Estado: 100% Completado

### Componentes

| Componente | Cantidad |
|------------|----------|
| Tablas SQL | 256 |
| Secciones FTS | 12,789 |
| Figuras PNG | 745 |
| Figuras catálogo | 116 |
| Nomenclatura | 223 símbolos |
| Referencias | 67 normas |
| Fórmulas Python/LaTeX | 29 |
| KG Nodos | 1,000 |
| KG Edges | 1,000 |

### Títulos NSR-10

- **A** - Sismo (42 tablas, 557 secciones)
- **B** - Cargas (13 tablas, 187 secciones)
- **C** - Concreto (19 tablas, 1000 secciones)
- **D** - Mampostería (13 tablas, 472 secciones)
- **E** - Casas 1-2 pisos (15 tablas, 258 secciones)
- **F** - Acero (54 tablas, 1000 secciones)
- **G** - Madera/Guadua (31 tablas, 514 secciones)
- **H** - Geotecnia (22 tablas, 241 secciones)
- **I** - Supervisión (7 tablas, 63 secciones)
- **J** - Incendio (14 tablas, 160 secciones)
- **K** - Complementarios (12 tablas, 423 secciones)

### Base de Datos

Supabase Project: `vdakfewjadwaczulcmvj`

### Estructura

```
normative-engine/
├── scripts/           # Scripts de extracción y API
├── figuras/           # 745 imágenes PNG extraídas
│   ├── titulo_a/
│   ├── titulo_b/
│   └── ...
├── docs/              # Documentación
└── README.md
```

### Uso

```python
# Consultar tabla SQL
SELECT * FROM nsr10_barras_refuerzo WHERE numero = 5;

# Búsqueda FTS
SELECT * FROM nsr10_secciones 
WHERE search_vector @@ to_tsquery('spanish', 'cortante & concreto');

# Fórmula Python
from nsr10_formulas import Mn_flexion
Mn = Mn_flexion(As=12.7, fy=420, d=450, a=85)  # kN·m
```

### Fecha

Última actualización: 2026-03-23
