"""
NormativePackage — Interfaz abstracta para consultar normativas estructurales.

Cada código (NSR-10, ASCE 7, Eurocode 8) implementa esta interfaz.
El Knowledge Graph + embeddings permiten búsqueda semántica de requisitos.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
import os

from supabase import create_client, Client
import openai


class ComplianceStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    NOT_APPLICABLE = "n/a"
    MISSING_DATA = "missing"


@dataclass
class Requirement:
    """Un requisito normativo verificable."""
    id: str
    section: str
    title: str
    description: str
    check_type: str  # drift, period, seismic_coef, combination, etc.
    limit_value: Optional[float] = None
    limit_formula: Optional[str] = None
    unit: Optional[str] = None
    
    
@dataclass
class CheckResult:
    """Resultado de verificar un requisito."""
    requirement: Requirement
    status: ComplianceStatus
    calculated_value: Optional[float] = None
    limit_value: Optional[float] = None
    margin: Optional[float] = None  # (limit - calculated) / limit * 100
    message: str = ""
    evidence: Optional[str] = None  # Texto de la norma que respalda


class NormativePackage(ABC):
    """Interfaz abstracta para paquetes normativos."""
    
    @property
    @abstractmethod
    def code_name(self) -> str:
        """Nombre del código (NSR-10, ASCE 7-22, etc.)"""
        pass
    
    @property
    @abstractmethod
    def country(self) -> str:
        """País de origen."""
        pass
    
    @abstractmethod
    def get_seismic_zone(self, location: str) -> Dict[str, Any]:
        """Obtiene parámetros sísmicos para una ubicación."""
        pass
    
    @abstractmethod
    def get_drift_limit(self, structural_system: str) -> float:
        """Límite de deriva para un sistema estructural."""
        pass
    
    @abstractmethod
    def get_load_combinations(self, design_method: str = "LRFD") -> List[Dict]:
        """Combinaciones de carga."""
        pass
    
    @abstractmethod
    def check_drift(self, drift: float, structural_system: str, floor_height: float) -> CheckResult:
        """Verifica deriva contra límite normativo."""
        pass
    
    @abstractmethod
    def check_period(self, T_calculated: float, T_approx: float, Cu: float) -> CheckResult:
        """Verifica periodo calculado vs aproximado."""
        pass
    
    @abstractmethod
    def search_requirements(self, query: str, limit: int = 5) -> List[Dict]:
        """Búsqueda semántica de requisitos en el Knowledge Graph."""
        pass


class NSR10Package(NormativePackage):
    """
    Implementación de NormativePackage para NSR-10 Colombia.
    Conecta con el Knowledge Graph en Supabase.
    """
    
    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        self.supabase_url = supabase_url or os.environ.get("STRUOS_SUPABASE_URL", "https://vdakfewjadwaczulcmvj.supabase.co")
        self.supabase_key = supabase_key or os.environ.get("STRUOS_SUPABASE_KEY", os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))
        
        self.db: Client = create_client(self.supabase_url, self.supabase_key)
        
        # OpenAI para embeddings de queries
        openai.api_key = os.environ.get("OPENAI_API_KEY")
        
        # Cache de datos frecuentes
        self._drift_limits = {
            "concreto": 0.010,
            "metalica": 0.010,
            "madera": 0.010,
            "mamposteria_flexion": 0.010,
            "mamposteria_cortante": 0.005,
        }
        
        self._cu_values = {
            # Cu según tipo de suelo y zona
            "alta": 1.2,
            "intermedia": 1.3,
            "baja": 1.4,
        }
    
    @property
    def code_name(self) -> str:
        return "NSR-10"
    
    @property
    def country(self) -> str:
        return "Colombia"
    
    def get_seismic_zone(self, location: str) -> Dict[str, Any]:
        """
        Obtiene Aa, Av, Fa, Fv y zona sísmica para un municipio.
        """
        # Buscar en el KG
        result = self.db.table("kg_nodes").select("*").ilike(
            "content", f"%{location}%"
        ).eq("norm_code", "NSR-10").limit(5).execute()
        
        # Valores por defecto para Bogotá (zona intermedia)
        defaults = {
            "location": location,
            "Aa": 0.15,
            "Av": 0.20,
            "Fa": 1.20,
            "Fv": 1.65,
            "zona": "Intermedia",
            "source": "NSR-10 Apéndice A-4"
        }
        
        # TODO: Parsear resultado del KG
        return defaults
    
    def get_drift_limit(self, structural_system: str) -> float:
        """
        Límite de deriva según A.6.4.1 y Tabla A.6.4-1.
        
        Retorna el límite como fracción de hpi (ej: 0.010 = 1.0%)
        """
        system_lower = structural_system.lower()
        
        if "mamposteria" in system_lower:
            if "cortante" in system_lower or "poco esbelt" in system_lower:
                return 0.005  # A.6.4.1.4
            else:
                return 0.010  # A.6.4.1.3 (flexión)
        
        # Concreto, metálica, madera
        return 0.010  # Tabla A.6.4-1
    
    def get_load_combinations(self, design_method: str = "LRFD") -> List[Dict]:
        """
        Combinaciones de carga según B.2.4.2 (LRFD).
        """
        if design_method.upper() == "LRFD":
            return [
                {"id": "1", "formula": "1.4D", "case": "Solo carga muerta"},
                {"id": "2", "formula": "1.2D + 1.6L + 0.5(Lr o S o R)", "case": "Gravitacional"},
                {"id": "3", "formula": "1.2D + 1.6(Lr o S o R) + (L o 0.5W)", "case": "Cubierta"},
                {"id": "4", "formula": "1.2D + 1.0W + L + 0.5(Lr o S o R)", "case": "Viento"},
                {"id": "5", "formula": "1.2D + 1.0E + L + 0.2S", "case": "Sismo"},
                {"id": "6", "formula": "0.9D + 1.0W", "case": "Volcamiento viento"},
                {"id": "7", "formula": "0.9D + 1.0E", "case": "Volcamiento sismo"},
            ]
        else:
            # ASD
            return [
                {"id": "1", "formula": "D", "case": "Carga muerta"},
                {"id": "2", "formula": "D + L", "case": "Servicio"},
                {"id": "3", "formula": "D + 0.75L + 0.75(Lr o S o R)", "case": "Combinada"},
                {"id": "4", "formula": "D + 0.6W", "case": "Viento"},
                {"id": "5", "formula": "D + 0.7E", "case": "Sismo"},
            ]
    
    def get_spectral_parameters(self, Aa: float, Av: float, Fa: float, Fv: float, I: float = 1.0) -> Dict:
        """
        Calcula parámetros espectrales según A.2.6.
        
        Returns:
            T0, TC, TL, Sa(T0), Sa(TC)
        """
        # A.2.6.1
        T0 = 0.1 * (Av * Fv) / (Aa * Fa)
        TC = 0.48 * (Av * Fv) / (Aa * Fa)
        TL = 2.4 * Fv  # A.2.6.2
        
        # Aceleración espectral
        Sa_T0 = 2.5 * Aa * Fa * I
        Sa_TC = 2.5 * Aa * Fa * I
        
        return {
            "T0": round(T0, 3),
            "TC": round(TC, 3),
            "TL": round(TL, 3),
            "Sa_plateau": round(Sa_TC, 3),
            "Aa": Aa,
            "Av": Av,
            "Fa": Fa,
            "Fv": Fv,
            "I": I
        }
    
    def check_drift(self, drift: float, structural_system: str, floor_height: float) -> CheckResult:
        """
        Verifica deriva contra límite NSR-10.
        
        Args:
            drift: Deriva calculada (absoluta, en mismas unidades que floor_height)
            structural_system: Tipo de sistema estructural
            floor_height: Altura de entrepiso
        
        Returns:
            CheckResult con status PASS/FAIL
        """
        limit_ratio = self.get_drift_limit(structural_system)
        limit_absolute = limit_ratio * floor_height
        
        drift_ratio = drift / floor_height if floor_height > 0 else 0
        
        # Buscar evidencia en KG
        evidence = self._get_section_text("A.6.4.1")
        
        req = Requirement(
            id="NSR10-A.6.4.1",
            section="A.6.4.1",
            title="Límites de la deriva",
            description=f"La deriva máxima no puede exceder {limit_ratio*100:.1f}% de hpi",
            check_type="drift",
            limit_value=limit_ratio,
            unit="fracción de hpi"
        )
        
        if drift_ratio <= limit_ratio:
            margin = (limit_ratio - drift_ratio) / limit_ratio * 100
            return CheckResult(
                requirement=req,
                status=ComplianceStatus.PASS,
                calculated_value=drift_ratio,
                limit_value=limit_ratio,
                margin=margin,
                message=f"Deriva {drift_ratio*100:.2f}% ≤ {limit_ratio*100:.1f}% OK (margen {margin:.1f}%)",
                evidence=evidence
            )
        else:
            exceedance = (drift_ratio - limit_ratio) / limit_ratio * 100
            return CheckResult(
                requirement=req,
                status=ComplianceStatus.FAIL,
                calculated_value=drift_ratio,
                limit_value=limit_ratio,
                margin=-exceedance,
                message=f"❌ Deriva {drift_ratio*100:.2f}% > {limit_ratio*100:.1f}% (excede {exceedance:.1f}%)",
                evidence=evidence
            )
    
    def check_period(self, T_calculated: float, T_approx: float, Cu: float = 1.2) -> CheckResult:
        """
        Verifica periodo calculado vs límite Cu*Ta según A.4.2.1.
        
        Args:
            T_calculated: Periodo del análisis (s)
            T_approx: Periodo aproximado Ta (s)
            Cu: Coeficiente de límite superior (tabla A.4.2-1)
        """
        T_limit = Cu * T_approx
        
        req = Requirement(
            id="NSR10-A.4.2.1",
            section="A.4.2.1",
            title="Límite del periodo fundamental",
            description=f"T ≤ Cu × Ta = {Cu} × {T_approx:.3f} = {T_limit:.3f} s",
            check_type="period",
            limit_value=T_limit,
            unit="s"
        )
        
        evidence = self._get_section_text("A.4.2.1")
        
        if T_calculated <= T_limit:
            margin = (T_limit - T_calculated) / T_limit * 100
            return CheckResult(
                requirement=req,
                status=ComplianceStatus.PASS,
                calculated_value=T_calculated,
                limit_value=T_limit,
                margin=margin,
                message=f"T = {T_calculated:.3f}s ≤ Cu×Ta = {T_limit:.3f}s OK",
                evidence=evidence
            )
        else:
            return CheckResult(
                requirement=req,
                status=ComplianceStatus.WARNING,
                calculated_value=T_calculated,
                limit_value=T_limit,
                margin=0,
                message=f"T = {T_calculated:.3f}s > Cu×Ta = {T_limit:.3f}s — Usar Cu×Ta para cortante basal",
                evidence=evidence
            )
    
    def check_fa_fv(self, Aa: float, Av: float, soil_type: str, Fa_used: float, Fv_used: float) -> Tuple[CheckResult, CheckResult]:
        """
        Verifica que Fa y Fv usados coincidan con tablas A.2.4-3 y A.2.4-4.
        """
        # Tablas hardcoded (simplificado)
        fa_table = {
            ("A", 0.05): 0.8, ("A", 0.10): 0.8, ("A", 0.15): 0.8, ("A", 0.20): 0.8,
            ("B", 0.05): 1.0, ("B", 0.10): 1.0, ("B", 0.15): 1.0, ("B", 0.20): 1.0,
            ("C", 0.05): 1.2, ("C", 0.10): 1.2, ("C", 0.15): 1.1, ("C", 0.20): 1.0,
            ("D", 0.05): 1.6, ("D", 0.10): 1.4, ("D", 0.15): 1.2, ("D", 0.20): 1.1,
            ("E", 0.05): 2.5, ("E", 0.10): 1.7, ("E", 0.15): 1.2, ("E", 0.20): 0.9,
        }
        
        fv_table = {
            ("A", 0.05): 0.8, ("A", 0.10): 0.8, ("A", 0.15): 0.8, ("A", 0.20): 0.8,
            ("B", 0.05): 1.0, ("B", 0.10): 1.0, ("B", 0.15): 1.0, ("B", 0.20): 1.0,
            ("C", 0.05): 1.7, ("C", 0.10): 1.6, ("C", 0.15): 1.5, ("C", 0.20): 1.4,
            ("D", 0.05): 2.4, ("D", 0.10): 2.0, ("D", 0.15): 1.8, ("D", 0.20): 1.6,
            ("E", 0.05): 3.5, ("E", 0.10): 3.2, ("E", 0.15): 2.8, ("E", 0.20): 2.4,
        }
        
        # Buscar Fa correcto (interpolar si es necesario)
        soil = soil_type.upper()
        Fa_correct = fa_table.get((soil, Aa), None)
        Fv_correct = fv_table.get((soil, Av), None)
        
        results = []
        
        # Check Fa
        req_fa = Requirement(
            id="NSR10-A.2.4-3",
            section="Tabla A.2.4-3",
            title="Coeficiente Fa",
            description=f"Fa para suelo {soil} y Aa={Aa}",
            check_type="seismic_coef",
            limit_value=Fa_correct
        )
        
        if Fa_correct and abs(Fa_used - Fa_correct) < 0.05:
            results.append(CheckResult(
                requirement=req_fa,
                status=ComplianceStatus.PASS,
                calculated_value=Fa_used,
                limit_value=Fa_correct,
                message=f"Fa = {Fa_used} ≈ {Fa_correct} OK"
            ))
        elif Fa_correct:
            results.append(CheckResult(
                requirement=req_fa,
                status=ComplianceStatus.FAIL,
                calculated_value=Fa_used,
                limit_value=Fa_correct,
                message=f"❌ Fa usado = {Fa_used}, debería ser {Fa_correct}"
            ))
        else:
            results.append(CheckResult(
                requirement=req_fa,
                status=ComplianceStatus.MISSING_DATA,
                message=f"No se encontró Fa para suelo {soil}, Aa={Aa}"
            ))
        
        # Check Fv
        req_fv = Requirement(
            id="NSR10-A.2.4-4",
            section="Tabla A.2.4-4",
            title="Coeficiente Fv",
            description=f"Fv para suelo {soil} y Av={Av}",
            check_type="seismic_coef",
            limit_value=Fv_correct
        )
        
        if Fv_correct and abs(Fv_used - Fv_correct) < 0.05:
            results.append(CheckResult(
                requirement=req_fv,
                status=ComplianceStatus.PASS,
                calculated_value=Fv_used,
                limit_value=Fv_correct,
                message=f"Fv = {Fv_used} ≈ {Fv_correct} OK"
            ))
        elif Fv_correct:
            results.append(CheckResult(
                requirement=req_fv,
                status=ComplianceStatus.FAIL,
                calculated_value=Fv_used,
                limit_value=Fv_correct,
                message=f"❌ Fv usado = {Fv_used}, debería ser {Fv_correct}"
            ))
        else:
            results.append(CheckResult(
                requirement=req_fv,
                status=ComplianceStatus.MISSING_DATA,
                message=f"No se encontró Fv para suelo {soil}, Av={Av}"
            ))
        
        return tuple(results)
    
    def search_requirements(self, query: str, limit: int = 5, threshold: float = 0.3) -> List[Dict]:
        """
        Búsqueda semántica en el Knowledge Graph.
        
        Args:
            query: Texto de búsqueda
            limit: Máximo de resultados
            threshold: Umbral de similitud (0-1)
        
        Returns:
            Lista de secciones relevantes con similitud
        """
        # Generar embedding del query
        response = openai.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
        query_embedding = response.data[0].embedding
        
        # Buscar via RPC
        result = self.db.rpc("search_kg_semantic", {
            "query_embedding": query_embedding,
            "match_threshold": threshold,
            "match_count": limit,
            "filter_norm_code": "NSR-10"
        }).execute()
        
        return result.data
    
    def get_section(self, section_path: str) -> Optional[Dict]:
        """
        Obtiene una sección específica del KG.
        """
        result = self.db.table("kg_nodes").select("*").eq(
            "section_path", section_path
        ).eq("norm_code", "NSR-10").limit(1).execute()
        
        return result.data[0] if result.data else None
    
    def _get_section_text(self, section_path: str) -> str:
        """Helper para obtener texto de una sección."""
        section = self.get_section(section_path)
        if section and section.get("content"):
            return section.get("content", "")[:500]
        return f"Ver {section_path}"


# Función de conveniencia
def get_nsr10() -> NSR10Package:
    """Obtiene instancia de NSR10Package."""
    return NSR10Package()


if __name__ == "__main__":
    # Test básico
    nsr = get_nsr10()
    
    print(f"\n{'='*50}")
    print(f"NormativePackage: {nsr.code_name} ({nsr.country})")
    print(f"{'='*50}\n")
    
    # Test drift
    result = nsr.check_drift(drift=0.025, structural_system="concreto reforzado", floor_height=3.0)
    print(f"Deriva: {result.message}")
    print(f"  Status: {result.status.value}")
    
    # Test period
    result = nsr.check_period(T_calculated=0.8, T_approx=0.6, Cu=1.2)
    print(f"\nPeriodo: {result.message}")
    
    # Test búsqueda
    print("\n🔍 Búsqueda: 'combinaciones de carga'")
    results = nsr.search_requirements("combinaciones de carga", limit=3)
    for r in results:
        title = (r.get('title') or '')[:50]
        print(f"  - [{r['section_path']}] {title}")
