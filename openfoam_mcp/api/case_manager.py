"""Case manager for creating and managing OpenFOAM cases."""

import os
import json
import shutil
import struct
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

            stl_file = Path(stl_path)
            if not stl_file.exists():
                raise ValueError(f"STL file not found: {stl_path}")

            # Parse geometry bounds/centroid in the STL's native units, used to
            # size the background mesh and pick a point outside the immersed
            # solid for snappyHexMesh's locationInMesh.
            raw_min, raw_max, _ = self._parse_stl_bounds_and_centroid(stl_file)
            raw_extent = [raw_max[i] - raw_min[i] for i in range(3)]
            max_extent = max(raw_extent)

            # Heuristic: real castings run centimeters to ~1m across. A
            # bounding box bigger than ~5 (native units) is almost certainly
            # millimeters, not meters, so convert to meters (this codebase's
            # templates assume SI/meters throughout).
            if max_extent > 5:
                scale = 0.001
                unit_note = "assumed millimeters (bounding box > 5 units) -> scaled to meters"
            else:
                scale = 1.0
                unit_note = "assumed already in meters"

            tri_surface_dir = case_dir / "constant" / "triSurface"
            tri_surface_dir.mkdir(parents=True, exist_ok=True)
            dest_stl = tri_surface_dir / stl_file.name
            self._write_scaled_stl(stl_file, dest_stl, scale)

            scaled_min = tuple(v * scale for v in raw_min)
            scaled_max = tuple(v * scale for v in raw_max)

            # Pad a background box around the (scaled) geometry so
            # snappyHexMesh has room to castellate/snap to the STL surface.
            # The STL is treated as a solid immersed in this box (matching
            # the walls/inlet/outlet boundary patches the 0/* field
            # templates expect), so locationInMesh must sit in the padding
            # gap, strictly outside the STL's own bounding box on every
            # axis -- guaranteeing it's outside the solid regardless of the
            # STL's shape/convexity.
            extent = [scaled_max[i] - scaled_min[i] for i in range(3)]
            pad = [max(e * 0.2, 0.01) for e in extent]
            box_min = tuple(scaled_min[i] - pad[i] for i in range(3))
            box_max = tuple(scaled_max[i] + pad[i] for i in range(3))
            location_in_mesh = tuple(box_min[i] + pad[i] / 2 for i in range(3))

            self._create_block_mesh_dict_from_bounds(case_dir, box_min, box_max, mesh_refinement)
            self._create_snappy_dict(case_dir, stl_file.name, mesh_refinement, location_in_mesh)

            return {
                "geometry_type": "stl_file",
                "stl_file": stl_file.name,
                "unit_scale": unit_note,
                "bounding_box_m": {"min": scaled_min, "max": scaled_max},
                "location_in_mesh_m": location_in_mesh,
                "details": (
                    f"STL imported ({unit_note}), background mesh + snappyHexMesh "
                    f"configured with {mesh_refinement} refinement"
                )
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

    def _is_binary_stl(self, stl_file: Path) -> bool:
        with open(stl_file, 'rb') as f:
            if not f.read(80).lstrip().lower().startswith(b'solid'):
                return True
            # An ASCII header is not conclusive: binary STLs may also start
            # with "solid". Confirm by checking the declared triangle count
            # against the actual file size (84 + 50 bytes per triangle).
            count_bytes = f.read(4)
            if len(count_bytes) < 4:
                return False
            n_tris = struct.unpack('<I', count_bytes)[0]
            return stl_file.stat().st_size == 84 + n_tris * 50

    def _parse_stl_bounds_and_centroid(self, stl_file: Path):
        """Return (min_xyz, max_xyz, centroid_xyz) of an STL in its native units."""
        mins = [float('inf')] * 3
        maxs = [float('-inf')] * 3
        total = [0.0, 0.0, 0.0]
        count = 0

        def accumulate(x, y, z):
            nonlocal count
            for i, v in enumerate((x, y, z)):
                if v < mins[i]:
                    mins[i] = v
                if v > maxs[i]:
                    maxs[i] = v
                total[i] += v
            count += 1

        if self._is_binary_stl(stl_file):
            with open(stl_file, 'rb') as f:
                f.seek(80)
                n_tris = struct.unpack('<I', f.read(4))[0]
                for _ in range(n_tris):
                    data = f.read(50)
                    if len(data) < 50:
                        break
                    vals = struct.unpack('<12fH', data)
                    for v in range(3):
                        accumulate(*vals[3 + v * 3: 6 + v * 3])
        else:
            with open(stl_file, 'r', errors='ignore') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) == 4 and parts[0] == 'vertex':
                        accumulate(float(parts[1]), float(parts[2]), float(parts[3]))

        if count == 0:
            raise ValueError(f"No vertices found in STL file: {stl_file}")

        centroid = tuple(t / count for t in total)
        return tuple(mins), tuple(maxs), centroid

    def _write_scaled_stl(self, src: Path, dest: Path, scale: float):
        """Copy an STL, scaling vertex coordinates by `scale`.

        OpenFOAM works in meters; CAD exports are usually millimeters.
        Scaling here (rather than via snappyHexMesh scaling knobs) keeps the
        copied STL, the background mesh, and locationInMesh in one unit system.
        """
        if scale == 1.0:
            shutil.copy(src, dest)
            return

        if self._is_binary_stl(src):
            with open(src, 'rb') as fin, open(dest, 'wb') as fout:
                header = fin.read(80)
                count_bytes = fin.read(4)
                fout.write(header)
                fout.write(count_bytes)
                n_tris = struct.unpack('<I', count_bytes)[0]
                for _ in range(n_tris):
                    data = fin.read(50)
                    if len(data) < 50:
                        break
                    vals = list(struct.unpack('<12fH', data))
                    # vals[0:3] is the unit normal - direction only, not scaled.
                    for i in range(3, 12):
                        vals[i] *= scale
                    fout.write(struct.pack('<12fH', *vals))
            return

        with open(src, 'r', errors='ignore') as fin, open(dest, 'w') as fout:
            for line in fin:
                parts = line.split()
                if len(parts) == 4 and parts[0] == 'vertex':
                    indent = line[:len(line) - len(line.lstrip())]
                    x, y, z = (float(p) * scale for p in parts[1:4])
                    fout.write(f"{indent}vertex {x:.6e} {y:.6e} {z:.6e}\n")
                else:
                    fout.write(line)

    def _create_block_mesh_dict_from_bounds(
        self,
        case_dir: Path,
        box_min,
        box_max,
        mesh_refinement: str
    ):
        """Create a background blockMeshDict spanning the given bounds."""
        dimensions = {
            "length": box_max[0] - box_min[0],
            "width": box_max[1] - box_min[1],
            "height": box_max[2] - box_min[2],
        }
        self._create_block_mesh_dict(case_dir, dimensions, mesh_refinement, origin=box_min)

    def _create_block_mesh_dict(
        self,
        case_dir: Path,
        dimensions: Dict[str, float],
        mesh_refinement: str,
        origin=(0.0, 0.0, 0.0)
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

        # Size cells off the largest dimension so the background mesh stays
        # roughly isotropic and the cell count stays bounded regardless of
        # how big the geometry is.
        largest = max(length, width, height)
        cell_size = largest / cells_per_dim
        nx = max(1, round(length / cell_size))
        ny = max(1, round(width / cell_size))
        nz = max(1, round(height / cell_size))

        x0, y0, z0 = origin
        x1, y1, z1 = x0 + length, y0 + width, z0 + height

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
    ({x0} {y0} {z0})
    ({x1} {y0} {z0})
    ({x1} {y1} {z0})
    ({x0} {y1} {z0})
    ({x0} {y0} {z1})
    ({x1} {y0} {z1})
    ({x1} {y1} {z1})
    ({x0} {y1} {z1})
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
        mesh_refinement: str,
        location_in_mesh=(0.001, 0.001, 0.001)
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
        loc_x, loc_y, loc_z = location_in_mesh

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
    "{stl_name}"
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
    locationInMesh ({loc_x} {loc_y} {loc_z});
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
            metal_properties: Metal material properties (density, specific_heat,
                            thermal_conductivity, viscosity, liquidus_temp, solidus_temp, latent_heat)
            mold_properties: Mold material properties (density, specific_heat, thermal_conductivity)

        Returns:
            Dictionary with setup info
        """
        case_dir = self.run_dir / case_name

        if not case_dir.exists():
            raise ValueError(f"Case {case_name} does not exist")

        updated_files = []

        # Update metal properties if provided
        if metal_properties:
            metal_props_file = case_dir / "constant" / "physicalProperties.metal"
            if metal_props_file.exists():
                with open(metal_props_file, 'r') as f:
                    content = f.read()

                # Update density
                if "density" in metal_properties:
                    content = self._update_dict_value(content, "rho", metal_properties["density"])

                # Update specific heat
                if "specific_heat" in metal_properties:
                    content = self._update_dict_value(content, "Cp", metal_properties["specific_heat"])

                # Update viscosity (dynamic)
                if "viscosity" in metal_properties:
                    content = self._update_dict_value(content, "mu", metal_properties["viscosity"])

                # Update thermal conductivity (if using const transport with Pr)
                # Note: For const transport with Pr, k = mu * Cp / Pr
                # OpenFOAM calculates k internally, so we just update mu and Pr

                with open(metal_props_file, 'w') as f:
                    f.write(content)
                updated_files.append("physicalProperties.metal")

        # Update mold/wall properties if provided
        # For thermal boundary conditions, this is typically handled via boundary conditions
        # rather than a separate mold properties file

        logger.info(f"Material properties configured for {case_name}: {updated_files}")

        return {
            "status": "configured",
            "files_updated": updated_files
        }

    def _update_dict_value(self, content: str, key: str, value: float) -> str:
        """Update a value in an OpenFOAM dictionary.

        Args:
            content: File content
            key: Dictionary key
            value: New value

        Returns:
            Updated content
        """
        import re
        # Pattern matches: key  value; (with flexible whitespace)
        pattern = rf'({key}\s+)[0-9.eE+-]+(\s*;)'
        replacement = rf'\g<1>{value}\g<2>'
        return re.sub(pattern, replacement, content)

    async def setup_boundary_conditions(
        self,
        case_name: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Set up boundary conditions.

        Args:
            case_name: Name of the case
            **kwargs: Boundary condition parameters (ALL TEMPERATURES IN KELVIN):
                - inlet_velocity: Inlet velocity (m/s)
                - inlet_temperature: Inlet temperature in KELVIN (OpenFOAM SI units)
                - mold_wall_temperature: Mold wall temperature in KELVIN (OpenFOAM SI units)
                - ambient_temperature: Ambient temperature in KELVIN (OpenFOAM SI units)
                - heat_transfer_coefficient: Wall heat transfer coefficient (W/m²K)

        Returns:
            Dictionary with setup info

        Note:
            All temperatures MUST be in Kelvin (OpenFOAM native SI units).
            No automatic Celsius-to-Kelvin conversion is performed.

            Common casting temperatures:
              - Room/ambient: 293-300 K (20-27°C)
              - Mold preheat: 373-573 K (100-300°C)
              - Aluminum pouring: 973-1073 K (700-800°C)
              - Steel pouring: 1773-1873 K (1500-1600°C)

            Values outside 200-3500 K are rejected with clear error messages.
        """
        case_dir = self.run_dir / case_name

        if not case_dir.exists():
            raise ValueError(f"Case {case_name} does not exist")

        updated_files = []
        import re

        # Validate temperature inputs (Kelvin only, no conversion)
        def validate_temperature(temp: float, name: str) -> float:
            """Validate temperature is in reasonable Kelvin range for casting."""
            if temp < 200:
                raise ValueError(
                    f"{name} = {temp} K is too low. "
                    f"Temperatures must be in Kelvin (not Celsius). "
                    f"Did you mean {temp + 273.15} K ({temp}°C)?"
                )
            if temp > 3500:
                raise ValueError(
                    f"{name} = {temp} K is unrealistically high for casting. "
                    f"Maximum is ~3500 K. Check units (must be Kelvin)."
                )
            return temp

        # Update velocity field (0/U)
        if "inlet_velocity" in kwargs:
            u_file = case_dir / "0" / "U"
            if u_file.exists():
                with open(u_file, 'r') as f:
                    content = f.read()

                # Update inlet velocity (assuming vertical inlet in z-direction)
                v = kwargs["inlet_velocity"]
                velocity_vec = f"(0 0 {v})"

                # Update inlet boundary condition
                content = self._update_boundary_value(content, "inlet", velocity_vec)

                with open(u_file, 'w') as f:
                    f.write(content)
                updated_files.append("0/U")

        # Update temperature field (0/T)
        if any(k in kwargs for k in ["inlet_temperature", "mold_wall_temperature", "ambient_temperature"]):
            t_file = case_dir / "0" / "T"
            if t_file.exists():
                with open(t_file, 'r') as f:
                    content = f.read()

                if "inlet_temperature" in kwargs:
                    T_inlet = validate_temperature(kwargs["inlet_temperature"], "inlet_temperature")
                    content = self._update_boundary_value(content, "inlet", T_inlet)

                if "mold_wall_temperature" in kwargs:
                    T_wall = validate_temperature(kwargs["mold_wall_temperature"], "mold_wall_temperature")
                    # Update wall boundary condition
                    content = self._update_boundary_value(content, "walls", T_wall)

                    # CRITICAL: Set internalField to mold temperature (domain starts at mold temp)
                    pattern = r'(internalField\s+uniform\s+)[0-9.eE+-]+(\s*;)'
                    content = re.sub(pattern, rf'\g<1>{T_wall}\g<2>', content)

                    # Update metal Tref to match mold temperature
                    # For hConst: h = Cp * (T - Tref) + Hf
                    # When domain starts at T_wall, Tref should be T_wall for sensible initial enthalpy
                    metal_path = case_dir / "constant" / "physicalProperties.metal"
                    if metal_path.exists():
                        with open(metal_path, 'r') as f:
                            metal_content = f.read()
                        metal_content = self._update_dict_value(metal_content, "Tref", T_wall)
                        with open(metal_path, 'w') as f:
                            f.write(metal_content)
                        if "constant/physicalProperties.metal" not in updated_files:
                            updated_files.append("constant/physicalProperties.metal")

                if "ambient_temperature" in kwargs:
                    T_ambient = validate_temperature(kwargs["ambient_temperature"], "ambient_temperature")

                    # Update gas Tref to ambient temperature
                    # Gas properties reference ambient conditions
                    gas_path = case_dir / "constant" / "physicalProperties.gas"
                    if gas_path.exists():
                        with open(gas_path, 'r') as f:
                            gas_content = f.read()
                        gas_content = self._update_dict_value(gas_content, "Tref", T_ambient)
                        with open(gas_path, 'w') as f:
                            f.write(gas_content)
                        if "constant/physicalProperties.gas" not in updated_files:
                            updated_files.append("constant/physicalProperties.gas")

                with open(t_file, 'w') as f:
                    f.write(content)
                updated_files.append("0/T")

        # Update heat transfer coefficient if specified (would need mixed BC type)
        if "heat_transfer_coefficient" in kwargs:
            # This would require changing BC type to mixed or externalWallHeatFluxTemperature
            # Skipping for now as it requires more complex BC modification
            logger.warning("heat_transfer_coefficient specified but requires mixed BC type - not implemented yet")

        logger.info(f"Boundary conditions configured for {case_name}: {updated_files}")

        return {
            "status": "configured",
            "files_updated": updated_files
        }

    def _update_boundary_value(self, content: str, patch_name: str, value) -> str:
        """Update a boundary condition value for a specific patch.

        Args:
            content: File content
            patch_name: Name of the patch (e.g., "inlet", "walls")
            value: New value (can be scalar or vector string)

        Returns:
            Updated content
        """
        import re

        # Find the patch section
        patch_pattern = rf'({patch_name}\s*\{{[^}}]*?value\s+uniform\s+)([^;]+)(;)'

        def replace_value(match):
            return f"{match.group(1)}{value}{match.group(3)}"

        return re.sub(patch_pattern, replace_value, content, flags=re.DOTALL)

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
