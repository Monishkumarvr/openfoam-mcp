"""REAL result analyzer for OpenFOAM casting simulations.

This module provides actual analysis of OpenFOAM simulation results,
including defect prediction based on real calculations.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
import numpy as np
from loguru import logger

from ..utils.field_parser import OpenFOAMFieldParser
from .openfoam_client import OpenFOAMClient


class RealResultAnalyzer:
    """Real analyzer that actually parses OpenFOAM results."""

    # Interim literature defaults for the Niyama threshold, in the
    # (K*s)^0.5/mm units the casting literature reports (Carlson &
    # Beckermann and others). Steel ~2.0 for micro-shrinkage onset. These
    # are family-level approximations, not grade-specific -- superseded by
    # the materials database's per-grade thresholds once that lands.
    _NIYAMA_THRESHOLD_MM = {
        "steel": 2.0,
        "iron": 1.0,       # cast iron: graphite expansion partially self-feeds
        "aluminum": 0.5,
        "copper": 1.0,
        "bronze": 1.0,
    }

    def __init__(self, run_dir: Optional[str] = None, client: Optional[OpenFOAMClient] = None):
        """Initialize analyzer.

        Args:
            run_dir: Directory containing simulation cases
            client: OpenFOAMClient used to run postProcess function objects
                (grad, writeCellCentres, writeCellVolumes) needed for real,
                mesh-based defect analysis. Defaults to a new client pointed
                at the same ~/foam/run directory.
        """
        self.run_dir = Path(run_dir) if run_dir else Path.home() / "foam" / "run"
        self.client = client or OpenFOAMClient()

    async def analyze(
        self,
        case_name: str,
        analysis_type: str = "all",
        time_step: Optional[float] = None
    ) -> Dict[str, Any]:
        """Analyze simulation results.

        Args:
            case_name: Name of the case
            analysis_type: Type of analysis
            time_step: Specific time step to analyze

        Returns:
            Dictionary with actual analysis results
        """
        case_dir = self.run_dir / case_name

        if not case_dir.exists():
            raise ValueError(f"Case {case_name} not found at {case_dir}")

        parser = OpenFOAMFieldParser(case_dir)

        # Check if simulation has run
        times = parser.get_time_directories()
        if not times:
            return {
                "error": "No time directories found - simulation may not have run",
                "case_dir": str(case_dir)
            }

        results = {
            "case_name": case_name,
            "time_directories": times,
            "latest_time": times[-1] if times else None
        }

        try:
            if analysis_type in ["filling_pattern", "all"]:
                results["filling_pattern"] = await self._analyze_filling_pattern(parser, time_step)

            if analysis_type in ["temperature_distribution", "all"]:
                results["temperature_distribution"] = await self._analyze_temperature(case_name, parser, time_step)

            if analysis_type in ["solidification_time", "all"]:
                results["solidification"] = await self._analyze_solidification(parser)

            if analysis_type in ["defect_prediction", "all"]:
                results["defects"] = await self.predict_defects(
                    case_name,
                    ["porosity", "shrinkage", "hot_spots"]
                )

        except Exception as e:
            logger.error(f"Error analyzing case {case_name}: {e}")
            results["error"] = str(e)

        return results

    async def _analyze_filling_pattern(
        self,
        parser: OpenFOAMFieldParser,
        time_step: Optional[float]
    ) -> Dict[str, Any]:
        """Analyze mold filling pattern from alpha.metal field.

        Args:
            parser: Field parser
            time_step: Time to analyze

        Returns:
            Analysis of filling pattern
        """
        try:
            # Read alpha.metal (volume fraction of metal)
            alpha_data = parser.read_scalar_field('alpha.metal', time_step)
            alpha_values = alpha_data['internal_field']

            if len(alpha_values) == 0:
                return {"error": "No data in alpha.metal field"}

            # Calculate fill statistics
            stats = parser.calculate_field_statistics(alpha_values)

            # Estimate filling percentage
            filled_cells = np.sum(alpha_values > 0.5)
            total_cells = len(alpha_values)
            fill_percentage = (filled_cells / total_cells * 100) if total_cells > 0 else 0

            # Check for air entrapment (cells with 0 < alpha < 1)
            partially_filled = np.sum((alpha_values > 0.01) & (alpha_values < 0.99))
            entrapment_risk = (partially_filled / total_cells * 100) if total_cells > 0 else 0

            return {
                "fill_percentage": float(fill_percentage),
                "filled_cells": int(filled_cells),
                "total_cells": int(total_cells),
                "air_entrapment_risk": float(entrapment_risk),
                "alpha_stats": stats,
                "time": alpha_data['time'],
                "analysis": self._interpret_filling(fill_percentage, entrapment_risk)
            }

        except FileNotFoundError:
            return {"error": "alpha.metal field not found - may need to run simulation"}
        except Exception as e:
            return {"error": f"Error analyzing filling: {str(e)}"}

    async def _analyze_temperature(
        self,
        case_name: str,
        parser: OpenFOAMFieldParser,
        time_step: Optional[float]
    ) -> Dict[str, Any]:
        """Analyze temperature distribution.

        Args:
            case_name: Name of the case (needed to run postProcess grad(T))
            parser: Field parser
            time_step: Time to analyze

        Returns:
            Temperature analysis
        """
        try:
            # Read temperature field
            T_data = parser.read_scalar_field('T', time_step)
            T_values = T_data['internal_field']

            if len(T_values) == 0:
                return {"error": "No data in T field"}

            # Calculate statistics
            stats = parser.calculate_field_statistics(T_values)

            # Real, mesh-based spatial gradient via OpenFOAM's own grad
            # function object -- NOT a finite difference over cell-storage
            # order, which has no relationship to physical space.
            try:
                await self._ensure_derived_fields(case_name, parser)
                grad_vec = parser.read_vector_field('grad(T)', T_data['time'])['internal_field']
                grad_T = np.linalg.norm(grad_vec, axis=1) if grad_vec.ndim == 2 else np.array([])
                grad_stats = parser.calculate_field_statistics(grad_T)
            except Exception as e:
                logger.warning(f"Could not compute real temperature gradient: {e}")
                grad_stats = {"min": 0.0, "max": 0.0, "mean": 0.0, "std": 0.0, "count": 0}

            return {
                "temperature_stats": stats,
                "gradient_stats": grad_stats,
                "time": T_data['time'],
                "analysis": self._interpret_temperature(stats, grad_stats),
                "note": "For hotspot/porosity/shrinkage detection use analysis_type='defect_prediction' -- "
                        "those evaluate at the solidification front over time, not a single-snapshot percentile."
            }

        except FileNotFoundError:
            return {"error": "T field not found - solidification simulation may not have run"}
        except Exception as e:
            return {"error": f"Error analyzing temperature: {str(e)}"}

    async def _analyze_solidification(self, parser: OpenFOAMFieldParser) -> Dict[str, Any]:
        """Analyze solidification process.

        Args:
            parser: Field parser

        Returns:
            Solidification analysis
        """
        try:
            times = parser.get_time_directories()

            if len(times) < 2:
                return {"error": "Need at least 2 time steps for solidification analysis"}

            # Read temperature at different times
            T_initial = parser.read_scalar_field('T', times[0])
            T_final = parser.read_scalar_field('T', times[-1])

            T_init_values = T_initial['internal_field']
            T_final_values = T_final['internal_field']

            # Calculate cooling rate
            dt = times[-1] - times[0]
            if dt > 0 and len(T_init_values) == len(T_final_values):
                cooling_rate = (T_init_values - T_final_values) / dt
                cooling_stats = parser.calculate_field_statistics(np.abs(cooling_rate))
            else:
                cooling_stats = {"mean": 0, "max": 0}

            return {
                "initial_time": times[0],
                "final_time": times[-1],
                "time_span": dt,
                "cooling_rate_stats": cooling_stats,
                "initial_temp_stats": parser.calculate_field_statistics(T_init_values),
                "final_temp_stats": parser.calculate_field_statistics(T_final_values),
                "analysis": f"Average cooling rate: {cooling_stats['mean']:.2f} K/s"
            }

        except Exception as e:
            return {"error": f"Error analyzing solidification: {str(e)}"}

    async def predict_defects(
        self,
        case_name: str,
        defect_types: List[str]
    ) -> Dict[str, Any]:
        """Predict casting defects based on REAL simulation data.

        Args:
            case_name: Name of the case
            defect_types: Types of defects to predict

        Returns:
            Dictionary mapping defect type to actual prediction
        """
        parser = OpenFOAMFieldParser(self.run_dir / case_name)

        predictions = {}

        for defect_type in defect_types:
            if defect_type == "porosity":
                predictions["porosity"] = await self._predict_porosity_real(case_name, parser)
            elif defect_type == "shrinkage":
                predictions["shrinkage"] = await self._predict_shrinkage_real(case_name, parser)
            elif defect_type == "hot_spots":
                predictions["hot_spots"] = await self._predict_hot_spots_real(case_name, parser)

        return predictions

    # ------------------------------------------------------------------
    # Shared machinery: a per-cell solidification profile built once from
    # the full time history, used by all three defect predictors below.
    # ------------------------------------------------------------------

    def _read_case_metadata(self, case_name: str) -> Dict[str, Any]:
        """Read the case metadata CaseManager wrote at creation time."""
        meta_file = self.run_dir / ".cases_metadata.json"
        if not meta_file.exists():
            return {}
        try:
            with open(meta_file, 'r') as f:
                return json.load(f).get(case_name, {})
        except Exception:
            return {}

    def _read_phase_change_temps(self, case_dir: Path) -> tuple:
        """Read the solidus/liquidus temperatures this case's solver was
        actually configured with.

        These are baked as literal constants into the generated coded
        fvOptions (see builders/templates.py) at case-creation time, so
        reading them back from the case is the only way to know what the
        solver used, rather than re-deriving them from the metal type and
        risking disagreement with the running simulation.
        """
        fv_options = case_dir / "system" / "fvOptions"
        if not fv_options.exists():
            raise ValueError(
                f"No system/fvOptions in {case_dir.name}: solidification "
                f"defect analysis requires a case_type='solidification' case "
                f"with the phase-change fvOptions configured."
            )
        content = fv_options.read_text()
        solidus_m = re.search(r'Tsolidus\s*=\s*([\d.eE+-]+)', content)
        liquidus_m = re.search(r'Tliquidus\s*=\s*([\d.eE+-]+)', content)
        if not solidus_m or not liquidus_m:
            raise ValueError(f"Could not find Tsolidus/Tliquidus in {fv_options}")
        return float(solidus_m.group(1)), float(liquidus_m.group(1))

    def _niyama_threshold_mm(self, metal_type: str) -> float:
        return self._NIYAMA_THRESHOLD_MM.get(metal_type, 2.0)

    async def _ensure_derived_fields(self, case_name: str, parser: OpenFOAMFieldParser):
        """Make sure grad(T), cell centers (C) and cell volumes (Vc) exist.

        Idempotent: each postProcess call is skipped if its output is
        already on disk, so repeated defect-analysis calls don't re-run
        these on every invocation.
        """
        times = parser.get_time_directories()
        if not times:
            raise ValueError(f"No written time steps in {case_name} -- run the simulation first")

        try:
            parser.read_vector_field('grad(T)', times[-1])
        except FileNotFoundError:
            result = await self.client.compute_gradient(case_name, 'T')
            if result.get("returncode", 1) != 0:
                raise RuntimeError(f"postProcess grad(T) failed: {result.get('stderr')}")

        try:
            parser.read_vector_field('C', 0.0)
        except FileNotFoundError:
            result = await self.client.compute_cell_centers(case_name)
            if result.get("returncode", 1) != 0:
                raise RuntimeError(f"postProcess writeCellCentres failed: {result.get('stderr')}")

        try:
            parser.read_scalar_field('Vc', 0.0)
        except FileNotFoundError:
            result = await self.client.compute_cell_volumes(case_name)
            if result.get("returncode", 1) != 0:
                raise RuntimeError(f"postProcess writeCellVolumes failed: {result.get('stderr')}")

    async def _build_solidification_profile(
        self, case_name: str, parser: OpenFOAMFieldParser
    ) -> Dict[str, Any]:
        """Walk every written time step once, recording per cell: the
        (interpolated) time it crosses the alloy solidus, the cooling rate
        and the real spatial |grad T| at that crossing.

        This is the shared basis for porosity (Niyama), hotspot and
        feeding/shrinkage analysis -- previously each recomputed its own
        (broken) approximation independently, using a whole-field snapshot
        at an arbitrary time instead of conditions at the freezing front.
        """
        case_dir = self.run_dir / case_name
        await self._ensure_derived_fields(case_name, parser)

        times = parser.get_time_directories()
        if len(times) < 2:
            raise ValueError("Need at least 2 written time steps to detect a solidification front")

        solidus_temp, liquidus_temp = self._read_phase_change_temps(case_dir)

        alpha_final = parser.read_scalar_field('alpha.metal', times[-1])['internal_field']
        n = len(alpha_final)
        is_metal = alpha_final > 0.5

        cell_centers = parser.get_cell_centers(0.0)
        cell_volumes = parser.read_scalar_field('Vc', 0.0)['internal_field']
        if len(cell_volumes) != n or len(cell_centers) != n:
            raise ValueError(
                f"Mesh size mismatch: alpha.metal has {n} cells, Vc has "
                f"{len(cell_volumes)}, C has {len(cell_centers)}. The mesh "
                f"may have been regenerated after this run."
            )

        def expand(arr: np.ndarray) -> np.ndarray:
            """A field that hasn't been solved yet (typically only t=0,
            straight from the case template) is written 'uniform' and comes
            back from the parser as a single value rather than one per cell
            -- broadcast it so every snapshot has the same per-cell shape.
            Advanced indexing (T_prev[idx]) doesn't broadcast like
            elementwise comparison does, so without this a uniform t=0
            reliably crashed as soon as the first crossing was found.
            """
            if arr.size == n:
                return arr
            if arr.size == 1:
                return np.full(n, arr.item())
            return arr

        def grad_mag(t: float) -> np.ndarray:
            vec = parser.read_vector_field('grad(T)', t)['internal_field']
            if vec.ndim != 2 or vec.shape[0] != n:
                return np.zeros(n)
            return np.linalg.norm(vec, axis=1)

        t_solidus = np.full(n, np.nan)
        cooling_rate = np.zeros(n)
        grad_at_front = np.zeros(n)

        T_prev = expand(parser.read_scalar_field('T', times[0])['internal_field'])
        g_prev = grad_mag(times[0])
        t_prev = times[0]

        # Cells already below solidus at the very first write solidified
        # faster than the write interval could resolve. Flag them at
        # times[0] instead of losing them as "never solidified"; their
        # cooling rate is genuinely unknown (frozen before the first
        # sample), so they're excluded from Niyama via solidified_mask
        # below rather than assigned a fabricated rate.
        presolidified = is_metal & (T_prev < solidus_temp) & np.isnan(t_solidus)
        t_solidus[presolidified] = t_prev
        grad_at_front[presolidified] = g_prev[presolidified]

        for t in times[1:]:
            T_curr = expand(parser.read_scalar_field('T', t)['internal_field'])
            if len(T_curr) != n:
                T_prev, t_prev = T_curr, t
                continue
            g_curr = grad_mag(t)

            crossing = np.isnan(t_solidus) & is_metal & (T_prev >= solidus_temp) & (T_curr < solidus_temp)
            idx = np.where(crossing)[0]
            if idx.size:
                denom = np.maximum(T_prev[idx] - T_curr[idx], 1e-9)
                frac = np.clip((T_prev[idx] - solidus_temp) / denom, 0.0, 1.0)
                dt = max(t - t_prev, 1e-12)
                t_solidus[idx] = t_prev + frac * dt
                cooling_rate[idx] = np.abs(T_prev[idx] - T_curr[idx]) / dt
                use_curr = frac > 0.5
                grad_at_front[idx] = np.where(use_curr, g_curr[idx], g_prev[idx])

            T_prev, g_prev, t_prev = T_curr, g_curr, t

        solidified_mask = ~np.isnan(t_solidus) & is_metal & (cooling_rate > 0)
        still_liquid_mask = is_metal & np.isnan(t_solidus)
        metal_volume = float(cell_volumes[is_metal].sum()) if is_metal.any() else 0.0

        return {
            "n_cells": n,
            "is_metal": is_metal,
            "solidus_temp": solidus_temp,
            "liquidus_temp": liquidus_temp,
            "t_solidus": t_solidus,
            "cooling_rate": cooling_rate,
            "grad_at_front": grad_at_front,
            "cell_centers": cell_centers,
            "cell_volumes": cell_volumes,
            "solidified_mask": solidified_mask,
            "still_liquid_mask": still_liquid_mask,
            "presolidified_mask": presolidified,
            "metal_volume_m3": metal_volume,
            "still_liquid_volume_fraction_pct": (
                float(cell_volumes[still_liquid_mask].sum() / metal_volume * 100)
                if metal_volume > 0 else 0.0
            ),
            "final_time": times[-1],
        }

    def _cluster_cells(
        self,
        indices: np.ndarray,
        cell_centers: np.ndarray,
        cell_size: float,
    ) -> List[np.ndarray]:
        """Group candidate cell indices into spatially contiguous clusters.

        Buckets cells into a grid of `cell_size` voxels and unions cells in
        adjacent occupied voxels (26-connectivity). This stands in for real
        mesh-face connectivity, which snappyHexMesh's unstructured output
        doesn't expose without extra plumbing -- good enough to turn "cells
        with anomalous solidification time" into a handful of discrete
        regions with real 3D locations instead of a bare cell count.
        """
        if len(indices) == 0:
            return []
        if cell_size <= 0:
            cell_size = 1e-3

        coords = cell_centers[indices]
        voxel = np.floor(coords / cell_size).astype(int)
        voxel_to_local: Dict[tuple, List[int]] = {}
        for local_i, key in enumerate(map(tuple, voxel)):
            voxel_to_local.setdefault(key, []).append(local_i)

        parent = list(range(len(indices)))

        def find(a: int) -> int:
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        def union(a: int, b: int):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        offsets = [(dx, dy, dz) for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)]
        for key, locals_here in voxel_to_local.items():
            for dx, dy, dz in offsets:
                neighbour_key = (key[0] + dx, key[1] + dy, key[2] + dz)
                neighbours = voxel_to_local.get(neighbour_key)
                if neighbours:
                    for a in locals_here:
                        for b in neighbours:
                            union(a, b)

        clusters: Dict[int, List[int]] = {}
        for local_i in range(len(indices)):
            clusters.setdefault(find(local_i), []).append(local_i)

        return [indices[local_list] for local_list in clusters.values()]

    # ------------------------------------------------------------------
    # Defect predictors
    # ------------------------------------------------------------------

    async def _predict_porosity_real(self, case_name: str, parser: OpenFOAMFieldParser) -> Dict[str, Any]:
        """Niyama-criterion porosity risk, evaluated at the solidification front.

        Ny = G / sqrt(R), with G = |grad T| (real, mesh-based via OpenFOAM's
        own grad function object) and R = cooling rate, both taken at the
        moment each cell crosses the alloy solidus -- not across the whole
        field at one arbitrary snapshot time. Reported in the (K*s)^0.5/mm
        units the casting literature uses (SI value / 775), against a
        per-metal-family threshold.
        """
        try:
            profile = await self._build_solidification_profile(case_name, parser)
        except Exception as e:
            logger.error(f"Error building solidification profile: {e}")
            return {"error": str(e)}

        mask = profile["solidified_mask"]
        if not mask.any():
            return {
                "error": "No cells have both solidified and a resolvable cooling rate yet",
                "still_liquid_volume_fraction_pct": profile["still_liquid_volume_fraction_pct"],
            }

        G = profile["grad_at_front"][mask]
        R = profile["cooling_rate"][mask]
        V = profile["cell_volumes"][mask]

        niyama_SI = G / np.sqrt(np.maximum(R, 1e-6))   # K s^0.5 / m
        niyama_mm = niyama_SI / 775.0                   # (K*s)^0.5 / mm (SI <-> mm/min conversion factor)

        metal_type = self._read_case_metadata(case_name).get("metal_type", "steel")
        threshold = self._niyama_threshold_mm(metal_type)

        below = niyama_mm < threshold
        total_metal_volume = V.sum()
        risky_volume_pct = float(V[below].sum() / total_metal_volume * 100) if total_metal_volume > 0 else 0.0

        ny_stats = {
            "min": float(niyama_mm.min()),
            "max": float(niyama_mm.max()),
            "mean": float(niyama_mm.mean()),
            "std": float(niyama_mm.std()),
            "count": int(niyama_mm.size),
        }

        return {
            "niyama_stats_K_s0.5_per_mm": ny_stats,
            "threshold_K_s0.5_per_mm": threshold,
            "metal_type": metal_type,
            "porous_volume_fraction_pct": risky_volume_pct,
            "still_liquid_volume_fraction_pct": profile["still_liquid_volume_fraction_pct"],
            "criterion": "Niyama Ny = G/sqrt(R), evaluated at solidus crossing",
            "recommendation": self._porosity_recommendation(ny_stats["mean"], risky_volume_pct, threshold),
        }

    async def _predict_hot_spots_real(self, case_name: str, parser: OpenFOAMFieldParser) -> Dict[str, Any]:
        """Locate regions that solidify anomalously late relative to the
        rest of the casting, instead of reporting a fixed percentile of
        instantaneous temperature (which is always ~5% of cells by
        construction, whatever the casting actually looks like).
        """
        try:
            profile = await self._build_solidification_profile(case_name, parser)
        except Exception as e:
            logger.error(f"Error building solidification profile: {e}")
            return {"error": str(e)}

        mask = profile["solidified_mask"] | profile["presolidified_mask"]
        if not mask.any():
            return {"error": "No solidified cells to analyse yet"}

        t_sol = profile["t_solidus"]
        centers = profile["cell_centers"]
        volumes = profile["cell_volumes"]

        idx_all = np.where(mask)[0]
        values = t_sol[idx_all]
        median = float(np.median(values))
        mad = float(np.median(np.abs(values - median)))
        scaled_mad = 1.4826 * mad if mad > 0 else float(np.std(values))

        if scaled_mad <= 0:
            return {
                "hotspot_count": 0,
                "hotspots": [],
                "analysis": "Solidification time is uniform across the casting -- no anomalous last-to-freeze regions detected.",
            }

        threshold = median + 1.5 * scaled_mad
        candidates = idx_all[values > threshold]

        if len(candidates) == 0:
            return {
                "hotspot_count": 0,
                "hotspots": [],
                "analysis": "No cells solidify anomalously later than their surroundings.",
            }

        mean_cell_size = float(np.cbrt(np.median(volumes[mask])))
        clusters = self._cluster_cells(candidates, centers, cell_size=2.0 * mean_cell_size)

        hotspots = []
        for cluster_idx in clusters:
            v = volumes[cluster_idx]
            c = centers[cluster_idx]
            centroid = (c * v[:, None]).sum(axis=0) / v.sum()
            hotspots.append({
                "location_m": tuple(round(float(x), 5) for x in centroid),
                "volume_m3": float(v.sum()),
                "cell_count": int(len(cluster_idx)),
                "max_solidification_time_s": float(t_sol[cluster_idx].max()),
                "mean_solidification_time_s": float(t_sol[cluster_idx].mean()),
            })

        hotspots.sort(key=lambda h: h["volume_m3"], reverse=True)

        return {
            "hotspot_count": len(hotspots),
            "hotspots": hotspots[:10],
            "detection_method": (
                "Cells whose solidification time exceeds median + 1.5x robust "
                "MAD of the casting's solidification-time distribution, "
                "clustered spatially into contiguous regions (grid-voxel "
                "union-find, not true mesh-face connectivity)."
            ),
            "recommendation": self._hot_spot_recommendation(hotspots),
        }

    async def _predict_shrinkage_real(self, case_name: str, parser: OpenFOAMFieldParser) -> Dict[str, Any]:
        """Shrinkage/feeding risk.

        The last-to-freeze regions detected by hotspot analysis are exactly
        where shrinkage forms if not fed by a riser, so this reuses that
        detection rather than a second, redundant metric, and adds a
        thermal-modulus estimate (equivalent-sphere V/A) per region -- the
        quantity Chvorinov's rule uses for riser sizing.
        """
        hotspots = await self._predict_hot_spots_real(case_name, parser)
        if "error" in hotspots:
            return hotspots

        for h in hotspots.get("hotspots", []):
            v = h["volume_m3"]
            r = (3 * v / (4 * np.pi)) ** (1 / 3)
            h["modulus_m"] = round(r / 3.0, 6)  # equivalent-sphere V/A approximation

        regions = hotspots.get("hotspots", [])
        total_isolated_volume = sum(h["volume_m3"] for h in regions)

        return {
            "isolated_regions": regions,
            "isolated_region_count": hotspots.get("hotspot_count", 0),
            "total_isolated_volume_m3": total_isolated_volume,
            "detection_method": hotspots.get("detection_method"),
            "analysis": (
                "Each region is a location the casting is last to solidify; "
                "without a riser feeding it, this is where shrinkage forms. "
                "'modulus_m' is an equivalent-sphere V/A estimate -- for "
                "actual riser sizing, size the riser's own modulus to exceed "
                "this by 1.2-1.5x (Chvorinov's rule)."
            ),
            "recommendation": self._shrinkage_recommendation(regions),
        }

    def _interpret_filling(self, fill_pct: float, entrapment_risk: float) -> str:
        """Interpret filling results."""
        msg = f"Mold filling: {fill_pct:.1f}% complete. "

        if fill_pct < 50:
            msg += "⚠️ Incomplete fill detected. "
        elif fill_pct < 95:
            msg += "Partial fill - may indicate misrun. "
        else:
            msg += "✅ Good fill. "

        if entrapment_risk > 5:
            msg += f"⚠️ Air entrapment risk: {entrapment_risk:.1f}% of cells partially filled."
        else:
            msg += "Minimal air entrapment."

        return msg

    def _interpret_temperature(self, temp_stats: Dict, grad_stats: Dict) -> str:
        """Interpret temperature distribution."""
        return (f"Temperature range: {temp_stats['min']:.1f} K to {temp_stats['max']:.1f} K. "
                f"Average: {temp_stats['mean']:.1f} K. "
                f"Max gradient: {grad_stats['max']:.1f} K/m indicates thermal stress.")

    def _porosity_recommendation(self, avg_ny: float, risky_pct: float, threshold: float) -> str:
        """Generate porosity recommendation."""
        if avg_ny >= threshold * 1.25 and risky_pct < 5:
            return "✅ Low porosity risk. Niyama criterion satisfied across most of the casting."
        elif avg_ny >= threshold * 0.75 and risky_pct < 20:
            return (
                f"⚠️ Moderate porosity risk ({risky_pct:.1f}% of metal volume below "
                f"threshold {threshold:.2f}). Consider increasing feeding or reducing "
                f"pouring temperature."
            )
        else:
            return (
                f"❌ High porosity risk: {risky_pct:.1f}% of metal volume below the "
                f"Niyama threshold ({threshold:.2f}). Recommend larger risers, "
                f"directional solidification, or reduced superheat."
            )

    def _hot_spot_recommendation(self, hotspots: List[Dict[str, Any]]) -> str:
        """Generate hot spot recommendation."""
        if not hotspots:
            return "✅ No anomalous last-to-freeze regions detected."
        largest = hotspots[0]
        return (
            f"⚠️ {len(hotspots)} last-to-freeze region(s) found; largest is "
            f"{largest['volume_m3'] * 1e6:.1f} cm3 near {largest['location_m']}. "
            f"These are the natural riser-placement candidates."
        )

    def _shrinkage_recommendation(self, regions: List[Dict[str, Any]]) -> str:
        """Generate shrinkage recommendation."""
        if not regions:
            return "✅ No isolated late-freezing regions found."
        lines = [f"❌ {len(regions)} isolated region(s) at risk of shrinkage without feeding."]
        for h in regions[:3]:
            modulus_mm = h.get("modulus_m", 0.0) * 1000
            lines.append(
                f"  - {h['volume_m3'] * 1e6:.1f} cm3 near {h['location_m']}, "
                f"modulus {modulus_mm:.2f} mm: size a riser modulus "
                f">= {modulus_mm * 1.3:.2f} mm feeding this region."
            )
        return "\n".join(lines)
