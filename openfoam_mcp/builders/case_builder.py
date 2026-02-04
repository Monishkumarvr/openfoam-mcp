"""Case builder for creating OpenFOAM case templates."""

from typing import Dict, Any
from .templates import MOLD_FILLING_TEMPLATE, SOLIDIFICATION_TEMPLATE


class CaseBuilder:
    """Builder for OpenFOAM casting simulation cases."""

    def __init__(self, case_type: str):
        """Initialize case builder.

        Args:
            case_type: Type of casting simulation
        """
        self.case_type = case_type
        self.metal_type = None
        self.pouring_temperature = None
        self.mold_material = None

        # Material properties database
        self.metal_database = {
            "steel": {
                "density": 7800,
                "viscosity": 0.006,
                "thermal_conductivity": 30,
                "specific_heat": 600,
                "liquidus_temp": 1809,
                "solidus_temp": 1673,
                "latent_heat": 270000
            },
            "aluminum": {
                "density": 2700,
                "viscosity": 0.0013,
                "thermal_conductivity": 200,
                "specific_heat": 900,
                "liquidus_temp": 933,
                "solidus_temp": 821,
                "latent_heat": 397000
            },
            "iron": {
                "density": 7200,
                "viscosity": 0.005,
                "thermal_conductivity": 35,
                "specific_heat": 540,
                "liquidus_temp": 1811,
                "solidus_temp": 1422,
                "latent_heat": 247000
            },
            "copper": {
                "density": 8940,
                "viscosity": 0.004,
                "thermal_conductivity": 380,
                "specific_heat": 385,
                "liquidus_temp": 1358,
                "solidus_temp": 1358,
                "latent_heat": 205000
            },
            "bronze": {
                "density": 8800,
                "viscosity": 0.0045,
                "thermal_conductivity": 120,
                "specific_heat": 380,
                "liquidus_temp": 1223,
                "solidus_temp": 1093,
                "latent_heat": 180000
            }
        }

        self.mold_database = {
            "sand": {
                "density": 1600,
                "thermal_conductivity": 1.0,
                "specific_heat": 1000
            },
            "ceramic": {
                "density": 2000,
                "thermal_conductivity": 1.5,
                "specific_heat": 900
            },
            "metal": {
                "density": 7800,
                "thermal_conductivity": 50,
                "specific_heat": 500
            },
            "graphite": {
                "density": 2200,
                "thermal_conductivity": 150,
                "specific_heat": 700
            }
        }

    def set_metal_type(self, metal_type: str):
        """Set metal type."""
        self.metal_type = metal_type

    def set_pouring_temperature(self, temperature: float):
        """Set pouring temperature in Celsius."""
        self.pouring_temperature = temperature

    def set_mold_material(self, material: str):
        """Set mold material."""
        self.mold_material = material

    def build(self) -> Dict[str, str]:
        """Build case files.

        Returns:
            Dictionary mapping file paths to content
        """
        files = {}

        # Get material properties
        metal_props = self.metal_database.get(self.metal_type, self.metal_database["steel"])
        mold_props = self.mold_database.get(self.mold_material, self.mold_database["sand"])

        # Select template based on case type
        if self.case_type == "mold_filling":
            template = MOLD_FILLING_TEMPLATE
        elif self.case_type == "solidification":
            template = SOLIDIFICATION_TEMPLATE
        elif self.case_type == "continuous_casting":
            template = SOLIDIFICATION_TEMPLATE  # Would have dedicated template
        elif self.case_type == "die_casting":
            template = MOLD_FILLING_TEMPLATE  # Would have dedicated template
        else:
            template = MOLD_FILLING_TEMPLATE

        # Generate files from template
        for file_path, content_template in template.items():
            content = content_template.format(
                metal_density=metal_props["density"],
                metal_viscosity=metal_props["viscosity"],
                metal_k=metal_props["thermal_conductivity"],
                metal_cp=metal_props["specific_heat"],
                liquidus_temp=metal_props["liquidus_temp"],
                solidus_temp=metal_props["solidus_temp"],
                latent_heat=metal_props["latent_heat"],
                pouring_temp=self.pouring_temperature + 273.15,  # Convert to Kelvin
                mold_density=mold_props["density"],
                mold_k=mold_props["thermal_conductivity"],
                mold_cp=mold_props["specific_heat"],
                ambient_temp=300
            )
            files[file_path] = content

        return files
