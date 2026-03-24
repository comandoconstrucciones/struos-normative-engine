# NSR-10 MCP Server

Motor normativo de ingeniería estructural Colombia para Model Context Protocol.

## Instalación

```bash
pip install mcp httpx
```

## Configuración Claude Desktop

Agregar a `~/.config/claude/claude_desktop_config.json` (Linux) o `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "nsr10": {
      "command": "python3",
      "args": ["/ruta/a/mcp/server.py"]
    }
  }
}
```

**No requiere API keys** — usa la API pública https://struos-api.vercel.app

## Herramientas disponibles

| Tool | Descripción |
|------|-------------|
| `parametros_sismicos` | Aa, Av, zona de amenaza para cualquier municipio |
| `coeficiente_fa` | Coef Fa por tipo de suelo y Aa |
| `coeficiente_fv` | Coef Fv por tipo de suelo y Av |
| `coeficiente_r` | R₀, Ω₀, Cd para sistemas estructurales |
| `barras_refuerzo` | Propiedades de barras (Ø, área, masa) |
| `deriva_maxima` | Derivas máximas permitidas |
| `buscar_seccion` | Búsqueda FTS en secciones NSR-10 |

## Ejemplos de uso en Claude

```
"¿Cuáles son los parámetros sísmicos para Bogotá?"
→ Usa parametros_sismicos(municipio="Bogotá")

"Dame el coeficiente Fa para suelo tipo D con Aa=0.25"
→ Usa coeficiente_fa(tipo_suelo="D", aa=0.25)

"¿Cuál es el R para pórticos especiales de concreto?"
→ Usa coeficiente_r(sistema="pórticos", capacidad="DES")

"Propiedades de la barra #5"
→ Usa barras_refuerzo(designacion="5")
```

## API REST

La API también está disponible directamente:

```bash
# Parámetros sísmicos
curl https://struos-api.vercel.app/municipios/Bogotá

# Coeficiente Fa
curl https://struos-api.vercel.app/coef/fa/D/0.25

# Barras de refuerzo
curl https://struos-api.vercel.app/barras?designacion=5

# Derivas máximas
curl https://struos-api.vercel.app/deriva
```

## Links

- **Landing**: https://struos-ai.vercel.app
- **API**: https://struos-api.vercel.app
- **GitHub**: https://github.com/comandoconstrucciones/struos-normative-engine
