#!/usr/bin/env python3
"""
NSR-10 Query Engine v2.0 - SQL First, 100% Exacto
Todas las tablas del Título A
"""
import os, re, unicodedata
import requests

SUPABASE_URL = os.environ.get('STRUOS_SUPABASE_URL')
SERVICE_ROLE = os.environ.get('STRUOS_SUPABASE_SERVICE_ROLE')
HEADERS = {'apikey': SERVICE_ROLE, 'Authorization': f'Bearer {SERVICE_ROLE}', 'Content-Type': 'application/json'}

def normalize(text: str) -> str:
    """Normaliza texto removiendo acentos"""
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower().strip()) 
                   if unicodedata.category(c) != 'Mn')

def sql_get(table: str, filters: dict = None, limit: int = 10) -> list:
    """Query genérica a Supabase"""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    if filters:
        params = "&".join([f"{k}={v}" for k, v in filters.items()])
        url += f"?{params}"
    url += f"&limit={limit}" if filters else f"?limit={limit}"
    
    r = requests.get(url, headers=HEADERS, timeout=5)
    return r.json() if r.status_code == 200 else []

# =====================================================
# QUERY FUNCTIONS
# =====================================================

def query_municipio(nombre: str) -> dict | None:
    """Busca parámetros sísmicos de un municipio"""
    nombre_norm = normalize(nombre)[:4]
    results = sql_get("nsr10_municipios", {"municipio": f"ilike.*{nombre_norm}*"}, 5)
    if results:
        for row in results:
            if nombre_norm in normalize(row.get('municipio', '')):
                return row
        return results[0]
    return None

def query_coef_r(sistema: str) -> dict | None:
    """Busca R0, Ω0, Cd para un sistema estructural"""
    s = sistema.lower()
    
    # Detectar sistema
    if 'pórtico' in s or 'portico' in s:
        search = 'Pórtico'
    elif 'muro' in s:
        search = 'Muro'
    elif 'dual' in s:
        search = 'dual'
    elif 'arriostr' in s or 'riostra' in s:
        search = 'riostra'
    else:
        search = sistema[:10]
    
    # Detectar capacidad
    capacidad = None
    if 'des' in s or 'especial' in s:
        capacidad = 'especial'
    elif 'dmo' in s or 'moderada' in s:
        capacidad = 'moderada'
    elif 'dmi' in s or 'mínima' in s or 'minima' in s:
        capacidad = 'mínima'
    
    results = sql_get("nsr10_coef_r", {"sistema": f"ilike.*{search}*"}, 10)
    
    if results:
        # Filtrar por capacidad si se especificó
        if capacidad:
            for row in results:
                if capacidad in row['sistema'].lower():
                    return row
        # También filtrar por material
        if 'concreto' in s:
            for row in results:
                if 'concreto' in row['sistema'].lower():
                    return row
        elif 'acero' in s:
            for row in results:
                if 'acero' in row['sistema'].lower():
                    return row
        return results[0]
    return None

def query_coef_fa(suelo: str, aa: float) -> float | None:
    """Busca coeficiente Fa"""
    results = sql_get("nsr10_coef_fa", {"soil_type": f"eq.{suelo.upper()}", "aa_value": f"eq.{aa}"}, 1)
    return results[0]['fa'] if results else None

def query_coef_fv(suelo: str, av: float) -> float | None:
    """Busca coeficiente Fv"""
    results = sql_get("nsr10_coef_fv", {"soil_type": f"eq.{suelo.upper()}", "av_value": f"eq.{av}"}, 1)
    return results[0]['fv'] if results else None

def query_importancia(grupo: str = None) -> list | dict:
    """Busca coeficientes de importancia"""
    if grupo:
        results = sql_get("nsr10_coef_importancia", {"grupo_uso": f"eq.{grupo.upper()}"}, 1)
        return results[0] if results else None
    return sql_get("nsr10_coef_importancia", limit=4)

