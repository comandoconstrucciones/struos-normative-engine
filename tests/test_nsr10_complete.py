"""
test_nsr10_complete.py — Suite completa de validación NSR-10

Ejecutar: python3 -m pytest test_nsr10_complete.py -v
"""

import os
import sys

import pytest

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from nsr10_formulas import (
    calc_delta_inelastic,
    calc_k,
    calc_R,
    calc_Sa,
    calc_T0,
    calc_T_limit,
    calc_Ta,
    calc_TC,
    calc_TL,
    calc_Vs,
    check_drift_limit,
    get_seismic_params_bogota,
    spectrum_nsr10,
)

# ============================================================
# TEST: Parámetros sísmicos básicos
# ============================================================

class TestSeismicParams:
    """Tests para parámetros sísmicos A.2"""

    def test_bogota_params(self):
        """Verifica parámetros de Bogotá (zona intermedia)."""
        params = get_seismic_params_bogota()
        assert params["Aa"] == 0.15
        assert params["Av"] == 0.20
        assert params["Fa"] == 1.20
        assert params["Fv"] == 1.65
        assert params["zona"] == "Intermedia"

    def test_T0_bogota(self):
        """T0 para Bogotá con suelo D."""
        T0 = calc_T0(Av=0.20, Fv=1.65, Aa=0.15, Fa=1.20)
        # T0 = 0.1 × (0.20×1.65)/(0.15×1.20) = 0.1 × 0.33/0.18 = 0.183s
        assert abs(T0 - 0.183) < 0.01

    def test_TC_bogota(self):
        """TC para Bogotá con suelo D."""
        TC = calc_TC(Av=0.20, Fv=1.65, Aa=0.15, Fa=1.20)
        # TC = 0.48 × (0.20×1.65)/(0.15×1.20) = 0.48 × 1.833 = 0.88s
        assert abs(TC - 0.88) < 0.01

    def test_TL_suelo_D(self):
        """TL para suelo tipo D."""
        TL = calc_TL(Fv=1.65)
        # TL = 2.4 × 1.65 = 3.96s
        assert abs(TL - 3.96) < 0.01


# ============================================================
# TEST: Espectro de diseño
# ============================================================

class TestSpectrum:
    """Tests para espectro de diseño A.2.6"""

    @pytest.fixture
    def bogota_params(self):
        return {"Aa": 0.15, "Fa": 1.20, "Av": 0.20, "Fv": 1.65, "I": 1.0}

    def test_Sa_T0_rampa(self, bogota_params):
        """Sa en T=0 debe ser 0.4 × Sa_max."""
        Sa = calc_Sa(T=0.0, **bogota_params)
        # Sa(0) = 2.5×0.15×1.2×1.0×0.4 = 0.18g
        assert abs(Sa - 0.18) < 0.02

    def test_Sa_meseta(self, bogota_params):
        """Sa en la meseta (T0 < T ≤ TC)."""
        Sa = calc_Sa(T=0.5, **bogota_params)
        # Sa_max = 2.5×0.15×1.2×1.0 = 0.45g
        assert abs(Sa - 0.45) < 0.02

    def test_Sa_descendente(self, bogota_params):
        """Sa en rama descendente (TC < T ≤ TL)."""
        Sa = calc_Sa(T=1.0, **bogota_params)
        # Sa = 1.2×0.20×1.65×1.0/1.0 = 0.396g
        assert abs(Sa - 0.396) < 0.02

    def test_Sa_descendente_2(self, bogota_params):
        """Sa más allá de T=2s."""
        Sa = calc_Sa(T=2.0, **bogota_params)
        # Sa = 1.2×0.20×1.65×1.0/2.0 = 0.198g
        assert abs(Sa - 0.198) < 0.02

    def test_spectrum_generation(self, bogota_params):
        """Genera espectro completo."""
        spectrum = spectrum_nsr10(**bogota_params, T_max=3.0, steps=31)
        assert len(spectrum) == 31
        assert spectrum[0]["T"] == 0.0
        assert spectrum[-1]["T"] == 3.0

        # Verificar que Sa decrece después de la meseta
        Sa_05 = next(s["Sa"] for s in spectrum if s["T"] == 0.5)
        Sa_20 = next(s["Sa"] for s in spectrum if abs(s["T"] - 2.0) < 0.1)
        assert Sa_05 > Sa_20


