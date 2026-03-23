#!/usr/bin/env python3
"""
NSR-10 API — LLM Classifier + SQL Engine
"""
import os
import json
import requests
from openai import OpenAI

# Config
SUPABASE_URL = os.environ.get('STRUOS_SUPABASE_URL')
SERVICE_ROLE = os.environ.get('STRUOS_SUPABASE_SERVICE_ROLE')
OPENAI_KEY = os.environ.get('OPENAI_API_KEY')

client = OpenAI(api_key=OPENAI_KEY)

HEADERS = {
    'apikey': SERVICE_ROLE,
    'Authorization': f'Bearer {SERVICE_ROLE}',
    'Content-Type': 'application/json'
}

# Schema de tablas disponibles
SCHEMA = """
TABLAS DISPONIBLES:

1. nsr10_municipios (parámetros sísmicos por municipio)
   - municipio, departamento, aa, av, zona_amenaza, ae, ad
   
2. nsr10_coef_r (coeficientes R₀, Ω₀, Cd por sistema estructural)
   - sistema, material, capacidad_disipacion (DES/DMO/DMI), r0, omega0, cd
   
3. nsr10_coef_fa (coeficiente Fa por tipo de suelo y Aa)
   - soil_type (A-F), aa_value, fa
   
4. nsr10_coef_fv (coeficiente Fv por tipo de suelo y Av)
   - soil_type (A-F), av_value, fv
   
5. nsr10_coef_importancia (factor de importancia I por grupo de uso)
   - grupo_uso (I-IV), coef_i, descripcion
   
6. nsr10_coef_periodo (Ct, α para período aproximado Ta)
   - sistema, ct, alfa
   
7. nsr10_deriva_limites (deriva máxima permitida)
   - sistema_estructural, deriva_max_pct
   
8. nsr10_irregularidad_planta (irregularidades en planta)
   - tipo, nombre, descripcion, phi_p, prohibida_alta
   
9. nsr10_irregularidad_altura (irregularidades en altura)
   - tipo, nombre, descripcion, phi_a, prohibida_alta
   
10. nsr10_separacion_sismica (separación entre edificios)
    - pisos, separacion_coincide_pct, separacion_no_coincide_pct
    
11. nsr10_perfil_suelo (clasificación de suelos A-F)
    - tipo, nombre, vs_min, vs_max, n_min, n_max, su_min, su_max
    
12. nsr10_formulas (fórmulas principales)
    - nombre, simbolo, formula_texto, variables, seccion
    
13. nsr10_coef_no_estructural (ap, Rp para elementos no estructurales)
    - componente, ap, rp, categoria
    
14. nsr10_coef_r_especial (R₀ para estructuras especiales)
    - tipo_estructura, r0
    
15. nsr10_secciones (todas las secciones del título A)
    - seccion, titulo, contenido, pagina

16. nsr10_contenido (full-text de todo el documento)
    - titulo, contenido, tipo

17. nsr10_cargas_vivas (cargas vivas mínimas - Título B)
    - categoria, uso, carga_kn_m2, carga_kgf_m2
    
18. nsr10_cargas_cubiertas (cargas vivas en cubiertas)
    - tipo_cubierta, carga_kn_m2, carga_kgf_m2
    
19. nsr10_masas_materiales (densidades de materiales)
    - material, densidad_kg_m3
    
20. nsr10_cargas_muertas (cargas muertas alternativas)
    - ocupacion, descripcion, fachada_particiones_kn_m2, afinado_piso_kn_m2
    
21. nsr10_combinaciones_carga (combinaciones de carga mayoradas)
    - numero, combinacion, descripcion

22. nsr10_cargas_elementos (cargas muertas de elementos no estructurales - B.3.4.x)
    - categoria (Cielo raso|Relleno piso|Pisos|Cubiertas|Recubrimiento muros|Particiones|Enchapes|Muros|Ventanas)
    - elemento, carga_kn_m2, tabla_ref

23. nsr10_viento (factores de viento - B.6.5)
    - tabla (B.6.5-1|B.6.5-4), parametro, valor, condicion

24. nsr10_exposicion_viento (exposición al viento - B.6.5-2)
    - exposicion (B|C|D), alpha, zg_m, zmin_m

25. nsr10_coef_kz (coeficientes Kz por altura - B.6.5-3)
    - altura_m, kz_exp_b_caso1, kz_exp_b_caso2, kz_exp_c, kz_exp_d

TÍTULO C - CONCRETO:
26. nsr10_espesores_minimos (espesores mínimos vigas/losas - C.9.5(a))
    - elemento, condicion_apoyo, h_min

27. nsr10_deflexiones (deflexiones admisibles - C.9.5(b))
    - tipo_elemento, deflexion_considerada, limite

28. nsr10_doblado_barras (diámetros mínimos de doblado - C.7.2)
    - barra_desde, barra_hasta, diametro_min

29. nsr10_recubrimientos (recubrimientos mínimos - C.7.7.1)
    - condicion, recubrimiento_reforzado_mm, recubrimiento_preesforzado_mm

30. nsr10_exposicion_concreto (clases de exposición - C.4.2.1)
    - categoria, clase, severidad, condicion

31. nsr10_requisitos_concreto (requisitos por exposición - C.4.3.1)
    - clase_exposicion, fc_min_mpa, relacion_ac_max, requisitos_adicionales

32. nsr10_aire_concreto (contenido de aire - C.4.4.1)
    - tamano_agregado_mm, contenido_aire_pct

33. nsr10_fcr (resistencia promedio requerida - C.5.3.2)
    - fc_especificado, formula_fcr, condicion

34. nsr10_phi_concreto (factores de reducción phi - C.9.3.2)
    - condicion, phi

35. nsr10_cuantias_minimas (cuantías mínimas de refuerzo)
    - elemento, tipo_refuerzo, cuantia_min, formula

36. nsr10_barras_refuerzo (dimensiones barras - C.3.5.3-1/2)
    - designacion, sistema (métrico/imperial), diametro_mm, area_mm2, masa_kg_m

37. nsr10_losas_sin_vigas (espesores losas sin vigas - C.9.5(c))
    - fy_mpa, tipo_panel, con_abaco, h_min

38. nsr10_factor_ss (factor modificación desviación estándar - C.5.3.1.2)
    - num_ensayos, factor_modificacion

TÍTULO D - MAMPOSTERÍA:
39. nsr10_morteros_pega (morteros de pega - D.3.4-1)
    - tipo (H|M|S|N), resistencia_min_mpa, proporcion_cemento, proporcion_cal, proporcion_arena

40. nsr10_morteros_relleno (morteros de relleno - D.3.5-1)
    - tipo (Fino|Grueso), proporcion_cemento, proporcion_cal, proporcion_arena, proporcion_agregado

41. nsr10_mamposteria_espesores (espesores mínimos bloques - D.3.6-1)
    - tipo_unidad, espesor_nominal_mm, espesor_pared_min_mm, espesor_tabique_min_mm

42. nsr10_mamposteria_esbeltez (factor corrección esbeltez - D.3.7-1)
    - relacion_h_t, factor_correccion

43. nsr10_mamposteria_doblado (diámetros doblado - D.4.2-1)
    - diametro_barra, diametro_doblado_db

44. nsr10_mamposteria_tolerancias (tolerancias constructivas - D.4.2-2)
    - elemento, tolerancia, unidad

45. nsr10_mamposteria_inyeccion (altura máxima inyección - D.4.6-1)
    - dimension_espacio, altura_max_m, metodo

46. nsr10_mamposteria_machones (coeficientes machones - D.5.4-1)
    - espaciamiento_e_t, espesor_machon_muro, coeficiente

47. nsr10_mamposteria_ruptura (módulo de ruptura fr - D.5.8-1)
    - direccion, tipo_unidad, mortero_tipo, fr_mpa

48. nsr10_mamposteria_cortante (cortante nominal Vm - D.5.8-2)
    - condicion, formula, vm_max

49. nsr10_mamposteria_vn_max (valores máximos Vn - D.5.8-3)
    - condicion, vn_max_formula

50. nsr10_mamposteria_confinada (resistencia mínima unidades - D.10.3-1)
    - tipo_unidad, resistencia_min_mpa, notas

51. nsr10_muros_diafragma (vm máximo muros diafragma - D.11.1-1)
    - condicion, vm_max_mpa

TÍTULO E - CASAS 1-2 PISOS:
52. nsr10_casas_separacion (separación sísmica - E.1.3-1)
    - numero_pisos, separacion_mm

53. nsr10_casas_cimentacion (cimentaciones - E.2.2-1)
    - parametro, un_piso, dos_pisos, unidad

54. nsr10_casas_muros_espesor (espesores muros - E.3.5-1)
    - tipo_unidad, un_piso_mm, dos_pisos_mm

55. nsr10_casas_coef_mo (coeficiente Mo longitud muros - E.3.6-1)
    - zona_amenaza, un_piso, dos_pisos

56. nsr10_casas_losas (espesores losas - E.5.1-1)
    - tipo_losa, espesor_min_mm, notas

57. nsr10_casas_refuerzo_losa (refuerzo losas - E.5.1-2/3)
    - tipo_losa, refuerzo, notas

58. nsr10_casas_bahareque (bahareque encementado - E.7.8-1, E.A-1)
    - parametro, valor, unidad

59. nsr10_casas_guadua (columnas/viguetas guadua - E.7.10-1, E.8.2-1, E.9.2-1)
    - elemento, luz_m, carga_kn, seccion

60. nsr10_casas_madera (viguetas/correas madera - E.8.2-2, E.9.2-2)
    - elemento, grupo_madera, luz_m, separacion_m, seccion

TÍTULO F - ESTRUCTURAS METÁLICAS:
61. nsr10_acero_materiales (propiedades acero - F.2.1)
    - norma, grado, fy_mpa, fu_mpa, uso

62. nsr10_acero_phi (factores de reducción - F.2.4)
    - estado_limite, phi

63. nsr10_acero_esbeltez (límites de esbeltez - F.2.4.1)
    - elemento, tipo, lambda_limite, formula

64. nsr10_acero_soldadura_filete (tamaño mínimo soldadura - F.2.10.2-4)
    - espesor_min_mm, espesor_max_mm, tamano_min_mm

65. nsr10_acero_soldadura_resist (resistencia soldaduras - F.2.10.2-5)
    - tipo_soldadura, tipo_carga, phi, fnw

66. nsr10_acero_pernos_tension (tensión mínima pernos - F.2.10.3-1)
    - diametro_pulg, diametro_mm, tension_min_kn

67. nsr10_acero_pernos_resist (resistencia pernos - F.2.10.3-2)
    - tipo_perno, fnt_mpa, fnv_mpa

68. nsr10_acero_perforaciones (dimensiones perforaciones - F.2.10.3-3)
    - diametro_perno, estandar, sobredimensionada, corta_slot, larga_slot

69. nsr10_acero_distancia_borde (distancia al borde - F.2.10.3-4)
    - diametro_perno, distancia_min_mm

70. nsr10_acero_perfiles (perfiles laminados AISC)
    - tipo, designacion, area_cm2, ix_cm4, zx_cm3, peso_kg_m

71. nsr10_acero_sismico (requisitos sísmicos acero - F.3)
    - sistema, requisito, dmo, des
"""

