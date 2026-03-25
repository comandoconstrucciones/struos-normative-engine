# ComandoCalc — Roadmap de Mejoras

> Documento generado: 2026-03-25
> Última revisión del código: commit `d2a86eb`

---

## Estado Actual del Proyecto

### Módulos Implementados (17)

| Módulo | Calculador | Endpoint | Norma |
|--------|------------|----------|-------|
| Viga mezanine | `beam_calculator.py` | `/api/calc/beam`, `/optimal` | AISC F |
| Columna | `column_calculator.py` | `/api/calc/column`, `/optimal` | AISC E |
| Correas cubierta | `purlin_calculator.py` | `/api/calc/purlin` | NSR-10 B |
| Correas fachada | `facade_purlin_calculator.py` | `/api/calc/facade-purlin` | NSR-10 B |
| Viento | `wind_calculator.py` | `/api/calc/wind` | NSR-10 B.6 |
| Vibraciones | `vibration_calculator.py` | `/api/calc/vibration`, `/optimal` | AISC DG11 |
| Steel Deck | `steeldeck_calculator.py` | `/api/calc/steeldeck`, `/optimal` | AISC |
| Placa base | `connection_calculator.py` | `/api/calc/baseplate` | AISC DG1 |
| Shear Tab | `connection_calculator.py` | `/api/calc/connection/shear-tab` | AISC J3, J4 |
| Soldadura filete | `connection_calculator.py` | `/api/calc/connection/fillet-weld` | AISC J2 |
| Conexión momento | `connection_calculator.py` | `/api/calc/connection/moment` | AISC J2, J4 |
| Cercha | `truss_calculator.py` | `/api/calc/truss`, `/optimal` | AISC |
| Pórtico 2D | `frame_calculator.py` | `/api/calc/frame` | NSR-10 A |
| Flexo-compresión | `flexo_compression_calculator.py` | `/api/calc/flexo-compression` | AISC H1 |
| Columna compuesta | `composite_column_calculator.py` | `/api/calc/composite-column` | AISC I |
| Presupuesto | `budget_calculator.py` | `/api/calc/budget` | — |
| Nave industrial | `industrial_building_calculator.py` | `/api/calc/industrial-building` | AISC + NSR-10 |

### Conexiones Implementadas

| Tipo | Clase | Estado |
|------|-------|--------|
| Placa base | `BasePlateCalculator` | ✅ Completo |
| Shear tab (cortante) | `ShearTabCalculator` | ✅ Completo |
| Soldadura filete | `FilletWeldCalculator` | ✅ Completo |
| Conexión momento soldada | `MomentConnectionCalculator` | ✅ Completo |

---

## Roadmap de Mejoras

### Fase 1: Quick Wins (1-2 semanas)

#### 1.1 Top 3 Perfiles en vez de 1 Óptimo
**Prioridad:** Alta | **Esfuerzo:** Bajo | **Impacto:** Alto

**Problema:** Los endpoints `/optimal` solo devuelven 1 perfil. En la práctica, el ingeniero quiere ver alternativas porque:
- El perfil óptimo puede no estar disponible en bodega
- A veces un perfil ligeramente más pesado es más barato por oferta
- El cliente puede preferir estética (HEA vs IPE)

**Implementación:**
1. Modificar `select_optimal_beam()`, `select_optimal_column()`, etc.
2. En vez de `return best`, hacer `return sorted_profiles[:3]`
3. Agregar campo `alternatives` al response schema
4. Incluir delta de peso vs óptimo: `+5.2 kg/m (+12%)`

**Archivos a modificar:**
- `backend/calculators/beam_calculator.py` → `select_optimal_beam()`
- `backend/calculators/column_calculator.py` → `select_optimal_column()`
- `backend/calculators/purlin_calculator.py` → `select_optimal_purlin()`
- `backend/models/schemas.py` → Agregar `alternatives: List[ProfileResult]`

**Ejemplo de response:**
```json
{
  "optimal": {
    "profile": "IPE 200",
    "weight_kg_m": 22.4,
    "utilization": 0.87
  },
  "alternatives": [
    {"profile": "IPE 220", "weight_kg_m": 26.2, "delta_weight": "+17%", "utilization": 0.72},
    {"profile": "HEA 180", "weight_kg_m": 35.5, "delta_weight": "+58%", "utilization": 0.65}
  ]
}
```

---


### Fase 2: Cálculo Sísmico Real (2-3 semanas)

#### 2.1 Espectro de Diseño NSR-10
**Prioridad:** Alta | **Esfuerzo:** Medio | **Impacto:** Muy Alto

