"""Parametric study engine for OpenFOAM casting simulations.

This module provides tools for running and comparing multiple simulations
with different parameters to optimize casting processes.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import asyncio
from loguru import logger

from .case_manager import CaseManager
from .openfoam_client import OpenFOAMClient
from .result_analyzer_real import RealResultAnalyzer


class ParametricStudyEngine:
    """Engine for running parametric studies on casting simulations."""

    def __init__(self, run_dir: Optional[str] = None):
        """Initialize parametric study engine.

        Args:
            run_dir: Directory for simulation cases
        """
        self.run_dir = Path(run_dir) if run_dir else Path.home() / "foam" / "run"
        self.case_manager = CaseManager(run_dir)
        self.openfoam_client = OpenFOAMClient()
        self.analyzer = RealResultAnalyzer(run_dir)

        self.results = {}  # Store results for comparison

    async def run_parametric_study(
        self,
        base_case_name: str,
        parameters: Dict[str, List[Any]],
        metric: str = "minimize_porosity"
    ) -> Dict[str, Any]:
        """Run parametric study by varying parameters.

        Args:
            base_case_name: Base case to vary
            parameters: Dictionary of parameter names to lists of values
                       e.g., {"inlet_velocity": [0.3, 0.5, 0.7],
                              "pouring_temperature": [730, 750, 770]}
            metric: Optimization metric to track

        Returns:
            Dictionary with study results and optimal configuration
        """
        logger.info(f"Starting parametric study on {base_case_name}")
        logger.info(f"Parameters: {parameters}")

        # Generate all parameter combinations
        combinations = self._generate_combinations(parameters)

        logger.info(f"Generated {len(combinations)} parameter combinations")

        # Run simulations for each combination
        study_results = []

        for i, combo in enumerate(combinations):
            logger.info(f"Running combination {i+1}/{len(combinations)}: {combo}")

            case_name = self._generate_case_name(base_case_name, combo, i)

            try:
                # Create case with these parameters
                result = await self._run_case_with_parameters(
                    base_case_name,
                    case_name,
                    combo
                )

                study_results.append({
                    "case_name": case_name,
                    "parameters": combo,
                    "results": result,
                    "index": i
                })

            except Exception as e:
                logger.error(f"Error running case {case_name}: {e}")
                study_results.append({
                    "case_name": case_name,
                    "parameters": combo,
                    "error": str(e),
                    "index": i
                })

        # Compare results and find optimal
        comparison = self._compare_results(study_results, metric)

        return {
            "total_runs": len(combinations),
            "completed_runs": len([r for r in study_results if "results" in r]),
            "failed_runs": len([r for r in study_results if "error" in r]),
            "study_results": study_results,
            "comparison": comparison,
            "optimal_configuration": comparison.get("best_case"),
            "metric": metric
        }

    def _generate_combinations(self, parameters: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
        """Generate all combinations of parameters.

        Args:
            parameters: Dictionary of parameter lists

        Returns:
            List of parameter combination dictionaries
        """
        if not parameters:
            return [{}]

        # Get keys and values
        keys = list(parameters.keys())
        value_lists = [parameters[k] for k in keys]

        # Generate combinations using recursion
        combinations = []

        def generate(index: int, current: Dict):
            if index == len(keys):
                combinations.append(current.copy())
                return

            key = keys[index]
            for value in value_lists[index]:
                current[key] = value
                generate(index + 1, current)
                del current[key]

        generate(0, {})
        return combinations

    def _generate_case_name(self, base_name: str, params: Dict[str, Any], index: int) -> str:
        """Generate unique case name from parameters.

        Args:
            base_name: Base case name
            params: Parameter values
            index: Combination index

        Returns:
            Generated case name
        """
        # Create short parameter string
        param_str = "_".join([f"{k[:1]}{v}" for k, v in params.items()])
        return f"{base_name}_param{index}_{param_str}"

    async def _run_case_with_parameters(
        self,
        base_case: str,
        new_case: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run a case with specific parameter values.

        Args:
            base_case: Base case to copy from
            new_case: New case name
            parameters: Parameter values to apply

        Returns:
            Analysis results for this case
        """
        # Copy base case
        base_path = self.run_dir / base_case
        new_path = self.run_dir / new_case

        if not base_path.exists():
            raise ValueError(f"Base case {base_case} not found")

        # Create new case by copying base
        import shutil
        if new_path.exists():
            shutil.rmtree(new_path)
        shutil.copytree(base_path, new_path)

        # Modify parameters in new case
        await self._modify_case_parameters(new_path, parameters)

        # Run simulation
        mesh_result = await self.openfoam_client.run_mesh_generation(
            case_name=new_case,
            parallel=False
        )

        sim_result = await self.openfoam_client.run_simulation(
            case_name=new_case,
            solver="interFoam",
            parallel=False
        )

        # Analyze results
        analysis = await self.analyzer.analyze(
            case_name=new_case,
            analysis_type="all"
        )

        return {
            "mesh": mesh_result,
            "simulation": sim_result,
            "analysis": analysis
        }

    async def _modify_case_parameters(self, case_path: Path, parameters: Dict[str, Any]):
        """Modify OpenFOAM case files to set parameters.

        Args:
            case_path: Path to case directory
            parameters: Parameters to modify
        """
        for param_name, param_value in parameters.items():
            if param_name == "inlet_velocity":
                await self._set_inlet_velocity(case_path, param_value)
            elif param_name == "pouring_temperature":
                await self._set_temperature(case_path, param_value)
            elif param_name == "mesh_refinement":
                await self._set_mesh_refinement(case_path, param_value)
            # Add more parameter handlers as needed

    async def _set_inlet_velocity(self, case_path: Path, velocity: float):
        """Set inlet velocity in 0/U file."""
        u_file = case_path / "0" / "U"

        if u_file.exists():
            with open(u_file, 'r') as f:
                content = f.read()

            # Replace inlet velocity (assumes z-direction inlet)
            import re
            content = re.sub(
                r'(inlet\s*{.*?value\s+uniform\s+)\([^)]+\)',
                f'\\1(0 0 {velocity})',
                content,
                flags=re.DOTALL
            )

            with open(u_file, 'w') as f:
                f.write(content)

    async def _set_temperature(self, case_path: Path, temperature: float):
        """Set inlet temperature in 0/T file (if exists)."""
        t_file = case_path / "0" / "T"

        if t_file.exists():
            with open(t_file, 'r') as f:
                content = f.read()

            # Convert Celsius to Kelvin
            temp_k = temperature + 273.15

            import re
            content = re.sub(
                r'(inlet\s*{.*?value\s+uniform\s+)([\d.]+)',
                f'\\g<1>{temp_k}',
                content,
                flags=re.DOTALL
            )

            with open(t_file, 'w') as f:
                f.write(content)

    async def _set_mesh_refinement(self, case_path: Path, refinement: str):
        """Modify blockMeshDict for different refinement levels."""
        # This would modify cell counts in blockMeshDict
        # Implementation depends on specific mesh structure
        pass

    def _compare_results(self, results: List[Dict], metric: str) -> Dict[str, Any]:
        """Compare results from different parameter sets.

        Args:
            results: List of result dictionaries
            metric: Metric to optimize

        Returns:
            Comparison summary with best case
        """
        valid_results = [r for r in results if "results" in r and "error" not in r.get("results", {})]

        if not valid_results:
            return {
                "error": "No valid results to compare",
                "best_case": None
            }

        # Extract metrics for comparison
        comparison_data = []

        for result in valid_results:
            case_name = result["case_name"]
            params = result["parameters"]
            analysis = result["results"].get("analysis", {})

            # Extract key metrics
            defects = analysis.get("defects", {})
            porosity = defects.get("porosity", {})
            shrinkage = defects.get("shrinkage", {})

            # Calculate composite score based on metric
            score = self._calculate_score(metric, porosity, shrinkage, analysis)

            comparison_data.append({
                "case_name": case_name,
                "parameters": params,
                "score": score,
                "porosity_risk": porosity.get("high_risk_percentage", 0),
                "shrinkage_risk": shrinkage.get("shrinkage_risk_percentage", 0),
                "niyama_avg": porosity.get("niyama_stats", {}).get("mean", 0)
            })

        # Sort by score (lower is better for risks)
        comparison_data.sort(key=lambda x: x["score"])

        # Best case is first after sorting
        best_case = comparison_data[0] if comparison_data else None

        # Calculate improvements
        if len(comparison_data) > 1:
            worst_score = comparison_data[-1]["score"]
            best_score = best_case["score"]
            improvement = ((worst_score - best_score) / worst_score * 100) if worst_score > 0 else 0
        else:
            improvement = 0

        return {
            "all_cases": comparison_data,
            "best_case": best_case,
            "worst_case": comparison_data[-1] if comparison_data else None,
            "improvement_percentage": improvement,
            "ranking": [c["case_name"] for c in comparison_data]
        }

    def _calculate_score(
        self,
        metric: str,
        porosity: Dict,
        shrinkage: Dict,
        analysis: Dict
    ) -> float:
        """Calculate optimization score based on metric.

        Args:
            metric: Optimization objective
            porosity: Porosity prediction data
            shrinkage: Shrinkage prediction data
            analysis: Full analysis data

        Returns:
            Score (lower is better)
        """
        if metric == "minimize_porosity":
            # Use porosity risk percentage as score
            return porosity.get("high_risk_percentage", 100.0)

        elif metric == "minimize_shrinkage":
            return shrinkage.get("shrinkage_risk_percentage", 100.0)

        elif metric == "uniform_solidification":
            # Want low temperature variation
            temp_dist = analysis.get("temperature_distribution", {})
            temp_stats = temp_dist.get("temperature_stats", {})
            return temp_stats.get("std", 1000.0)

        elif metric == "minimize_fill_time":
            # Extract fill time from analysis
            filling = analysis.get("filling_pattern", {})
            return filling.get("time", 999.0)

        else:
            # Composite score: weighted sum of all defects
            porosity_risk = porosity.get("high_risk_percentage", 0)
            shrinkage_risk = shrinkage.get("shrinkage_risk_percentage", 0)
            return porosity_risk * 0.6 + shrinkage_risk * 0.4

    async def compare_two_cases(
        self,
        case1: str,
        case2: str
    ) -> Dict[str, Any]:
        """Compare two specific cases in detail.

        Args:
            case1: First case name
            case2: Second case name

        Returns:
            Detailed comparison
        """
        # Analyze both cases
        analysis1 = await self.analyzer.analyze(case1, "all")
        analysis2 = await self.analyzer.analyze(case2, "all")

        # Extract key metrics
        def extract_metrics(analysis):
            defects = analysis.get("defects", {})
            return {
                "porosity_risk": defects.get("porosity", {}).get("high_risk_percentage", 0),
                "shrinkage_risk": defects.get("shrinkage", {}).get("shrinkage_risk_percentage", 0),
                "niyama_avg": defects.get("porosity", {}).get("niyama_stats", {}).get("mean", 0),
                "fill_percentage": analysis.get("filling_pattern", {}).get("fill_percentage", 0),
                "avg_temp": analysis.get("temperature_distribution", {}).get("temperature_stats", {}).get("mean", 0)
            }

        metrics1 = extract_metrics(analysis1)
        metrics2 = extract_metrics(analysis2)

        # Calculate differences
        differences = {
            key: metrics2[key] - metrics1[key]
            for key in metrics1.keys()
        }

        # Determine which is better
        winner = case2 if metrics2["porosity_risk"] < metrics1["porosity_risk"] else case1

        return {
            "case1": case1,
            "case2": case2,
            "case1_metrics": metrics1,
            "case2_metrics": metrics2,
            "differences": differences,
            "better_case": winner,
            "summary": self._generate_comparison_summary(case1, case2, metrics1, metrics2, differences)
        }

    def _generate_comparison_summary(
        self,
        case1: str,
        case2: str,
        metrics1: Dict,
        metrics2: Dict,
        diff: Dict
    ) -> str:
        """Generate human-readable comparison summary."""
        summary = f"Comparison: {case1} vs {case2}\n\n"

        summary += "Porosity Risk:\n"
        summary += f"  {case1}: {metrics1['porosity_risk']:.1f}%\n"
        summary += f"  {case2}: {metrics2['porosity_risk']:.1f}%\n"
        summary += f"  Difference: {diff['porosity_risk']:+.1f}%\n\n"

        summary += "Shrinkage Risk:\n"
        summary += f"  {case1}: {metrics1['shrinkage_risk']:.1f}%\n"
        summary += f"  {case2}: {metrics2['shrinkage_risk']:.1f}%\n"
        summary += f"  Difference: {diff['shrinkage_risk']:+.1f}%\n\n"

        summary += "Average Niyama:\n"
        summary += f"  {case1}: {metrics1['niyama_avg']:.3f}\n"
        summary += f"  {case2}: {metrics2['niyama_avg']:.3f}\n"
        summary += f"  Difference: {diff['niyama_avg']:+.3f}\n\n"

        # Recommend better case
        if metrics2['porosity_risk'] < metrics1['porosity_risk']:
            summary += f"✅ {case2} shows better performance (lower porosity risk)"
        else:
            summary += f"✅ {case1} shows better performance (lower porosity risk)"

        return summary
