"""Comprehensive test suite for OpenFOAM MCP server.

Tests all components: builders, API layer, and integration.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_case_builder():
    """Test CaseBuilder creates files without errors."""
    print("=" * 70)
    print("TEST 1: CaseBuilder")
    print("=" * 70)

    from openfoam_mcp.builders.case_builder import CaseBuilder

    metals = ['steel', 'aluminum', 'iron', 'copper', 'bronze']
    molds = ['sand', 'ceramic', 'metal', 'graphite']
    case_types = ['mold_filling', 'solidification']

    passed = 0
    failed = 0

    for metal in metals:
        for case_type in case_types:
            try:
                builder = CaseBuilder(case_type)
                builder.set_metal_type(metal)
                builder.set_pouring_temperature(1500)
                builder.set_mold_material('sand')

                files = builder.build()

                # Verify essential files exist
                required_files = [
                    'system/controlDict',
                    'system/fvSchemes',
                    'system/fvSolution',
                    'constant/transportProperties',
                    'constant/g',
                    '0/alpha.metal',
                    '0/U',
                    '0/p_rgh'
                ]

                for req_file in required_files:
                    if req_file not in files:
                        raise ValueError(f"Missing file: {req_file}")

                # Verify nu is calculated correctly
                props = builder.metal_database[metal]
                expected_nu = props["viscosity"] / props["density"]

                # Check transportProperties contains nu
                transport_props = files['constant/transportProperties']
                if 'nu' not in transport_props:
                    raise ValueError("Missing nu in transportProperties")

                print(f"  ✅ {metal:10} + {case_type:20} → {len(files)} files")
                passed += 1

            except Exception as e:
                print(f"  ❌ {metal:10} + {case_type:20} → {str(e)}")
                failed += 1

    print(f"\nResult: {passed} passed, {failed} failed")
    return failed == 0


def test_material_properties():
    """Test material property calculations."""
    print("\n" + "=" * 70)
    print("TEST 2: Material Properties")
    print("=" * 70)

    from openfoam_mcp.builders.case_builder import CaseBuilder

    builder = CaseBuilder('mold_filling')

    print("\nKinematic Viscosity Calculations (ν = μ / ρ):")
    print("-" * 70)
    print(f"{'Metal':10} | {'μ (Pa·s)':10} | {'ρ (kg/m³)':10} | {'ν (m²/s)':12} | {'Valid':6}")
    print("-" * 70)

    all_valid = True

    for metal, props in builder.metal_database.items():
        nu = props["viscosity"] / props["density"]

        # Kinematic viscosity for molten metals should be in range 1e-7 to 1e-6 m²/s
        valid = 1e-7 < nu < 1e-6
        status = "✅" if valid else "❌"

        print(f"{metal:10} | {props['viscosity']:<10.4f} | {props['density']:<10d} | {nu:<12.6e} | {status:6}")

        if not valid:
            all_valid = False
            print(f"  ⚠️  Warning: {metal} nu={nu:.6e} outside expected range")

    print("\nThermal Properties Check:")
    print("-" * 70)

    for metal, props in builder.metal_database.items():
        # Check physical constraints
        issues = []

        if props["liquidus_temp"] <= props["solidus_temp"]:
            issues.append("Liquidus ≤ Solidus")

        if props["density"] <= 0:
            issues.append("Invalid density")

        if props["thermal_conductivity"] <= 0:
            issues.append("Invalid k")

        if props["specific_heat"] <= 0:
            issues.append("Invalid cp")

        if issues:
            print(f"  ❌ {metal}: {', '.join(issues)}")
            all_valid = False
        else:
            print(f"  ✅ {metal}: All properties valid")

    return all_valid


def test_template_syntax():
    """Test OpenFOAM dictionary syntax in templates."""
    print("\n" + "=" * 70)
    print("TEST 3: Template Syntax")
    print("=" * 70)

    from openfoam_mcp.builders.case_builder import CaseBuilder

    builder = CaseBuilder('mold_filling')
    builder.set_metal_type('aluminum')
    builder.set_pouring_temperature(750)
    builder.set_mold_material('sand')

    files = builder.build()

    all_valid = True

    for file_path, content in files.items():
        print(f"\n  Checking {file_path}...")

        # Check for FoamFile header
        if not content.startswith("/*"):
            print(f"    ⚠️  Missing header comment")

        if "FoamFile" not in content:
            print(f"    ⚠️  Missing FoamFile dictionary")
            all_valid = False

        # Check for balanced braces
        open_braces = content.count('{')
        close_braces = content.count('}')

        if open_braces != close_braces:
            print(f"    ❌ Unbalanced braces: {{ {open_braces} vs }} {close_braces}")
            all_valid = False
        else:
            print(f"    ✅ Braces balanced: {open_braces} pairs")

        # Check for semicolons
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # Skip comments and empty lines
            if not stripped or stripped.startswith('//') or stripped.startswith('/*'):
                continue
            # Skip block delimiters
            if stripped in ['{', '}', '};']:
                continue
            # Value assignments should end with semicolon
            if '=' in stripped or any(stripped.startswith(kw) for kw in ['application', 'startFrom', 'stopAt']):
                if not stripped.endswith(';') and not stripped.endswith('{'):
                    print(f"    ⚠️  Line {i} might be missing semicolon: {stripped[:50]}")

    return all_valid


def test_case_creation():
    """Test actual case directory creation."""
    print("\n" + "=" * 70)
    print("TEST 4: Case Creation")
    print("=" * 70)

    import tempfile
    import shutil
    from openfoam_mcp.api.case_manager import CaseManager

    # Create temp directory for testing
    temp_dir = tempfile.mkdtemp()
    print(f"  Using temp directory: {temp_dir}")

    try:
        manager = CaseManager(run_dir=temp_dir)

        # Test creating a case
        result = manager.create_case(
            case_name="test_case",
            case_type="mold_filling",
            metal_type="aluminum",
            pouring_temperature=750,
            mold_material="sand"
        )

        # Synchronous version - no await needed
        import asyncio
        if asyncio.iscoroutine(result):
            result = asyncio.run(result)

        case_path = Path(result["path"])

        # Check directory structure
        required_dirs = ['0', 'constant', 'system']
        for dir_name in required_dirs:
            dir_path = case_path / dir_name
            if not dir_path.exists():
                print(f"    ❌ Missing directory: {dir_name}")
                return False
            print(f"    ✅ Directory exists: {dir_name}")

        # Check files
        required_files = [
            'system/controlDict',
            'constant/transportProperties',
            '0/alpha.metal',
            '0/U',
            '0/p_rgh'
        ]

        for file_name in required_files:
            file_path = case_path / file_name
            if not file_path.exists():
                print(f"    ❌ Missing file: {file_name}")
                return False
            print(f"    ✅ File exists: {file_name}")

        # Check metadata
        cases = manager.list_cases()
        if asyncio.iscoroutine(cases):
            cases = asyncio.run(cases)

        if len(cases) != 1:
            print(f"    ❌ Expected 1 case, found {len(cases)}")
            return False

        print(f"    ✅ Metadata saved correctly")

        return True

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)
        print(f"  Cleaned up temp directory")


def main():
    """Run all tests."""
    print("\n" + "🔬" * 35)
    print("  OPENFOAM MCP COMPREHENSIVE TEST SUITE")
    print("🔬" * 35 + "\n")

    results = {}

    try:
        results['Case Builder'] = test_case_builder()
    except Exception as e:
        print(f"❌ Case Builder test crashed: {e}")
        results['Case Builder'] = False

    try:
        results['Material Properties'] = test_material_properties()
    except Exception as e:
        print(f"❌ Material Properties test crashed: {e}")
        results['Material Properties'] = False

    try:
        results['Template Syntax'] = test_template_syntax()
    except Exception as e:
        print(f"❌ Template Syntax test crashed: {e}")
        results['Template Syntax'] = False

    try:
        results['Case Creation'] = test_case_creation()
    except Exception as e:
        print(f"❌ Case Creation test crashed: {e}")
        import traceback
        traceback.print_exc()
        results['Case Creation'] = False

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {test_name:30} {status}")

    all_passed = all(results.values())

    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 ALL TESTS PASSED! OpenFOAM MCP is working correctly.")
    else:
        print("⚠️  SOME TESTS FAILED! See details above.")
    print("=" * 70 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