**Problema:** ComandoCalc no tiene análisis sísmico. El endpoint de viento existe, pero sismo no.

**Alcance:**
- Espectro elástico de aceleraciones (NSR-10 A.2.6)
- Espectro de diseño reducido por R
- Período fundamental aproximado Ta (NSR-10 A.4.2)
- Cortante basal (NSR-10 A.4.3)
- Distribución vertical de fuerzas (NSR-10 A.4.3)

**Implementación:**

Nuevo archivo: `backend/calculators/seismic_calculator.py`

```python
"""
Análisis sísmico según NSR-10 Título A

Normas referenciadas:
- A.2.4 — Coeficientes de sitio Fa, Fv
- A.2.6 — Espectro elástico de aceleraciones
- A.3 — Coeficientes de disipación de energía R
- A.4.2 — Período fundamental aproximado
- A.4.3 — Cortante sísmico en la base
- A.4.4 — Distribución vertical de fuerzas
"""

@dataclass
class SeismicInput:
    # Ubicación
    municipio: str              # o Aa, Av directos
    
    # Suelo
    soil_type: str              # A, B, C, D, E, F
    
    # Estructura
    system_type: str            # portico_concreto_des, muro_concreto_dmo, etc.
    height_m: float             # Altura total
    num_stories: int
    story_weights_kn: List[float]  # Peso por piso
    ct: float = 0.047           # Coef para período (0.047 pórticos concreto)
    alpha: float = 0.9          # Exponente (0.9 pórticos, 0.75 otros)
    
    # Importancia
    importance_group: str = "II"  # I, II, III, IV

@dataclass
class SeismicResult:
    # Parámetros básicos
    Aa: float
    Av: float
    Fa: float
    Fv: float
    I: float                    # Coeficiente de importancia
    
    # Sistema estructural
    R0: float
    omega0: float
    Cd: float
    R: float                    # R efectivo = R0 * phi_a * phi_r * phi_p
    
    # Espectro
    T0: float                   # Período corto
    Tc: float                   # Período de transición
    TL: float                   # Período largo
    
    # Período estructura
    Ta: float                   # Período aproximado
    Cu: float                   # Factor de amplificación
    T_max: float                # = Cu * Ta
    
    # Aceleraciones espectrales
    Sa_T: float                 # Sa en período T
    Sa_design: float            # Sa / R (para diseño)
    
    # Fuerzas
    Vs_kn: float                # Cortante basal
    k: float                    # Exponente distribución vertical
    story_forces_kn: List[float]  # Fx por piso
    story_shears_kn: List[float]  # Vx acumulado
    story_moments_kn_m: List[float]  # Momento de volcamiento
```

**Tablas Struos a usar:**
- `nsr10_municipios` → Aa, Av, zona
- `nsr10_coef_fa` → Fa por suelo/Aa
- `nsr10_coef_fv` → Fv por suelo/Av
- `nsr10_coef_r` → R0, Ω0, Cd por sistema
- `nsr10_coef_importancia` → I por grupo

**Endpoint:**
```
POST /api/calc/seismic
{
  "municipio": "Bogota",
  "soil_type": "D",
  "system_type": "portico_concreto_des",
  "height_m": 15.0,
  "num_stories": 5,
  "story_weights_kn": [800, 800, 800, 800, 600],
  "importance_group": "II"
}
```

**Response:**
```json
{
  "location": {"municipio": "Bogotá", "Aa": 0.15, "Av": 0.20, "zona": "Intermedia"},
  "site_coefficients": {"Fa": 1.35, "Fv": 1.90},
  "system": {"type": "Pórtico concreto DES", "R0": 7.0, "omega0": 3.0, "Cd": 5.5, "R": 7.0},
  "importance": {"group": "II", "I": 1.0},
  "spectrum": {"T0": 0.084, "Tc": 0.42, "TL": 2.4},
  "period": {"Ta": 0.53, "Cu": 1.75, "T_design": 0.53},
  "accelerations": {"Sa_elastic": 0.71, "Sa_design": 0.10},
  "base_shear": {
    "Vs_kn": 360.0,
    "Vs_ratio": "10.0% W"
  },
  "vertical_distribution": [
    {"story": 5, "height_m": 15.0, "Wx_kn": 600, "Fx_kn": 108.0, "Vx_kn": 108.0},
    {"story": 4, "height_m": 12.0, "Wx_kn": 800, "Fx_kn": 86.4, "Vx_kn": 194.4},
    {"story": 3, "height_m": 9.0, "Wx_kn": 800, "Fx_kn": 64.8, "Vx_kn": 259.2},
    {"story": 2, "height_m": 6.0, "Wx_kn": 800, "Fx_kn": 43.2, "Vx_kn": 302.4},
    {"story": 1, "height_m": 3.0, "Wx_kn": 800, "Fx_kn": 57.6, "Vx_kn": 360.0}
  ],
  "checks": {
    "min_Vs": {"value": 0.03, "limit": 0.03, "status": "OK"},
    "T_vs_Tc": "T > Tc → usar espectro descendente"
  },
  "references": ["NSR-10 A.2.6", "NSR-10 A.4.2-1", "NSR-10 A.4.3-1"]
}
```

