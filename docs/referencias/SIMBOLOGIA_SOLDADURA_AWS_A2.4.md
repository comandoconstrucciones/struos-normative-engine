# Simbología de Soldadura — AWS A2.4

**Fuente:** ANSI/AWS A2.4, Símbolos para Soldadura
**Autor original del resumen:** Ing. José Manuel Ramírez (2011)
**Guardado:** 2026-03-25

---

## 1. Elementos Básicos del Símbolo de Soldadura

### Línea de Referencia
- Línea horizontal que sirve como plataforma principal
- Todos los demás símbolos se agregan a esta línea
- Las instrucciones de ejecución van alineadas a ella

### Flecha
- Conecta la línea de referencia con la junta a soldar
- Puede apuntar en distintas direcciones
- Define el "lado de la flecha" vs "el otro lado"

### Cola del Símbolo
- Ubicación para información suplementaria:
  - Proceso requerido
  - Tipo de electrodo
  - Detalle de dibujo
  - Cualquier información adicional

---

## 2. Símbolos Especiales

| Símbolo | Significado |
|---------|-------------|
| **Bandera** (en la unión línea-flecha) | Soldadura en campo/montaje |
| **Sin bandera** | Soldadura en taller |
| **Círculo vacío** (en la unión) | Soldadura todo alrededor (circunferencial) |
| **Círculo negro** (dibujos antiguos) | Equivalente a bandera de campo |

---

## 3. Tipos de Soldadura

### 3.1 Soldadura de Filete (Fillet Weld)

**Uso:** Juntas perpendiculares, esquinas, juntas "T"

**Símbolo:** Triángulo (representa sección transversal)
- La cara perpendicular siempre se dibuja a la izquierda

**Dimensionado:**
- Si ambas caras son iguales → una sola medida
- Si son desiguales → ambas medidas + nota indicando cuál es más larga

**Soldadura intermitente:**
```
Formato: [largo porción]-[centro a centro]
Ejemplo: 50-100 = 50mm de soldadura cada 100mm de paso
```
- Se coloca a la derecha del símbolo del filete

### 3.2 Soldadura de Canal (Groove Weld)

**Uso:** Juntas borde a borde, esquinas, juntas "T", curvas, piezas planas

**Tipos de canal:**

| Tipo | Descripción | Datos en símbolo |
|------|-------------|------------------|
| **Cuadrado** | Separación específica o ninguna | Distancia de separación |
| **V** | Bordes biselados (1 o 2 lados) | Ángulo del bisel, luz de raíz |
| **Bisel simple** | Un borde biselado, otro cuadrado | Flecha apunta al lado a biselar |
| **U** | Ambos bordes cóncavos | Profundidad, garganta efectiva, luz de raíz |
| **Doble V** | Biseles en ambas caras | Profundidades a la izquierda del símbolo |

**Garganta efectiva:**
- Si la penetración > profundidad del canal
- Se indica entre paréntesis después de la profundidad

### 3.3 Soldadura de Conexión y Óvalo
(Mencionada pero no desarrollada en el documento)

---

## 4. Reglas de Posicionamiento

| Elemento | Posición |
|----------|----------|
| Símbolo básico | Centro de la línea de referencia |
| Profundidades (V, U) | Izquierda del símbolo |
| Dimensiones intermitentes | Derecha del símbolo filete |
| Garganta efectiva | Entre paréntesis, después de profundidad |
| Ángulo del bisel | Sobre o debajo del símbolo según lado |

---

## 5. Interpretación de Lados

```
                    ┌─────────────────────┐
                    │   "El otro lado"    │  ← Instrucciones arriba
                    │                     │
    ════════════════╪═════════════════════╪════════════════
                    │                     │
                    │ "Lado de la flecha" │  ← Instrucciones abajo
                    └─────────────────────┘
                              │
                              ▼
                         [JUNTA]
```

---

## 6. Flecha Quebrada (Broken Arrow)

- Se usa en bisel cuando un solo lado debe ser preparado
- La flecha se corta y dobla en ángulo
- Apunta específicamente al lado que debe biselarse
- Opcional si el soldador es calificado para interpretar

---

## 7. Referencias Normativas

- **AWS A2.4** — Standard Symbols for Welding, Brazing, and Nondestructive Examination
- **AWS D1.1** — Structural Welding Code — Steel (complementaria)

---

## 8. Notas para Diseño Estructural

Para conexiones en estructuras metálicas (AISC):
- Soldadura en taller preferible (mejor control de calidad)
- Soldadura en campo solo cuando sea necesario (marcar con bandera)
- Especificar siempre el tamaño mínimo de filete según espesor (AISC J2.2b)
- Indicar si se requiere inspección visual, UT, RT, etc.

**Tamaños mínimos de filete (AISC Tabla J2.4):**

| Espesor material más grueso | Tamaño mínimo filete |
|-----------------------------|----------------------|
| ≤ 6 mm (1/4") | 3 mm (1/8") |
| > 6 mm a 13 mm (1/4" a 1/2") | 5 mm (3/16") |
| > 13 mm a 19 mm (1/2" a 3/4") | 6 mm (1/4") |
| > 19 mm (3/4") | 8 mm (5/16") |