CLASSIFIER_PROMPT = f"""Eres un clasificador de consultas NSR-10 (norma sísmica colombiana).

{SCHEMA}

Dada una pregunta del usuario, responde SOLO con un JSON válido:
{{
  "tabla": "nombre_tabla",
  "filtros": {{"columna": "valor"}},
  "busqueda_texto": "términos si es búsqueda full-text",
  "limite": 5
}}

Reglas:
- Para municipios específicos: tabla=nsr10_municipios, filtros={{"municipio": "ilike.*nombre*"}}
- Para coeficientes R: tabla=nsr10_coef_r, filtros según material/capacidad/sistema
- Para Fa/Fv: necesitas soil_type y aa_value/av_value
- Para búsquedas generales: tabla=nsr10_contenido o nsr10_secciones, usa busqueda_texto
- Si no sabes qué tabla usar: tabla=nsr10_contenido, busqueda_texto="términos clave"

Ejemplos:
- "Aa de Bogotá" → {{"tabla": "nsr10_municipios", "filtros": {{"municipio": "ilike.*Bogotá*"}}}}
- "R0 pórticos concreto DES" → {{"tabla": "nsr10_coef_r", "filtros": {{"sistema": "ilike.*pórtico*concreto*especial*"}}}}
- "R0 pórticos" o "coeficiente R para pórticos" → {{"tabla": "nsr10_coef_r", "filtros": {{"sistema": "ilike.*pórtico*"}}}}
- IMPORTANTE: Para pórticos, muros, sistemas duales → usa nsr10_coef_r (NO nsr10_coef_r_especial)
- nsr10_coef_r_especial es SOLO para tanques, silos, chimeneas, torres, estructuras especiales
- "deriva máxima" → {{"tabla": "nsr10_deriva_limites", "filtros": {{}}}}
- "qué es piso blando" → {{"tabla": "nsr10_irregularidad_altura", "filtros": {{"nombre": "ilike.*blando*"}}}}
- "cortante basal" → {{"tabla": "nsr10_formulas", "filtros": {{"nombre": "ilike.*cortante*"}}}}
- "fórmula Fp" o "fuerza no estructural" → {{"tabla": "nsr10_formulas", "filtros": {{"nombre": "ilike.*no estructural*"}}}}
- "período fundamental" o "calcular Ta" → {{"tabla": "nsr10_formulas", "filtros": {{"nombre": "ilike.*período*"}}}}
- "sección A.4.3" → {{"tabla": "nsr10_secciones", "filtros": {{"seccion": "eq.A.4.3"}}}}
- "hospitales" o "grupo IV" o "indispensables" → {{"tabla": "nsr10_coef_importancia", "filtros": {{"grupo_uso": "eq.IV"}}}}
- Para separación con más de 10 pisos: usar pisos=10 (máximo en tabla)

TÍTULO B - CARGAS:
Cargas vivas (nsr10_cargas_vivas tiene columnas: categoria, uso):
- "carga viva oficinas" → {{"tabla": "nsr10_cargas_vivas", "filtros": {{"categoria": "ilike.*Oficinas*"}}}}
- "carga viva vivienda" o "residencial" → {{"tabla": "nsr10_cargas_vivas", "filtros": {{"categoria": "ilike.*Residencial*"}}}}
- "carga viva bodegas" o "almacenamiento" → {{"tabla": "nsr10_cargas_vivas", "filtros": {{"categoria": "ilike.*Almacenamiento*"}}}}
- "carga viva comercio" → {{"tabla": "nsr10_cargas_vivas", "filtros": {{"categoria": "ilike.*Comercio*"}}}}
- "carga viva hospitales" o "institucional" → {{"tabla": "nsr10_cargas_vivas", "filtros": {{"categoria": "ilike.*Institucional*"}}}}
- "carga viva colegios" o "educativos" o "salones" → {{"tabla": "nsr10_cargas_vivas", "filtros": {{"categoria": "ilike.*Educativos*"}}}}
- "carga viva gimnasios" o "reunión" o "teatros" → {{"tabla": "nsr10_cargas_vivas", "filtros": {{"categoria": "ilike.*Reunión*"}}}}
- "carga viva escaleras" o "corredores" → {{"tabla": "nsr10_cargas_vivas", "filtros": {{"uso": "ilike.*escalera*"}}}}
- "carga cubierta" → {{"tabla": "nsr10_cargas_cubiertas", "filtros": {{}}}}

Materiales y densidades:
- "densidad concreto" o "peso concreto" → {{"tabla": "nsr10_masas_materiales", "filtros": {{"material": "ilike.*concreto*"}}}}
- "densidad acero" → {{"tabla": "nsr10_masas_materiales", "filtros": {{"material": "ilike.*acero*"}}}}
- "peso mampostería" → {{"tabla": "nsr10_masas_materiales", "filtros": {{"material": "ilike.*mampostería*"}}}}

Cargas muertas elementos (nsr10_cargas_elementos):
- "carga cielo raso" o "carga falso techo" → {{"tabla": "nsr10_cargas_elementos", "filtros": {{"categoria": "ilike.*Cielo*"}}}}
- "carga particiones" o "drywall" → {{"tabla": "nsr10_cargas_elementos", "filtros": {{"categoria": "ilike.*Particiones*"}}}}
- "carga muros" o "peso muros" → {{"tabla": "nsr10_cargas_elementos", "filtros": {{"categoria": "ilike.*Muros*"}}}}
- "carga teja" o "carga cubierta muerta" → {{"tabla": "nsr10_cargas_elementos", "filtros": {{"categoria": "ilike.*Cubiertas*"}}}}
- "carga piso" o "acabado piso" → {{"tabla": "nsr10_cargas_elementos", "filtros": {{"categoria": "ilike.*Pisos*"}}}}
- "carga enchape" → {{"tabla": "nsr10_cargas_elementos", "filtros": {{"categoria": "ilike.*Enchapes*"}}}}

Combinaciones:
- "combinaciones de carga" → {{"tabla": "nsr10_combinaciones_carga", "filtros": {{}}}}
- "combinación sismo" o "combinación sísmica" → {{"tabla": "nsr10_combinaciones_carga", "filtros": {{"descripcion": "ilike.*sísm*"}}}}

Viento:
- "factor importancia viento" o "factor I viento" → {{"tabla": "nsr10_viento", "filtros": {{"tabla": "eq.B.6.5-1"}}}}
- "factor Kd" o "direccionalidad viento" → {{"tabla": "nsr10_viento", "filtros": {{"tabla": "eq.B.6.5-4"}}}}
- "exposición B" → {{"tabla": "nsr10_exposicion_viento", "filtros": {{"exposicion": "eq.B"}}}}
- "exposición C" o "exposición tipo C" → {{"tabla": "nsr10_exposicion_viento", "filtros": {{"exposicion": "eq.C"}}}}
- "exposición D" → {{"tabla": "nsr10_exposicion_viento", "filtros": {{"exposicion": "eq.D"}}}}
- "todas las exposiciones viento" → {{"tabla": "nsr10_exposicion_viento", "filtros": {{}}}}
- "coeficiente Kz" o "Kz altura" → {{"tabla": "nsr10_coef_kz", "filtros": {{}}}}

TÍTULO C - CONCRETO:
- "espesor mínimo losa" o "altura mínima viga" → {{"tabla": "nsr10_espesores_minimos", "filtros": {{}}}}
- "deflexión máxima" o "deflexión admisible" → {{"tabla": "nsr10_deflexiones", "filtros": {{}}}}
- "diámetro doblado" o "radio doblado barra" → {{"tabla": "nsr10_doblado_barras", "filtros": {{}}}}
- "recubrimiento" o "protección refuerzo" → {{"tabla": "nsr10_recubrimientos", "filtros": {{}}}}
- "clase exposición concreto" o "exposición sulfatos" → {{"tabla": "nsr10_exposicion_concreto", "filtros": {{}}}}
- "f'c mínimo" o "requisitos concreto" → {{"tabla": "nsr10_requisitos_concreto", "filtros": {{}}}}
- "contenido aire" o "aire incorporado" → {{"tabla": "nsr10_aire_concreto", "filtros": {{}}}}
- "f'cr" o "resistencia promedio requerida" o "fcr" → {{"tabla": "nsr10_fcr", "filtros": {{}}}}
- "factor phi" o "reducción resistencia" → {{"tabla": "nsr10_phi_concreto", "filtros": {{}}}}
- "cuantía mínima" o "As mínimo" → {{"tabla": "nsr10_cuantias_minimas", "filtros": {{}}}}
- "cuantía columnas" → {{"tabla": "nsr10_cuantias_minimas", "filtros": {{"elemento": "ilike.*Columna*"}}}}
- "cuantía vigas" → {{"tabla": "nsr10_cuantias_minimas", "filtros": {{"elemento": "ilike.*Viga*"}}}}
- "cuantía muros" → {{"tabla": "nsr10_cuantias_minimas", "filtros": {{"elemento": "ilike.*Muro*"}}}}
- "área barra No.5" o "diámetro barra" → {{"tabla": "nsr10_barras_refuerzo", "filtros": {{"designacion": "ilike.*No.5*"}}}}
- "barras de refuerzo" o "tabla de barras" → {{"tabla": "nsr10_barras_refuerzo", "filtros": {{}}}}
- "espesor losa sin vigas" o "losa plana" → {{"tabla": "nsr10_losas_sin_vigas", "filtros": {{}}}}
- "factor modificación ss" o "desviación estándar ensayos" → {{"tabla": "nsr10_factor_ss", "filtros": {{}}}}

TÍTULO D - MAMPOSTERÍA:
- "mortero tipo M" o "mortero tipo S" → {{"tabla": "nsr10_morteros_pega", "filtros": {{"tipo": "ilike.*M*"}}}}
- "morteros de pega" o "resistencia morteros" → {{"tabla": "nsr10_morteros_pega", "filtros": {{}}}}
- "mortero relleno" o "mortero inyección" → {{"tabla": "nsr10_morteros_relleno", "filtros": {{}}}}
- "espesor mínimo bloque" o "espesor pared bloque" → {{"tabla": "nsr10_mamposteria_espesores", "filtros": {{}}}}
- "factor esbeltez mampostería" o "corrección esbeltez" → {{"tabla": "nsr10_mamposteria_esbeltez", "filtros": {{}}}}
- "doblado mampostería" → {{"tabla": "nsr10_mamposteria_doblado", "filtros": {{}}}}
- "tolerancias mampostería" o "verticalidad muros" → {{"tabla": "nsr10_mamposteria_tolerancias", "filtros": {{}}}}
- "altura inyección" o "inyección mampostería" → {{"tabla": "nsr10_mamposteria_inyeccion", "filtros": {{}}}}
- "coeficientes machones" → {{"tabla": "nsr10_mamposteria_machones", "filtros": {{}}}}
- "módulo ruptura mampostería" o "fr mampostería" → {{"tabla": "nsr10_mamposteria_ruptura", "filtros": {{}}}}
- "cortante mampostería" o "Vm mampostería" → {{"tabla": "nsr10_mamposteria_cortante", "filtros": {{}}}}
- "Vn máximo mampostería" → {{"tabla": "nsr10_mamposteria_vn_max", "filtros": {{}}}}
- "resistencia mampostería confinada" o "unidades confinada" → {{"tabla": "nsr10_mamposteria_confinada", "filtros": {{}}}}
- "muros diafragma" → {{"tabla": "nsr10_muros_diafragma", "filtros": {{}}}}

TÍTULO E - CASAS 1-2 PISOS:
- "separación sísmica casas" → {{"tabla": "nsr10_casas_separacion", "filtros": {{}}}}
- "cimentación casas" o "cimiento corrido" → {{"tabla": "nsr10_casas_cimentacion", "filtros": {{}}}}
- "espesor muros casas" → {{"tabla": "nsr10_casas_muros_espesor", "filtros": {{}}}}
- "coeficiente Mo" o "longitud muros casas" → {{"tabla": "nsr10_casas_coef_mo", "filtros": {{}}}}
- "espesor losa casas" → {{"tabla": "nsr10_casas_losas", "filtros": {{}}}}
- "refuerzo losa casas" → {{"tabla": "nsr10_casas_refuerzo_losa", "filtros": {{}}}}
- "bahareque" o "CB bahareque" → {{"tabla": "nsr10_casas_bahareque", "filtros": {{}}}}
- "columnas guadua" o "capacidad guadua" → {{"tabla": "nsr10_casas_guadua", "filtros": {{"elemento": "ilike.*Columna*"}}}}
- "viguetas guadua" → {{"tabla": "nsr10_casas_guadua", "filtros": {{"elemento": "ilike.*Vigueta*"}}}}
- "correas guadua" → {{"tabla": "nsr10_casas_guadua", "filtros": {{"elemento": "ilike.*Correa*"}}}}
- "viguetas madera" → {{"tabla": "nsr10_casas_madera", "filtros": {{"elemento": "ilike.*Vigueta*"}}}}
- "correas madera" → {{"tabla": "nsr10_casas_madera", "filtros": {{"elemento": "ilike.*Correa*"}}}}

TÍTULO F - ESTRUCTURAS METÁLICAS:
- "acero A36" o "fy acero" o "propiedades acero" → {{"tabla": "nsr10_acero_materiales", "filtros": {{}}}}
- "A572" o "A992" → {{"tabla": "nsr10_acero_materiales", "filtros": {{"norma": "ilike.*A572*"}}}}
- "factor phi acero" o "reducción acero" → {{"tabla": "nsr10_acero_phi", "filtros": {{}}}}
- "esbeltez acero" o "compacidad" o "lambda limite" → {{"tabla": "nsr10_acero_esbeltez", "filtros": {{}}}}
- "soldadura filete" o "tamaño mínimo soldadura" → {{"tabla": "nsr10_acero_soldadura_filete", "filtros": {{}}}}
- "resistencia soldadura" o "Fnw soldadura" → {{"tabla": "nsr10_acero_soldadura_resist", "filtros": {{}}}}
- "tensión pernos" o "pretensión pernos" → {{"tabla": "nsr10_acero_pernos_tension", "filtros": {{}}}}
- "resistencia pernos" o "A325" o "A490" → {{"tabla": "nsr10_acero_pernos_resist", "filtros": {{}}}}
- "perforaciones pernos" o "agujeros pernos" → {{"tabla": "nsr10_acero_perforaciones", "filtros": {{}}}}
- "distancia al borde" → {{"tabla": "nsr10_acero_distancia_borde", "filtros": {{}}}}
- "perfil W" o "propiedades W14" → {{"tabla": "nsr10_acero_perfiles", "filtros": {{"designacion": "ilike.*W14*"}}}}
- "perfiles acero" o "HSS" → {{"tabla": "nsr10_acero_perfiles", "filtros": {{}}}}
- "pórtico especial acero" o "SMF" o "requisitos sísmicos acero" → {{"tabla": "nsr10_acero_sismico", "filtros": {{}}}}
- "arriostrado concéntrico" o "SCBF" → {{"tabla": "nsr10_acero_sismico", "filtros": {{"sistema": "ilike.*SCBF*"}}}}
"""