---

### Fase 3: Conexiones Adicionales (3-4 semanas)

#### 3.1 Clip Angles (Ángulos de conexión)
**Norma:** AISC 360-16 J3, J4 | AISC Design Guide 4

**Alcance:**
- Conexión doble ángulo a cortante
- Pernos en alma de viga + pernos/soldadura en soporte
- Chequeos: cortante pernos, aplastamiento, ruptura bloque, flexión ángulo

**Implementación:**
```python
@dataclass
class ClipAngleInput:
    Vu_kn: float                # Cortante último
    beam_profile: str           # Perfil de viga
    support_type: str           # "column_flange" | "column_web" | "girder_web"
    angle_size: str             # L4x4x3/8, L5x3.5x3/8, etc.
    bolt_type: str              # A325, A490
    bolt_diameter: str          # 3/4", 7/8"
    num_bolts: int
    bolt_spacing_cm: float
    edge_distance_cm: float
```

---

#### 3.2 End Plate (Placa de tope a momento)
**Norma:** AISC 360-16 J10 | AISC Design Guide 4, 16

**Tipos:**
- 4-bolt unstiffened
- 4-bolt stiffened
- 8-bolt stiffened

**Implementación:**
```python
@dataclass
class EndPlateInput:
    Mu_kn_m: float              # Momento último
    Vu_kn: float                # Cortante último
    beam_profile: str
    column_profile: str
    plate_type: str             # "4E", "4ES", "8ES"
    plate_thickness_mm: float
    bolt_type: str
    bolt_diameter: str
    stiffener_thickness_mm: float = None
```

**Chequeos requeridos:**
- Flexión placa de tope
- Tracción pernos
- Cortante pernos
- Pandeo local ala columna (si aplica)
- Fluencia panel zone
- Soldadura viga-placa

---

#### 3.3 Conexión Arriostrada (Bracing Connection)
**Norma:** AISC 360-16 J4 | AISC Seismic Provisions

**Alcance:**
- Gusset plate a nudo viga-columna
- Riostras en X, V invertida, diagonal
- Método Whitmore, Thornton

**Implementación:**
```python
@dataclass
class BracingConnectionInput:
    brace_force_kn: float       # Tracción/compresión
    brace_profile: str          # HSS, ángulo doble, W
    beam_profile: str
    column_profile: str
    gusset_thickness_mm: float
    connection_type: str        # "bolted" | "welded"
    brace_angle_deg: float      # Ángulo vs horizontal
```

**Chequeos:**
- Ancho Whitmore
- Pandeo gusset (Thornton)
- Longitud de soldadura/pernos
- Interfaz gusset-viga, gusset-columna

---

#### 3.4 Empalme de Columna
**Norma:** AISC 360-16 J1.4, M2.1 | AISC Design Guide 4

**Tipos:**
- Empalme con contacto directo (bearing)
- Empalme con placa dividida
- Empalme para transición de sección

**Implementación:**
```python
@dataclass
class ColumnSpliceInput:
    Pu_kn: float
    Mux_kn_m: float
    Muy_kn_m: float
    upper_column: str           # Perfil superior (más pequeño)
    lower_column: str           # Perfil inferior
    splice_type: str            # "bearing" | "divided_plate"
    splice_height_m: float      # Altura sobre piso
```

---

### Fase 4: Precios y Disponibilidad en Tiempo Real (4-6 semanas)

#### 4.1 Arquitectura del Sistema de Precios

**Problema:** No existe API pública de precios de acero en Colombia. Los distribuidores (Corpacero, Colmena, Diaco, Aceros Mapa) publican listas en PDF o solo por cotización telefónica.

