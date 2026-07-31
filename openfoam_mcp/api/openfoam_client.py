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
            stderr=asyncio.subprocess.PIPE if capture_output else None,
            executable='/bin/bash'  # Use bash explicitly for 'source' command
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
                self._write_decompose_par_dict(case_dir, num_processors)

                # Decompose mesh
                decompose_result = await self.run_command(["decomposePar"], str(case_dir))
                if decompose_result["returncode"] != 0:
                    raise RuntimeError(f"decomposePar failed: {decompose_result['stderr']}")

                # Run snappyHexMesh in parallel
                mesh_result = await self.run_command(
                    ["mpirun", "-np", str(num_processors), "snappyHexMesh", "-parallel", "-overwrite"],
                    str(case_dir)
                )
                if mesh_result["returncode"] != 0:
                    raise RuntimeError(f"parallel snappyHexMesh failed: {mesh_result['stderr']}")

                # Reconstruct mesh
                reconstruct_result = await self.run_command(
                    ["reconstructParMesh", "-constant"],
                    str(case_dir)
                )
                if reconstruct_result["returncode"] != 0:
                    raise RuntimeError(f"reconstructParMesh failed: {reconstruct_result['stderr']}")
            else:
                await self.run_command(
                    ["snappyHexMesh", "-overwrite"],
                    str(case_dir)
                )

        # Split the gate/vent patches out of the STL surface patch. Without
        # this the cavity is sealed: no inlet for the metal, no outlet for the
        # air it displaces.
        topo_set_dict = case_dir / "system" / "topoSetDict"
        create_patch_dict = case_dir / "system" / "createPatchDict"
        if topo_set_dict.exists() and create_patch_dict.exists():
            logger.info("Creating gate/vent patches")

            topo_result = await self.run_command(["topoSet"], str(case_dir))
            if topo_result["returncode"] != 0:
                raise RuntimeError(f"topoSet failed: {topo_result['stderr']}")

            patch_result = await self.run_command(
                ["createPatch", "-overwrite"],
                str(case_dir)
            )
            if patch_result["returncode"] != 0:
                raise RuntimeError(f"createPatch failed: {patch_result['stderr']}")

        # Get mesh statistics
        check_mesh_result = await self.run_command(
            ["checkMesh"],
            str(case_dir)
        )

        # Parse mesh statistics from output
        stats = self._parse_mesh_stats(check_mesh_result["stdout"])

        return stats

    def _write_decompose_par_dict(self, case_dir: Path, num_processors: int):
        """Write system/decomposeParDict for a parallel run.

        Neither run_mesh_generation nor run_simulation previously wrote
        this, so `decomposePar` had nothing to read and failed silently
        (its return code was never checked either -- see the checks added
        around every call site above). Always overwrites so a case
        previously decomposed for a different processor count doesn't
        leave a stale, mismatched dict behind.
        """
        content = f"""/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  11                                    |
|   \\\\  /    A nd           | Website:  www.openfoam.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      decomposeParDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

numberOfSubdomains {num_processors};

method          scotch;

// ************************************************************************* //
"""
        decompose_path = case_dir / "system" / "decomposeParDict"
        decompose_path.write_text(content)

    async def compute_gradient(self, case_name: str, field_name: str = 'T') -> Dict[str, Any]:
        """Compute the real, mesh-based spatial gradient of a field.

        Runs OpenFOAM's own 'grad' function object over every written time
        directory, writing 'grad(<field_name>)' alongside the field it was
        computed from. This is the correct replacement for differencing
        field values in cell-storage order (which has no relationship to
        physical space and was silently wrong).
        """
        case_dir = self.run_dir / case_name
        return await self.run_command(
            ["postProcess", "-func", f"'grad({field_name})'"],
            str(case_dir)
        )

    async def compute_cell_centers(self, case_name: str, time: str = "0") -> Dict[str, Any]:
        """Write cell-center coordinates (field 'C') into `time`.

        Cell centers are static for these solvers (no mesh motion), so one
        time is enough; downstream code reads it back at time 0 regardless
        of which simulation time is being analysed.
        """
        case_dir = self.run_dir / case_name
        return await self.run_command(
            ["postProcess", "-func", "writeCellCentres", "-time", time],
            str(case_dir)
        )

    async def compute_cell_volumes(self, case_name: str, time: str = "0") -> Dict[str, Any]:
        """Write cell volumes (field 'Vc') into `time`. Static mesh, same as above."""
        case_dir = self.run_dir / case_name
        return await self.run_command(
            ["postProcess", "-func", "writeCellVolumes", "-time", time],
            str(case_dir)
        )

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

    def _detect_solver_from_controldict(self, case_dir: Path) -> tuple[str, Optional[str]]:
        """Detect which solver to use from controlDict.

        Args:
            case_dir: Case directory

        Returns:
            Tuple of (application, solver_module) where solver_module is only used for foamRun
        """
        control_dict = case_dir / "system" / "controlDict"

        if not control_dict.exists():
            return ("interFoam", None)  # fallback

        with open(control_dict, 'r') as f:
            content = f.read()

        import re

        # Check for OpenFOAM 11+ style (foamRun with solver directive)
        app_match = re.search(r'application\s+(\w+);', content)
        if app_match and app_match.group(1) == 'foamRun':
            # Extract solver module name
            solver_match = re.search(r'solver\s+(\w+);', content)
            if solver_match:
                solver_module = solver_match.group(1)
                return ("foamRun", solver_module)
            else:
                logger.warning("foamRun detected but no solver module found in controlDict")
                return ("foamRun", "incompressibleVoF")  # fallback to common module

        # Check for traditional application directive
        if app_match:
            return (app_match.group(1), None)

        # Fallback
        return ("interFoam", None)

    async def run_simulation(
        self,
        case_name: str,
        solver: Optional[str] = None,
        end_time: Optional[float] = None,
        write_interval: Optional[float] = None,
        parallel: bool = False,
        num_processors: int = 4
    ) -> Dict[str, Any]:
        """Run OpenFOAM simulation.

        Args:
            case_name: Name of the case
            solver: Solver to use (if None, auto-detect from controlDict)
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

        # Auto-detect solver if not specified
        solver_app = None
        solver_module = None

        if solver is None:
            solver_app, solver_module = self._detect_solver_from_controldict(case_dir)
            logger.info(f"Auto-detected solver: {solver_app}" +
                       (f" with module {solver_module}" if solver_module else ""))
        else:
            # Legacy: solver provided as string
            solver_app = solver

        # Build solver command
        if solver_app == "foamRun" and solver_module:
            solver_cmd = ["foamRun", "-solver", solver_module]
        else:
            solver_cmd = [solver_app]

        if parallel:
            self._write_decompose_par_dict(case_dir, num_processors)

            # Decompose case
            decompose_result = await self.run_command(["decomposePar"], str(case_dir))
            if decompose_result["returncode"] != 0:
                return {
                    "status": "failed",
                    "stage": "decomposePar",
                    "error": decompose_result["stderr"]
                }

            # Run solver in parallel
            if solver_app == "foamRun":
                # For foamRun, -parallel goes after -solver
                result = await self.run_command(
                    ["mpirun", "-np", str(num_processors)] + solver_cmd + ["-parallel"],
                    str(case_dir)
                )
            else:
                result = await self.run_command(
                    ["mpirun", "-np", str(num_processors), solver_app, "-parallel"],
                    str(case_dir)
                )

            if result["returncode"] != 0:
                return {
                    "status": "failed",
                    "stage": "solve",
                    "error": result["stderr"]
                }

            # Reconstruct case
            reconstruct_result = await self.run_command(["reconstructPar"], str(case_dir))
            if reconstruct_result["returncode"] != 0:
                # The per-processor results still exist and are analysable;
                # only the merge step failed, so report it but don't call
                # the whole run a failure.
                return {
                    "status": "completed_unreconstructed",
                    "final_time": end_time or "N/A",
                    "output_dir": str(case_dir),
                    "warning": f"reconstructPar failed: {reconstruct_result['stderr']}"
                }
        else:
            result = await self.run_command(
                solver_cmd,
                str(case_dir)
            )

            if result["returncode"] != 0:
                return {
                    "status": "failed",
                    "stage": "solve",
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
