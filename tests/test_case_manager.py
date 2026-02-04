"""Tests for CaseManager."""

import pytest
import tempfile
from pathlib import Path

from openfoam_mcp.api.case_manager import CaseManager


@pytest.fixture
def temp_run_dir():
    """Create temporary run directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def case_manager(temp_run_dir):
    """Create CaseManager with temporary directory."""
    return CaseManager(run_dir=temp_run_dir)


@pytest.mark.asyncio
async def test_create_case(case_manager, temp_run_dir):
    """Test creating a new case."""
    result = await case_manager.create_case(
        case_name="test_case",
        case_type="mold_filling",
        metal_type="aluminum",
        pouring_temperature=750,
        mold_material="sand"
    )

    assert result["name"] == "test_case"
    assert result["status"] == "created"
    assert Path(result["path"]).exists()

    # Check directory structure
    case_dir = Path(result["path"])
    assert (case_dir / "0").exists()
    assert (case_dir / "constant").exists()
    assert (case_dir / "system").exists()


@pytest.mark.asyncio
async def test_create_duplicate_case(case_manager):
    """Test that creating duplicate case raises error."""
    await case_manager.create_case(
        case_name="test_case",
        case_type="mold_filling",
        metal_type="aluminum",
        pouring_temperature=750
    )

    with pytest.raises(ValueError, match="already exists"):
        await case_manager.create_case(
            case_name="test_case",
            case_type="mold_filling",
            metal_type="steel",
            pouring_temperature=1650
        )


@pytest.mark.asyncio
async def test_list_cases(case_manager):
    """Test listing cases."""
    # Create multiple cases
    await case_manager.create_case(
        case_name="case1",
        case_type="mold_filling",
        metal_type="aluminum",
        pouring_temperature=750
    )

    await case_manager.create_case(
        case_name="case2",
        case_type="solidification",
        metal_type="steel",
        pouring_temperature=1650
    )

    # List all cases
    cases = await case_manager.list_cases()
    assert len(cases) == 2

    # Filter by type
    mold_filling_cases = await case_manager.list_cases(filter_type="mold_filling")
    assert len(mold_filling_cases) == 1
    assert mold_filling_cases[0]["name"] == "case1"


@pytest.mark.asyncio
async def test_setup_geometry_blockmesh(case_manager):
    """Test setting up blockMesh geometry."""
    await case_manager.create_case(
        case_name="test_case",
        case_type="mold_filling",
        metal_type="aluminum",
        pouring_temperature=750
    )

    result = await case_manager.setup_geometry(
        case_name="test_case",
        geometry_type="blockMesh",
        dimensions={"length": 0.2, "width": 0.15, "height": 0.1},
        mesh_refinement="medium"
    )

    assert result["geometry_type"] == "blockMesh"
    assert "medium" in result["details"]

    # Check blockMeshDict was created
    case_dir = case_manager.run_dir / "test_case"
    assert (case_dir / "system" / "blockMeshDict").exists()


@pytest.mark.asyncio
async def test_get_case_status(case_manager):
    """Test getting case status."""
    await case_manager.create_case(
        case_name="test_case",
        case_type="mold_filling",
        metal_type="aluminum",
        pouring_temperature=750
    )

    status = await case_manager.get_case_status("test_case")
    assert status["state"] == "created"
    assert "progress" in status


@pytest.mark.asyncio
async def test_get_nonexistent_case_status(case_manager):
    """Test getting status of non-existent case raises error."""
    with pytest.raises(ValueError, match="not found"):
        await case_manager.get_case_status("nonexistent_case")


def test_material_database(case_manager):
    """Test that material database contains expected materials."""
    from openfoam_mcp.builders.case_builder import CaseBuilder

    builder = CaseBuilder("mold_filling")

    # Check metals
    assert "steel" in builder.metal_database
    assert "aluminum" in builder.metal_database
    assert "iron" in builder.metal_database
    assert "copper" in builder.metal_database
    assert "bronze" in builder.metal_database

    # Check molds
    assert "sand" in builder.mold_database
    assert "ceramic" in builder.mold_database
    assert "metal" in builder.mold_database
    assert "graphite" in builder.mold_database

    # Verify properties exist
    steel_props = builder.metal_database["steel"]
    assert "density" in steel_props
    assert "viscosity" in steel_props
    assert "thermal_conductivity" in steel_props
    assert "liquidus_temp" in steel_props