def classify_query(pregunta: str) -> dict:
    """Usa GPT-4o-mini para clasificar la query"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": CLASSIFIER_PROMPT},
            {"role": "user", "content": pregunta}
        ],
        temperature=0,
        max_tokens=200
    )
    
    content = response.choices[0].message.content.strip()
    # Extraer JSON
    if "```" in content:
        content = content.split("```")[1].replace("json", "").strip()
    
    return json.loads(content)

def execute_query(clasificacion: dict) -> list:
    """Ejecuta la query SQL en Supabase"""
    tabla = clasificacion.get('tabla', 'nsr10_contenido')
    filtros = clasificacion.get('filtros', {})
    busqueda = clasificacion.get('busqueda_texto', '')
    limite = clasificacion.get('limite', 5)
    
    # Fix: Para separación sísmica, pisos > 10 usa 10
    if tabla == 'nsr10_separacion_sismica' and 'pisos' in filtros:
        pisos_val = filtros['pisos']
        if isinstance(pisos_val, str):
            pisos_num = int(pisos_val.replace('eq.', '').replace('gte.', '').replace('lte.', ''))
        else:
            pisos_num = int(pisos_val)
        if pisos_num > 10:
            filtros['pisos'] = '10'
    
    url = f"{SUPABASE_URL}/rest/v1/{tabla}?limit={limite}"
    
    # Agregar filtros
    for col, val in filtros.items():
        val_str = str(val)
        if val_str.startswith('ilike.') or val_str.startswith('eq.') or val_str.startswith('gte.') or val_str.startswith('lte.'):
            url += f"&{col}={val_str}"
        else:
            url += f"&{col}=eq.{val_str}"
    
    # Full-text search
    if busqueda and not filtros:
        url += f"&contenido=ilike.*{busqueda.replace(' ', '*')}*"
    
    r = requests.get(url, headers=HEADERS, timeout=10)
    return r.json() if r.status_code == 200 else []

def format_response(tabla: str, data: list) -> str:
    """Formatea la respuesta según el tipo de tabla"""
    if not data:
        return "No encontré resultados."
    
    if tabla == 'nsr10_municipios':
        row = data[0]
        return f"""**{row['municipio']}, {row['departamento']}**