def query_deriva() -> list:
    """Busca límites de deriva"""
    results = sql_get("nsr10_deriva_limites", limit=10)
    for row in results:
        row['sistema'] = row.get('sistema_estructural', 'N/A')
        row['deriva'] = f"{row.get('deriva_max_pct', 0)}%"
    return results

def query_periodo(sistema: str = None) -> list | dict:
    """Busca coeficientes Ct, α para período"""
    if sistema:
        s = sistema.lower()
        if 'concreto' in s:
            search = 'concreto'
        elif 'acero' in s:
            search = 'acero'
        else:
            search = sistema[:10]
        results = sql_get("nsr10_coef_periodo", {"sistema": f"ilike.*{search}*"}, 1)
        return results[0] if results else None
    return sql_get("nsr10_coef_periodo", limit=10)

def query_irregularidad_planta(tipo: str = None) -> list | dict:
    """Busca irregularidades en planta"""
    if tipo:
        results = sql_get("nsr10_irregularidad_planta", {"tipo": f"eq.{tipo}"}, 1)
        return results[0] if results else None
    return sql_get("nsr10_irregularidad_planta", limit=10)

def query_irregularidad_altura(tipo: str = None) -> list | dict:
    """Busca irregularidades en altura"""
    if tipo:
        results = sql_get("nsr10_irregularidad_altura", {"tipo": f"eq.{tipo}"}, 1)
        return results[0] if results else None
    return sql_get("nsr10_irregularidad_altura", limit=10)

def query_irregularidades_prohibidas() -> list:
    """Busca irregularidades prohibidas en zona alta"""
    planta = sql_get("nsr10_irregularidad_planta", {"prohibida_alta": "eq.true"}, 10)
    altura = sql_get("nsr10_irregularidad_altura", {"prohibida_alta": "eq.true"}, 10)
    return planta + altura

def query_separacion(pisos: int = None) -> list | dict:
    """Busca separación sísmica mínima"""
    if pisos:
        p = min(pisos, 10)  # Tabla va hasta 10
        results = sql_get("nsr10_separacion_sismica", {"pisos": f"eq.{p}"}, 1)
        return results[0] if results else None
    return sql_get("nsr10_separacion_sismica", limit=10)

def query_perfil_suelo(tipo: str = None) -> list | dict:
    """Busca clasificación de perfil de suelo"""
    if tipo:
        results = sql_get("nsr10_perfil_suelo", {"tipo": f"eq.{tipo.upper()}"}, 1)
        return results[0] if results else None
    return sql_get("nsr10_perfil_suelo", limit=6)

def query_formula(nombre: str = None) -> list | dict:
    """Busca fórmula"""
    if nombre:
        n = nombre.lower()
        if 'cortante' in n or 'vs' in n:
            search = 'Cortante'
        elif 'período' in n or 'periodo' in n or 'ta' in n:
            search = 'Período'
        elif 'tc' in n or 'transición' in n:
            search = 'transición'
        elif 'fp' in n or 'no estructural' in n:
            search = 'no estructural'
        elif 'qi' in n or 'estabilidad' in n or 'delta' in n:
            search = 'estabilidad'
        elif 'sa' in n or 'espectral' in n:
            search = 'espectral'
        elif 'deriva' in n or 'delta' in n or 'δ' in n:
            search = 'Deriva'
        elif 'tl' in n:
            search = 'largo'
        else:
            search = nombre[:10]
        results = sql_get("nsr10_formulas", {"nombre": f"ilike.*{search}*"}, 1)
        return results[0] if results else None
    return sql_get("nsr10_formulas", limit=10)

def query_no_estructural(componente: str = None) -> list | dict:
    """Busca coeficientes para elementos no estructurales"""
    if componente:
        results = sql_get("nsr10_coef_no_estructural", {"componente": f"ilike.*{componente[:15]}*"}, 5)
        return results[0] if results else None
    return sql_get("nsr10_coef_no_estructural", limit=20)

# =====================================================
# CLASSIFIER
# =====================================================

