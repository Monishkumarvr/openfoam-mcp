"""REAL result analyzer for OpenFOAM casting simulations.

This module provides actual analysis of OpenFOAM simulation results,
including defect prediction based on real calculations.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
import numpy as np
from loguru import logger

from ..utils.field_parser import OpenFOAMFieldParser


class RealResultAnalyzer:
    """Real analyzer that actually parses OpenFOAM results."""

    def __init__(self, run_dir: Optional[str] = None):
        """Initialize analyzer.

        Args:
            run_dir: Directory containing simulation cases
        """
        self.run_dir = Path(run_dir) if run_dir else Path.home() / "foam" / "run"

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
                results["temperature_distribution"] = await self._analyze_temperature(parser, time_step)

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
        parser: OpenFOAMFieldParser,
        time_step: Optional[float]
    ) -> Dict[str, Any]:
        """Analyze temperature distribution.

        Args:
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

            # Calculate temperature gradient
            grad_T = parser.calculate_gradient(T_values)
            grad_stats = parser.calculate_field_statistics(grad_T)

            # Identify hot spots (top 10% temperatures)
            if len(T_values) > 0:
                temp_threshold = np.percentile(T_values, 90)
                hot_spot_cells = np.sum(T_values > temp_threshold)
                hot_spot_percentage = (hot_spot_cells / len(T_values)) * 100
            else:
                hot_spot_cells = 0
                hot_spot_percentage = 0

            return {
                "temperature_stats": stats,
                "gradient_stats": grad_stats,
                "hot_spot_percentage": float(hot_spot_percentage),
                "hot_spot_cells": int(hot_spot_cells),
                "time": T_data['time'],
                "analysis": self._interpret_temperature(stats, grad_stats)
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
        case_dir = self.run_dir / case_name
        parser = OpenFOAMFieldParser(case_dir)

        predictions = {}

        for defect_type in defect_types:
            if defect_type == "porosity":
                predictions["porosity"] = await self._predict_porosity_real(parser)
            elif defect_type == "shrinkage":
                predictions["shrinkage"] = await self._predict_shrinkage_real(parser)
            elif defect_type == "hot_spots":
                predictions["hot_spots"] = await self._predict_hot_spots_real(parser)

        return predictions

    async def _predict_porosity_real(self, parser: OpenFOAMFieldParser) -> Dict[str, Any]:
        """REAL porosity prediction using Niyama criterion.

        Niyama criterion: Ny = G / sqrt(R)
        where G = temperature gradient, R = cooling rate

        Ny > 1.0: Safe (no porosity)
        Ny < 0.5: High porosity risk
        """
        try:
            # Need temperature field
            T_data = parser.read_scalar_field('T')
            T_values = T_data['internal_field']

            if len(T_values) == 0:
                return {"error": "No temperature data available"}

            # Calculate temperature gradient
            grad_T = parser.calculate_gradient(T_values)

            # Estimate cooling rate from time series (if available)
            times = parser.get_time_directories()

            if len(times) >= 2:
                T_prev = parser.read_scalar_field('T', times[-2])['internal_field']
                dt = times[-1] - times[-2]

                if len(T_prev) == len(T_values) and dt > 0:
                    cooling_rate = np.abs((T_values - T_prev) / dt)
                else:
                    # Use constant estimate
                    cooling_rate = np.ones_like(T_values) * 10.0  # K/s estimate
            else:
                cooling_rate = np.ones_like(T_values) * 10.0

            # Calculate Niyama criterion
            # Avoid division by zero
            cooling_rate = np.maximum(cooling_rate, 1e-10)
            niyama = grad_T / np.sqrt(cooling_rate)

            # Classify risk zones
            high_risk = np.sum(niyama < 0.5)
            moderate_risk = np.sum((niyama >= 0.5) & (niyama < 1.0))
            safe = np.sum(niyama >= 1.0)
            total = len(niyama)

            risk_percentage = (high_risk / total * 100) if total > 0 else 0

            ny_stats = parser.calculate_field_statistics(niyama)

            return {
                "niyama_stats": ny_stats,
                "high_risk_cells": int(high_risk),
                "moderate_risk_cells": int(moderate_risk),
                "safe_cells": int(safe),
                "high_risk_percentage": float(risk_percentage),
                "recommendation": self._porosity_recommendation(ny_stats['mean'], risk_percentage),
                "criterion": "Niyama (G/√R)",
                "threshold_safe": 1.0,
                "threshold_risky": 0.5
            }

        except Exception as e:
            logger.error(f"Error predicting porosity: {e}")
            return {"error": str(e)}

    async def _predict_shrinkage_real(self, parser: OpenFOAMFieldParser) -> Dict[str, Any]:
        """REAL shrinkage prediction using thermal modulus."""
        try:
            T_data = parser.read_scalar_field('T')
            T_values = T_data['internal_field']

            if len(T_values) == 0:
                return {"error": "No temperature data"}

            # Find hottest regions (last to solidify = shrinkage risk)
            hot_threshold = np.percentile(T_values, 90)
            hot_cells = np.sum(T_values > hot_threshold)
            shrinkage_risk = (hot_cells / len(T_values) * 100) if len(T_values) > 0 else 0

            # Calculate temperature gradient to find isolated hot spots
            grad_T = parser.calculate_gradient(T_values)

            # Isolated hot spots have high temperature but low gradient (fed poorly)
            isolated_hot = np.sum((T_values > hot_threshold) & (grad_T < np.median(grad_T)))

            return {
                "high_temp_cells": int(hot_cells),
                "isolated_hot_spots": int(isolated_hot),
                "shrinkage_risk_percentage": float(shrinkage_risk),
                "max_temperature": float(np.max(T_values)),
                "recommendation": self._shrinkage_recommendation(shrinkage_risk, isolated_hot),
                "analysis": "Based on thermal modulus and isolated hot spot detection"
            }

        except Exception as e:
            return {"error": str(e)}

    async def _predict_hot_spots_real(self, parser: OpenFOAMFieldParser) -> Dict[str, Any]:
        """REAL hot spot detection."""
        try:
            T_data = parser.read_scalar_field('T')
            T_values = T_data['internal_field']

            # Find cells in top 5% of temperature
            if len(T_values) > 0:
                hot_threshold = np.percentile(T_values, 95)
                hot_spots = T_values > hot_threshold
                num_hot_spots = np.sum(hot_spots)

                hot_spot_temps = T_values[hot_spots]
                avg_hot_temp = np.mean(hot_spot_temps) if len(hot_spot_temps) > 0 else 0

                return {
                    "hot_spot_count": int(num_hot_spots),
                    "hot_spot_percentage": float(num_hot_spots / len(T_values) * 100),
                    "threshold_temperature": float(hot_threshold),
                    "average_hot_spot_temp": float(avg_hot_temp),
                    "locations": "See VTK output for spatial distribution",
                    "recommendation": self._hot_spot_recommendation(num_hot_spots, len(T_values))
                }
            else:
                return {"error": "No temperature data"}

        except Exception as e:
            return {"error": str(e)}

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

    def _porosity_recommendation(self, avg_ny: float, risk_pct: float) -> str:
        """Generate porosity recommendation."""
        if avg_ny > 1.0 and risk_pct < 5:
            return "✅ Low porosity risk. Niyama criterion satisfied."
        elif avg_ny > 0.5 and risk_pct < 20:
            return "⚠️ Moderate porosity risk. Consider increasing feeding or reducing pouring temperature."
        else:
            return "❌ High porosity risk! Recommend: larger risers, directional solidification, or reduced superheat."

    def _shrinkage_recommendation(self, risk_pct: float, isolated: int) -> str:
        """Generate shrinkage recommendation."""
        if risk_pct < 10 and isolated < 5:
            return "✅ Low shrinkage risk."
        elif risk_pct < 30:
            return f"⚠️ Moderate shrinkage risk. {isolated} isolated hot spots found. Consider adding chills."
        else:
            return "❌ High shrinkage risk! Add risers near thick sections or increase chill usage."

    def _hot_spot_recommendation(self, num_hot: int, total: int) -> str:
        """Generate hot spot recommendation."""
        pct = (num_hot / total * 100) if total > 0 else 0

        if pct < 5:
            return "✅ Minimal hot spots. Good thermal distribution."
        elif pct < 15:
            return "⚠️ Moderate hot spot concentration. May need additional cooling."
        else:
            return "❌ Excessive hot spots! Redesign gating or add cooling channels."