| Parámetro | Valor |
|-----------|-------|
| Aa | {row['aa']} |
| Av | {row['av']} |
| Zona | {row['zona_amenaza']} |
| Ae | {row.get('ae', 'N/A')} |
| Ad | {row.get('ad', 'N/A')} |"""

    elif tabla == 'nsr10_coef_r':
        row = data[0]
        return f"""**{row['sistema']}**

| Coef. | Valor |
|-------|-------|
| R₀ | **{row['r0']}** |
| Ω₀ | {row['omega0']} |
| Cd | {row['cd']} |"""

    elif tabla == 'nsr10_coef_fa':
        row = data[0]
        return f"**Fa = {row['fa']}** (suelo {row['soil_type']}, Aa={row['aa_value']})"

    elif tabla == 'nsr10_coef_fv':
        row = data[0]
        return f"**Fv = {row['fv']}** (suelo {row['soil_type']}, Av={row['av_value']})"

    elif tabla == 'nsr10_deriva_limites':
        lines = ["**Derivas máximas permitidas:**\n"]
        for row in data:
            lines.append(f"- {row['sistema_estructural']}: **{row['deriva_max_pct']}%**")
        return "\n".join(lines)

    elif tabla in ('nsr10_irregularidad_planta', 'nsr10_irregularidad_altura'):
        row = data[0]
        phi = row.get('phi_p') or row.get('phi_a') or 'N/A'
        prohib = "**PROHIBIDA en zona alta**" if row.get('prohibida_alta') else f"φ = {phi}"
        return f"""**{row['tipo']} — {row['nombre']}**

