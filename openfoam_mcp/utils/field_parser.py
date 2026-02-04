"""OpenFOAM field file parser and utilities.

This module provides utilities for reading and parsing OpenFOAM field files
(both ASCII and binary formats) and extracting data for analysis.
"""

import re
import struct
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union
import numpy as np
from loguru import logger


class OpenFOAMFieldParser:
    """Parser for OpenFOAM field files."""

    def __init__(self, case_dir: Union[str, Path]):
        """Initialize parser.

        Args:
            case_dir: Path to OpenFOAM case directory
        """
        self.case_dir = Path(case_dir)

    def get_time_directories(self) -> List[float]:
        """Get all time directories in case.

        Returns:
            List of time values (sorted)
        """
        time_dirs = []

        for item in self.case_dir.iterdir():
            if item.is_dir():
                try:
                    # Try to convert directory name to float (time value)
                    time_val = float(item.name)
                    time_dirs.append(time_val)
                except ValueError:
                    # Not a time directory (e.g., '0.orig', 'constant', 'system')
                    continue

        return sorted(time_dirs)

    def get_latest_time(self) -> Optional[float]:
        """Get latest time in simulation.

        Returns:
            Latest time value or None if no time directories
        """
        times = self.get_time_directories()
        return times[-1] if times else None

    def read_scalar_field(self, field_name: str, time: Optional[float] = None) -> Dict[str, any]:
        """Read scalar field from OpenFOAM case.

        Args:
            field_name: Name of field (e.g., 'T', 'p', 'alpha.metal')
            time: Time directory to read from (uses latest if None)

        Returns:
            Dictionary with field data:
            {
                'internal_field': np.array of values,
                'boundary_field': dict of boundary conditions,
                'dimensions': field dimensions,
                'class': field class
            }
        """
        if time is None:
            time = self.get_latest_time()
            if time is None:
                raise ValueError("No time directories found in case")

        # Handle time formatting: OpenFOAM uses "0" for t=0, but keeps decimals for other times
        # Try to find the actual directory name
        time_str = str(int(time)) if time == 0.0 else str(time)
        field_path = self.case_dir / time_str / field_name

        # If not found, try alternative formatting
        if not field_path.exists() and time != 0.0:
            # Try without trailing .0
            if str(time).endswith('.0'):
                alt_time_str = str(int(time))
                alt_field_path = self.case_dir / alt_time_str / field_name
                if alt_field_path.exists():
                    field_path = alt_field_path
                    time_str = alt_time_str

        if not field_path.exists():
            raise FileNotFoundError(f"Field file not found: {field_path}")

        with open(field_path, 'r') as f:
            content = f.read()

        # Parse FoamFile header
        foam_file = self._parse_foam_file_header(content)

        # Check if it's a scalar field
        if 'volScalarField' not in foam_file.get('class', ''):
            logger.warning(f"Field {field_name} may not be scalar (class: {foam_file.get('class')})")

        # Parse dimensions
        dimensions = self._parse_dimensions(content)

        # Parse internal field
        internal_field = self._parse_internal_field(content)

        # Parse boundary field
        boundary_field = self._parse_boundary_field(content)

        return {
            'internal_field': internal_field,
            'boundary_field': boundary_field,
            'dimensions': dimensions,
            'class': foam_file.get('class', 'unknown'),
            'time': time
        }

    def read_vector_field(self, field_name: str, time: Optional[float] = None) -> Dict[str, any]:
        """Read vector field from OpenFOAM case.

        Args:
            field_name: Name of field (e.g., 'U')
            time: Time directory to read from

        Returns:
            Dictionary with field data (vectors as Nx3 array)
        """
        if time is None:
            time = self.get_latest_time()

        # Handle time formatting: OpenFOAM uses "0" for t=0, but keeps decimals for other times
        time_str = str(int(time)) if time == 0.0 else str(time)
        field_path = self.case_dir / time_str / field_name

        # If not found, try alternative formatting
        if not field_path.exists() and time != 0.0:
            if str(time).endswith('.0'):
                alt_time_str = str(int(time))
                alt_field_path = self.case_dir / alt_time_str / field_name
                if alt_field_path.exists():
                    field_path = alt_field_path

        with open(field_path, 'r') as f:
            content = f.read()

        foam_file = self._parse_foam_file_header(content)
        dimensions = self._parse_dimensions(content)

        # Parse internal field (vectors)
        internal_field = self._parse_vector_internal_field(content)
        boundary_field = self._parse_boundary_field(content)

        return {
            'internal_field': internal_field,
            'boundary_field': boundary_field,
            'dimensions': dimensions,
            'class': foam_file.get('class', 'unknown'),
            'time': time
        }

    def _parse_foam_file_header(self, content: str) -> Dict[str, str]:
        """Parse FoamFile dictionary."""
        foam_file = {}

        # Extract FoamFile block
        match = re.search(r'FoamFile\s*{([^}]*)}', content, re.DOTALL)
        if match:
            block = match.group(1)

            # Parse key-value pairs
            for line in block.split(';'):
                parts = line.strip().split(None, 1)
                if len(parts) == 2:
                    key, value = parts
                    foam_file[key] = value.strip()

        return foam_file

    def _parse_dimensions(self, content: str) -> List[int]:
        """Parse dimensions line."""
        match = re.search(r'dimensions\s*\[([^\]]+)\]', content)
        if match:
            dims_str = match.group(1)
            return [int(d) for d in dims_str.split()]
        return [0, 0, 0, 0, 0, 0, 0]

    def _parse_internal_field(self, content: str) -> np.ndarray:
        """Parse internalField for scalar values.

        Handles both 'uniform' and 'nonuniform' formats.
        """
        # Try uniform first
        match = re.search(r'internalField\s+uniform\s+([-+]?[\d.eE]+)', content)
        if match:
            value = float(match.group(1))
            # For uniform, we don't know the size, return single value
            return np.array([value])

        # Try nonuniform List<scalar>
        match = re.search(r'internalField\s+nonuniform\s+List<scalar>\s*\n(\d+)\s*\(\s*((?:[-+]?[\d.eE]+\s*)+)\)',
                         content, re.DOTALL)
        if match:
            size = int(match.group(1))
            values_str = match.group(2)
            values = [float(v) for v in values_str.split()]
            return np.array(values[:size])  # Take only 'size' values

        # Couldn't parse
        logger.warning("Could not parse internalField")
        return np.array([])

    def _parse_vector_internal_field(self, content: str) -> np.ndarray:
        """Parse internalField for vector values."""
        # Try uniform
        match = re.search(r'internalField\s+uniform\s+\(([-+\d.eE\s]+)\)', content)
        if match:
            values = [float(v) for v in match.group(1).split()]
            return np.array([values])

        # Try nonuniform List<vector>
        match = re.search(r'internalField\s+nonuniform\s+List<vector>\s*\n(\d+)\s*\(\s*(.*?)\s*\)',
                         content, re.DOTALL)
        if match:
            size = int(match.group(1))
            vectors_str = match.group(2)

            # Parse vectors
            vector_matches = re.findall(r'\(([-+\d.eE\s]+)\)', vectors_str)
            vectors = []
            for vm in vector_matches[:size]:
                values = [float(v) for v in vm.split()]
                vectors.append(values)

            return np.array(vectors)

        return np.array([])

    def _parse_boundary_field(self, content: str) -> Dict[str, Dict]:
        """Parse boundaryField dictionary."""
        boundary_field = {}

        # Find boundaryField block
        match = re.search(r'boundaryField\s*{(.*)}', content, re.DOTALL)
        if not match:
            return boundary_field

        block = match.group(1)

        # Find each patch
        patch_matches = re.finditer(r'(\w+)\s*{([^}]+)}', block)

        for patch_match in patch_matches:
            patch_name = patch_match.group(1)
            patch_content = patch_match.group(2)

            patch_data = {}

            # Parse type
            type_match = re.search(r'type\s+(\w+)', patch_content)
            if type_match:
                patch_data['type'] = type_match.group(1)

            # Parse value (if present)
            value_match = re.search(r'value\s+uniform\s+([-+\d.eE()\s]+)', patch_content)
            if value_match:
                patch_data['value'] = value_match.group(1)

            boundary_field[patch_name] = patch_data

        return boundary_field

    def get_cell_centers(self) -> np.ndarray:
        """Get cell center coordinates.

        Reads from constant/polyMesh/C file if available.

        Returns:
            Nx3 array of cell centers
        """
        c_file = self.case_dir / "constant" / "polyMesh" / "C"

        if not c_file.exists():
            # Try to generate with postProcess
            logger.warning("Cell centers file not found. Run 'postProcess -func writeCellCentres'")
            return np.array([])

        # Read C file (similar to vector field)
        with open(c_file, 'r') as f:
            content = f.read()

        return self._parse_vector_internal_field(content)

    def calculate_field_statistics(self, field_data: np.ndarray) -> Dict[str, float]:
        """Calculate statistics for a field.

        Args:
            field_data: Array of field values

        Returns:
            Dictionary with min, max, mean, std
        """
        if len(field_data) == 0:
            return {
                'min': 0.0,
                'max': 0.0,
                'mean': 0.0,
                'std': 0.0,
                'count': 0
            }

        return {
            'min': float(np.min(field_data)),
            'max': float(np.max(field_data)),
            'mean': float(np.mean(field_data)),
            'std': float(np.std(field_data)),
            'count': len(field_data)
        }

    def calculate_gradient(self, field_data: np.ndarray, cell_centers: Optional[np.ndarray] = None) -> np.ndarray:
        """Calculate gradient of scalar field.

        Args:
            field_data: Scalar field values
            cell_centers: Cell center coordinates (if None, uses simple finite difference)

        Returns:
            Gradient magnitude at each cell
        """
        if cell_centers is not None and len(cell_centers) == len(field_data):
            # Use actual geometry for gradient
            # This is simplified - real implementation would use face values
            gradient = np.gradient(field_data)
            return np.abs(gradient)
        else:
            # Simple finite difference
            return np.abs(np.gradient(field_data))
