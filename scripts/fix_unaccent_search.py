#!/usr/bin/env python3
"""
Fix: Agregar columna normalizada para búsqueda sin acentos
Ejecutar: python3 scripts/fix_unaccent_search.py
"""
import os
import unicodedata
from supabase import create_client

# Config
SUPABASE_URL = "https://vdakfewjadwaczulcmvj.supabase.co"
SUPABASE_KEY = os.environ.get('STRUOS_SUPABASE_SERVICE_ROLE')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def normalize_text(text: str) -> str:
    """Quita acentos y convierte a minúsculas"""
    if not text:
        return ""
    # NFD descompone caracteres (á → a + ́)
    # Luego filtramos los combining marks
    normalized = unicodedata.normalize('NFD', text)
    without_accents = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    return without_accents.lower()

def main():
    print("=== Actualizando municipios con búsqueda normalizada ===")
    
    # 1. Obtener todos los municipios
    response = supabase.table('nsr10_municipios').select('id, municipio').execute()
    municipios = response.data
    print(f"Total municipios: {len(municipios)}")
    
    # 2. Verificar si la columna existe
    # Primero intentamos un update para ver si falla
    test = supabase.table('nsr10_municipios').select('municipio_normalized').limit(1).execute()
    if hasattr(test, 'error') and test.error:
        print("La columna municipio_normalized no existe. Créala primero en Supabase Dashboard:")
        print("  ALTER TABLE nsr10_municipios ADD COLUMN municipio_normalized TEXT;")
        print("  CREATE INDEX idx_municipios_normalized ON nsr10_municipios(municipio_normalized);")
        return
    
    # 3. Actualizar cada municipio
    updated = 0
    for m in municipios:
        municipio = m.get('municipio', '')
        normalized = normalize_text(municipio)
        
        supabase.table('nsr10_municipios').update({
            'municipio_normalized': normalized
        }).eq('id', m['id']).execute()
        
        updated += 1
        if updated % 100 == 0:
            print(f"  Actualizados: {updated}/{len(municipios)}")
    
    print(f"\n✅ Actualizados {updated} municipios")
    print("\nAhora puedes buscar con:")
    print("  ?municipio_normalized=ilike.*bogota*")

if __name__ == "__main__":
    main()