{row['descripcion']}

{prohib}"""

    elif tabla == 'nsr10_perfil_suelo':
        row = data[0]
        return f"""**Suelo tipo {row['tipo']} — {row['nombre']}**

- Vs: {row.get('vs_min', '-')} - {row.get('vs_max', '∞')} m/s
- N (SPT): {row.get('n_min', '-')} - {row.get('n_max', '∞')}
- Su: {row.get('su_min', '-')} - {row.get('su_max', '∞')} kPa"""

    elif tabla == 'nsr10_formulas':
        row = data[0]
        return f"""**{row['nombre']} ({row['simbolo']})**

`{row['formula_texto']}`

Variables: {row['variables']}
Sección: {row['seccion']}"""

    elif tabla == 'nsr10_secciones':
        row = data[0]
        return f"""**{row['seccion']} — {row['titulo']}**

{row['contenido'][:800]}..."""

    elif tabla == 'nsr10_coef_importancia':
        row = data[0]
        return f"**Grupo {row['grupo_uso']}:** I = {row['coef_i']}\n\n{row['descripcion']}"

    elif tabla == 'nsr10_separacion_sismica':
        row = data[0]
        return f"""**Separación sísmica para {row['pisos']} pisos:**

- Losas coinciden: {row['separacion_coincide_pct']}% hn
- No coinciden: {row['separacion_no_coincide_pct']}% hn"""

    elif tabla == 'nsr10_coef_r_especial':
        lines = ["**R₀ para estructuras especiales:**\n"]
        for row in data:
            lines.append(f"- {row['tipo_estructura']}: **R₀ = {row['r0']}**")
        return "\n".join(lines)

    elif tabla == 'nsr10_coef_periodo':
        lines = ["**Coeficientes Ct y α para período Ta = Ct × hn^α:**\n"]
        for row in data:
            lines.append(f"- {row.get('sistema', 'N/A')}: Ct = {row.get('ct', 'N/A')}, α = {row.get('alfa', 'N/A')}")
        return "\n".join(lines)

    elif tabla == 'nsr10_cargas_vivas':
        lines = ["**Cargas vivas mínimas (Tabla B.4.2.1-1):**\n"]
        for row in data:
            lines.append(f"- {row['categoria']} - {row['uso']}: **{row['carga_kn_m2']} kN/m²** ({row['carga_kgf_m2']} kgf/m²)")
        return "\n".join(lines)

    elif tabla == 'nsr10_cargas_cubiertas':
        lines = ["**Cargas vivas en cubiertas (Tabla B.4.2.1-2):**\n"]
        for row in data:
            carga = f"{row['carga_kn_m2']} kN/m²" if row['carga_kn_m2'] else row.get('notas', 'Ver nota')
            lines.append(f"- {row['tipo_cubierta']}: **{carga}**")
        return "\n".join(lines)

    elif tabla == 'nsr10_masas_materiales':
        lines = ["**Masas de materiales (Tabla B.3.2-1):**\n"]
        for row in data:
            lines.append(f"- {row['material']}: **{row['densidad_kg_m3']} kg/m³**")
        return "\n".join(lines)

    elif tabla == 'nsr10_cargas_muertas':
        lines = ["**Cargas muertas alternativas (Tabla B.3.4.3-1):**\n"]
        for row in data:
            desc = f" ({row['descripcion']})" if row.get('descripcion') else ""
            lines.append(f"- {row['ocupacion']}{desc}: Fachada={row['fachada_particiones_kn_m2']} kN/m², Piso={row['afinado_piso_kn_m2']} kN/m²")
        return "\n".join(lines)

    elif tabla == 'nsr10_combinaciones_carga':
        lines = ["**Combinaciones de carga mayoradas (B.2.4.2):**\n"]
        for row in data:
            lines.append(f"- **{row['numero']}**: `{row['combinacion']}` — {row.get('descripcion', '')}")
        return "\n".join(lines)

    elif tabla == 'nsr10_cargas_elementos':
        lines = ["**Cargas muertas elementos no estructurales:**\n"]
        for row in data:
            lines.append(f"- {row['categoria']} - {row['elemento']}: **{row['carga_kn_m2']} kN/m²** (Tabla {row.get('tabla_ref', '')})")
        return "\n".join(lines)

    elif tabla == 'nsr10_viento':
        lines = ["**Factores de viento:**\n"]
        for row in data:
            cond = f" ({row['condicion']})" if row.get('condicion') else ""
            lines.append(f"- {row['parametro']}: **{row['valor']}**{cond}")
        return "\n".join(lines)

    elif tabla == 'nsr10_exposicion_viento':
        lines = ["**Exposición al viento (Tabla B.6.5-2):**\n"]
        for row in data:
            lines.append(f"- Exposición {row['exposicion']}: α={row['alpha']}, Zg={row['zg_m']}m, Zmin={row['zmin_m']}m")
        return "\n".join(lines)

    elif tabla == 'nsr10_coef_kz':
        lines = ["**Coeficientes Kz por altura (Tabla B.6.5-3):**\n"]
        lines.append("| Altura (m) | Exp B (Caso 1) | Exp B (Caso 2) | Exp C | Exp D |")
        lines.append("|------------|----------------|----------------|-------|-------|")
        for row in data:
            lines.append(f"| {row['altura_m']} | {row['kz_exp_b_caso1']} | {row['kz_exp_b_caso2']} | {row['kz_exp_c']} | {row['kz_exp_d']} |")
        return "\n".join(lines)

    # TÍTULO C - CONCRETO
    elif tabla == 'nsr10_espesores_minimos':
        lines = ["**Espesores mínimos vigas/losas (Tabla C.9.5(a)):**\n"]
        for row in data:
            lines.append(f"- {row['elemento']} - {row['condicion_apoyo']}: **h ≥ {row['h_min']}**")
        return "\n".join(lines)

    elif tabla == 'nsr10_deflexiones':
        lines = ["**Deflexiones admisibles (Tabla C.9.5(b)):**\n"]
        for row in data:
            lines.append(f"- {row['tipo_elemento']}: **{row['limite']}**")
        return "\n".join(lines)

    elif tabla == 'nsr10_doblado_barras':
        lines = ["**Diámetros mínimos de doblado (Tabla C.7.2):**\n"]
        for row in data:
            lines.append(f"- {row['barra_desde']} a {row['barra_hasta']}: **{row['diametro_min']}**")
        return "\n".join(lines)

    elif tabla == 'nsr10_recubrimientos':
        lines = ["**Recubrimientos mínimos (C.7.7.1):**\n"]
        for row in data:
            ref = f"{row['recubrimiento_reforzado_mm']}mm" if row['recubrimiento_reforzado_mm'] else "N/A"
            pre = f"{row['recubrimiento_preesforzado_mm']}mm" if row['recubrimiento_preesforzado_mm'] else "N/A"
            lines.append(f"- {row['condicion']}: Reforzado={ref}, Preesforzado={pre}")
        return "\n".join(lines)

    elif tabla == 'nsr10_exposicion_concreto':
        lines = ["**Clases de exposición (Tabla C.4.2.1):**\n"]
        for row in data:
            lines.append(f"- **{row['clase']}** ({row['categoria']}, {row['severidad']}): {row['condicion']}")
        return "\n".join(lines)

    elif tabla == 'nsr10_requisitos_concreto':
        lines = ["**Requisitos de concreto por exposición (Tabla C.4.3.1):**\n"]
        for row in data:
            fc = f"f'c ≥ {row['fc_min_mpa']} MPa" if row['fc_min_mpa'] else "Sin requisito"
            ac = f"a/c ≤ {row['relacion_ac_max']}" if row['relacion_ac_max'] else ""
            lines.append(f"- **{row['clase_exposicion']}**: {fc}, {ac}")
            if row.get('requisitos_adicionales'):
                lines.append(f"  {row['requisitos_adicionales']}")
        return "\n".join(lines)

    elif tabla == 'nsr10_aire_concreto':
        lines = ["**Contenido de aire (Tabla C.4.4.1):**\n"]
        for row in data:
            lines.append(f"- Agregado {row['tamano_agregado_mm']}mm: **{row['contenido_aire_pct']}%**")
        return "\n".join(lines)

    elif tabla == 'nsr10_fcr':
        lines = ["**Resistencia promedio requerida f'cr:**\n"]
        for row in data:
            lines.append(f"- {row['fc_especificado']}: **{row['formula_fcr']}** ({row['condicion']})")
        return "\n".join(lines)

    elif tabla == 'nsr10_phi_concreto':
        lines = ["**Factores de reducción φ (C.9.3.2):**\n"]
        for row in data:
            lines.append(f"- {row['condicion']}: **φ = {row['phi']}**")
        return "\n".join(lines)

    elif tabla == 'nsr10_cuantias_minimas':
        lines = ["**Cuantías mínimas de refuerzo:**\n"]
        for row in data:
            formula = f" ({row['formula']})" if row.get('formula') else ""
            lines.append(f"- {row['elemento']} - {row['tipo_refuerzo']}: **{row['cuantia_min']}**{formula}")
        return "\n".join(lines)

    elif tabla == 'nsr10_barras_refuerzo':
        lines = ["**Barras de refuerzo (Tabla C.3.5.3-1/2):**\n"]
        lines.append("| Barra | Ø (mm) | Área (mm²) | Masa (kg/m) |")
        lines.append("|-------|--------|------------|-------------|")
        for row in data:
            lines.append(f"| {row['designacion']} | {row['diametro_mm']} | {row['area_mm2']} | {row['masa_kg_m']} |")
        return "\n".join(lines)

    elif tabla == 'nsr10_losas_sin_vigas':
        lines = ["**Espesores mínimos losas sin vigas (Tabla C.9.5(c)):**\n"]
        for row in data:
            abaco = "con ábaco" if row['con_abaco'] else "sin ábaco"
            lines.append(f"- fy={row['fy_mpa']} MPa, {row['tipo_panel']}, {abaco}: **h ≥ {row['h_min']}**")
        return "\n".join(lines)

    elif tabla == 'nsr10_factor_ss':
        lines = ["**Factor de modificación desviación estándar (Tabla C.5.3.1.2):**\n"]
        for row in data:
            lines.append(f"- {row['num_ensayos']} ensayos: factor = **{row['factor_modificacion']}**")
        return "\n".join(lines)

    # TÍTULO D - MAMPOSTERÍA
    elif tabla == 'nsr10_morteros_pega':
        lines = ["**Morteros de pega (Tabla D.3.4-1):**\n"]
        for row in data:
            lines.append(f"- Tipo {row['tipo']}: f'm ≥ **{row['resistencia_min_mpa']} MPa** — Cemento:{row['proporcion_cemento']}, Cal:{row['proporcion_cal']}, Arena:{row['proporcion_arena']}")
        return "\n".join(lines)

    elif tabla == 'nsr10_morteros_relleno':
        lines = ["**Morteros de relleno (Tabla D.3.5-1):**\n"]
        for row in data:
            lines.append(f"- {row['tipo']}: Cemento:{row['proporcion_cemento']}, Cal:{row['proporcion_cal']}, Arena:{row['proporcion_arena']}, Agregado:{row['proporcion_agregado']}")
        return "\n".join(lines)

    elif tabla == 'nsr10_mamposteria_espesores':
        lines = ["**Espesores mínimos bloques (Tabla D.3.6-1):**\n"]
        for row in data:
            lines.append(f"- {row['tipo_unidad']}: Pared ≥ **{row['espesor_pared_min_mm']} mm**, Tabique ≥ **{row['espesor_tabique_min_mm']} mm**")
        return "\n".join(lines)

    elif tabla == 'nsr10_mamposteria_esbeltez':
        lines = ["**Factor corrección esbeltez (Tabla D.3.7-1):**\n"]
        for row in data:
            lines.append(f"- h/t = {row['relacion_h_t']}: factor = **{row['factor_correccion']}**")
        return "\n".join(lines)

    elif tabla == 'nsr10_mamposteria_doblado':
        lines = ["**Diámetros doblado mampostería (Tabla D.4.2-1):**\n"]
        for row in data:
            lines.append(f"- {row['diametro_barra']}: **{row['diametro_doblado_db']} db**")
        return "\n".join(lines)

    elif tabla == 'nsr10_mamposteria_tolerancias':
        lines = ["**Tolerancias constructivas (Tabla D.4.2-2):**\n"]
        for row in data:
            lines.append(f"- {row['elemento']}: **{row['tolerancia']} {row.get('unidad', '')}**")
        return "\n".join(lines)

    elif tabla == 'nsr10_mamposteria_inyeccion':
        lines = ["**Altura máxima inyección (Tabla D.4.6-1):**\n"]
        for row in data:
            lines.append(f"- Espacio {row['dimension_espacio']}: h ≤ **{row['altura_max_m']} m** ({row.get('metodo', '')})")
        return "\n".join(lines)

    elif tabla == 'nsr10_mamposteria_machones':
        lines = ["**Coeficientes machones (Tabla D.5.4-1):**\n"]
        for row in data:
            lines.append(f"- Espaciamiento {row['espaciamiento_e_t']}, espesor machón/muro={row['espesor_machon_muro']}: coef = **{row['coeficiente']}**")
        return "\n".join(lines)

    elif tabla == 'nsr10_mamposteria_ruptura':
        lines = ["**Módulo de ruptura fr (Tabla D.5.8-1):**\n"]
        for row in data:
            lines.append(f"- {row['direccion']}, {row['tipo_unidad']}, mortero {row['mortero_tipo']}: fr = **{row['fr_mpa']} MPa**")
        return "\n".join(lines)

    elif tabla == 'nsr10_mamposteria_cortante':
        lines = ["**Cortante nominal Vm (Tabla D.5.8-2):**\n"]
        for row in data:
            lines.append(f"- {row['condicion']}: `{row['formula']}`")
        return "\n".join(lines)

    elif tabla == 'nsr10_mamposteria_vn_max':
        lines = ["**Valores máximos Vn (Tabla D.5.8-3):**\n"]
        for row in data:
            lines.append(f"- {row['condicion']}: Vn ≤ `{row['vn_max_formula']}`")
        return "\n".join(lines)

    elif tabla == 'nsr10_mamposteria_confinada':
        lines = ["**Resistencia mínima mampostería confinada (Tabla D.10.3-1):**\n"]
        for row in data:
            lines.append(f"- {row['tipo_unidad']}: f'cu ≥ **{row['resistencia_min_mpa']} MPa**")
        return "\n".join(lines)

    elif tabla == 'nsr10_muros_diafragma':
        lines = ["**Cortante máximo muros diafragma (Tabla D.11.1-1):**\n"]
        for row in data:
            lines.append(f"- {row['condicion']}: vm ≤ **{row['vm_max_mpa']} MPa**")
        return "\n".join(lines)

    # TÍTULO E - CASAS 1-2 PISOS
    elif tabla == 'nsr10_casas_separacion':
        lines = ["**Separación sísmica casas (Tabla E.1.3-1):**\n"]
        for row in data:
            lines.append(f"- {row['numero_pisos']} piso(s): **{row['separacion_mm']} mm**")
        return "\n".join(lines)

    elif tabla == 'nsr10_casas_cimentacion':
        lines = ["**Cimentaciones casas (Tabla E.2.2-1):**\n"]
        for row in data:
            lines.append(f"- {row['parametro']}: 1 piso={row['un_piso']}, 2 pisos={row['dos_pisos']} {row.get('unidad', '')}")
        return "\n".join(lines)

    elif tabla == 'nsr10_casas_muros_espesor':
        lines = ["**Espesores muros casas (Tabla E.3.5-1):**\n"]
        for row in data:
            lines.append(f"- {row['tipo_unidad']}: 1 piso=**{row['un_piso_mm']} mm**, 2 pisos=**{row['dos_pisos_mm']} mm**")
        return "\n".join(lines)

    elif tabla == 'nsr10_casas_coef_mo':
        lines = ["**Coeficiente Mo longitud muros (Tabla E.3.6-1):**\n"]
        for row in data:
            lines.append(f"- Amenaza {row['zona_amenaza']}: 1 piso=**{row['un_piso']}**, 2 pisos=**{row['dos_pisos']}**")
        return "\n".join(lines)

    elif tabla == 'nsr10_casas_losas':
        lines = ["**Espesores losas casas (Tabla E.5.1-1):**\n"]
        for row in data:
            lines.append(f"- {row['tipo_losa']}: h ≥ **{row['espesor_min_mm']} mm** ({row.get('notas', '')})")
        return "\n".join(lines)

    elif tabla == 'nsr10_casas_refuerzo_losa':
        lines = ["**Refuerzo losas casas:**\n"]
        for row in data:
            lines.append(f"- {row['tipo_losa']}: **{row['refuerzo']}** ({row.get('notas', '')})")
        return "\n".join(lines)

    elif tabla == 'nsr10_casas_bahareque':
        lines = ["**Bahareque encementado:**\n"]
        for row in data:
            unidad = row.get('unidad', '') or ''
            lines.append(f"- {row['parametro']}: **{row['valor']}** {unidad}")
        return "\n".join(lines)

    elif tabla == 'nsr10_casas_guadua':
        lines = ["**Guadua estructural:**\n"]
        for row in data:
            carga = f", P={row['carga_kn']} kN" if row.get('carga_kn') else ""
            lines.append(f"- {row['elemento']} L={row['luz_m']}m: **{row['seccion']}**{carga}")
        return "\n".join(lines)

    elif tabla == 'nsr10_casas_madera':
        lines = ["**Madera estructural:**\n"]
        for row in data:
            lines.append(f"- {row['elemento']} {row['grupo_madera']} L={row['luz_m']}m @ {row['separacion_m']}m: **{row['seccion']}**")
        return "\n".join(lines)

    # TÍTULO F - ESTRUCTURAS METÁLICAS
    elif tabla == 'nsr10_acero_materiales':
        lines = ["**Propiedades de acero:**\n"]
        for row in data:
            grado = f" {row['grado']}" if row.get('grado') else ""
            lines.append(f"- {row['norma']}{grado}: Fy=**{row['fy_mpa']} MPa**, Fu=**{row['fu_mpa']} MPa** ({row.get('uso', '')})")
        return "\n".join(lines)

    elif tabla == 'nsr10_acero_phi':
        lines = ["**Factores de reducción φ (acero):**\n"]
        for row in data:
            lines.append(f"- {row['estado_limite']}: φ = **{row['phi']}**")
        return "\n".join(lines)

    elif tabla == 'nsr10_acero_esbeltez':
        lines = ["**Límites de esbeltez:**\n"]
        for row in data:
            lines.append(f"- {row['elemento']} ({row['tipo']}): {row['lambda_limite']} ≤ `{row['formula']}`")
        return "\n".join(lines)

    elif tabla == 'nsr10_acero_soldadura_filete':
        lines = ["**Tamaño mínimo soldadura filete (Tabla F.2.10.2-4):**\n"]
        for row in data:
            lines.append(f"- Espesor {row['espesor_min_mm']}-{row['espesor_max_mm']} mm: tamaño mín = **{row['tamano_min_mm']} mm**")
        return "\n".join(lines)

    elif tabla == 'nsr10_acero_soldadura_resist':
        lines = ["**Resistencia de soldaduras:**\n"]
        for row in data:
            lines.append(f"- {row['tipo_soldadura']} - {row['tipo_carga']}: φ={row['phi']}, Fnw=`{row['fnw']}`")
        return "\n".join(lines)

    elif tabla == 'nsr10_acero_pernos_tension':
        lines = ["**Tensión mínima pernos (Tabla F.2.10.3-1):**\n"]
        lines.append("| Diámetro | Tensión mín |")
        lines.append("|----------|-------------|")
        for row in data:
            lines.append(f"| {row['diametro_pulg']} ({row['diametro_mm']}mm) | **{row['tension_min_kn']} kN** |")
        return "\n".join(lines)

    elif tabla == 'nsr10_acero_pernos_resist':
        lines = ["**Resistencia nominal pernos (Tabla F.2.10.3-2):**\n"]
        for row in data:
            lines.append(f"- {row['tipo_perno']}: Fnt=**{row['fnt_mpa']} MPa**, Fnv=**{row['fnv_mpa']} MPa**")
        return "\n".join(lines)

    elif tabla == 'nsr10_acero_perforaciones':
        lines = ["**Dimensiones perforaciones (Tabla F.2.10.3-3):**\n"]
        for row in data:
            lines.append(f"- Perno {row['diametro_perno']}: Std={row['estandar']}, Sobredim={row['sobredimensionada']}")
        return "\n".join(lines)

    elif tabla == 'nsr10_acero_distancia_borde':
        lines = ["**Distancia mínima al borde (Tabla F.2.10.3-4):**\n"]
        for row in data:
            lines.append(f"- Perno {row['diametro_perno']}: **{row['distancia_min_mm']} mm**")
        return "\n".join(lines)

    elif tabla == 'nsr10_acero_perfiles':
        lines = ["**Perfiles laminados:**\n"]
        lines.append("| Perfil | Área (cm²) | Ix (cm⁴) | Zx (cm³) | Peso (kg/m) |")
        lines.append("|--------|------------|----------|----------|-------------|")
        for row in data:
            lines.append(f"| {row['designacion']} | {row['area_cm2']} | {row['ix_cm4']} | {row['zx_cm3']} | {row['peso_kg_m']} |")
        return "\n".join(lines)

    elif tabla == 'nsr10_acero_sismico':
        lines = ["**Requisitos sísmicos acero:**\n"]
        for row in data:
            lines.append(f"- {row['sistema']} - {row['requisito']}:")
            lines.append(f"  - DMO: {row['dmo']}")
            lines.append(f"  - DES: {row['des']}")
        return "\n".join(lines)

    else:
        # Genérico
        lines = []
        for row in data[:3]:
            titulo = row.get('titulo') or row.get('nombre') or row.get('tipo', '')
            contenido = row.get('contenido', '')[:200]
            lines.append(f"**{titulo}**\n{contenido}\n")
        return "\n---\n".join(lines)

def query_nsr10(pregunta: str) -> tuple[str, dict]:
    """Pipeline completo: clasificar → ejecutar → formatear"""
    # 1. Clasificar con LLM
    clasificacion = classify_query(pregunta)
    
    # 2. Ejecutar SQL
    data = execute_query(clasificacion)
    
    # 3. Formatear respuesta
    respuesta = format_response(clasificacion['tabla'], data)
    
    return respuesta, clasificacion

# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python3 nsr10_api.py \"tu pregunta\"")
        sys.exit(1)
    
    pregunta = " ".join(sys.argv[1:])
    
    print(f"📌 Pregunta: {pregunta}\n")
    
    respuesta, clasificacion = query_nsr10(pregunta)
    
    print(f"🔍 Clasificación: {json.dumps(clasificacion, ensure_ascii=False)}\n")
    print(f"📋 Respuesta:\n{respuesta}")
