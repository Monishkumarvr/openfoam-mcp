"""Gating system recommendations for casting simulations.

Combines the casting's own geometry (via the STL already used for
meshing) with material properties from materials.database and, when
available, the hotspot/shrinkage results from RealResultAnalyzer to
recommend a gating and risering scheme. This is deliberately NOT a
replacement for a foundry engineer: it applies well-established rules of
thumb (Chvorinov's rule, Campbell's critical ingate velocity, standard
gating ratios) to numbers computed from the actual part, and reports
which parts of the recommendation are geometry-exact vs. rule-of-thumb.

References used directly:
  - Campbell, J. -- critical ingate velocity <= 0.5 m/s for steel/
    superalloys (surface turbulence / bifilm entrainment threshold).
  - Chvorinov's rule: t_solidification = C * M^2, M = V/A (modulus).
  - Riser sizing: M_riser >= 1.2-1.5 x M_section being fed (standard
    foundry design margin so the riser freezes last).
  - Unpressurised gating system area ratios, sprue:runner:ingate,
    commonly 1:2:2 or 1:3:3 (keeps the ingate as the flow-controlling
    choke, avoiding a pressurised, more turbulent system).
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from loguru import logger

from .case_manager import CaseManager
from .result_analyzer_real import RealResultAnalyzer
from ..materials.database import get_material

# Campbell's critical ingate velocity for steel/superalloys. Aluminum and
# other alloys less prone to oxide-film entrainment tolerate somewhat
# higher velocities in practice, but 0.5 m/s is the conservative, widely
# -cited figure and what this tool already defaults gate velocities to.
CRITICAL_INGATE_VELOCITY_MS = 0.5

# Standard unpressurised gating area ratios (sprue : runner : ingate).
GATING_RATIOS = {
    "1:2:2": (1, 2, 2),
    "1:3:3": (1, 3, 3),
    "1:1:3": (1, 1, 3),
}


class GatingRecommender:
    """Recommends gating/risering parameters from a case's real geometry."""

    def __init__(self, run_dir: Optional[str] = None, case_manager: Optional[CaseManager] = None,
                 analyzer: Optional[RealResultAnalyzer] = None):
        self.run_dir = Path(run_dir) if run_dir else Path.home() / "foam" / "run"
        # CaseManager already has well-tested STL parsing (ASCII/binary,
        # unit-scale detection is in setup_geometry) -- reusing its private
        # helpers here rather than duplicating STL math in a second module.
        self.case_manager = case_manager or CaseManager(run_dir=str(self.run_dir))
        self.analyzer = analyzer or RealResultAnalyzer(run_dir=str(self.run_dir))

    def _find_case_stl(self, case_name: str) -> Path:
        tri_surface = self.run_dir / case_name / "constant" / "triSurface"
        stl_files = sorted(tri_surface.glob("*.stl")) if tri_surface.exists() else []
        if not stl_files:
            raise ValueError(
                f"No STL found in {tri_surface}. recommend_gating needs an "
                f"STL-based case (run setup_geometry with geometry_type='stl_file' first)."
            )
        return stl_files[0]

    def _load_material(self, case_name: str) -> Dict[str, Any]:
        metadata = self.case_manager.metadata.get(case_name, {})
        grade = metadata.get("metal_grade")
        metal_type = metadata.get("metal_type", "steel")
        if grade:
            try:
                return get_material(grade)
            except KeyError:
                logger.warning(f"metal_grade '{grade}' not found in database, falling back to metal_type")
        # No grade recorded (or it didn't resolve) -- approximate from
        # metal_type using the closest database entry, clearly flagged.
        fallback_grade = {
            "steel": "WCB",
            "iron": "gray_iron_class30",
        }.get(metal_type)
        if fallback_grade:
            props = dict(get_material(fallback_grade))
            props["_approximated_from_metal_type"] = metal_type
            return props
        raise ValueError(
            f"No metal_grade recorded for '{case_name}' and metal_type "
            f"'{metal_type}' has no materials-database fallback (aluminum/"
            f"copper/bronze aren't in the steel/cast-iron database this "
            f"recommender uses). Pass metal_grade when creating the case."
        )

    async def recommend(
        self,
        case_name: str,
        mold_material: Optional[str] = None,
        gating_ratio: str = "1:2:2",
        riser_safety_factor: float = 1.3,
    ) -> Dict[str, Any]:
        """Build a gating/risering recommendation for `case_name`.

        Args:
            case_name: Case with STL geometry already set up.
            mold_material: Overrides the mold material recorded at case
                creation, if given.
            gating_ratio: One of GATING_RATIOS' keys.
            riser_safety_factor: M_riser = this x M_fed_section (1.2-1.5
                is the standard range; defaults to the middle of it).
        """
        if gating_ratio not in GATING_RATIOS:
            raise ValueError(f"gating_ratio must be one of {list(GATING_RATIOS)}")

        stl_path = self._find_case_stl(case_name)
        metadata = self.case_manager.metadata.get(case_name, {})
        mold_material = mold_material or metadata.get("mold_material", "sand")
        pouring_temp_c = metadata.get("pouring_temperature")

        material = self._load_material(case_name)

        # Re-derive the same unit scale setup_geometry used (mm heuristic),
        # since gating math needs real meters, not raw file units.
        tris_raw = self.case_manager._read_stl_triangles(stl_path, scale=1.0)
        pts_raw = tris_raw.reshape(-1, 3)
        extent_raw = pts_raw.max(axis=0) - pts_raw.min(axis=0)
        scale = 0.001 if float(np.max(extent_raw)) > 5 else 1.0
        tris = tris_raw * scale if scale != 1.0 else tris_raw

        volume = self._enclosed_volume(tris)
        area = self._surface_area(tris)
        modulus = volume / area  # Chvorinov modulus M = V/A

        # Casting-wide (bulk) risering estimate from the whole part's modulus.
        riser_modulus_bulk = modulus * riser_safety_factor

        # Refine with real hotspot data if the case has already been run --
        # the last-to-freeze regions found by defect analysis are exactly
        # where a riser is actually needed, and are usually much smaller
        # (and give a much smaller, more realistic riser) than the whole
        # -casting bulk modulus above.
        hotspot_risers = await self._risers_from_hotspots(case_name, riser_safety_factor)

        recommendation: Dict[str, Any] = {
            "case_name": case_name,
            "material": {
                "grade": material.get("display_name", "unknown"),
                "density_kg_m3": material.get("density"),
                "liquidus_K": material.get("liquidus_temp"),
                "solidus_K": material.get("solidus_temp"),
                "approximated_from_metal_type": material.get("_approximated_from_metal_type"),
            },
            "geometry": {
                "casting_volume_m3": round(volume, 8),
                "casting_surface_area_m2": round(area, 6),
                "casting_modulus_m": round(modulus, 6),
                "unit_scale_applied": "assumed mm -> m (1/1000)" if scale != 1.0 else "assumed already meters",
            },
            "ingate": self._ingate_recommendation(volume),
            "gating_system": self._gating_system(gating_ratio),
            "riser_bulk_estimate": {
                "modulus_m": round(riser_modulus_bulk, 6),
                "note": (
                    f"{riser_safety_factor}x the WHOLE casting's modulus -- a "
                    f"conservative upper bound. If the case has been meshed and "
                    f"run, see 'riser_from_hotspots' below for a much more "
                    f"targeted (and usually smaller) recommendation based on "
                    f"where the casting actually freezes last."
                ),
            },
            "risers_from_hotspots": hotspot_risers,
            "assumptions": [
                "Campbell critical ingate velocity <= 0.5 m/s (steel/superalloy "
                "threshold; less conservative for some non-ferrous alloys).",
                f"Riser modulus sized at {riser_safety_factor}x the fed section's "
                f"modulus (standard 1.2-1.5x range).",
                f"Gating ratio sprue:runner:ingate = {gating_ratio} (unpressurised system).",
                "Does not model an actual meshed sprue/runner/riser -- these are "
                "sizing recommendations for you to add to the geometry, not "
                "simulated.",
            ],
        }
        return recommendation

    # ------------------------------------------------------------------

    def _enclosed_volume(self, tris: np.ndarray) -> float:
        a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
        return float(abs(np.einsum('ij,ij->i', a, np.cross(b, c)).sum() / 6.0))

    def _surface_area(self, tris: np.ndarray) -> float:
        a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
        return float(0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1).sum())

    def _ingate_recommendation(self, volume: float,
                                target_fill_time_s: Optional[float] = None) -> Dict[str, Any]:
        """Ingate area from the critical velocity and a target fill time.

        Without a specified fill time, uses a common foundry rule of thumb
        of ~3-10s for small/medium castings; this is far less certain than
        the geometry-derived numbers above and should be adjusted for the
        actual part size and running system design.
        """
        if target_fill_time_s is None:
            # Heuristic: scale with casting volume, bounded to a sane range.
            target_fill_time_s = float(np.clip(volume * 5000, 3.0, 30.0))

        required_flow_rate = volume / target_fill_time_s  # m^3/s
        ingate_area = required_flow_rate / CRITICAL_INGATE_VELOCITY_MS  # m^2

        return {
            "target_fill_time_s": round(target_fill_time_s, 2),
            "required_flow_rate_m3_s": round(required_flow_rate, 8),
            "min_ingate_area_m2": round(ingate_area, 8),
            "min_ingate_area_mm2": round(ingate_area * 1e6, 2),
            "basis": (
                f"area = (casting_volume / target_fill_time) / "
                f"{CRITICAL_INGATE_VELOCITY_MS} m/s. target_fill_time is a "
                f"rule-of-thumb scaled to casting volume (3-30s range) unless "
                f"you have a specific pour-time requirement -- this is the "
                f"least certain number in this report."
            ),
        }

    def _gating_system(self, gating_ratio: str) -> Dict[str, Any]:
        sprue_r, runner_r, ingate_r = GATING_RATIOS[gating_ratio]
        return {
            "ratio": gating_ratio,
            "note": (
                f"Given an ingate area A_gate, size sprue exit area = "
                f"A_gate x {sprue_r}/{ingate_r}, runner area = A_gate x "
                f"{runner_r}/{ingate_r}. Keeping the ingate as the smallest "
                f"(choking) cross-section keeps the system unpressurised, "
                f"reducing turbulence and air entrainment through the runner."
            ),
        }

    async def _risers_from_hotspots(self, case_name: str, riser_safety_factor: float) -> Any:
        """Pull the last-to-freeze regions from defect analysis, if the
        case has been run, and turn each into a riser-sizing recommendation.
        """
        case_dir = self.run_dir / case_name
        from ..utils.field_parser import OpenFOAMFieldParser
        parser = OpenFOAMFieldParser(case_dir)
        if not parser.get_time_directories():
            return "Case hasn't been run yet -- run_simulation, then re-call recommend_gating for targeted riser placement."

        try:
            hotspots = await self.analyzer._predict_hot_spots_real(case_name, parser)
        except Exception as e:
            return f"Could not compute hotspots: {e}"

        if "error" in hotspots:
            return hotspots

        risers = []
        for h in hotspots.get("hotspots", []):
            v = h["volume_m3"]
            r = (3 * v / (4 * np.pi)) ** (1 / 3)
            section_modulus = r / 3.0
            risers.append({
                "feeds_location_m": h["location_m"],
                "fed_section_volume_m3": v,
                "fed_section_modulus_m": round(section_modulus, 6),
                "required_riser_modulus_m": round(section_modulus * riser_safety_factor, 6),
                "required_riser_modulus_mm": round(section_modulus * riser_safety_factor * 1000, 3),
            })
        return risers if risers else "No last-to-freeze hotspots detected -- casting solidifies uniformly, may not need a riser."