def classify_and_query(pregunta: str) -> tuple[str, any]:
    """Clasifica la pregunta y ejecuta la query SQL apropiada"""
    p = pregunta.lower()
    
    # === MUNICIPIO ===
    ciudades = ['bogotá', 'bogota', 'medellín', 'medellin', 'cali', 'barranquilla', 
                'cartagena', 'bucaramanga', 'pereira', 'cúcuta', 'cucuta', 'ibagué',
                'santa marta', 'villavicencio', 'pasto', 'manizales', 'armenia',
                'neiva', 'montería', 'sincelejo', 'popayán', 'valledupar', 'tunja']
    for ciudad in ciudades:
        if ciudad in p and any(t in p for t in ['aa', 'av', 'zona', 'parámetro', 'sísmic', 'amenaza', 'valor', 'coeficiente']):
            result = query_municipio(ciudad)
            if result:
                return ('MUNICIPIO', result)
    
    # === COEFICIENTE R ===
    if re.search(r'\b(r0?|coeficiente\s*r|factor.*reducci[oó]n|ω|omega|cd)\b', p):
        if re.search(r'\b(pórtico|portico|muro|dual|arriostr|des|dmo|dmi|especial|moderada|mínima|acero|concreto)\b', p):
            # Detectar tipo de sistema y capacidad
            is_portico = 'pórtico' in p or 'portico' in p
            is_muro = 'muro' in p and not is_portico
            is_acero = 'acero' in p
            is_concreto = 'concreto' in p
            cap_term = 'especial' if ('des' in p or 'especial' in p) else ('moderada' if ('dmo' in p or 'moderada' in p) else ('mínima' if ('dmi' in p or 'mínima' in p) else None))
            
            # Construir búsqueda específica
            if is_portico:
                if is_acero:
                    search = "Pórtico*acero"
                elif is_concreto:
                    search = "Pórtico*concreto"
                else:
                    search = "Pórtico"
            elif is_muro:
                search = "Muro"
            elif is_acero:
                search = "acero"
            elif is_concreto:
                search = "concreto"
            else:
                search = None
            
            if search and cap_term:
                results = sql_get("nsr10_coef_r", {"sistema": f"ilike.*{search}*{cap_term}*"}, 5)
                if results:
                    # Filtrar mejor
                    for r in results:
                        s = r['sistema'].lower()
                        if is_portico and 'pórtico' in s:
                            return ('COEF_R', r)
                        elif is_muro and 'muro' in s:
                            return ('COEF_R', r)
                    return ('COEF_R', results[0])
            
            result = query_coef_r(pregunta)
            if result:
                return ('COEF_R', result)
    
    # === COEFICIENTE FA ===
    fa_match = re.search(r'fa.*suelo.*tipo\s*([a-e])|suelo.*tipo\s*([a-e]).*fa', p)
    aa_match = re.search(r'aa\s*[=:]?\s*(0?[.,]\d+)', p)
    if fa_match and aa_match:
        suelo = (fa_match.group(1) or fa_match.group(2)).upper()
        aa = float(aa_match.group(1).replace(',', '.'))
        result = query_coef_fa(suelo, aa)
        if result:
            return ('COEF_FA', {'suelo': suelo, 'aa': aa, 'fa': result})
    
    # === COEFICIENTE FV ===
    fv_match = re.search(r'fv.*suelo.*tipo\s*([a-e])|suelo.*tipo\s*([a-e]).*fv', p)
    av_match = re.search(r'av\s*[=:]?\s*(0?[.,]\d+)', p)
    if fv_match and av_match:
        suelo = (fv_match.group(1) or fv_match.group(2)).upper()
        av = float(av_match.group(1).replace(',', '.'))
        result = query_coef_fv(suelo, av)
        if result:
            return ('COEF_FV', {'suelo': suelo, 'av': av, 'fv': result})
    
    # === IMPORTANCIA ===
    if 'importancia' in p or 'grupo' in p:
        if 'hospital' in p or 'iv' in p or 'indispensable' in p:
            result = query_importancia('IV')
        elif 'iii' in p or 'seguridad' in p:
            result = query_importancia('III')
        elif 'ii' in p or 'reunión' in p:
            result = query_importancia('II')
        elif ' i ' in p or 'normal' in p:
            result = query_importancia('I')
        else:
            result = query_importancia()
        if result:
            return ('IMPORTANCIA', result)
    
    # === DERIVA ===
    if 'deriva' in p or ('desplazamiento' in p and ('máxim' in p or 'límite' in p)):
        result = query_deriva()
        if result:
            return ('DERIVA', result)
    
    # === PERÍODO ===
    if ('período' in p or 'periodo' in p or 'ta' in p) and ('ct' in p or 'alfa' in p or 'α' in p or 'calcul' in p or 'fórmula' in p or 'aproximado' in p):
        if 'concreto' in p or 'acero' in p:
            result = query_periodo(pregunta)
        else:
            result = query_periodo()
        if result:
            return ('PERIODO', result)
    
    # === IRREGULARIDADES ===
    if 'irregularidad' in p or 'irregular' in p:
        if 'prohibida' in p or 'prohiben' in p:
            result = query_irregularidades_prohibidas()
            if result:
                return ('IRREGULARIDAD_PROHIBIDA', result)
        elif 'torsion' in p or 'torsión' in p:
            if 'extrema' in p:
                result = query_irregularidad_planta('1bP')
            else:
                result = query_irregularidad_planta('1aP')
            if result:
                return ('IRREGULARIDAD_PLANTA', result)
        elif 'piso blando' in p:
            if 'extrem' in p:
                result = query_irregularidad_altura('1bA')
            else:
                result = query_irregularidad_altura('1aA')
            if result:
                return ('IRREGULARIDAD_ALTURA', result)
        elif 'piso débil' in p or 'piso debil' in p:
            if 'extrem' in p:
                result = query_irregularidad_altura('5bA')
            else:
                result = query_irregularidad_altura('5aA')
            if result:
                return ('IRREGULARIDAD_ALTURA', result)
        elif 'planta' in p:
            result = query_irregularidad_planta()
            if result:
                return ('IRREGULARIDAD_PLANTA', result)
        elif 'altura' in p:
            result = query_irregularidad_altura()
            if result:
                return ('IRREGULARIDAD_ALTURA', result)
        else:
            # Todas las irregularidades
            planta = query_irregularidad_planta()
            altura = query_irregularidad_altura()
            if planta or altura:
                return ('IRREGULARIDADES', {'planta': planta, 'altura': altura})
    
    # === SEPARACIÓN SÍSMICA ===
    if 'separación' in p or 'separacion' in p or 'golpeteo' in p:
        pisos_match = re.search(r'(\d+)\s*piso', p)
        if pisos_match:
            pisos = int(pisos_match.group(1))
            result = query_separacion(pisos)
        else:
            result = query_separacion()
        if result:
            return ('SEPARACION', result)
    
    # === PERFIL DE SUELO ===
    if 'perfil' in p or ('suelo' in p and 'tipo' in p and not ('fa' in p or 'fv' in p)):
        tipo_match = re.search(r'tipo\s*([a-f])', p)
        if tipo_match:
            result = query_perfil_suelo(tipo_match.group(1))
        else:
            result = query_perfil_suelo()
        if result:
            return ('PERFIL_SUELO', result)
    
    # === FÓRMULAS ===
    if 'fórmula' in p or 'formula' in p or 'ecuación' in p or 'calcul' in p:
        result = query_formula(pregunta)
        if result:
            return ('FORMULA', result)
    
    # === ELEMENTOS NO ESTRUCTURALES ===
    if 'no estructural' in p or 'fp' in p or 'partici' in p or 'fachada' in p or 'cielo raso' in p:
        result = query_no_estructural(pregunta) if any(t in p for t in ['partici', 'fachada', 'tanque', 'cielo']) else query_no_estructural()
        if result:
            return ('NO_ESTRUCTURAL', result)
    
    # === PERÍODO (Ct, alfa) ===
    if ('ct' in p or 'alfa' in p or 'α' in p) and ('pórtico' in p or 'portico' in p or 'sistema' in p):
        if 'concreto' in p:
            result = query_periodo('concreto')
        elif 'acero' in p:
            result = query_periodo('acero')
        else:
            result = query_periodo()
        if result:
            return ('PERIODO', result)
    
    # === CASOS ESPECIALES ===
    # Cielos rasos
    if 'cielo' in p:
        results = sql_get("nsr10_coef_no_estructural", {"componente": "ilike.*cielo*"}, 1)
        if results:
            return ('NO_ESTRUCTURAL', results[0])
    
    # Fórmula cortante basal
    if 'cortante' in p or (' vs ' in f" {p} ") or p.endswith(' vs'):
        results = sql_get("nsr10_formulas", {"nombre": "ilike.*Cortante*"}, 1)
        if results:
            return ('FORMULA', results[0])
    
    return ('NONE', None)

