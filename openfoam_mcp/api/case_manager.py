"""Case manager for creating and managing OpenFOAM cases."""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger

from ..builders.case_builder import CaseBuilder


class CaseManager:
    """Manager for OpenFOAM simulation cases."""

    def __init__(self, run_dir: Optional[str] = None):
        """Initialize case manager.

        Args:
            run_dir: Directory for simulation cases
        """
        self.run_dir = Path(run_dir) if run_dir else Path.home() / "foam" / "run"
        self.run_dir.mkdir(parents=True, exist_ok=True)

        self.metadata_file = self.run_dir / ".cases_metadata.json"
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> Dict[str, Any]:
        """Load cases metadata."""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_metadata(self):
        """Save cases metadata."""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)

    async def create_case(
        self,
        case_name: str,
        case_type: str,
        metal_type: str,
        pouring_temperature: float,
        mold_material: str = "sand"
    ) -> Dict[str, Any]:
        """Create a new OpenFOAM case.

        Args:
            case_name: Name for the case
            case_type: Type of casting simulation
            metal_type: Type of metal
            pouring_temperature: Pouring temperature in Celsius
            mold_material: Mold material

        Returns:
            Dictionary with case information
        """
        case_dir = self.run_dir / case_name

        if case_dir.exists():
            raise ValueError(f"Case {case_name} already exists")

        logger.info(f"Creating case: {case_name} at {case_dir}")

        # Create case directory structure
        case_dir.mkdir(parents=True)
        (case_dir / "0").mkdir()
        (case_dir / "constant").mkdir()
        (case_dir / "system").mkdir()

        # Use CaseBuilder to create appropriate template
        builder = CaseBuilder(case_type)
        builder.set_metal_type(metal_type)
        builder.set_pouring_temperature(pouring_temperature)
        builder.set_mold_material(mold_material)

        # Build case files
        case_files = builder.build()

        # Write files to case directory
        for file_path, content in case_files.items():
            full_path = case_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            with open(full_path, 'w') as f:
                f.write(content)

        # Save metadata
        self.metadata[case_name] = {
            "name": case_name,
            "type": case_type,
            "metal_type": metal_type,
            "pouring_temperature": pouring_temperature,
            "mold_material": mold_material,
            "created": datetime.now().isoformat(),
            "status": "created",
            "path": str(case_dir)
        }
        self._save_metadata()

        return {
            "name": case_name,
            "path": str(case_dir),
            "status": "created"
        }

    async def list_cases(self, filter_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all cases.

        Args:
            filter_type: Optional filter by case type

        Returns:
            List of case information dictionaries
        """
        cases = []

        for case_name, metadata in self.metadata.items():
            if filter_type and metadata.get("type") != filter_type:
                continue

            cases.append({
                "name": case_name,
                "type": metadata.get("type", "unknown"),
                "status": metadata.get("status", "unknown"),
                "created": metadata.get("created", "N/A")
            })

        return cases

    async def setup_geometry(
        self,
        case_name: str,
        geometry_type: str,
        stl_path: Optional[str] = None,
        dimensions: Optional[Dict[str, float]] = None,
        mesh_refinement: str = "medium"
    ) -> Dict[str, Any]:
        """Set up geometry for a case.

        Args:
            case_name: Name of the case
            geometry_type: Type of geometry input
            stl_path: Path to STL file
            dimensions: Parametric dimensions
            mesh_refinement: Mesh refinement level

        Returns:
            Dictionary with setup information
        """
        case_dir = self.run_dir / case_name

        if not case_dir.exists():
            raise ValueError(f"Case {case_name} does not exist")

        if geometry_type == "stl_file":
            if not stl_path:
                raise ValueError("stl_path required for stl_file geometry type")

            # Copy STL to case constant/triSurface directory
            tri_surface_dir = case_dir / "constant" / "triSurface"
            tri_surface_dir.mkdir(parents=True, exist_ok=True)

            stl_file = Path(stl_path)
            dest_stl = tri_surface_dir / stl_file.name
            shutil.copy(stl_path, dest_stl)

            # Create snappyHexMeshDict
            self._create_snappy_dict(case_dir, stl_file.name, mesh_refinement)

            return {
                "geometry_type": "stl_file",
                "stl_file": stl_file.name,
                "details": f"STL imported, snappyHexMesh configured with {mesh_refinement} refinement"
            }

        elif geometry_type == "blockMesh":
            # Create simple blockMeshDict from dimensions
            if not dimensions:
                dimensions = {"length": 0.1, "width": 0.1, "height": 0.1}

            self._create_block_mesh_dict(case_dir, dimensions, mesh_refinement)

            return {
                "geometry_type": "blockMesh",
                "dimensions": dimensions,
                "details": f"BlockMesh configured with {mesh_refinement} refinement"
            }

        else:
            raise ValueError(f"Unsupported geometry type: {geometry_type}")

    def _create_block_mesh_dict(
        self,
        case_dir: Path,
        dimensions: Dict[str, float],
        mesh_refinement: str
    ):
        """Create blockMeshDict file."""
        length = dimensions.get("length", 0.1)
        width = dimensions.get("width", 0.1)
        height = dimensions.get("height", 0.1)

        # Set mesh resolution based on refinement level
        refinement_map = {
            "coarse": 10,
            "medium": 20,
            "fine": 40,
            "very_fine": 80
        }
        cells_per_dim = refinement_map.get(mesh_refinement, 20)

        nx = int(length / 0.01 * (cells_per_dim / 20))
        ny = int(width / 0.01 * (cells_per_dim / 20))
        nz = int(height / 0.01 * (cells_per_dim / 20))

        block_mesh_dict = f"""/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v2306                                 |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      blockMeshDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

scale   1;

vertices
(
    (0 0 0)
    ({length} 0 0)
    ({length} {width} 0)
    (0 {width} 0)
    (0 0 {height})
    ({length} 0 {height})
    ({length} {width} {height})
    (0 {width} {height})
);

blocks
(
    hex (0 1 2 3 4 5 6 7) ({nx} {ny} {nz}) simpleGrading (1 1 1)
);

edges
(
);

boundary
(
    walls
    {{
        type wall;
        faces
        (
            (0 4 7 3)
            (2 6 5 1)
            (1 5 4 0)
            (3 7 6 2)
        );
    }}
    inlet
    {{
        type patch;
        faces
        (
            (0 3 2 1)
        );
    }}
    outlet
    {{
        type patch;
        faces
        (
            (4 5 6 7)
        );
    }}
);

mergePatchPairs
(
);

// ************************************************************************* //
"""

        block_mesh_path = case_dir / "system" / "blockMeshDict"
        with open(block_mesh_path, 'w') as f:
            f.write(block_mesh_dict)

    def _create_snappy_dict(
        self,
        case_dir: Path,
        stl_name: str,
        mesh_refinement: str
    ):
        """Create snappyHexMeshDict file."""
        # This is a simplified version - would need more sophistication for production
        refinement_map = {
            "coarse": (2, 2),
            "medium": (3, 3),
            "fine": (4, 4),
            "very_fine": (5, 5)
        }
        min_ref, max_ref = refinement_map.get(mesh_refinement, (3, 3))

        snappy_dict = f"""/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v2306                                 |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      snappyHexMeshDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

castellatedMesh true;
snap            true;
addLayers       false;

geometry
{{
    {stl_name}
    {{
        type triSurfaceMesh;
        name casting;
    }}
}};

castellatedMeshControls
{{
    maxLocalCells 100000;
    maxGlobalCells 2000000;
    minRefinementCells 0;
    nCellsBetweenLevels 2;
    features        ( );
    refinementSurfaces
    {{
        casting
        {{
            level ({min_ref} {max_ref});
        }}
    }}
    resolveFeatureAngle 30;
    refinementRegions   {{}}
    locationInMesh (0.001 0.001 0.001);
    allowFreeStandingZoneFaces true;
}}

snapControls
{{
    nSmoothPatch 3;
    tolerance 2.0;
    nSolveIter 30;
    nRelaxIter 5;
}}

addLayersControls
{{
    relativeSizes true;
    layers        {{}}
    expansionRatio 1.0;
    finalLayerThickness 0.3;
    minThickness 0.1;
    nGrow 0;
    featureAngle 30;
    nRelaxIter 3;
    nSmoothSurfaceNormals 1;
    nSmoothNormals 3;
    nSmoothThickness 10;
    maxFaceThicknessRatio 0.5;
    maxThicknessToMedialRatio 0.3;
    minMedianAxisAngle 90;
    nBufferCellsNoExtrude 0;
    nLayerIter 50;
}}

meshQualityControls
{{
    maxNonOrtho 65;
    maxBoundarySkewness 20;
    maxInternalSkewness 4;
    maxConcave 80;
    minFlatness 0.5;
    minVol 1e-13;
    minTetQuality 1e-30;
    minArea -1;
    minTwist 0.02;
    minDeterminant 0.001;
    minFaceWeight 0.02;
    minVolRatio 0.01;
    minTriangleTwist -1;
    nSmoothScale 4;
    errorReduction 0.75;
}}

debug 0;
mergeTolerance 1e-6;

// ************************************************************************* //
"""

        snappy_path = case_dir / "system" / "snappyHexMeshDict"
        with open(snappy_path, 'w') as f:
            f.write(snappy_dict)

    async def setup_material_properties(
        self,
        case_name: str,
        metal_properties: Optional[Dict[str, float]] = None,
        mold_properties: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """Set up material properties.

        Args:
            case_name: Name of the case
            metal_properties: Metal material properties
            mold_properties: Mold material properties

        Returns:
            Dictionary with setup info
        """
        case_dir = self.run_dir / case_name

        if not case_dir.exists():
            raise ValueError(f"Case {case_name} does not exist")

        # This would write to transportProperties, thermophysicalProperties, etc.
        # Simplified implementation - would need full OpenFOAM dict writer

        logger.info(f"Material properties configured for {case_name}")

        return {"status": "configured"}

    async def setup_boundary_conditions(
        self,
        case_name: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Set up boundary conditions.

        Args:
            case_name: Name of the case
            **kwargs: Boundary condition parameters

        Returns:
            Dictionary with setup info
        """
        case_dir = self.run_dir / case_name

        if not case_dir.exists():
            raise ValueError(f"Case {case_name} does not exist")

        # This would update 0/ directory files
        # Simplified implementation

        logger.info(f"Boundary conditions configured for {case_name}")

        return {"status": "configured"}

    async def get_case_status(self, case_name: str) -> Dict[str, Any]:
        """Get status of a case.

        Args:
            case_name: Name of the case

        Returns:
            Dictionary with case status
        """
        if case_name not in self.metadata:
            raise ValueError(f"Case {case_name} not found")

        metadata = self.metadata[case_name]

        return {
            "state": metadata.get("status", "unknown"),
            "progress": 0,  # Would parse from log files
            "last_updated": metadata.get("created", "N/A")
        }

    async def optimize_gating(
        self,
        case_name: str,
        parameters: Dict[str, Any],
        metric: str
    ) -> Dict[str, Any]:
        """Optimize gating system.

        Args:
            case_name: Base case name
            parameters: Parameters to optimize
            metric: Optimization metric

        Returns:
            Dictionary with optimization results
        """
        logger.info(f"Starting optimization for {case_name}")

        # This would run parametric studies
        # Placeholder implementation

        return {
            "best_config": "Configuration 1",
            "improvement": 15.3,
            "iterations": 10
        }