# ============================================================
# TEST: Periodo fundamental
# ============================================================

class TestPeriod:
    """Tests para periodo fundamental A.4"""

    def test_Ta_portico_concreto(self):
        """Ta para pórtico de concreto de 30m."""
        # Ct=0.047, α=0.90 para pórticos de concreto
        Ta = calc_Ta(Ct=0.047, h=30.0, alpha=0.90)
        assert abs(Ta - 1.00) < 0.05

    def test_Ta_portico_acero(self):
        """Ta para pórtico de acero de 20m."""
        # Ct=0.072, α=0.80 para pórticos de acero
        Ta = calc_Ta(Ct=0.072, h=20.0, alpha=0.80)
        assert abs(Ta - 0.79) < 0.05

    def test_T_limit(self):
        """Límite superior T ≤ Cu × Ta."""
        Ta = 0.8
        T_limit = calc_T_limit(Cu=1.2, Ta=Ta)
        assert T_limit == 0.96

    def test_T_limit_zona_baja(self):
        """Cu = 1.4 para zonas de amenaza baja."""
        Ta = 0.6
        T_limit = calc_T_limit(Cu=1.4, Ta=Ta)
        assert T_limit == 0.84


# ============================================================
# TEST: Cortante basal
# ============================================================

class TestBaseShear:
    """Tests para cortante basal A.4.3"""

    def test_Vs_basic(self):
        """Cortante basal básico."""
        Vs = calc_Vs(Sa=0.45, M=100000)  # 100 ton
        # Vs = 0.45 × 9.81 × 100000 / 1000 = 441.45 kN
        assert abs(Vs - 441.45) < 1.0

    def test_k_short_period(self):
        """k = 1.0 para T ≤ 0.5s."""
        assert calc_k(0.3) == 1.0
        assert calc_k(0.5) == 1.0

    def test_k_long_period(self):
        """k = 2.0 para T ≥ 2.5s."""
        assert calc_k(2.5) == 2.0
        assert calc_k(3.0) == 2.0

    def test_k_intermediate(self):
        """k interpolado para 0.5 < T < 2.5."""
        assert calc_k(1.0) == 1.25
        assert calc_k(2.0) == 1.75


# ============================================================
# TEST: Derivas
# ============================================================

class TestDrift:
    """Tests para límites de deriva A.6"""

    def test_delta_inelastic(self):
        """Deriva inelástica = Cd × elástica."""
        delta_i = calc_delta_inelastic(delta_elastic=0.005, Cd=4.0)
        assert delta_i == 0.020

    def test_drift_pass(self):
        """Deriva que cumple (0.833% < 1.0%)."""
        result = check_drift_limit(delta=0.025, hpi=3.0, limit_pct=1.0)
        assert result["passed"]
        assert result["status"] == "PASS"
        assert abs(result["drift_pct"] - 0.833) < 0.01

    def test_drift_fail(self):
        """Deriva que NO cumple (1.167% > 1.0%)."""
        result = check_drift_limit(delta=0.035, hpi=3.0, limit_pct=1.0)
        assert not result["passed"]
        assert result["status"] == "FAIL"
        assert abs(result["drift_pct"] - 1.167) < 0.01

    def test_drift_mamposteria(self):
        """Límite 0.5% para mampostería en cortante."""
        result = check_drift_limit(delta=0.012, hpi=3.0, limit_pct=0.5)
        # 0.012/3.0 = 0.4% < 0.5% OK
        assert result["passed"]

        result2 = check_drift_limit(delta=0.018, hpi=3.0, limit_pct=0.5)
        # 0.018/3.0 = 0.6% > 0.5% FAIL
        assert not result2["passed"]


# ============================================================
# TEST: Factor R
# ============================================================

class TestRFactor:
    """Tests para factor de disipación de energía A.3"""

    def test_R_sin_irregularidades(self):
        """R = R0 sin irregularidades."""
        R = calc_R(R0=7.0)
        assert R == 7.0

    def test_R_con_irregularidades(self):
        """R reducido por irregularidades."""
        R = calc_R(R0=7.0, phi_a=0.9, phi_p=0.9, phi_r=1.0)
        # R = 7.0 × 0.9 × 0.9 × 1.0 = 5.67
        assert abs(R - 5.67) < 0.1

    def test_R_sin_redundancia(self):
        """R reducido por falta de redundancia."""
        R = calc_R(R0=5.0, phi_r=0.75)
        # R = 5.0 × 1.0 × 1.0 × 0.75 = 3.75
        assert R == 3.75