# =====================================================
# FORMATTERS
# =====================================================

def format_response(tipo: str, data: any) -> str:
    """Formatea la respuesta SQL en lenguaje natural"""
    
    if tipo == 'MUNICIPIO':
        return f"""**Parámetros sísmicos para {data['municipio']}, {data['departamento']}:**

| Parámetro | Valor |
|-----------|-------|
| Aa | {data['aa']} |
| Av | {data['av']} |
| Zona de amenaza | {data['zona_amenaza']} |

_Fuente: NSR-10 Apéndice A-4_"""

    elif tipo == 'COEF_R':
        return f"""**Coeficientes para {data['sistema']}:**

| Coeficiente | Valor |
|-------------|-------|
| R₀ | **{data['r0']}** |
| Ω₀ | {data['omega0']} |
| Cd | {data['cd']} |
| Altura máxima | {data.get('altura_max') or 'Sin límite'} |

_Fuente: NSR-10 Tabla A.3-3_"""

    elif tipo == 'COEF_FA':
        return f"""**Coeficiente Fa para suelo tipo {data['suelo']} con Aa={data['aa']}:**

**Fa = {data['fa']}**

_Fuente: NSR-10 Tabla A.2.4-3_"""

    elif tipo == 'COEF_FV':
        return f"""**Coeficiente Fv para suelo tipo {data['suelo']} con Av={data['av']}:**

**Fv = {data['fv']}**

_Fuente: NSR-10 Tabla A.2.4-4_"""

    elif tipo == 'IMPORTANCIA':
        if isinstance(data, dict):
            return f"""**Coeficiente de importancia para Grupo {data['grupo_uso']}:**

**I = {data['coef_i']}**

Descripción: {data['descripcion']}

_Fuente: NSR-10 Tabla A.2.5-1_"""
        else:
            lines = ["**Coeficientes de importancia (Tabla A.2.5-1):**\n"]
            for row in data:
                lines.append(f"| Grupo {row['grupo_uso']} | I = {row['coef_i']} | {row['descripcion']} |")
            return "\n".join(lines)
    
    elif tipo == 'DERIVA':
        lines = ["**Derivas máximas permitidas (Tabla A.6.4-1):**\n"]
        lines.append("| Sistema estructural | Deriva máxima |")
        lines.append("|---------------------|---------------|")
        for row in data:
            lines.append(f"| {row['sistema']} | **{row['deriva']}** |")
        return "\n".join(lines)
    
    elif tipo == 'PERIODO':
        if isinstance(data, dict):
            return f"""**Coeficientes para período aproximado Ta = Ct × hn^α:**

Sistema: {data.get('sistema', 'N/A')}
- **Ct** = {data.get('ct', data.get('Ct', 'N/A'))}
- **α** = {data.get('alfa', data.get('alpha', 'N/A'))}

_Fuente: NSR-10 Tabla A.4.2-1_"""
        else:
            lines = ["**Coeficientes para período (Tabla A.4.2-1):**\n"]
            lines.append("| Sistema | Ct | α |")
            lines.append("|---------|-----|-----|")
            for row in data:
                lines.append(f"| {row.get('sistema', 'N/A')} | {row.get('ct', row.get('Ct', 'N/A'))} | {row.get('alfa', row.get('alpha', 'N/A'))} |")
            return "\n".join(lines)
    
    elif tipo == 'IRREGULARIDAD_PROHIBIDA':
        lines = ["**Irregularidades PROHIBIDAS en zona de amenaza sísmica alta:**\n"]
        for row in data:
            lines.append(f"- **{row['tipo']}** - {row['nombre']}: {row['descripcion']}")
        lines.append("\n_Fuente: NSR-10 Tablas A.3-6 y A.3-7_")
        return "\n".join(lines)
    
    elif tipo in ('IRREGULARIDAD_PLANTA', 'IRREGULARIDAD_ALTURA'):
        if isinstance(data, dict):
            phi = data.get('phi_p') or data.get('phi_a') or 'N/A'
            prohib = "**PROHIBIDA en zona alta**" if data.get('prohibida_alta') else f"φ = {phi}"
            return f"""**Irregularidad {data['tipo']} - {data['nombre']}:**

{data['descripcion']}

Penalización: {prohib}

_Fuente: NSR-10 Tabla {data.get('tabla_ref', 'A.3-6/7')}_"""
        else:
            lines = [f"**Irregularidades en {'planta' if tipo == 'IRREGULARIDAD_PLANTA' else 'altura'}:**\n"]
            lines.append("| Tipo | Nombre | φ |")
            lines.append("|------|--------|---|")
            for row in data:
                phi = row.get('phi_p') or row.get('phi_a') or ('PROHIBIDA' if row.get('prohibida_alta') else 'N/A')
                lines.append(f"| {row['tipo']} | {row['nombre']} | {phi} |")
            return "\n".join(lines)
    
    elif tipo == 'IRREGULARIDADES':
        lines = ["**Irregularidades estructurales:**\n"]
        lines.append("**En planta (Tabla A.3-6):**")
        for row in data.get('planta', []):
            phi = row.get('phi_p') or ('PROHIBIDA' if row.get('prohibida_alta') else 'N/A')
            lines.append(f"- {row['tipo']}: {row['nombre']} (φp={phi})")
        lines.append("\n**En altura (Tabla A.3-7):**")
        for row in data.get('altura', []):
            phi = row.get('phi_a') or ('PROHIBIDA' if row.get('prohibida_alta') else 'N/A')
            lines.append(f"- {row['tipo']}: {row['nombre']} (φa={phi})")
        return "\n".join(lines)
    
    elif tipo == 'SEPARACION':
        if isinstance(data, dict):
            h = f"h × {data['pisos']}" if data['pisos'] else "h"
            return f"""**Separación sísmica mínima para {data['pisos']} pisos:**

| Condición | Separación |
|-----------|------------|
| Losas coinciden con vecino | {data['separacion_coincide_pct']}% de hn |
| Losas NO coinciden con vecino | {data['separacion_no_coincide_pct']}% de hn |
| Sin edificación vecina | {data['separacion_sin_vecino_pct']}% de hn |

_Fuente: NSR-10 Tabla A.6.5-1_"""
        else:
            lines = ["**Separaciones sísmicas mínimas (Tabla A.6.5-1):**\n"]
            lines.append("| Pisos | Coincide | No coincide | Sin vecino |")
            lines.append("|-------|----------|-------------|------------|")
            for row in data:
                lines.append(f"| {row['pisos']} | {row['separacion_coincide_pct']}% | {row['separacion_no_coincide_pct']}% | {row['separacion_sin_vecino_pct']}% |")
            lines.append("\n_Valores en % de altura hn_")
            return "\n".join(lines)
    
    elif tipo == 'PERFIL_SUELO':
        if isinstance(data, dict):
            vs = f"{data.get('vs_min', '-')} - {data.get('vs_max', '∞')} m/s" if data.get('vs_min') or data.get('vs_max') else 'N/A'
            n = f"{data.get('n_min', '-')} - {data.get('n_max', '∞')}" if data.get('n_min') or data.get('n_max') else 'N/A'
            su = f"{data.get('su_min', '-')} - {data.get('su_max', '∞')} kPa" if data.get('su_min') or data.get('su_max') else 'N/A'
            return f"""**Perfil de suelo tipo {data['tipo']} - {data['nombre']}:**

| Parámetro | Rango |
|-----------|-------|
| Vs (velocidad onda) | {vs} |
| N (SPT) | {n} |
| Su (resistencia) | {su} |

{data.get('descripcion', '')}

_Fuente: NSR-10 Tabla A.2.4-1_"""
        else:
            lines = ["**Clasificación de perfiles de suelo (Tabla A.2.4-1):**\n"]
            lines.append("| Tipo | Nombre | Vs (m/s) |")
            lines.append("|------|--------|----------|")
            for row in data:
                vs = f"{row.get('vs_min', '-')} - {row.get('vs_max', '∞')}"
                lines.append(f"| {row['tipo']} | {row['nombre']} | {vs} |")
            return "\n".join(lines)
    
    elif tipo == 'FORMULA':
        return f"""**{data['nombre']} ({data['simbolo']}):**

**{data['formula_texto']}**

Variables:
{data['variables']}

Unidades: {data['unidades']}

{data.get('descripcion', '')}

_Fuente: NSR-10 {data['seccion']}_"""
    
    elif tipo == 'NO_ESTRUCTURAL':
        if isinstance(data, dict):
            return f"""**Coeficientes para {data['componente']}:**

- **ap** = {data['ap']}
- **Rp** = {data['rp']}

Categoría: {data['categoria']}

_Fuente: NSR-10 {data['tabla_ref']}_"""
        else:
            lines = ["**Coeficientes para elementos no estructurales:**\n"]
            lines.append("| Componente | ap | Rp |")
            lines.append("|------------|-----|-----|")
            for row in data:
                lines.append(f"| {row['componente']} | {row['ap']} | {row['rp']} |")
            return "\n".join(lines)
    
    return None

