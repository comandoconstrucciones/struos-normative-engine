#!/usr/bin/env python3
"""
Diccionario de sinónimos para NSR-10
Mapea términos coloquiales/variantes → terminología oficial de la norma
"""

NSR10_SYNONYMS = {
    # === FUERZAS Y CORTANTES ===
    'cortante basal': ['cortante sísmico en la base', 'Vs', 'fuerza cortante base', 'cortante en la base'],
    'cortante': ['corte', 'shear', 'fuerza cortante', 'esfuerzo cortante'],
    'momento': ['momento flector', 'momento de volteo', 'M'],
    'fuerza axial': ['carga axial', 'compresión', 'tensión', 'P'],
    
    # === DERIVA Y DESPLAZAMIENTOS ===
    'deriva': ['drift', 'desplazamiento relativo', 'desplazamiento de piso', 'desplazamiento lateral', 'desplazamiento de entrepiso'],
    'deriva máxima': ['deriva máxima permisible', 'límite de deriva', 'drift máximo', 'deriva permitida'],
    'desplazamiento': ['deflexión', 'deformación', 'delta'],
    
    # === PERÍODO Y FRECUENCIA ===
    'período': ['periodo', 'T', 'período fundamental', 'período natural de vibración', 'período de vibración'],
    'período aproximado': ['Ta', 'período empírico', 'período calculado'],
    'frecuencia': ['frecuencia natural', 'Hz', 'ciclos por segundo'],
    
    # === COEFICIENTES SÍSMICOS ===
    'coeficiente r': ['R', 'R0', 'Ro', 'capacidad de disipación', 'factor de reducción', 'coeficiente de disipación'],
    'coeficiente fa': ['Fa', 'amplificación suelo', 'factor de amplificación corto', 'coeficiente de sitio'],
    'coeficiente fv': ['Fv', 'amplificación períodos largos', 'factor de velocidad'],
    'coeficiente aa': ['Aa', 'aceleración pico', 'aceleración horizontal'],
    'coeficiente av': ['Av', 'velocidad pico', 'velocidad horizontal'],
    'coeficiente i': ['I', 'factor de importancia', 'coeficiente de importancia', 'grupo de uso'],
    'coeficiente cd': ['Cd', 'amplificación de deflexiones', 'factor de deflexión'],
    'coeficiente omega': ['Ω0', 'omega cero', 'sobrerresistencia', 'factor de sobrerresistencia'],
    
    # === SISTEMAS ESTRUCTURALES ===
    'pórtico': ['portico', 'marco', 'frame', 'sistema aporticado', 'estructura aporticada'],
    'pórtico especial': ['DES', 'capacidad especial de disipación', 'ductilidad especial', 'pórtico dúctil'],
    'pórtico intermedio': ['DMO', 'capacidad moderada', 'ductilidad moderada'],
    'pórtico mínimo': ['DMI', 'capacidad mínima', 'ductilidad mínima'],
    'muro estructural': ['muro de cortante', 'shear wall', 'muro de carga', 'muro portante'],
    'sistema dual': ['pórtico más muros', 'combinado', 'sistema mixto'],
    'pórtico arriostrado': ['contraviento', 'diagonal', 'arriostramiento'],
    
    # === SUELOS ===
    'suelo tipo': ['perfil de suelo', 'clasificación de suelo', 'tipo de perfil', 'categoría de sitio'],
    'suelo tipo a': ['roca dura', 'perfil A', 'roca competente'],
    'suelo tipo b': ['roca', 'perfil B', 'roca moderadamente fracturada'],
    'suelo tipo c': ['suelo muy denso', 'perfil C', 'suelo firme'],
    'suelo tipo d': ['suelo rígido', 'perfil D', 'suelo medio'],
    'suelo tipo e': ['suelo blando', 'perfil E', 'arcilla blanda'],
    'suelo tipo f': ['suelo especial', 'perfil F', 'licuable', 'turba'],
    
    # === ZONAS SÍSMICAS ===
    'zona sísmica': ['amenaza sísmica', 'región sísmica', 'zona de amenaza', 'zonificación'],
    'zona sísmica alta': ['alta sismicidad', 'zona roja', 'amenaza alta'],
    'zona sísmica intermedia': ['sismicidad media', 'zona naranja', 'amenaza intermedia'],
    'zona sísmica baja': ['baja sismicidad', 'zona verde', 'amenaza baja'],
    
    # === ESPECTRO ===
    'espectro': ['espectro de diseño', 'espectro elástico', 'espectro de aceleraciones', 'curva espectral'],
    'espectro de aceleraciones': ['Sa', 'ordenada espectral', 'aceleración espectral'],
    'espectro de velocidades': ['Sv', 'velocidad espectral'],
    'espectro de desplazamientos': ['Sd', 'desplazamiento espectral'],
    
    # === IRREGULARIDADES ===
    'irregularidad': ['irregularidad estructural', 'configuración irregular', 'asimetría'],
    'irregularidad en planta': ['asimetría en planta', 'torsión', 'excentricidad', 'planta irregular'],
    'irregularidad en altura': ['piso blando', 'columna corta', 'altura irregular', 'discontinuidad'],
    'piso blando': ['piso débil', 'soft story', 'rigidez reducida'],
    'columna corta': ['short column', 'columna cautiva'],
    
    # === ELEMENTOS ESTRUCTURALES ===
    'diafragma': ['losa', 'entrepiso rígido', 'placa'],
    'viga': ['elemento horizontal', 'trabe'],
    'columna': ['elemento vertical', 'pilar', 'pilastra'],
    'nudo': ['conexión', 'unión', 'junta', 'nodo'],
    'cimentación': ['fundación', 'foundation', 'base'],
    'zapata': ['cimiento aislado', 'footing'],
    'losa de cimentación': ['platea', 'mat foundation'],
    'pilote': ['pile', 'pila'],
    
    # === PROPIEDADES ===
    'ductilidad': ['capacidad de deformación', 'comportamiento inelástico', 'ductilidad estructural'],
    'rigidez': ['stiffness', 'módulo de rigidez', 'rigidez lateral'],
    'resistencia': ['capacidad', 'strength', 'resistencia nominal'],
    'amortiguamiento': ['damping', 'disipación de energía', 'amortiguamiento viscoso'],
    
    # === ANÁLISIS ===
    'análisis modal': ['análisis dinámico', 'modos de vibración', 'análisis modal espectral'],
    'fuerza horizontal equivalente': ['FHE', 'método estático', 'análisis estático equivalente'],
    'análisis tiempo-historia': ['time history', 'análisis cronológico', 'análisis transitorio'],
    'análisis pushover': ['análisis de empuje', 'análisis no lineal estático'],
    
    # === CIUDADES COLOMBIA ===
    'bogotá': ['bogota', 'cundinamarca', 'capital', 'distrito capital'],
    'medellín': ['medellin', 'antioquia', 'aburra'],
    'cali': ['valle', 'valle del cauca'],
    'barranquilla': ['atlántico', 'atlantico', 'caribe'],
    'cartagena': ['bolívar', 'bolivar'],
    'bucaramanga': ['santander'],
    'pereira': ['risaralda', 'eje cafetero'],
    'manizales': ['caldas', 'eje cafetero'],
    'armenia': ['quindío', 'quindio', 'eje cafetero'],
    'cúcuta': ['cucuta', 'norte de santander'],
    'ibagué': ['ibague', 'tolima'],
    'villavicencio': ['meta', 'llanos'],
    
    # === NORMATIVAS ===
    'nsr-10': ['nsr10', 'nsr 10', 'reglamento colombiano', 'norma sismo resistente'],
    'título a': ['titulo a', 'capítulo a', 'requisitos generales'],
    'título b': ['titulo b', 'capítulo b', 'cargas'],
    'título c': ['titulo c', 'capítulo c', 'concreto'],
}

def get_synonyms(term: str) -> list:
    """Obtiene sinónimos de un término"""
    term_lower = term.lower().strip()
    return NSR10_SYNONYMS.get(term_lower, [])

def expand_with_synonyms(query: str) -> list:
    """Expande un query con todos los sinónimos encontrados"""
    queries = [query]
    query_lower = query.lower()
    
    for term, synonyms in NSR10_SYNONYMS.items():
        if term in query_lower:
            for syn in synonyms[:2]:  # Max 2 por término
                expanded = query_lower.replace(term, syn)
                if expanded not in queries:
                    queries.append(expanded)
    
    return queries[:5]  # Max 5 queries

if __name__ == "__main__":
    print(f"Total términos: {len(NSR10_SYNONYMS)}")
    print(f"Total sinónimos: {sum(len(v) for v in NSR10_SYNONYMS.values())}")
    
    # Test
    test = "cortante basal en pórtico especial"
    expanded = expand_with_synonyms(test)
    print(f"\nTest: '{test}'")
    print(f"Expandido: {expanded}")