**Solución propuesta:**

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   ComandoCalc   │────▶│  Price Aggregator │────▶│    Supabase     │
│    Frontend     │     │     Service       │     │  (cache 24h)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
         ┌──────────┐   ┌──────────┐   ┌──────────┐
         │ Corpacero│   │ Colmena  │   │Aceros    │
         │ Scraper  │   │ Scraper  │   │Mapa API  │
         └──────────┘   └──────────┘   └──────────┘
```

**Componentes:**

**1. Scrapers por proveedor** (Python + Playwright)
- Corpacero: Login → catálogo → extraer precios
- Colmena: Descargar PDF lista → OCR → parse
- Aceros Mapa: Si tienen API, usar directamente

**2. Price Aggregator Service** (FastAPI)
- Endpoint: `GET /api/prices/{profile_type}`
- Cache en Supabase con TTL 24h
- Fallback a precio estimado si no hay dato fresco

**3. Tabla Supabase: `steel_prices`**
```sql
CREATE TABLE steel_prices (
  id SERIAL PRIMARY KEY,
  profile_designation VARCHAR(50),     -- IPE200, HEA180, TR80x80x3
  profile_type VARCHAR(20),            -- ipe, hea, tubular_square
  supplier VARCHAR(50),                -- corpacero, colmena, diaco
  price_cop_kg DECIMAL(10,2),          -- Precio por kg
  price_cop_unit DECIMAL(12,2),        -- Precio por barra (6m, 12m)
  unit_length_m DECIMAL(4,2),          -- 6.0, 12.0
  in_stock BOOLEAN,
  stock_quantity INTEGER,              -- NULL si no disponible
  city VARCHAR(50),                    -- bodega: bogota, medellin, cali
  updated_at TIMESTAMP,
  source_url TEXT
);
```

**4. Integración en Response de Cálculo**
```json
{
  "optimal": {
    "profile": "IPE 200",
    "weight_kg_m": 22.4,
    "total_weight_kg": 134.4,
    "pricing": {
      "available_suppliers": [
        {
          "supplier": "Corpacero",
          "price_cop_kg": 5200,
          "price_cop_total": 698880,
          "in_stock": true,
          "delivery_days": 1,
          "city": "Bogotá"
        },
        {
          "supplier": "Colmena",
          "price_cop_kg": 5400,
          "price_cop_total": 725760,
          "in_stock": true,
          "delivery_days": 3,
          "city": "Medellín"
        }
      ],
      "best_price": {"supplier": "Corpacero", "cop": 698880},
      "price_updated": "2026-03-25T10:30:00Z"
    }
  }
}
```

**5. Página de Precios en Frontend**
- `/precios` → Vista de precios actuales por categoría
- Comparador visual entre proveedores
- Historial de precios (gráfico últimos 30 días)
- Alerta de disponibilidad baja

**Consideraciones legales:**
- Scraping de precios públicos es legal en Colombia
- Almacenar y mostrar precios con atribución al proveedor
- No hacer reverse engineering de sistemas protegidos
- Contactar proveedores para partnership formal (preferible)

---

### Fase 5: Render 3D Automático (4-6 semanas)

#### 5.1 Arquitectura del Visor 3D

**Stack:**
- Three.js (rendering)
- React Three Fiber (integración React)
- @react-three/drei (helpers)

**Implementación:**

**1. Endpoint de geometría**
```
GET /api/render/frame/{calc_id}
→ Devuelve JSON con nodos, elementos, secciones
```

**2. Componente React**
```tsx
// frontend/src/components/StructureViewer.tsx
import { Canvas } from '@react-three/fiber'
import { OrbitControls, PerspectiveCamera } from '@react-three/drei'

interface Node { id: string; x: number; y: number; z: number }
interface Element { id: string; start: string; end: string; profile: string }

export function StructureViewer({ nodes, elements }: Props) {
  return (
    <Canvas>
      <PerspectiveCamera makeDefault position={[20, 15, 20]} />
      <OrbitControls />
      <ambientLight intensity={0.5} />
      <directionalLight position={[10, 10, 5]} />
      
      {/* Nodos */}
      {nodes.map(n => (
        <mesh key={n.id} position={[n.x, n.y, n.z]}>
          <sphereGeometry args={[0.1]} />
          <meshStandardMaterial color="red" />
        </mesh>
      ))}
      
      {/* Elementos como líneas o extrusiones */}
      {elements.map(e => (
        <BeamMesh key={e.id} start={nodes[e.start]} end={nodes[e.end]} profile={e.profile} />
      ))}
    </Canvas>
  )
}
```

**3. Perfiles como extrusiones**
- Cargar sección transversal (IPE, HEA) como Shape
- Extruir a lo largo de la línea del elemento
- Colores por tipo: columnas=azul, vigas=verde, arriostres=naranja

**4. Interactividad**
- Click en elemento → muestra propiedades
- Hover → highlight
- Panel lateral con lista de elementos
- Toggle: wireframe / solid / analysis results

**5. Export**
- Screenshot PNG
- Export STL para impresión 3D
- Export glTF para AR/VR

---

### Fase 6: Integración BIM — IFC Export (6-8 semanas)

#### 6.1 Exportación IFC

**Librería:** `ifcopenshell` (Python)

**Implementación:**

```python
# backend/core/ifc_generator.py
import ifcopenshell
from ifcopenshell.api import run