# =====================================================
# MAIN
# =====================================================

def query_nsr10(pregunta: str) -> str:
    """Responde preguntas sobre NSR-10 usando SQL"""
    tipo, data = classify_and_query(pregunta)
    
    if data:
        response = format_response(tipo, data)
        if response:
            return response
    
    return f"[NO_SQL_MATCH] Pregunta requiere consulta de texto: {pregunta}"

# =====================================================
# TEST
# =====================================================

if __name__ == "__main__":
    tests = [
        "¿Cuál es el valor de Aa para Bogotá?",
        "¿Cuál es el coeficiente R0 para pórticos de concreto DES?",
        "Coeficiente Fa para suelo tipo D con Aa=0.20",
        "Factor de importancia para hospitales",
        "¿Cuál es la deriva máxima permitida?",
        "¿Cuáles son las irregularidades prohibidas en zona alta?",
        "Separación sísmica para edificio de 6 pisos",
        "¿Qué características tiene el suelo tipo E?",
        "¿Cuál es la fórmula del cortante basal Vs?",
        "¿Cuál es la fórmula del período aproximado Ta?",
        "Coeficientes Ct y alfa para pórticos de concreto",
        "¿Qué es la irregularidad de piso blando?",
        "Coeficientes ap y Rp para cielos rasos",
        "R para pórticos de acero con capacidad especial DES",
        "¿Cuál es la fórmula de Fp para elementos no estructurales?",
    ]
    
    print("=" * 70)
    print("NSR-10 ENGINE v2.0 - SQL FIRST")
    print("=" * 70)
    
    passed = 0
    for t in tests:
        print(f"\n📌 {t}")
        print("-" * 70)
        result = query_nsr10(t)
        if "[NO_SQL_MATCH]" not in result:
            passed += 1
            print(result[:500] + "..." if len(result) > 500 else result)
        else:
            print(result)
    
    print("\n" + "=" * 70)
    print(f"RESULTADO: {passed}/{len(tests)} ({100*passed/len(tests):.0f}%)")
    print("=" * 70)

