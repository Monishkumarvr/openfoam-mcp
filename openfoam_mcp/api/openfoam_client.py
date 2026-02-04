"""OpenFOAM client for running commands and simulations."""

import asyncio
import subprocess
import os
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger


class OpenFOAMClient:
    """Client for executing OpenFOAM commands."""

    def __init__(self, foam_dir: Optional[str] = None):
        """Initialize OpenFOAM client.

        Args:
            foam_dir: Path to OpenFOAM installation (defaults to $FOAM_INST_DIR)
        """
        self.foam_dir = foam_dir or os.getenv("FOAM_INST_DIR", "/opt/openfoam11")
        self.run_dir = Path.home() / "foam" / "run"
        self.run_dir.mkdir(parents=True, exist_ok=True)

    async def run_command(
        self,
        command: list[str],
        case_dir: str,
        capture_output: bool = True
    ) -> Dict[str, Any]:
        """Run an OpenFOAM command.

        Args:
            command: Command and arguments to run
            case_dir: Case directory path
            capture_output: Whether to capture stdout/stderr

        Returns:
            Dictionary with returncode, stdout, stderr
        """
        logger.info(f"Running command: {' '.join(command)} in {case_dir}")

        # Source OpenFOAM environment and run command
        bash_cmd = f"""
        source {self.foam_dir}/etc/bashrc && \\
        cd {case_dir} && \\
        {' '.join(command)}
        """

        process = await asyncio.create_subprocess_shell(
            bash_cmd,
            stdout=asyncio.subprocess.PIPE if capture_output else None,
            stderr=asyncio.subprocess.PIPE if capture_output else None
        )

        stdout, stderr = await process.communicate()

        result = {
            "returncode": process.returncode,
            "stdout": stdout.decode() if stdout else "",
            "stderr": stderr.decode() if stderr else ""
        }

        if process.returncode != 0:
            logger.error(f"Command failed: {stderr.decode() if stderr else 'Unknown error'}")
        else:
            logger.info(f"Command completed successfully")

        return result

    async def run_mesh_generation(
        self,
        case_name: str,
        parallel: bool = False,
        num_processors: int = 4
    ) -> Dict[str, Any]:
        """Run mesh generation for a case.

        Args:
            case_name: Name of the case
            parallel: Whether to run in parallel
            num_processors: Number of processors for parallel execution

        Returns:
            Dictionary with mesh statistics
        """
        case_dir = self.run_dir / case_name

        # Run blockMesh
        result = await self.run_command(["blockMesh"], str(case_dir))

        if result["returncode"] != 0:
            raise RuntimeError(f"blockMesh failed: {result['stderr']}")

        # Check if snappyHexMesh is configured
        snappy_dict = case_dir / "system" / "snappyHexMeshDict"
        if snappy_dict.exists():
            logger.info("Running snappyHexMesh")

            if parallel:
                # Decompose mesh
                await self.run_command(
                    ["decomposePar"],
                    str(case_dir)
                )

                # Run snappyHexMesh in parallel
                await self.run_command(
                    ["mpirun", "-np", str(num_processors), "snappyHexMesh", "-parallel", "-overwrite"],
                    str(case_dir)
                )

                # Reconstruct mesh
                await self.run_command(
                    ["reconstructParMesh", "-constant"],
                    str(case_dir)
                )
            else:
                await self.run_command(
                    ["snappyHexMesh", "-overwrite"],
                    str(case_dir)
                )

        # Get mesh statistics
        check_mesh_result = await self.run_command(
            ["checkMesh"],
            str(case_dir)
        )

        # Parse mesh statistics from output
        stats = self._parse_mesh_stats(check_mesh_result["stdout"])

        return stats

    def _parse_mesh_stats(self, output: str) -> Dict[str, Any]:
        """Parse checkMesh output for statistics."""
        stats = {
            "num_cells": "N/A",
            "num_points": "N/A",
            "quality": "N/A"
        }

        for line in output.split("\n"):
            if "cells:" in line:
                parts = line.split()
                if len(parts) >= 2:
                    stats["num_cells"] = parts[1]
            elif "points:" in line:
                parts = line.split()
                if len(parts) >= 2:
                    stats["num_points"] = parts[1]
            elif "Mesh OK" in line:
                stats["quality"] = "OK"
            elif "Failed" in line:
                stats["quality"] = "FAILED"

        return stats

    async def run_simulation(
        self,
        case_name: str,
        solver: str = "interFoam",
        end_time: Optional[float] = None,
        write_interval: Optional[float] = None,
        parallel: bool = False,
        num_processors: int = 4
    ) -> Dict[str, Any]:
        """Run OpenFOAM simulation.

        Args:
            case_name: Name of the case
            solver: Solver to use
            end_time: Simulation end time
            write_interval: Write interval
            parallel: Run in parallel
            num_processors: Number of processors

        Returns:
            Dictionary with simulation results
        """
        case_dir = self.run_dir / case_name

        # Update controlDict if needed
        if end_time or write_interval:
            await self._update_control_dict(
                case_dir,
                end_time=end_time,
                write_interval=write_interval
            )

        if parallel:
            # Decompose case
            await self.run_command(
                ["decomposePar"],
                str(case_dir)
            )

            # Run solver in parallel
            result = await self.run_command(
                ["mpirun", "-np", str(num_processors), solver, "-parallel"],
                str(case_dir)
            )

            # Reconstruct case
            await self.run_command(
                ["reconstructPar"],
                str(case_dir)
            )
        else:
            result = await self.run_command(
                [solver],
                str(case_dir)
            )

        if result["returncode"] != 0:
            return {
                "status": "failed",
                "error": result["stderr"]
            }

        return {
            "status": "completed",
            "final_time": end_time or "N/A",
            "output_dir": str(case_dir)
        }

    async def _update_control_dict(
        self,
        case_dir: Path,
        end_time: Optional[float] = None,
        write_interval: Optional[float] = None
    ):
        """Update controlDict with new parameters."""
        control_dict_path = case_dir / "system" / "controlDict"

        if not control_dict_path.exists():
            return

        with open(control_dict_path, 'r') as f:
            content = f.read()

        if end_time is not None:
            # Simple replacement - could use PyFoam for more robust parsing
            import re
            content = re.sub(
                r'endTime\s+[\d.]+;',
                f'endTime        {end_time};',
                content
            )

        if write_interval is not None:
            import re
            content = re.sub(
                r'writeInterval\s+[\d.]+;',
                f'writeInterval  {write_interval};',
                content
            )

        with open(control_dict_path, 'w') as f:
            f.write(content)

    async def export_results(
        self,
        case_name: str,
        export_format: str,
        output_path: str
    ) -> Dict[str, Any]:
        """Export simulation results.

        Args:
            case_name: Name of the case
            export_format: Export format (vtk, stl, csv, images)
            output_path: Output path

        Returns:
            Dictionary with export info
        """
        case_dir = self.run_dir / case_name
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        if export_format == "vtk":
            await self.run_command(
                ["foamToVTK"],
                str(case_dir)
            )
            return {
                "output_path": str(case_dir / "VTK"),
                "format": "vtk"
            }

        elif export_format == "stl":
            # Export surface as STL
            await self.run_command(
                ["foamToSurface"],
                str(case_dir)
            )
            return {
                "output_path": str(case_dir / "surfaces"),
                "format": "stl"
            }

        else:
            raise ValueError(f"Unsupported export format: {export_format}")
