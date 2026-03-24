# NSR-10 MCP Server

Servidor MCP (Model Context Protocol) para consultas de la NSR-10 Colombia.

## Herramientas Disponibles

| Herramienta | Descripción |
|-------------|-------------|
| `parametros_sismicos` | Aa, Av, zona para cualquier municipio |
| `coeficiente_sitio` | Fa y Fv según tipo de suelo |
| `coeficiente_r` | R₀, Ω₀, Cd para sistemas estructurales |
| `coeficiente_importancia` | Factor I por grupo de uso |
| `barras_refuerzo` | Propiedades de barras |
| `cargas_vivas` | Cargas por uso de edificación |
| `deriva_maxima` | Derivas máximas permitidas |
| `recubrimientos` | Recubrimientos mínimos |
| `perfiles_acero` | Propiedades de perfiles W |
| `consulta_sql` | Consulta directa a 259 tablas |
| `buscar_seccion` | Búsqueda FTS en 12,789 secciones |

## Instalación Claude Desktop

1. Copiar configuración a `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac)
   o `%APPDATA%\Claude\claude_desktop_config.json` (Windows)

2. Agregar tu SUPABASE_SERVICE_ROLE key

3. Reiniciar Claude Desktop

## Uso

Una vez instalado, Claude puede usar comandos como:

- "¿Cuáles son los parámetros sísmicos para Medellín?"
- "Dame el coeficiente Fa para suelo tipo D con Aa=0.25"
- "¿Qué R uso para pórticos de concreto DES?"
- "Busca en la NSR-10 sobre diseño de vigas a cortante"

## Base de Datos

- 259 tablas SQL
- 12,789 secciones indexadas
- 3,109 nodos Knowledge Graph
- 568 referencias externas
- 558 fórmulas

## Licencia

Uso interno Comando Construcciones / Struos.AI
