#!/usr/bin/env python3
"""Vincula tablas del KG con tablas SQL existentes"""
import os, json, requests

SUPABASE_URL = os.environ.get('STRUOS_SUPABASE_URL')
SERVICE_ROLE = os.environ.get('STRUOS_SUPABASE_SERVICE_ROLE')
HEADERS = {'apikey': SERVICE_ROLE, 'Authorization': f'Bearer {SERVICE_ROLE}', 'Content-Type': 'application/json'}

# Mapeo de tablas KG a tablas SQL
TABLE_MAPPING = {
    'A.2.4-3': {
        'sql_table': 'nsr10_coef_fa',
        'sql_function': 'get_fa(p_soil, p_aa)',
        'description': 'Coeficiente Fa para zona de períodos cortos'
    },
    'A.2.4-4': {
        'sql_table': 'nsr10_coef_fv', 
        'sql_function': 'get_fv(p_soil, p_av)',
        'description': 'Coeficiente Fv para zona de períodos intermedios'
    },
    'A.6.4-1': {
        'sql_table': 'nsr10_deriva_limites',
        'sql_function': None,
        'description': 'Límites de deriva máxima'
    }
}

# Obtener tablas del KG
print("Buscando tablas en KG...")
url = f"{SUPABASE_URL}/rest/v1/kg_nodes?type=eq.TABLE&select=id,title,section_path,table_sql_ref"
r = requests.get(url, headers=HEADERS)
tables = r.json()

print(f"Total tablas: {len(tables)}")

# Buscar y vincular
linked = 0
for table in tables:
    title = table.get('title', '') or ''
    section = table.get('section_path', '') or ''
    
    # Buscar en el mapeo
    for table_id, mapping in TABLE_MAPPING.items():
        if table_id in title or table_id in section:
            # Actualizar con referencia SQL
            sql_ref = f"SQL: {mapping['sql_table']}"
            if mapping['sql_function']:
                sql_ref += f" | Function: {mapping['sql_function']}"
            
            update_url = f"{SUPABASE_URL}/rest/v1/kg_nodes?id=eq.{table['id']}"
            r = requests.patch(update_url, headers=HEADERS, json={'table_sql_ref': sql_ref})
            
            if r.status_code in [200, 204]:
                print(f"  ✓ {table_id} → {mapping['sql_table']}")
                linked += 1
            break

print(f"\nTablas vinculadas: {linked}")

# Verificar funciones SQL existentes
print("\n=== VERIFICANDO FUNCIONES SQL ===")
for name in ['get_fa', 'get_fv']:
    test_url = f"{SUPABASE_URL}/rest/v1/rpc/{name}"
    test_data = {'p_soil': 'D', 'p_aa': 0.15} if name == 'get_fa' else {'p_soil': 'D', 'p_av': 0.20}
    r = requests.post(test_url, headers=HEADERS, json=test_data)
    if r.status_code == 200:
        print(f"  ✓ {name}() = {r.text}")
    else:
        print(f"  ✗ {name}(): {r.text[:50]}")
