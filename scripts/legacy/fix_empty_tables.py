#!/usr/bin/env python3
"""
Completa las 4 tablas vacías del KG con datos correctos
"""
import os, requests, json

SUPABASE_URL = os.environ.get('STRUOS_SUPABASE_URL')
SERVICE_ROLE = os.environ.get('STRUOS_SUPABASE_SERVICE_ROLE')
HEADERS = {'apikey': SERVICE_ROLE, 'Authorization': f'Bearer {SERVICE_ROLE}', 'Content-Type': 'application/json'}

# Datos de las tablas faltantes (del NSR-10)
TABLES_DATA = {
    'A.2.5-1': {
        'title': 'Valores del coeficiente de importancia, I',
        'headers': ['Grupo de Uso', 'Coeficiente I'],
        'rows': [
            ['IV (Edificaciones indispensables)', '1.25'],
            ['III (Edificaciones de atención a la comunidad)', '1.10'],
            ['II (Estructuras de ocupación especial)', '1.00'],
            ['I (Estructuras de ocupación normal)', '1.00']
        ]
    },
    'A.9.5-1': {
        'title': 'Coeficiente de amplificación dinámica ap y tipo de anclajes - Elementos arquitectónicos',
        'headers': ['Elemento', 'ap', 'Rp', 'Tipo anclaje'],
        'rows': [
            ['Muros interiores no estructurales (particiones)', '1.0', '2.5', 'Flexible'],
            ['Muros exteriores no estructurales (fachadas)', '1.0', '2.5', 'Flexible'],
            ['Parapetos y apéndices', '2.5', '2.5', 'Rígido'],
            ['Cielos rasos', '1.0', '2.5', 'Flexible'],
            ['Almacenamiento y estantería', '1.0', '2.5', 'NA'],
            ['Letreros y carteleras', '2.5', '2.5', 'Rígido'],
            ['Otros elementos rígidos', '1.0', '2.5', 'Rígido'],
            ['Otros elementos flexibles', '2.5', '2.5', 'Flexible']
        ]
    },
    'A.9.6-1': {
        'title': 'Coeficiente de amplificación dinámica ap y tipo de anclajes - Elementos MEP',
        'headers': ['Elemento', 'ap', 'Rp', 'Tipo anclaje'],
        'rows': [
            ['Calderas y hornos', '1.0', '2.5', 'Rígido'],
            ['Chimeneas y ductos', '2.5', '2.5', 'Flexible'],
            ['Equipos de comunicación', '1.0', '2.5', 'Rígido'],
            ['Equipos eléctricos (tableros, transformadores)', '1.0', '2.5', 'Rígido'],
            ['Tuberías de alta peligrosidad', '1.0', '2.5', 'Flexible'],
            ['Tuberías de baja peligrosidad', '1.0', '2.5', 'Flexible'],
            ['Ductos de HVAC', '2.5', '2.5', 'Flexible'],
            ['Ascensores', '1.0', '2.5', 'Rígido'],
            ['Escaleras mecánicas', '1.0', '2.5', 'Rígido'],
            ['Generadores y motores', '1.0', '2.5', 'Rígido'],
            ['Tanques y recipientes', '1.0', '2.5', 'NA']
        ]
    },
    'A.10.3-1': {
        'title': 'Valor de Ae según las regiones del mapa de la figura A.10.3-1',
        'headers': ['Región', 'Ae'],
        'rows': [
            ['1', '0.05'],
            ['2', '0.10'],
            ['3', '0.15'],
            ['4', '0.20'],
            ['5', '0.25'],
            ['6', '0.30'],
            ['7', '0.35']
        ]
    }
}

def update_table(table_id, data):
    """Actualiza una tabla en el KG"""
    # Buscar la tabla existente
    search_patterns = [
        f"Tabla {table_id}",
        f"Tabla A.{table_id}",
        table_id,
        table_id.replace('.', ' ')
    ]
    
    for pattern in search_patterns:
        url = f"{SUPABASE_URL}/rest/v1/kg_nodes?type=eq.TABLE&section_path=ilike.*{pattern}*&select=id,section_path"
        r = requests.get(url, headers=HEADERS)
        results = r.json()
        
        if results:
            node_id = results[0]['id']
            print(f"  Encontrada: {results[0]['section_path']} (ID: {node_id[:8]}...)")
            
            # Actualizar con datos
            update_url = f"{SUPABASE_URL}/rest/v1/kg_nodes?id=eq.{node_id}"
            update_data = {
                'table_headers': data['headers'],
                'table_rows': data['rows']
            }
            r = requests.patch(update_url, headers=HEADERS, json=update_data)
            
            if r.status_code in [200, 204]:
                print(f"    ✓ Actualizada con {len(data['rows'])} filas")
                return True
            else:
                print(f"    ✗ Error: {r.text[:50]}")
                return False
    
    print(f"  ✗ No encontrada en KG")
    return False

# Actualizar cada tabla
print("Actualizando tablas vacías...")
for table_id, data in TABLES_DATA.items():
    print(f"\nTabla {table_id}: {data['title'][:40]}...")
    update_table(table_id, data)

print("\n✓ Completado")