def create_structure_ifc(frame_result: FrameCalcResponse) -> bytes:
    """Genera archivo IFC desde resultado de cálculo de pórtico"""
    
    model = ifcopenshell.file(schema="IFC4")
    
    # Crear proyecto
    project = run("root.create_entity", model, ifc_class="IfcProject", name="ComandoCalc Export")
    
    # Crear site, building, storey
    site = run("root.create_entity", model, ifc_class="IfcSite", name="Site")
    building = run("root.create_entity", model, ifc_class="IfcBuilding", name="Structure")
    storey = run("root.create_entity", model, ifc_class="IfcBuildingStorey", name="Ground Floor")
    
    # Agregar relaciones espaciales
    run("aggregate.assign_object", model, relating_object=project, product=site)
    run("aggregate.assign_object", model, relating_object=site, product=building)
    run("aggregate.assign_object", model, relating_object=building, product=storey)
    
    # Crear elementos estructurales
    for col in frame_result.columns:
        column = run("root.create_entity", model, ifc_class="IfcColumn", name=col.id)
        # Asignar geometría, perfil, material...
        
    for beam in frame_result.beams:
        beam_ifc = run("root.create_entity", model, ifc_class="IfcBeam", name=beam.id)
        # ...
    
    # Exportar a bytes
    return model.to_string().encode()
```

**Endpoint:**
```
POST /api/export/ifc/frame
Content-Type: application/json
→ Returns: application/octet-stream (archivo .ifc)
```

**Metadatos incluidos:**
- Propiedades de perfil (área, inercia, peso)
- Material (acero A36, A572)
- Cargas aplicadas (como IfcStructuralLoadSingleForce)
- Resultados (fuerzas internas como custom psets)

---

## Resumen de Prioridades

| Fase | Mejora | Esfuerzo | Impacto | Prioridad |
|------|--------|----------|---------|-----------|
| 1.1 | Top 3 perfiles | 2 días | Alto | 🔴 Crítica |
| 2.1 | Cálculo sísmico NSR-10 | 2 semanas | Muy Alto | 🔴 Crítica |
| 3.1 | Clip angles | 1 semana | Medio | 🟡 Alta |
| 3.2 | End plate | 1 semana | Medio | 🟡 Alta |
| 3.3 | Bracing connection | 1 semana | Medio | 🟡 Alta |
| 3.4 | Column splice | 1 semana | Medio | 🟡 Alta |
| 4.1 | Precios tiempo real | 4 semanas | Alto | 🟡 Alta |
| 5.1 | Render 3D | 4 semanas | Alto | 🟢 Media |
| 6.1 | Export IFC | 2 semanas | Medio | 🟢 Media |

---

## Referencias Normativas

### Conexiones

| Tipo | AISC 360-16 | Design Guide |
|------|-------------|--------------|
| Shear tab | J3, J4, J10.6 | DG4 Part 10 |
| Clip angle | J3, J4 | DG4 Part 9 |
| End plate | J3, J10 | DG4, DG16 |
| Bracing | J4, Seismic Provisions | DG29 |
| Column splice | J1.4, M2.1 | DG4 Part 14 |
| Base plate | J8 | DG1 |
| Moment welded | J2, J10 | DG4 Part 12 |

### Sismo

| Tema | NSR-10 |
|------|--------|
| Coeficientes Fa, Fv | A.2.4 Tablas 3, 4 |
| Espectro elástico | A.2.6 |
| Coeficientes R | A.3 Tabla 3 |
| Período aproximado | A.4.2 Ec. 4.2-1 |
| Cortante basal | A.4.3 Ec. 4.3-1 |
| Distribución vertical | A.4.4 |
| Derivas máximas | A.6.4 Tabla 1 |

---

## Contacto

**Desarrollo:** Leonardo (IA) + Claudio Palacios
**Empresa:** Comando Construcciones SAS
**Email:** claudio@comandoconstrucciones.com
