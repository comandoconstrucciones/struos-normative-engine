#!/bin/bash
# Instalar dependencias
pip install mcp httpx

# Verificar
python3 -c "import mcp; print(f'MCP version: {mcp.__version__}')"
