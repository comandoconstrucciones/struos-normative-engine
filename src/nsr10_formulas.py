"""
nsr10_formulas.py — Fórmulas NSR-10 como funciones Python ejecutables.

Generado automáticamente por enrich_kg_v2.py
Struos.AI - Motor Normativo NSR-10
"""

from typing import Dict, List, Optional


# NSR10-A.2.6-1 (A.2.6.1)
def calc_T0(Av: float, Fv: float, Aa: float, Fa: float) -> float:
    """Calcula T0 según NSR-10 A.2.6: T0 = 0.1 × (Av×Fv)/(Aa×Fa)"""
    return 0.1 * (Av * Fv) / (Aa * Fa)

# NSR10-A.2.6-2 (A.2.6.1)
def calc_TC(Av: float, Fv: float, Aa: float, Fa: float) -> float:
    """Calcula TC según NSR-10 A.2.6: TC = 0.48 × (Av×Fv)/(Aa×Fa)"""
    return 0.48 * (Av * Fv) / (Aa * Fa)

# NSR10-A.2.6-3 (A.2.6.2)
def calc_TL(Fv: float) -> float:
    """Calcula TL según NSR-10 A.2.6: TL = 2.4 × Fv"""
    return 2.4 * Fv

# NSR10-A.2.6-4 (A.2.6.3)
def calc_Sa(T: float, Aa: float, Fa: float, Av: float, Fv: float, I: float = 1.0) -> float:
    """Calcula Sa(T) según NSR-10 A.2.6"""
    # Periodos característicos
    T0 = 0.1 * (Av * Fv) / (Aa * Fa)
    TC = 0.48 * (Av * Fv) / (Aa * Fa)
    TL = 2.4 * Fv
    
    # Aceleración meseta
    Sa0 = 2.5 * Aa * Fa * I
    
    if T < T0:
        # Rampa ascendente
        return 2.5 * Aa * Fa * I * (0.4 + 0.6 * T / T0)
    elif T <= TC:
        # Meseta
        return Sa0
    elif T <= TL:
        # Rama descendente velocidad constante
        return 1.2 * Av * Fv * I / T
    else:
        # Rama descendente desplazamiento constante
        return 1.2 * Av * Fv * TL * I / (T ** 2)

# NSR10-A.4.2-1 (A.4.2.1)
def calc_Ta(Ct: float, h: float, alpha: float) -> float:
    """Calcula Ta según NSR-10 A.4.2.1: Ta = Ct × h^α"""
    return Ct * (h ** alpha)

# NSR10-A.4.2-2 (A.4.2.1)
def calc_T_limit(Cu: float, Ta: float) -> float:
    """Calcula T máximo según NSR-10 A.4.2.1: T_limit = Cu × Ta"""
    return Cu * Ta

# NSR10-A.4.3-1 (A.4.3)
def calc_Vs(Sa: float, M: float, g: float = 9.81) -> float:
    """Calcula Vs según NSR-10 A.4.3: Vs = Sa × g × M / 1000 (en kN)"""
    return Sa * g * M / 1000

# NSR10-A.4.3-2 (A.4.3.2)
def calc_k(T: float) -> float:
    """Calcula k según NSR-10 A.4.3.2"""
    if T <= 0.5:
        return 1.0
    elif T >= 2.5:
        return 2.0
    else:
        return 0.75 + 0.5 * T

# NSR10-A.6.3-1 (A.6.3.1)
def calc_delta_inelastic(delta_elastic: float, Cd: float) -> float:
    """Calcula deriva inelástica según NSR-10 A.6.3: Δinelástica = Cd × Δelástica"""
    return Cd * delta_elastic

# NSR10-A.6.4-1 (A.6.4.1)
def check_drift_limit(delta: float, hpi: float, limit_pct: float = 1.0) -> dict:
    """Verifica deriva según NSR-10 A.6.4.1"""
    drift_ratio = delta / hpi
    limit = limit_pct / 100
    passed = drift_ratio <= limit
    margin = (limit - drift_ratio) / limit * 100 if passed else (drift_ratio - limit) / limit * 100
    
    return {
        "passed": passed,
        "drift_pct": round(drift_ratio * 100, 3),
        "limit_pct": limit_pct,
        "margin_pct": round(margin, 1),
        "status": "PASS" if passed else "FAIL"
    }

# NSR10-A.3.3-1 (A.3.3.4)
def calc_R(R0: float, phi_a: float = 1.0, phi_p: float = 1.0, phi_r: float = 1.0) -> float:
    """Calcula R según NSR-10 A.3.3.4: R = R0 × φa × φp × φr"""
    return R0 * phi_a * phi_p * phi_r


# === Funciones de conveniencia ===

def spectrum_nsr10(Aa: float, Av: float, Fa: float, Fv: float, I: float = 1.0, T_max: float = 4.0, steps: int = 100) -> List[Dict]:
    """Genera el espectro de diseño NSR-10 completo."""
    import numpy as np
    
    T_values = np.linspace(0, T_max, steps)
    spectrum = []
    
    for T in T_values:
        Sa = calc_Sa(T, Aa, Fa, Av, Fv, I)
        spectrum.append({"T": round(T, 3), "Sa": round(Sa, 4)})
    
    return spectrum


def get_seismic_params_bogota() -> Dict:
    """Parámetros sísmicos para Bogotá (zona intermedia)."""
    return {
        "Aa": 0.15,
        "Av": 0.20,
        "Fa": 1.20,  # Suelo tipo D
        "Fv": 1.65,  # Suelo tipo D
        "I": 1.0,
        "zona": "Intermedia"
    }