# ============================================================
# TEST: Casos de diseño reales
# ============================================================

class TestRealCases:
    """Tests con casos reales de diseño en Colombia."""

    def test_edificio_10_pisos_bogota(self):
        """Edificio de 10 pisos en Bogotá."""
        # Datos
        h = 30.0  # m (10 pisos × 3m)
        M = 2000000  # kg (2000 ton)

        # Parámetros sísmicos Bogotá suelo D
        Aa, Av, Fa, Fv, I = 0.15, 0.20, 1.20, 1.65, 1.0

        # Periodo aproximado (pórtico de concreto)
        Ta = calc_Ta(Ct=0.047, h=h, alpha=0.90)
        calc_T_limit(Cu=1.2, Ta=Ta)

        # Aceleración espectral (usando Ta)
        Sa = calc_Sa(T=Ta, Aa=Aa, Fa=Fa, Av=Av, Fv=Fv, I=I)

        # Cortante basal
        Vs = calc_Vs(Sa=Sa, M=M)

        # Verificaciones
        assert 0.9 < Ta < 1.1, f"Ta fuera de rango: {Ta}"
        assert Sa > 0.30, f"Sa muy bajo: {Sa}"
        assert Vs > 500, f"Vs muy bajo: {Vs}"

    def test_cancha_padel_bogota(self):
        """Estructura ligera: cancha de pádel techada."""
        # Datos
        h = 10.0  # m altura cubierta
        M = 15000  # kg (15 ton)

        # Parámetros Bogotá suelo C
        Aa, Av, Fa, Fv, I = 0.15, 0.20, 1.10, 1.50, 1.0

        # Periodo (estructura metálica liviana)
        Ta = calc_Ta(Ct=0.072, h=h, alpha=0.80)

        # Sa
        Sa = calc_Sa(T=Ta, Aa=Aa, Fa=Fa, Av=Av, Fv=Fv, I=I)

        # Cortante
        calc_Vs(Sa=Sa, M=M)

        # Deriva típica
        delta = 0.025  # 25mm deriva de piso
        drift = check_drift_limit(delta=delta, hpi=3.0, limit_pct=1.0)

        # Verificaciones
        assert Ta < 0.5, f"Ta debería ser bajo: {Ta}"
        assert Sa >= 0.40, f"Sa debe estar en meseta: {Sa}"
        assert drift["passed"], f"Deriva no cumple: {drift['drift_pct']}%"


# ============================================================
# TEST: Validación cruzada con NSR-10
# ============================================================

class TestNSR10Compliance:
    """Validación de fórmulas contra valores publicados en NSR-10."""

    def test_tabla_A2_4_3_Fa(self):
        """Valores de Fa según Tabla A.2.4-3."""
        # Los Fa están implícitos en calc_Sa
        # Verificamos que los espectros sean consistentes

        # Suelo A (Fa bajo) vs Suelo E (Fa alto)
        Sa_A = calc_Sa(T=0.5, Aa=0.15, Fa=0.8, Av=0.20, Fv=0.8, I=1.0)
        Sa_E = calc_Sa(T=0.5, Aa=0.15, Fa=1.2, Av=0.20, Fv=2.4, I=1.0)

        # Suelo E debe tener mayor Sa en meseta
        assert Sa_E > Sa_A

    def test_tabla_A6_4_1_derivas(self):
        """Límites de deriva según Tabla A.6.4-1."""
        # Concreto/Acero/Madera: 1.0%
        result1 = check_drift_limit(delta=0.030, hpi=3.0, limit_pct=1.0)
        assert result1["passed"]

        # Mampostería en cortante: 0.5%
        result2 = check_drift_limit(delta=0.015, hpi=3.0, limit_pct=0.5)
        assert result2["passed"]


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    # Ejecutar con pytest
    pytest.main([__file__, "-v", "--tb=short"])
