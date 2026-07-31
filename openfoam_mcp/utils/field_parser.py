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

        content, raw = self._read_field_file(field_path)

        # Parse FoamFile header
        foam_file = self._parse_foam_file_header(content)
        is_binary = self._is_binary_format(foam_file)

        # Check if it's a scalar field
        if 'volScalarField' not in foam_file.get('class', ''):
            logger.warning(f"Field {field_name} may not be scalar (class: {foam_file.get('class')})")

        # Parse dimensions
        dimensions = self._parse_dimensions(content)

        # Parse internal field
        internal_field = self._parse_internal_field(content, raw if is_binary else None)

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

        if not field_path.exists():
            raise FileNotFoundError(f"Field file not found: {field_path}")

        content, raw = self._read_field_file(field_path)

        foam_file = self._parse_foam_file_header(content)
        is_binary = self._is_binary_format(foam_file)
        dimensions = self._parse_dimensions(content)

        # Parse internal field (vectors)
        internal_field = self._parse_vector_internal_field(content, raw if is_binary else None)
        boundary_field = self._parse_boundary_field(content)

        return {
            'internal_field': internal_field,
            'boundary_field': boundary_field,
            'dimensions': dimensions,
            'class': foam_file.get('class', 'unknown'),
            'time': time
        }

    def _read_field_file(self, field_path: Path) -> Tuple[str, bytes]:
        """Read a field file, returning both a text view and the raw bytes.

        OpenFOAM's default templates set writeFormat binary (see
        builders/templates.py), which packs the internalField/boundaryField
        numeric payload as raw IEEE-754 doubles rather than text -- opening
        in text mode and decoding as UTF-8 raises UnicodeDecodeError as soon
        as it hits one of those bytes. Every solidification-type case uses
        binary format, so this was never actually readable before.

        The file is always read as bytes, then decoded with latin-1, which
        maps every byte 0-255 to one character and can never raise --
        crucially, this keeps string index == byte index, so a regex match
        position found in the decoded text can be used directly to slice
        into `raw` for the binary payload. The FoamFile header, dimensions
        and boundaryField block are genuine ASCII/text in both formats, so
        parsing them via the same regexes as before is unaffected.
        """
        with open(field_path, 'rb') as f:
            raw = f.read()
        return raw.decode('latin-1'), raw

    def _is_binary_format(self, foam_file: Dict[str, str]) -> bool:
        return foam_file.get('format', '').strip().rstrip(';').strip() == 'binary'

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

    def _parse_internal_field(self, content: str, raw: Optional[bytes] = None) -> np.ndarray:
        """Parse internalField for scalar values.

        Handles 'uniform', 'nonuniform' ASCII, and 'nonuniform' binary
        (raw is the file's original bytes; only used when the FoamFile
        header said format binary -- see _read_field_file).
        """
        # Try uniform first
        match = re.search(r'internalField\s+uniform\s+([-+]?[\d.eE]+)', content)
        if match:
            value = float(match.group(1))
            # For uniform, we don't know the size, return single value
            return np.array([value])

        if raw is not None:
            match = re.search(r'internalField\s+nonuniform\s+List<scalar>\s*\n(\d+)\s*\n\(', content)
            if match:
                count = int(match.group(1))
                start = match.end()  # latin-1 char index == byte index
                data = raw[start:start + count * 8]
                if len(data) == count * 8:
                    return np.frombuffer(data, dtype='<f8', count=count).copy()
                logger.warning("Binary scalar internalField payload truncated")
                return np.array([])

        # Try nonuniform List<scalar> (ASCII)
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

    def _parse_vector_internal_field(self, content: str, raw: Optional[bytes] = None) -> np.ndarray:
        """Parse internalField for vector values.

        Handles 'uniform', 'nonuniform' ASCII, and 'nonuniform' binary (see
        _parse_internal_field / _read_field_file for the binary approach).
        """
        # Try uniform
        match = re.search(r'internalField\s+uniform\s+\(([-+\d.eE\s]+)\)', content)
        if match:
            values = [float(v) for v in match.group(1).split()]
            return np.array([values])

        if raw is not None:
            match = re.search(r'internalField\s+nonuniform\s+List<vector>\s*\n(\d+)\s*\n\(', content)
            if match:
                count = int(match.group(1))
                start = match.end()
                data = raw[start:start + count * 3 * 8]
                if len(data) == count * 3 * 8:
                    return np.frombuffer(data, dtype='<f8', count=count * 3).reshape(count, 3).copy()
                logger.warning("Binary vector internalField payload truncated")
                return np.array([])

        # Try nonuniform List<vector> (ASCII)
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

    def get_cell_centers(self, time: Optional[float] = None) -> np.ndarray:
        """Get cell center coordinates.

        `postProcess -func writeCellCentres` writes these as a regular
        volVectorField named 'C' into a time directory (there is no
        constant/polyMesh/C -- that path never exists, so this always
        returned an empty array before). Cell centers are static for these
        solvers (no mesh motion), so time 0 is enough once the function
        object has been run.

        Returns:
            Nx3 array of cell centers, or empty array if 'C' hasn't been
            written yet (run OpenFOAMClient.compute_cell_centers first).
        """
        try:
            return self.read_vector_field('C', time if time is not None else 0.0)['internal_field']
        except FileNotFoundError:
            logger.warning("Cell centers not found. Run 'postProcess -func writeCellCentres' first.")
            return np.array([])

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

    # NOTE: there used to be a calculate_gradient() here that called
    # np.gradient() on field_data directly. That treats the array as if
    # index i+1 were the physical neighbour of index i, but OpenFOAM cell
    # numbering after snappyHexMesh has no such relationship to space -- it
    # returned the difference between arbitrarily-adjacent cells, not a
    # spatial gradient. There is no way to fix that without the mesh
    # connectivity, so gradients are computed the correct way instead: via
    # OpenFOAM's own postProcess 'grad(<field>)' function object (see
    # OpenFOAMClient.compute_gradient), then read back with
    # read_vector_field exactly like any other field.
